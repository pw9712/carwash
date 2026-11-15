import pytest

from carwash.devices import Brushes, ChemicalDispenser, Conveyor, Dryer, WaterPump
from carwash.model import DeviceState, FaultType, Severity

# --------------------------------------------------------------- base behaviour


def test_starts_idle_without_faults() -> None:
    pump = WaterPump()
    assert pump.state is DeviceState.IDLE
    assert not pump.is_running
    assert pump.faults == ()


def test_start_and_stop() -> None:
    pump = WaterPump()
    assert pump.start()
    assert pump.state is DeviceState.RUNNING
    pump.stop()
    assert pump.state is DeviceState.IDLE


def test_critical_fault_trips_running_device() -> None:
    brushes = Brushes()
    assert brushes.start()
    brushes.inject_fault(FaultType.OVERHEAT, Severity.CRITICAL)
    assert not brushes.is_running
    assert brushes.state is DeviceState.FAULT


def test_cannot_start_with_critical_fault() -> None:
    conveyor = Conveyor()
    conveyor.inject_fault(FaultType.POWER_FAILURE, Severity.CRITICAL)
    assert not conveyor.start()
    assert not conveyor.is_running


def test_warning_does_not_stop_device() -> None:
    conveyor = Conveyor()
    conveyor.start()
    conveyor.inject_fault(FaultType.BLOCKED, Severity.WARNING)
    assert conveyor.is_running
    assert conveyor.state is DeviceState.RUNNING
    assert conveyor.has_warning()
    assert not conveyor.has_critical_fault()


def test_reinjecting_same_type_updates_severity() -> None:
    dryer = Dryer()
    dryer.inject_fault(FaultType.OVERHEAT, Severity.WARNING)
    dryer.inject_fault(FaultType.OVERHEAT, Severity.CRITICAL)
    assert len(dryer.faults) == 1
    assert dryer.faults[0].severity is Severity.CRITICAL


def test_multiple_faults_and_clearing() -> None:
    pump = WaterPump()
    pump.inject_fault(FaultType.LOW_PRESSURE, Severity.WARNING)
    pump.inject_fault(FaultType.COMMUNICATION_LOST, Severity.CRITICAL)
    assert len(pump.faults) == 2

    assert pump.clear_fault(FaultType.COMMUNICATION_LOST)
    assert not pump.clear_fault(FaultType.COMMUNICATION_LOST)
    assert pump.state is DeviceState.IDLE
    assert pump.has_fault(FaultType.LOW_PRESSURE)

    pump.clear_all_faults()
    assert pump.faults == ()
    assert pump.start()


def test_communication_lost_hides_telemetry() -> None:
    pump = WaterPump()
    pump.inject_fault(FaultType.COMMUNICATION_LOST, Severity.WARNING)
    assert "n/a" in pump.telemetry()


# ------------------------------------------------------------------- WaterPump


def test_pump_pressure_follows_state() -> None:
    pump = WaterPump()
    pump.tick()
    assert pump.pressure_bar == 0.0

    pump.start()
    pump.tick()
    assert pump.pressure_bar == WaterPump.NOMINAL_PRESSURE_BAR

    pump.inject_fault(FaultType.LOW_PRESSURE, Severity.WARNING)
    pump.tick()
    assert pump.pressure_bar == WaterPump.DEGRADED_PRESSURE_BAR
    assert pump.telemetry() == "pressure=15.0 bar"


def test_pump_pressure_drops_immediately_when_stopped_or_tripped() -> None:
    pump = WaterPump()
    pump.start()
    pump.tick()
    pump.stop()
    assert pump.pressure_bar == 0.0

    pump.start()
    pump.tick()
    pump.inject_fault(FaultType.OVERHEAT, Severity.CRITICAL)
    assert pump.pressure_bar == 0.0


# ----------------------------------------------------------- ChemicalDispenser


def test_chemicals_consume_only_when_running() -> None:
    chem = ChemicalDispenser(10.0)
    chem.tick()
    assert chem.level_percent == 100.0
    chem.start()
    chem.tick()
    chem.tick()
    assert chem.level_percent == pytest.approx(80.0)


def test_chemicals_raise_warning_then_critical_when_empty() -> None:
    chem = ChemicalDispenser(10.0)
    chem.set_level_percent(25.0)
    chem.start()

    chem.tick()  # 15% - still fine
    assert not chem.has_fault(FaultType.LOW_LEVEL)

    chem.tick()  # 5% - warning
    assert chem.has_warning()
    assert chem.is_running

    chem.tick()  # 0% - critical, trips
    assert chem.has_critical_fault()
    assert not chem.is_running
    assert chem.level_percent == 0.0


def test_clearing_fault_while_empty_comes_back() -> None:
    chem = ChemicalDispenser()
    chem.set_level_percent(0.0)
    assert chem.has_critical_fault()
    chem.clear_all_faults()
    chem.tick()
    assert chem.has_critical_fault(), "sensor still sees an empty tank"


def test_refill_fixes_level_fault() -> None:
    chem = ChemicalDispenser()
    chem.set_level_percent(0.0)
    chem.refill()
    assert chem.level_percent == 100.0
    assert not chem.has_fault(FaultType.LOW_LEVEL)
    assert chem.start()


@pytest.mark.parametrize(("value", "expected"), [(150.0, 100.0), (-3.0, 0.0)])
def test_level_is_clamped(value: float, expected: float) -> None:
    chem = ChemicalDispenser()
    chem.set_level_percent(value)
    assert chem.level_percent == expected


# --------------------------------------------------------------------- Brushes


def test_brushes_rpm_depends_on_blocked_warning() -> None:
    brushes = Brushes()
    brushes.start()
    brushes.tick()
    assert brushes.rpm == Brushes.NOMINAL_RPM
    brushes.inject_fault(FaultType.BLOCKED, Severity.WARNING)
    brushes.tick()
    assert brushes.rpm == Brushes.DEGRADED_RPM
    brushes.stop()
    assert brushes.rpm == 0


# ----------------------------------------------------------------------- Dryer


def test_dryer_heats_up_and_cools_down() -> None:
    dryer = Dryer()
    dryer.start()
    for _ in range(10):
        dryer.tick()
    assert dryer.temperature_c == Dryer.WORKING_TEMP

    dryer.stop()
    for _ in range(20):
        dryer.tick()
    assert dryer.temperature_c == Dryer.AMBIENT_TEMP


def test_dryer_overheat_warning_runs_away() -> None:
    dryer = Dryer()
    dryer.start()
    dryer.inject_fault(FaultType.OVERHEAT, Severity.WARNING)
    for _ in range(20):
        dryer.tick()
    assert dryer.temperature_c == Dryer.OVERHEAT_TEMP


def test_dryer_sensor_error_shows_unknown_temperature() -> None:
    dryer = Dryer()
    dryer.inject_fault(FaultType.SENSOR_ERROR, Severity.WARNING)
    assert "??" in dryer.telemetry()


# -------------------------------------------------------------------- Conveyor


def test_conveyor_speed_depends_on_state() -> None:
    conveyor = Conveyor()
    conveyor.start()
    conveyor.tick()
    assert conveyor.speed_m_per_min == Conveyor.NOMINAL_SPEED
    conveyor.inject_fault(FaultType.BLOCKED, Severity.WARNING)
    conveyor.tick()
    assert conveyor.speed_m_per_min == Conveyor.DEGRADED_SPEED
