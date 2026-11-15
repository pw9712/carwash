import pytest

from carwash import programs
from carwash.car_wash import CarWash, CarWashConfig, WashError, WashState, render_status
from carwash.devices import Dryer, WaterPump
from carwash.event_log import Event, EventLevel
from carwash.model import DeviceId, DeviceState, FaultType, Severity


@pytest.fixture
def wash() -> CarWash:
    return CarWash()


def test_initial_state(wash: CarWash) -> None:
    assert wash.state is WashState.IDLE
    assert wash.time == 0
    assert wash.current_program is None
    assert not wash.any_critical_fault()
    assert all(d.state is DeviceState.IDLE for d in wash.devices)


def test_full_program_completes_in_expected_time(wash: CarWash) -> None:
    wash.start_wash(programs.STANDARD)
    assert wash.state is WashState.WASHING
    assert wash.run_until_done() == programs.STANDARD.total_ticks
    assert wash.state is WashState.COMPLETED
    assert wash.completed_washes == 1
    assert not any(d.is_running for d in wash.devices)


def test_only_step_devices_run(wash: CarWash) -> None:
    wash.start_wash(programs.STANDARD)
    # prewash: conveyor + pump
    assert wash.conveyor.is_running
    assert wash.pump.is_running
    assert not wash.chemicals.is_running

    wash.advance(2)  # -> foam
    assert wash.current_step is not None
    assert wash.current_step.name == "foam"
    assert wash.chemicals.is_running
    assert not wash.pump.is_running


def test_step_progression(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)  # prewash 3, rinse 3, dry 3
    assert wash.current_step_index == 0
    assert wash.ticks_left_in_step == 3
    wash.advance(3)
    assert wash.current_step_index == 1
    wash.advance(3)
    assert wash.current_step is not None and wash.current_step.name == "dry"
    wash.advance(2)
    assert wash.state is WashState.WASHING
    wash.tick()
    assert wash.state is WashState.COMPLETED


def test_cannot_start_while_washing(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)
    with pytest.raises(WashError, match="in progress"):
        wash.start_wash(programs.BASIC)


def test_can_start_again_after_completion(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)
    wash.run_until_done()
    wash.start_wash(programs.BASIC)
    assert wash.state is WashState.WASHING


def test_refuses_start_when_required_device_broken(wash: CarWash) -> None:
    wash.inject_fault(DeviceId.DRYER, FaultType.OVERHEAT, Severity.CRITICAL)
    with pytest.raises(WashError, match="dryer"):
        wash.start_wash(programs.BASIC)
    assert wash.state is WashState.IDLE
    assert wash.log.contains("Cannot start")


def test_broken_device_not_used_by_program_does_not_block_start(wash: CarWash) -> None:
    wash.inject_fault(DeviceId.BRUSHES, FaultType.BLOCKED, Severity.CRITICAL)
    wash.start_wash(programs.BASIC)  # basic has no brushes
    wash.run_until_done()
    assert wash.state is WashState.COMPLETED


def test_critical_fault_on_active_device_aborts_immediately(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)
    wash.tick()
    wash.inject_fault(DeviceId.WATER_PUMP, FaultType.POWER_FAILURE)
    assert wash.state is WashState.ABORTED
    assert wash.aborted_washes == 1
    assert "pump" in wash.last_abort_reason
    assert "power_failure" in wash.last_abort_reason
    assert not any(d.is_running for d in wash.devices)


def test_critical_fault_on_inactive_device_aborts_when_step_needs_it(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)  # dryer used only in the last step
    wash.tick()
    wash.inject_fault(DeviceId.DRYER, FaultType.OVERHEAT, Severity.CRITICAL)
    assert wash.state is WashState.WASHING
    wash.advance(4)
    assert wash.state is WashState.WASHING
    wash.tick()  # t=6 -> enter dry
    assert wash.state is WashState.ABORTED
    assert "dry" in wash.last_abort_reason


def test_warnings_do_not_abort(wash: CarWash) -> None:
    wash.start_wash(programs.PREMIUM)
    wash.inject_fault(DeviceId.WATER_PUMP, FaultType.LOW_PRESSURE, Severity.WARNING)
    wash.inject_fault(DeviceId.CONVEYOR, FaultType.BLOCKED, Severity.WARNING)
    wash.run_until_done()
    assert wash.state is WashState.COMPLETED
    assert wash.log.count(EventLevel.WARNING) >= 2


