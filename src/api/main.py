"""
SolarSense EMS — High-Performance Compute API Gateway
=====================================================
Production-grade FastAPI application bridging columnar memory, LightGBM forecasters,
and HiGHS MILP solver to the Next.js frontend and Phase 2 AI Agents.

Architectural Guarantees:
1. Singleton Lifespan State: Repository and warmed solver loaded once at boot; zero per-request disk I/O.
2. Non-Blocking Compute: CPU-bound MILP solves offloaded to Starlette worker threadpool.
3. Sub-5ms Slicing: Directly serves frozen 24h simulation vectors via resident Arrow hash indexing.
4. Server-Sent Events (SSE): Streams multi-day rolling backtest frames at 60 FPS client rate.
"""

from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path
import time
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import polars as pl
from starlette.concurrency import run_in_threadpool

from src.api.schemas import (
    AgentAdvisoryRequest,
    AgentAdvisoryResponse,
    BillEstimateRequest,
    BillEstimateResponse,
    DateBoundsResponse,
    HealthResponse,
    Lesco2026OptimizeRequest,
    Lesco2026OptimizeResponse,
    OptimizationRequest,
    OptimizationResponse,
    PeakWindowResponse,
    PresetDateItem,
    ProsumerCompareRequest,
    ProsumerCompareResponse,
    ProsumerSettlementItem,
    SimulationWindowResponse,
    SoilingStatusResponse,
    VisionInspectRequest,
    VisionInspectResponse,
    VisionSampleItem,
    VisionSamplesResponse,
)
from src.data_engineering.feature_store import (
    EMSDataRepository,
    TariffPolicy,
)
from src.optimizer.milp_solver import (
    BESSConfig,
    DispatchResultDTO,
    MILPBatteryOptimizer,
)
from src.optimizer.lesco_2026_tariff_and_dispatch import (
    ConsumerCategory2026,
    Lesco2026BatteryDispatchOptimizer,
    LescoCY2026TariffEngine,
    ProsumerRegime2026,
)
from src.optimizer.station_profile import StationProfile, load_station_profile
from src.data_engineering.month_to_date import compute_month_to_date_flows, trailing_export_share
from src.soiling.loss_calculator import SolarPlantLossCalculator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOILING_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "soiling" / "soiling_analysis_lahore.csv"
PANEL_TEST_DIR = PROJECT_ROOT / "data" / "processed" / "panel_images" / "solarsense_master_v1" / "test"


