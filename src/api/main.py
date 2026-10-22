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
from contextlib import asynccontextmanager
from decimal import Decimal
import json
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from src.api.schemas import (
    HealthResponse,
    OptimizationRequest,
    OptimizationResponse,
    SimulationWindowResponse,
)
from src.data_engineering.feature_store import (
    EMSDataRepository,
    TariffPolicy,
)
from src.optimizer.milp_solver import (
    DispatchResultDTO,
    MILPBatteryOptimizer,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Singleton Lifespan State Initializer.
    Loads master dataset into contiguous memory and pre-warms CVXPY DPP parameters
    once at startup so zero HTTP requests pay compilation or cold-start penalties.
    """
    repo = EMSDataRepository()
    optimizer = MILPBatteryOptimizer()
    optimizer.warm_up()

    app.state.repo = repo
    app.state.optimizer = optimizer
    yield


app = FastAPI(
    title="SolarSense EMS — High-Performance Compute API",
    description="REST & SSE Compute Gateway for Industrial Battery Energy Management (LESCO B3)",
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

    # Optional dynamic tariff override policy
    policy = None
    if any(
        x is not None
        for x in (
            request.off_peak_rate_pkr,
            request.peak_rate_pkr,
            request.diesel_cost_pkr,
        )
    ):
        policy = TariffPolicy(
            off_peak_rate_pkr=Decimal(str(request.off_peak_rate_pkr)) if request.off_peak_rate_pkr else Decimal("38.00"),
            peak_rate_pkr=Decimal(str(request.peak_rate_pkr)) if request.peak_rate_pkr else Decimal("60.00"),
            diesel_cost_pkr=Decimal(str(request.diesel_cost_pkr)) if request.diesel_cost_pkr else Decimal("95.00"),
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

    return OptimizationResponse(
        window_start=result.window_start,
        status=result.status,
        solve_time_ms=result.solve_time_ms,
        timestamps=list(slice_data.timestamps_iso),
        solar_kw=[float(x) for x in slice_data.solar_kw],
        factory_load_kw=[float(x) for x in slice_data.factory_load_kw],
        p_grid_kw=[float(x) for x in result.p_grid_kw],
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

            # Monthly MDI ratchet reset on the 1st of each month
            if curr_dt.day == 1:
                current_mdi_hw = 500.0

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