def test_scheduled_fault_fires_at_given_tick(wash: CarWash) -> None:
    wash.start_wash(programs.STANDARD)
    wash.schedule_fault(7, DeviceId.BRUSHES, FaultType.BLOCKED, Severity.CRITICAL)
    wash.advance(6)
    assert wash.state is WashState.WASHING
    assert not wash.brushes.has_critical_fault()
    wash.tick()
    assert wash.state is WashState.ABORTED
    assert wash.brushes.has_fault(FaultType.BLOCKED)


def test_faults_on_multiple_devices_at_once(wash: CarWash) -> None:
    for device in (DeviceId.WATER_PUMP, DeviceId.DRYER, DeviceId.CONVEYOR):
        wash.inject_fault(device, FaultType.COMMUNICATION_LOST)
    assert wash.any_critical_fault()
    with pytest.raises(WashError):
        wash.start_wash(programs.BASIC)

    wash.clear_faults(DeviceId.WATER_PUMP)
    wash.clear_faults(DeviceId.CONVEYOR)
    with pytest.raises(WashError, match="dryer"):
        wash.start_wash(programs.BASIC)

    wash.clear_all_faults()
    assert not wash.any_critical_fault()
    wash.start_wash(programs.BASIC)


def test_aborted_requires_reset(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)
    wash.inject_fault(DeviceId.CONVEYOR, FaultType.BLOCKED, Severity.CRITICAL)
    assert wash.state is WashState.ABORTED

    wash.clear_all_faults()
    with pytest.raises(WashError, match="reset"):
        wash.start_wash(programs.BASIC)

    wash.reset()
    assert wash.state is WashState.IDLE
    wash.start_wash(programs.BASIC)


def test_reset_does_not_clear_faults(wash: CarWash) -> None:
    wash.inject_fault(DeviceId.WATER_PUMP, FaultType.POWER_FAILURE)
    wash.reset()
    assert wash.pump.has_critical_fault()


def test_reset_refused_while_washing(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)
    with pytest.raises(WashError):
        wash.reset()
    assert wash.state is WashState.WASHING


def test_emergency_stop(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)
    wash.advance(2)
    wash.emergency_stop()
    assert wash.state is WashState.EMERGENCY_STOP
    assert wash.aborted_washes == 1
    assert not any(d.is_running for d in wash.devices)
    with pytest.raises(WashError):
        wash.start_wash(programs.BASIC)
    wash.reset()
    wash.start_wash(programs.BASIC)


def test_chemical_tank_runs_out_after_several_washes(wash: CarWash) -> None:
    # standard program: 3 foam ticks * 5% = 15% per wash
    for i in range(6):
        wash.start_wash(programs.STANDARD)
        wash.run_until_done()
        assert wash.state is WashState.COMPLETED, f"wash {i}"
    assert wash.chemicals.level_percent == pytest.approx(10.0)
    assert wash.chemicals.has_warning()

    wash.start_wash(programs.STANDARD)
    wash.run_until_done()
    assert wash.state is WashState.ABORTED
    assert wash.log.contains("chemicals")

    wash.refill_chemicals()
    wash.reset()
    wash.start_wash(programs.STANDARD)
    wash.run_until_done()
    assert wash.state is WashState.COMPLETED


def test_custom_consumption_config() -> None:
    thirsty = CarWash(CarWashConfig(chemical_consumption_per_tick=40.0))
    thirsty.start_wash(programs.STANDARD)
    thirsty.run_until_done()
    assert thirsty.state is WashState.ABORTED  # 3 * 40% > 100%


def test_random_faults_eventually_stop_wash(wash: CarWash) -> None:
    wash.fault_injector.enable_random_faults(1.0, 99)
    wash.start_wash(programs.PREMIUM)
    wash.run_until_done(100)
    assert wash.state is not WashState.WASHING
    assert wash.log.count(EventLevel.WARNING) + wash.log.count(EventLevel.ERROR) > 0


def test_telemetry_reflects_washing(wash: CarWash) -> None:
    wash.start_wash(programs.BASIC)
    wash.tick()
    assert wash.pump.pressure_bar == WaterPump.NOMINAL_PRESSURE_BAR
    wash.advance(7)  # into dry step
    assert wash.dryer.temperature_c > Dryer.AMBIENT_TEMP


def test_status_report_contains_devices_and_faults(wash: CarWash) -> None:
    wash.inject_fault(DeviceId.DRYER, FaultType.OVERHEAT, Severity.WARNING)
    wash.start_wash(programs.BASIC)
    status = render_status(wash)
    for device in DeviceId:
        assert str(device) in status
    assert "overheat(W)" in status
    assert "state=washing" in status
    assert "prewash" in status


def test_log_listener_is_notified(wash: CarWash) -> None:
    received: list[Event] = []
    wash.log.listener = received.append
    wash.start_wash(programs.BASIC)
    assert received
    assert received[0].level is EventLevel.INFO