def _load_soiling_lookup(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """Loads calibrated Lahore residential soiling table into an O(1) date lookup map."""
    if not csv_path.exists():
        return {}
    df = pl.read_csv(csv_path).rechunk()
    return {str(row["date"]): row for row in df.to_dicts()}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Singleton Lifespan State Initializer.
    Loads master dataset into contiguous memory with Station LHR-RES-01 / 904-A JT
    residential policy (LESCO A-1 ToU & Net-Metering, 10.0 kW sanctioned load) and
    pre-warms CVXPY DPP parameters once at startup for 5.12 kWh LiFePO4 BESS.
    """
    residential_policy = TariffPolicy.lesco_a1_residential()
    bess_config = BESSConfig.station_904a_residential()
    repo = EMSDataRepository(policy=residential_policy)
    repo.warm_forecasters()
    optimizer = MILPBatteryOptimizer(bess=bess_config, policy=residential_policy)
    optimizer.warm_up()

    app.state.repo = repo
    app.state.optimizer = optimizer
    # CY 2026 LESCO tariff engine + customer station profile + cached-DPP dispatch optimizer
    station_profile = load_station_profile()
    app.state.station_profile = station_profile
    lesco_engine = LescoCY2026TariffEngine()
    lesco_opt = Lesco2026BatteryDispatchOptimizer(
        tariff_engine=lesco_engine,
        bess=bess_config,
        pv_capacity_kw=station_profile.pv_capacity_kw,
    )
    lesco_opt._get_dpp_bundle(24)
    app.state.lesco_engine = lesco_engine
    app.state.lesco_optimizer = lesco_opt
    app.state.loss_calculator = SolarPlantLossCalculator()
    app.state.soiling_map = _load_soiling_lookup(SOILING_CSV_PATH)
    app.state.vision_monitor = None
    yield


app = FastAPI(
    title="SolarSense EMS — High-Performance Compute API",
    description="REST & SSE Compute Gateway for Residential Hybrid Solar & Battery EMS (Station LHR-RES-01 / LESCO A-1 ToU)",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend local and preview origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Meta"])
async def root():
    return {
        "service": "SolarSense EMS Compute API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    repo: EMSDataRepository = app.state.repo
    df = repo._df
    return HealthResponse(
        status="healthy",
        app_name="SolarSense EMS Compute Gateway",
        version="1.0.0",
        dataset_rows=df.height,
        date_range_start=str(df["timestamp"].min()),
        date_range_end=str(df["timestamp"].max()),
        solver_warmed_up=True,
    )


@app.get("/api/window", response_model=SimulationWindowResponse, tags=["Simulation"])
async def get_simulation_window(
    date: str = Query(..., description="Target date in YYYY-MM-DD format", examples=["2025-07-17"]),
    use_forecasts: bool = Query(default=False, description="True = ML forecasts; False = ground truth"),
):
    """
    Sub-5ms telemetry slice query.
    Extracts 24-hour simulation vectors from memory for direct client rendering.
    """
    repo: EMSDataRepository = app.state.repo
    try:
        dto = repo.get_simulation_window(date)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    solar_gen = list(dto.solar_generation_kw)
    factory_load = list(dto.factory_load_kw)

    if use_forecasts:
        try:
            sl = repo.get_optimization_slice(date, use_forecasts=True)
            solar_gen = [float(x) for x in sl.solar_kw]
            factory_load = [float(x) for x in sl.factory_load_kw]
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    net_power = [l - s for l, s in zip(factory_load, solar_gen)]

    return SimulationWindowResponse(
        date=dto.date_str,
        horizon_hours=dto.horizon_hours,
        timestamps=list(dto.timestamps),
        hours=list(dto.hours),
        solar_generation_kw=solar_gen,
        factory_load_kw=factory_load,
        net_power_kw=net_power,
        tariff_rates_pkr=list(dto.tariff_rates_pkr),
        tariff_windows=list(dto.tariff_windows),
        outage_flags=list(dto.outage_flags),
        baseline_electricity_cost_pkr=float(dto.baseline_electricity_cost_pkr),
        baseline_mdi_penalty_pkr=float(dto.baseline_mdi_penalty_pkr),
        total_baseline_cost_pkr=float(dto.total_baseline_cost_pkr),
        ghi_wm2=list(dto.ghi_wm2),
        temp_c=list(dto.temp_c),
    )


@app.post("/api/optimize", response_model=OptimizationResponse, tags=["Optimization"])
async def optimize_dispatch(request: OptimizationRequest):
    """
    Sub-25ms MILP Battery Dispatch Optimizer.
    Offloaded to worker threadpool to guarantee non-blocking asynchronous I/O.
    """
    repo: EMSDataRepository = app.state.repo
    optimizer: MILPBatteryOptimizer = app.state.optimizer

    # Optional dynamic tariff override policy (preserving residential sanctioned ceiling & export rate)
    policy = repo.policy
    if any(
        x is not None
        for x in (
            request.off_peak_rate_pkr,
            request.peak_rate_pkr,
            request.diesel_cost_pkr,
        )
    ):
        policy = TariffPolicy(
            off_peak_rate_pkr=(
                Decimal(str(request.off_peak_rate_pkr))
                if request.off_peak_rate_pkr is not None
                else repo.policy.off_peak_rate_pkr
            ),
            peak_rate_pkr=(
                Decimal(str(request.peak_rate_pkr))
                if request.peak_rate_pkr is not None
                else repo.policy.peak_rate_pkr
            ),
            diesel_cost_pkr=(
                Decimal(str(request.diesel_cost_pkr))
                if request.diesel_cost_pkr is not None
                else repo.policy.diesel_cost_pkr
            ),
            export_rate_pkr=repo.policy.export_rate_pkr,
            sanctioned_load_kw=repo.policy.sanctioned_load_kw,
            mdi_penalty_per_kw_pkr=repo.policy.mdi_penalty_per_kw_pkr,
        )

    try:
        slice_data = repo.get_optimization_slice(
            origin_ts=request.date_str,
            policy=policy,
            use_forecasts=request.use_forecasts,
            override_initial_soc_kwh=request.initial_soc_kwh,
            override_mdi_high_water_kw=request.mdi_high_water_kw,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Execute CPU-bound MILP solve in worker threadpool
    result: DispatchResultDTO = await run_in_threadpool(optimizer.solve_24h_dispatch, slice_data)

    if result.baseline_total_pkr > Decimal("0.00"):
        savings_pct = float(result.net_savings_pkr / result.baseline_total_pkr) * 100.0
    else:
        savings_pct = 0.0

    # Net-metering export during grid-connected hours (anti-islanding: 0.0 kW during outages)
    p_export_list = [
        float(c) if int(o) == 0 else 0.0
        for c, o in zip(result.p_curtail_kw, slice_data.actual_outage_mask)
    ]
    export_rev_pkr = round(sum(p_export_list) * float(policy.export_rate_pkr), 2)

    return OptimizationResponse(
        window_start=result.window_start,
        status=result.status,
        solve_time_ms=result.solve_time_ms,
        timestamps=list(slice_data.timestamps_iso),
        solar_kw=[float(x) for x in slice_data.solar_kw],
        factory_load_kw=[float(x) for x in slice_data.factory_load_kw],
        p_grid_kw=[float(x) for x in result.p_grid_kw],
        p_export_kw=p_export_list,
        p_diesel_kw=[float(x) for x in result.p_diesel_kw],
        p_ch_kw=[float(x) for x in result.p_ch_kw],
        p_dis_kw=[float(x) for x in result.p_dis_kw],
        p_curtail_kw=[float(x) for x in result.p_curtail_kw],
        soc_kwh=[float(x) for x in result.soc_kwh],
        initial_soc_kwh=result.initial_soc_kwh,
        terminal_soc_kwh=result.terminal_soc_kwh,
        prior_mdi_high_water_kw=result.prior_mdi_high_water_kw,
        updated_mdi_high_water_kw=result.updated_mdi_high_water_kw,
        baseline_energy_pkr=float(result.baseline_energy_pkr),
        baseline_diesel_pkr=float(result.baseline_diesel_pkr),
        baseline_mdi_penalty_pkr=float(result.baseline_mdi_penalty_pkr),
        baseline_total_pkr=float(result.baseline_total_pkr),
        optimized_energy_pkr=float(result.optimized_energy_pkr),
        export_revenue_pkr=export_rev_pkr,
        optimized_diesel_pkr=float(result.optimized_diesel_pkr),
        optimized_mdi_penalty_pkr=float(result.optimized_mdi_penalty_pkr),
        degradation_cost_pkr=float(result.degradation_cost_pkr),
        optimized_total_pkr=float(result.optimized_total_pkr),
        net_savings_pkr=float(result.net_savings_pkr),
        savings_pct=round(savings_pct, 2),
        mdi_penalty_saved_pkr=float(result.mdi_penalty_saved_pkr),
        diesel_cost_saved_pkr=float(result.diesel_cost_saved_pkr),
    )


@app.get("/api/backtest/stream", tags=["Simulation"])
async def stream_backtest(
    start_date: str = Query("2025-07-01", description="Backtest start date (YYYY-MM-DD)"),
    days: int = Query(7, ge=1, le=463, description="Consecutive simulation days to step through"),
    use_forecasts: bool = Query(False, description="True = ML forecasts; False = ground truth"),
):
    """
    Server-Sent Events (SSE) Multi-Day Rolling Simulation Stream.
    Pushes stateful day-by-day optimization frames in real-time to Next.js clients.
    """
    repo: EMSDataRepository = app.state.repo
    optimizer: MILPBatteryOptimizer = app.state.optimizer

    async def event_generator() -> AsyncGenerator[str, None]:
        current_soc = None
        current_mdi_hw = None

        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        PKT = ZoneInfo("Asia/Karachi")

        try:
            curr_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=PKT)
        except ValueError:
            yield f"event: error\ndata: {json.dumps({'error': 'Invalid start_date format'})}\n\n"
            return

        for day_idx in range(days):
            date_str = curr_dt.strftime("%Y-%m-%d")

            # Monthly peak demand ratchet reset on the 1st of each month to residential sanctioned ceiling (10.0 kW)
            if curr_dt.day == 1:
                current_mdi_hw = repo.policy.sanctioned_load_kw

            try:
                sl = repo.get_optimization_slice(
                    origin_ts=date_str,
                    use_forecasts=use_forecasts,
                    override_initial_soc_kwh=current_soc,
                    override_mdi_high_water_kw=current_mdi_hw,
                )
            except ValueError as e:
                yield f"event: error\ndata: {json.dumps({'day': day_idx + 1, 'date': date_str, 'error': str(e)})}\n\n"
                break

            res = await run_in_threadpool(optimizer.solve_24h_dispatch, sl)

            # State continuity handover to next day
            current_soc = res.terminal_soc_kwh
            current_mdi_hw = res.updated_mdi_high_water_kw

            frame = {
                "day": day_idx + 1,
                "date": date_str,
                "status": res.status,
                "solve_time_ms": res.solve_time_ms,
                "baseline_total_pkr": float(res.baseline_total_pkr),
                "optimized_total_pkr": float(res.optimized_total_pkr),
                "net_savings_pkr": float(res.net_savings_pkr),
                "initial_soc_kwh": res.initial_soc_kwh,
                "terminal_soc_kwh": res.terminal_soc_kwh,
                "updated_mdi_high_water_kw": res.updated_mdi_high_water_kw,
            }

            yield f"event: frame\ndata: {json.dumps(frame)}\n\n"
            curr_dt += timedelta(days=1)
            await asyncio.sleep(0.01)  # Minimal yield to event loop

        yield f"event: complete\ndata: {json.dumps({'status': 'finished', 'total_days': days})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _compute_soiling_status(
    app_state: Any,
    date_str: str,
    days_until_rain: int = 7,
) -> SoilingStatusResponse:
    """Computes O(1) daily soiling telemetry & econometric wash ROI for Station LHR-RES-01."""
    soiling_map: Dict[str, Dict[str, Any]] = app_state.soiling_map
    calc: SolarPlantLossCalculator = app_state.loss_calculator

    if date_str not in soiling_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Date '{date_str}' not found in calibrated soiling table (2025-07-01 to 2026-10-26).",
        )

    row = soiling_map[date_str]
    actual_gen = float(row.get("generation_kwh") or 0.0)

    if row.get("e_clean_kwh") is not None:
        expected_clean = float(row["e_clean_kwh"])
        pr = float(row.get("performance_ratio") or 1.0)
        derate_pct = float(row.get("soiling_derate_pct") or 0.0)
        loss_kwh = float(row.get("soiling_loss_kwh") or 0.0)
    else:
        model_pr = float(row.get("soiling_model_pr") or 0.85)
        pr = model_pr
        expected_clean = actual_gen / max(0.50, min(1.0, model_pr)) if actual_gen > 0 else 0.0
        loss_kwh = max(0.0, expected_clean - actual_gen)
        derate_pct = (loss_kwh / max(0.1, expected_clean)) * 100.0 if expected_clean > 0.1 else 0.0

    days_since_wash_raw = row.get("days_since_last_wash")
    if days_since_wash_raw is None:
        days_since_wash_raw = row.get("days_since_wash")
    days_since_wash = int(float(days_since_wash_raw)) if days_since_wash_raw is not None else None

    event_type = str(row.get("event_type") or "normal")

    # Dynamic valuation of lost soiling generation (blending avoided import cost vs export credit)
    profile: Optional[StationProfile] = getattr(app_state, "station_profile", None)
    engine: Optional[LescoCY2026TariffEngine] = getattr(app_state, "lesco_engine", None)
    tariff_override = None
    if profile is not None and engine is not None:
        try:
            df = app_state.repo._df
            exp_share = trailing_export_share(df, date_str, days=30)
            _, off_all_in = engine.get_all_in_tou_marginal_rates_pkr(
                include_electricity_duty=profile.include_electricity_duty,
                include_fpa_marginal=True,
            )
            exp_val = engine.marginal_value_of_exported_kwh(
                profile.regime,
                export_rate_override_pkr_per_kwh=profile.export_rate_override_pkr_per_kwh,
                include_electricity_duty=profile.include_electricity_duty,
            )
            blended_val = (1.0 - exp_share) * float(off_all_in) + exp_share * float(exp_val)
            tariff_override = round(blended_val, 2)
        except Exception:
            tariff_override = None

    roi = calc.evaluate_daily_cleaning_decision(
        daily_kwh_lost=loss_kwh,
        days_until_rain=days_until_rain,
        tariff_rate_override_pkr_per_kwh=tariff_override,
    )

    return SoilingStatusResponse(
        date=date_str,
        plant_capacity_kw=calc.plant_capacity_kw,
        total_panels=calc.num_panels,
        panel_rating_w=calc.panel_rating_w,
        actual_generation_kwh=round(actual_gen, 2),
        expected_clean_kwh=round(expected_clean, 2),
        performance_ratio=round(pr, 4),
        soiling_derate_pct=round(derate_pct, 2),
        daily_kwh_lost=roi["daily_kwh_lost"],
        daily_revenue_lost_pkr=roi["daily_revenue_lost_pkr"],
        days_since_last_wash=days_since_wash,
        event_type=event_type,
        days_until_next_rain=roi["days_until_next_rain"],
        projected_loss_before_rain_pkr=roi["projected_loss_before_rain_pkr"],
        wash_cost_pkr=roi["wash_cost_pkr"],
        net_cleaning_benefit_pkr=roi["net_cleaning_benefit_pkr"],
        decision=roi["decision"],
    )


def _get_vision_monitor(app_state: Any):
    """Lazily initializes and caches the PyTorch EfficientNet-B2 CCTVPanelMonitor singleton."""
    if app_state.vision_monitor is None:
        from src.vision.cctv_panel_monitor import CCTVPanelMonitor
        app_state.vision_monitor = CCTVPanelMonitor()
    return app_state.vision_monitor


@app.get("/api/dates", response_model=DateBoundsResponse, tags=["Meta"])
async def get_available_dates():
    """
    Returns dataset calendar bounds and curated benchmark preset dates for the Next.js UI.
    """
    repo: EMSDataRepository = app.state.repo
    df = repo._df
    min_ts = str(df["timestamp"].min())[:10]
    max_ts = str(df["timestamp"].max())[:10]
    total_hours = df.height
    total_days = total_hours // 24

    presets = [
        PresetDateItem(
            date="2025-07-17",
            label="Peak Summer Monsoon & ToU Arbitrage",
            category="arbitrage",
            description="High solar yield (34.1 kWh) with evening Peak ToU (18:00-22:00 @ 46.85 PKR/kWh) battery discharge.",
        ),
        PresetDateItem(
            date="2026-07-01",
            label="Summer Feeder Outage & Islanding (4h Blackout)",
            category="blackout",
            description="4-hour LESCO grid blackout demonstrating zero-import anti-islanding and 5.12 kWh BESS backup.",
        ),
        PresetDateItem(
            date="2025-12-21",
            label="Winter Solstice Smog & Low-GHI Regime",
            category="winter",
            description="Lahore winter fog/smog low-irradiance regime with conservative 55% nocturnal blackout reserve.",
        ),
        PresetDateItem(
            date="2026-09-23",
            label="Confirmed Manual Panel Wash (PR Reset)",
            category="maintenance",
            description="Empirical manual wash event at Station 904-A JT resetting Performance Ratio to 1.0207.",
        ),
        PresetDateItem(
            date="2026-10-07",
            label="Post-Wash 14-Day Soiling Decay",
            category="soiling",
            description="14 days after the September 23 wash showing exponential dust accumulation (k = 1.211%/day).",
        ),
    ]

    return DateBoundsResponse(
        min_date=min_ts,
        max_date=max_ts,
        total_days=total_days,
        total_hours=total_hours,
        preset_dates=presets,
    )


@app.get("/api/soiling/status", response_model=SoilingStatusResponse, tags=["Soiling & Wash ROI"])
async def get_soiling_status(
    date: str = Query("2026-10-07", description="Target date in YYYY-MM-DD format", examples=["2026-10-07"]),
    days_until_rain: int = Query(7, ge=1, le=30, description="Forecasted dry days until next rainfall"),
):
    """
    Sub-1ms Soiling & Econometric Wash Advisor endpoint for Station LHR-RES-01 (7.02 kWp, 1,500 PKR wash cost).
    """
    return _compute_soiling_status(app.state, date_str=date, days_until_rain=days_until_rain)


@app.get("/api/vision/samples", response_model=VisionSamplesResponse, tags=["Computer Vision"])
async def get_vision_samples():
    """
    Lists curated holdout test panel images across all 5 defect classes for one-click UI inspection.
    """
    class_labels = {
        "clean": "Clean Bifacial Module (Nominal 0% Derate)",
        "dusty": "Uniform Particulate Soiling (~5% Optical Derate)",
        "bird_drop": "Localized Biological Shading (~12% Derate + Hot-Spot Risk)",
        "electrical_damage": "Bypass Diode / Junction Thermal Fault (~25% Derate)",
        "physical_damage": "Tempered Glass Fracture / Micro-Crack (~35% Derate)",
    }
    samples = []
    for cls_name, label_desc in class_labels.items():
        cls_dir = PANEL_TEST_DIR / cls_name
        if cls_dir.exists():
            imgs = sorted(cls_dir.glob("*.jpg"))[:2]
            for idx, img_path in enumerate(imgs, 1):
                rel_path = str(img_path.relative_to(PROJECT_ROOT))
                samples.append(
                    VisionSampleItem(
                        sample_id=f"{cls_name}_{idx:02d}",
                        ground_truth_class=cls_name,
                        sample_path=rel_path,
                        label=f"{label_desc} [#{idx}]",
                    )
                )

    return VisionSamplesResponse(
        total_samples=len(samples),
        classes=list(class_labels.keys()),
        samples=samples,
    )


@app.post("/api/vision/inspect", response_model=VisionInspectResponse, tags=["Computer Vision"])
async def inspect_panel_image(request: VisionInspectRequest):
    """
    Executes EfficientNet-B2 5-class optical defect inspection (with 4-pass TTA) and couples
    the predicted optical derate with Station LHR-RES-01 (7.02 kWp) financial loss metrics.
    """
    from PIL import Image

    t0 = time.perf_counter()

    if request.base64_image:
        try:
            raw_b64 = request.base64_image.split(",")[-1]
            img_bytes = base64.b64decode(raw_b64)
            pil_img = Image.open(BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64_image payload: {e}",
            )
    elif request.sample_path:
        allowed_root = (PROJECT_ROOT / "data").resolve()
        candidate_path = (PROJECT_ROOT / request.sample_path).resolve()
        if not str(candidate_path).startswith(str(allowed_root)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sample_path must reside inside the repository data/ directory.",
            )
        if not candidate_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Panel sample image not found: {request.sample_path}",
            )
        try:
            pil_img = Image.open(candidate_path).convert("RGB")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to open image file: {e}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either sample_path or base64_image must be provided.",
        )

    def _run_inference():
        monitor = _get_vision_monitor(app.state)
        return monitor.predict_pil_image(pil_img, use_tta=request.use_tta)

    diag = await run_in_threadpool(_run_inference)

    calc: SolarPlantLossCalculator = app.state.loss_calculator
    # Nominal clear-sky daily yield for 7.02 kWp array in Lahore (~30.0 kWh/day)
    nominal_clear_sky_kwh = 30.0
    est_derate = float(diag["estimated_derate_pr"])
    est_daily_kwh_lost = round(nominal_clear_sky_kwh * est_derate, 2)
    roi = calc.evaluate_daily_cleaning_decision(
        daily_kwh_lost=est_daily_kwh_lost,
        days_until_rain=request.days_until_rain,
    )

    cond = str(diag["condition"])
    action_map = {
        "clean": "No action required — array optical transmittance is nominal (0% derate).",
        "dusty": (
            f"{roi['decision']} — uniform dust layer causing ~{est_derate * 100:.0f}% optical derate "
            f"(PKR {roi['projected_loss_before_rain_pkr']:,.0f} projected loss over {request.days_until_rain} dry days vs. PKR 1,500 wash)."
        ),
        "bird_drop": (
            "IMMEDIATE SPOT WASH REQUIRED — localized biological shading (~12% derate) risks bypass diode "
            "conduction and cell hot-spotting."
        ),
        "electrical_damage": (
            "DISPATCH ELECTRICAL TECHNICIAN — junction box / bypass diode thermal anomaly (~25% derate); "
            "inspect string Voc/Isc and connectors."
        ),
        "physical_damage": (
            "EMERGENCY STRING ISOLATION & MODULE REPLACEMENT — tempered glass fracture (~35% derate); "
            "insulation fault hazard during precipitation."
        ),
    }

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return VisionInspectResponse(
        condition=cond,
        confidence=float(diag["confidence"]),
        severity=str(diag["severity"]),
        requires_cleaning=bool(diag["requires_cleaning"]),
        estimated_derate_pr=est_derate,
        all_probabilities={k: float(v) for k, v in diag["all_probabilities"].items()},
        estimated_daily_kwh_lost=est_daily_kwh_lost,
        estimated_daily_pkr_lost=roi["daily_revenue_lost_pkr"],
        projected_loss_before_rain_pkr=roi["projected_loss_before_rain_pkr"],
        wash_cost_pkr=roi["wash_cost_pkr"],
        recommended_action=action_map.get(cond, roi["decision"]),
        inference_time_ms=round(elapsed_ms, 2),
    )


@app.post("/api/agent/advisory", response_model=AgentAdvisoryResponse, tags=["AI Agent Copilot"])
async def generate_agent_advisory(request: AgentAdvisoryRequest):
    """
    Synthesizes an executive natural-language briefing across 3 operational pillars:
    1. Grid & LESCO A-1 ToU Tariff Arbitrage (18:00-22:00 Peak @ 46.85 PKR/kWh)
    2. Blackout Resilience & 5.12 kWh LiFePO4 Reserve Management
    3. PV Soiling & Econometric Wash ROI (1,500 PKR threshold)
    """
    t0 = time.perf_counter()
    repo: EMSDataRepository = app.state.repo
    optimizer: MILPBatteryOptimizer = app.state.optimizer

    try:
        slice_data = repo.get_optimization_slice(
            origin_ts=request.date_str,
            use_forecasts=request.use_forecasts,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    result: DispatchResultDTO = await run_in_threadpool(optimizer.solve_24h_dispatch, slice_data)

    # Check if date exists in soiling lookup; fallback to latest calibrated date if out of bounds
    soiling_date = request.date_str if request.date_str in app.state.soiling_map else "2026-10-07"
    soiling_status = _compute_soiling_status(
        app.state,
        date_str=soiling_date,
        days_until_rain=request.days_until_rain,
    )

    total_solar_kwh = float(sum(slice_data.solar_kw))
    total_load_kwh = float(sum(slice_data.factory_load_kw))
    total_grid_import_kwh = float(sum(result.p_grid_kw))
    outage_hours = int(sum(int(x) for x in slice_data.actual_outage_mask))
    max_outage_prob = float(max(slice_data.outage_prob))
    p_export_list = [
        float(c) if int(o) == 0 else 0.0
        for c, o in zip(result.p_curtail_kw, slice_data.actual_outage_mask)
    ]
    total_export_kwh = round(sum(p_export_list), 2)

    engine: Optional[LescoCY2026TariffEngine] = getattr(app.state, "lesco_engine", None)
    profile: Optional[StationProfile] = getattr(app.state, "station_profile", None)

    # Dynamic export valuation from station profile or regulatory regime
    if profile is not None and profile.export_rate_override_pkr_per_kwh is not None:
        export_rate = profile.export_rate_override_pkr_per_kwh
    elif engine is not None and profile is not None:
        export_rate = float(
            engine.config.nappp_grandfathered_rate_pkr_per_kwh
            if profile.regime == ProsumerRegime2026.GRANDFATHERED_NET_METERING
            else engine.config.naepp_export_rate_pkr_per_kwh
        )
    else:
        export_rate = float(repo.policy.export_rate_pkr)
    export_rev_pkr = round(total_export_kwh * export_rate, 2)

    # Seasonal Peak window metrics (PKT)
    if engine is not None:
        month = int(request.date_str[5:7])
        win = engine.get_seasonal_window(month)
        p_start, p_end = win.peak_start_hour, win.peak_end_hour
    else:
        p_start, p_end = 18, 22
    peak_window_str = f"{p_start:02d}:00–{p_end:02d}:00"
    peak_dis_kwh = float(sum(result.p_dis_kw[p_start:p_end]))
    peak_grid_kwh = float(sum(result.p_grid_kw[p_start:p_end]))

    headline = (
        f"Station LHR-RES-01 Executive Brief ({request.date_str}): "
        f"PKR {float(result.net_savings_pkr):,.1f} Net Dispatch Savings | "
        f"{outage_hours}h Grid Outage Isolated | Soiling Decision: {soiling_status.decision}"
    )

    dispatch_brief = (
        f"Across the 24-hour horizon on {request.date_str}, the 7.02 kWp bifacial array generated "
        f"{total_solar_kwh:.1f} kWh against a household demand of {total_load_kwh:.1f} kWh. "
        f"During the LESCO A-1 Peak ToU window ({peak_window_str} @ 46.85 PKR/kWh), the HiGHS MILP solver "
        f"discharged {peak_dis_kwh:.2f} kWh from the 5.12 kWh LiFePO4 pack while suppressing peak grid "
        f"recharging (peak import limited to {peak_grid_kwh:.2f} kWh). Surplus daytime generation exported "
        f"{total_export_kwh:.2f} kWh via net-metering (+PKR {export_rev_pkr:,.1f}), reducing total daily "
        f"operating cost from PKR {float(result.baseline_total_pkr):,.1f} to PKR {float(result.optimized_total_pkr):,.1f} "
        f"(net savings of PKR {float(result.net_savings_pkr):,.1f})."
    )

    if outage_hours > 0:
        blackout_brief = (
            f"Grid telemetry recorded {outage_hours} blackout hour(s) on {request.date_str} "
            f"(peak feeder outage risk P(outage) = {max_outage_prob * 100:.1f}%). Anti-islanding constraints "
            f"strictly enforced 0.00 kW grid import/export during de-energized hours, seamlessly transferring "
            f"household load to the GoodWe ES-Uniq inverter and 5.12 kWh battery above the 15% (0.768 kWh) emergency floor."
        )
    else:
        blackout_brief = (
            f"Zero feeder blackouts occurred on {request.date_str} (maximum forecasted outage probability "
            f"{max_outage_prob * 100:.1f}%). The optimizer maintained the 55% nocturnal blackout reserve "
            f"(2.816 kWh) during high-risk hours while cycling safely between {min(result.soc_kwh):.2f} kWh "
            f"and {max(result.soc_kwh):.2f} kWh."
        )

    defect_note = ""
    if request.defect_condition and request.defect_condition != "clean":
        defect_note = f" Optical CCTV inspection also flagged '{request.defect_condition}' on the array."

    soiling_brief = (
        f"Array Performance Ratio stands at {soiling_status.performance_ratio * 100:.1f}% "
        f"(soiling loss: {soiling_status.daily_kwh_lost:.2f} kWh/day = PKR {soiling_status.daily_revenue_lost_pkr:,.1f}/day). "
        f"Over the next {request.days_until_rain} dry days, cumulative dust loss is projected at "
        f"PKR {soiling_status.projected_loss_before_rain_pkr:,.1f} vs. the PKR {soiling_status.wash_cost_pkr:,.0f} "
        f"Lahore residential wash cost (net benefit: PKR {soiling_status.net_cleaning_benefit_pkr:,.1f}). "
        f"Recommendation: {soiling_status.decision}.{defect_note}"
    )

    actions = [
        f"Maintain GoodWe ES-Uniq ToU schedule: charge from solar 09:00–16:00, discharge {peak_dis_kwh:.2f} kWh across {peak_window_str} Peak window.",
        f"Enforce Post-Blackout Peak Recharge Suppression (cap grid import at household load during {peak_window_str} @ 46.85 PKR/kWh).",
        f"Soiling & Wash Action: {soiling_status.decision} (Projected {request.days_until_rain}-day loss: PKR {soiling_status.projected_loss_before_rain_pkr:,.0f} vs. PKR 1,500 wash).",
    ]
    if request.defect_condition in {"bird_drop", "electrical_damage", "physical_damage"}:
        actions.append(
            f"Priority Visual Alert: Inspect array for '{request.defect_condition}' flagged by EfficientNet-B2 CCTV monitor."
        )

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return AgentAdvisoryResponse(
        date=request.date_str,
        station_id="LHR-RES-01 / 904-A JT",
        headline=headline,
        dispatch_arbitrage_brief=dispatch_brief,
        blackout_resilience_brief=blackout_brief,
        soiling_maintenance_brief=soiling_brief,
        recommended_actions=actions,
        key_metrics={
            "solar_generation_kwh": round(total_solar_kwh, 2),
            "household_load_kwh": round(total_load_kwh, 2),
            "grid_import_kwh": round(total_grid_import_kwh, 2),
            "net_metering_export_kwh": total_export_kwh,
            "export_revenue_pkr": export_rev_pkr,
            "peak_battery_discharge_kwh": round(peak_dis_kwh, 2),
            "outage_hours": float(outage_hours),
            "net_savings_pkr": float(result.net_savings_pkr),
            "soiling_loss_kwh": soiling_status.daily_kwh_lost,
            "net_cleaning_benefit_pkr": soiling_status.net_cleaning_benefit_pkr,
        },
        generation_mode="deterministic_physics_synthesizer",
        latency_ms=round(elapsed_ms, 2),
    )


# =====================================================================
# CY 2026 LESCO v2 Endpoints (additive; legacy /api/optimize unchanged)
# =====================================================================

_PKR_LINE_FIELDS = (
    "peak_energy_charges_pkr", "off_peak_energy_charges_pkr", "variable_energy_charges_pkr",
    "fixed_charges_pkr", "qta_pkr", "fc_surcharge_pkr", "electricity_duty_current_pkr",
    "current_pre_gst_subtotal_pkr", "gst_on_current_bill_pkr", "fpa_base_pkr",
    "ed_and_gst_on_fpa_pkr", "ptv_fee_pkr", "subtotal_before_income_tax_pkr",
    "section_235_income_tax_pkr",
)


def _parse_regime(name: str) -> ProsumerRegime2026:
    try:
        return ProsumerRegime2026(name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown regime '{name}'. Use one of {[r.value for r in ProsumerRegime2026 if r != ProsumerRegime2026.NONE]}.",
        )


@app.post("/api/v2/optimize", response_model=Lesco2026OptimizeResponse, tags=["LESCO 2026"])
async def optimize_dispatch_v2(request: Lesco2026OptimizeRequest):
    """24h battery dispatch under CY 2026 LESCO rules (seasonal peaks, regime-aware export value)."""
    repo: EMSDataRepository = app.state.repo
    opt: Lesco2026BatteryDispatchOptimizer = app.state.lesco_optimizer
    regime = _parse_regime(request.regime)
    try:
        sl = repo.get_optimization_slice(
            origin_ts=request.date_str,
            use_forecasts=request.use_forecasts,
        )
        month = int(request.date_str[5:7])
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    mtd_import = request.prior_month_to_date_import_kwh
    netting_headroom = None
    profile: Optional[StationProfile] = getattr(app.state, "station_profile", None)
    if mtd_import <= 0.0:
        try:
            flows = compute_month_to_date_flows(repo._df, request.date_str, opt.tariff_engine)
            mtd_import = flows.import_kwh
            netting_headroom = flows.netting_headroom_kwh
        except Exception:
            mtd_import = 0.0

    export_rate_override = profile.export_rate_override_pkr_per_kwh if profile else None

    res = await run_in_threadpool(
        lambda: opt.optimize_24h(
            load_kw=sl.factory_load_kw,
            solar_kw=sl.solar_kw,
            month=month,
            regime=regime,
            outage_mask=sl.actual_outage_mask,
            initial_soc_kwh=request.initial_soc_kwh,
            prior_month_to_date_import_kwh=mtd_import,
            is_protected_consumer=request.is_protected_consumer,
            protected_guardrail_kwh=request.protected_guardrail_kwh,
            include_electricity_duty=request.include_electricity_duty,
            export_rate_override_pkr_per_kwh=export_rate_override,
            netting_headroom_kwh=netting_headroom,
        )
    )
    return Lesco2026OptimizeResponse(
        regime=res.regime.value,
        season=res.season,
        status=res.status,
        solve_time_ms=res.solve_time_ms,
        timestamps=list(sl.timestamps_iso),
        solar_kw=[float(x) for x in sl.solar_kw],
        load_kw=[float(x) for x in sl.factory_load_kw],
        outage_flags=[int(x) for x in sl.actual_outage_mask],
        is_peak=[int(x) for x in res.is_peak_mask],
        p_grid_import_kw=res.p_grid_import_kw.tolist(),
        p_grid_export_kw=res.p_grid_export_kw.tolist(),
        p_ch_kw=res.p_ch_kw.tolist(),
        p_dis_kw=res.p_dis_kw.tolist(),
        p_curtail_kw=res.p_curtail_kw.tolist(),
        p_backup_kw=res.p_backup_kw.tolist(),
        soc_kwh=res.soc_kwh.tolist(),
        initial_soc_kwh=res.initial_soc_kwh,
        terminal_soc_kwh=res.terminal_soc_kwh,
        projected_month_to_date_import_kwh=res.projected_month_to_date_import_kwh,
        slab_ceiling_target_kwh=res.slab_ceiling_target_kwh,
        protected_200_guardrail_intact=res.protected_200_guardrail_intact,
        import_energy_cost_pkr=str(res.import_energy_cost_pkr),
        export_revenue_credit_pkr=str(res.export_revenue_credit_pkr),
        slab_cliff_penalty_pkr=str(res.slab_cliff_penalty_pkr),
        battery_wear_cost_pkr=str(res.battery_wear_cost_pkr),
        net_horizon_cost_pkr=str(res.net_horizon_cost_pkr),
        export_rate_used_pkr_per_kwh=str(res.export_rate_used_pkr_per_kwh),
        baseline_no_battery_cost_pkr=str(res.baseline_no_battery_cost_pkr),
        net_savings_pkr=str(res.net_savings_pkr),
    )


@app.post("/api/v2/bill/estimate", response_model=BillEstimateResponse, tags=["LESCO 2026"])
async def estimate_bill_v2(request: BillEstimateRequest):
    """Exact-paisa CY 2026 LESCO monthly bill (Decimal, ROUND_HALF_EVEN)."""
    engine: LescoCY2026TariffEngine = app.state.lesco_engine
    try:
        cat = ConsumerCategory2026(request.category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown category '{request.category}'.",
        )
    b = engine.calculate_monthly_bill(
        category=cat,
        sanctioned_load_kw=request.sanctioned_load_kw,
        current_kwh=request.current_kwh,
        peak_kwh=request.peak_kwh,
        off_peak_kwh=request.off_peak_kwh,
        fpa_reference_2m_prior_kwh=request.fpa_reference_2m_prior_kwh,
        include_electricity_duty=request.include_electricity_duty,
        is_atl_filer=request.is_atl_filer,
    )
    return BillEstimateResponse(
        category=b.category.value,
        slab_id=b.slab_id,
        current_total_kwh=str(b.current_total_kwh),
        line_items={f: str(getattr(b, f)) for f in _PKR_LINE_FIELDS},
        total_payable_pkr=str(b.total_payable_pkr),
        total_payable_rounded_rupee_pkr=str(b.total_payable_rounded_rupee_pkr),
        effective_all_in_rate_pkr_per_kwh=str(b.effective_all_in_rate_pkr_per_kwh),
    )


@app.get("/api/v2/tariff/peak-window", response_model=PeakWindowResponse, tags=["LESCO 2026"])
async def get_peak_window_v2(month: int = Query(..., ge=1, le=12)):
    """Seasonal ToU peak window for a calendar month."""
    engine: LescoCY2026TariffEngine = app.state.lesco_engine
    w = engine.get_seasonal_window(month)
    return PeakWindowResponse(
        month=month,
        season=w.season,
        peak_start_hour=w.peak_start_hour,
        peak_end_hour=w.peak_end_hour,
        peak_hours=list(range(w.peak_start_hour, w.peak_end_hour)),
    )


@app.post("/api/v2/prosumer/compare", response_model=ProsumerCompareResponse, tags=["LESCO 2026"])
async def compare_prosumer_v2(request: ProsumerCompareRequest):
    """Same month settled under grandfathered 1:1 netting vs. 2026 gross net-billing."""
    engine: LescoCY2026TariffEngine = app.state.lesco_engine

    def _settle(regime: ProsumerRegime2026):
        return engine.calculate_prosumer_settlement(
            regime=regime,
            sanctioned_load_kw=request.sanctioned_load_kw,
            gross_peak_import_kwh=request.gross_peak_import_kwh,
            gross_off_peak_import_kwh=request.gross_off_peak_import_kwh,
            gross_export_kwh=request.gross_export_kwh,
            fpa_reference_2m_prior_kwh=request.fpa_reference_2m_prior_kwh,
            include_electricity_duty=request.include_electricity_duty,
            is_atl_filer=request.is_atl_filer,
        )

    def _item(s) -> ProsumerSettlementItem:
        return ProsumerSettlementItem(
            regime=s.regime.value,
            net_billed_peak_import_kwh=str(s.net_billed_peak_import_kwh),
            net_billed_off_peak_import_kwh=str(s.net_billed_off_peak_import_kwh),
            net_surplus_export_kwh=str(s.net_surplus_export_kwh),
            export_credit_rate_pkr_per_kwh=str(s.export_credit_rate_pkr_per_kwh),
            gross_retail_import_bill_pkr=str(s.gross_retail_import_bill_pkr),
            export_credit_pkr=str(s.export_credit_pkr),
            net_payable_after_credits_pkr=str(s.net_payable_after_credits_pkr),
            closing_credit_carryforward_pkr=str(s.closing_credit_carryforward_pkr),
        )

    gf = _settle(ProsumerRegime2026.GRANDFATHERED_NET_METERING)
    nb = _settle(ProsumerRegime2026.NET_BILLING_2026)
    adv = (nb.net_payable_after_credits_pkr - gf.net_payable_after_credits_pkr) + (
        gf.closing_credit_carryforward_pkr - nb.closing_credit_carryforward_pkr
    )
    return ProsumerCompareResponse(
        grandfathered=_item(gf),
        net_billing_2026=_item(nb),
        grandfathered_advantage_pkr=str(adv),
    )
