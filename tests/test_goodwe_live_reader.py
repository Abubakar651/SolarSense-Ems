"""
Unit tests for GoodWe Local Live Telemetry Reader (Station LHR-RES-01).
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.data_engineering.goodwe_live_reader import (
    GoodWeLiveReader,
    GoodWeLiveTelemetryDTO,
)


@pytest.fixture
def sample_runtime_data():
    return {
        "vgrid": 0.0,
        "fgrid": 0.0,
        "grid_mode_label": "Not connected to grid",
        "errors": "Utility Loss, Vac Failure",
        "work_mode_label": "Normal (Off-Grid)",
        "pbattery1": 2012.0,
        "battery_mode_label": "Discharge",
        "battery_soc": 89.0,
        "battery_soh": 100.0,
        "vbattery1": 52.2,
        "ibattery1": 38.5,
        "battery_temperature": 26.5,
        "vpv1": 0.0,
        "ppv1": 0.0,
        "vpv2": 0.0,
        "ppv2": 0.0,
        "ppv": 0.0,
        "house_consumption": 2012.0,
        "backup_v1": 228.3,
        "backup_ptotal": 435.0,
        "e_day": 13.2,
        "e_day_exp": 12.6,
        "e_day_imp": 0.2,
        "e_load_day": 16.1,
        "e_bat_charge_day": 0.0,
        "e_bat_discharge_day": 0.5,
        "temperature_air": 38.0,
        "temperature_radiator": 37.0,
    }


def test_goodwe_live_reader_telemetry_parsing(sample_runtime_data):
    async def _run():
        reader = GoodWeLiveReader(host="192.168.100.102")
        
        mock_inverter = AsyncMock()
        mock_inverter.model_name = "GW6000ES20"
        mock_inverter.serial_number = "9010KESC253L0146"
        mock_inverter.read_runtime_data.return_value = sample_runtime_data
        
        with patch.object(reader, "_get_connected_inverter", return_value=mock_inverter):
            telemetry = await reader.fetch_telemetry()
            
            assert isinstance(telemetry, GoodWeLiveTelemetryDTO)
            assert telemetry.model_name == "GW6000ES20"
            assert telemetry.serial_number == "9010KESC253L0146"
            assert telemetry.battery_soc_pct == 89.0
            assert telemetry.battery_soh_pct == 100.0
            assert telemetry.battery_voltage_v == 52.2
            assert telemetry.battery_power_w == -2012.0  # Discharge is negative
            assert telemetry.is_blackout is True
            assert telemetry.is_grid_connected is False
            assert telemetry.total_pv_power_w == 0.0
            assert telemetry.house_consumption_w == 2012.0
            assert telemetry.backup_voltage_v == 228.3
            assert telemetry.today_pv_kwh == 13.2
            assert telemetry.today_export_kwh == 12.6

    import asyncio
    asyncio.run(_run())


def test_goodwe_live_reader_grid_connected():
    async def _run():
        reader = GoodWeLiveReader(host="192.168.100.102")
        
        connected_data = {
            "vgrid": 230.5,
            "fgrid": 50.02,
            "grid_mode_label": "Inverter On-Grid",
            "errors": "",
            "work_mode_label": "Normal (On-Grid)",
            "pbattery1": 1500.0,
            "battery_mode_label": "Charge",
            "battery_soc": 55.0,
            "ppv": 3500.0,
            "house_consumption": 2000.0,
        }
        
        mock_inverter = AsyncMock()
        mock_inverter.model_name = "GW6000ES20"
        mock_inverter.serial_number = "9010KESC253L0146"
        mock_inverter.read_runtime_data.return_value = connected_data
        
        with patch.object(reader, "_get_connected_inverter", return_value=mock_inverter):
            telemetry = await reader.fetch_telemetry()
            
            assert telemetry.is_blackout is False
            assert telemetry.is_grid_connected is True
            assert telemetry.battery_power_w == 1500.0  # Charge is positive
            assert telemetry.battery_soc_pct == 55.0

    import asyncio
    asyncio.run(_run())
