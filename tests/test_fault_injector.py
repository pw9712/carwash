import pytest

from carwash.fault_injector import FaultInjector, FaultRequest
from carwash.model import DeviceId, FaultType, Severity

PUMP_LOW_PRESSURE = FaultRequest(DeviceId.WATER_PUMP, FaultType.LOW_PRESSURE, Severity.CRITICAL)


def test_nothing_due_by_default() -> None:
    injector = FaultInjector()
    assert injector.collect_due(100) == []
    assert not injector.random_faults_enabled


def test_scheduled_fault_fires_exactly_once_at_its_tick() -> None:
    injector = FaultInjector()
    injector.schedule(5, PUMP_LOW_PRESSURE)
    assert injector.collect_due(4) == []
    assert injector.collect_due(5) == [PUMP_LOW_PRESSURE]
    assert injector.collect_due(6) == []
    assert injector.scheduled == ()


def test_overdue_faults_are_delivered() -> None:
    injector = FaultInjector()
    injector.schedule(3, PUMP_LOW_PRESSURE)
    assert len(injector.collect_due(10)) == 1


def test_multiple_faults_kept_sorted_by_time() -> None:
    injector = FaultInjector()
    injector.schedule(9, FaultRequest(DeviceId.DRYER, FaultType.OVERHEAT, Severity.CRITICAL))
    injector.schedule(2, FaultRequest(DeviceId.BRUSHES, FaultType.BLOCKED, Severity.WARNING))
    injector.schedule(2, FaultRequest(DeviceId.CONVEYOR, FaultType.BLOCKED, Severity.WARNING))

    assert injector.scheduled[0].at_tick == 2
    due = injector.collect_due(2)
    assert [f.device for f in due] == [DeviceId.BRUSHES, DeviceId.CONVEYOR]  # stable order
    assert len(injector.scheduled) == 1


def test_clear_scheduled() -> None:
    injector = FaultInjector()
    injector.schedule(1, PUMP_LOW_PRESSURE)
    injector.clear_scheduled()
    assert injector.collect_due(1) == []


def test_random_with_probability_one_fires_every_tick() -> None:
    injector = FaultInjector()
    injector.enable_random_faults(1.0, 123)
    for t in range(1, 51):
        assert len(injector.collect_due(t)) == 1


def test_random_with_probability_zero_is_disabled() -> None:
    injector = FaultInjector()
    injector.enable_random_faults(0.0, 123)
    assert not injector.random_faults_enabled
    assert all(injector.collect_due(t) == [] for t in range(1, 51))


def test_random_is_deterministic_for_seed() -> None:
    a, b = FaultInjector(), FaultInjector()
    a.enable_random_faults(0.3, 7)
    b.enable_random_faults(0.3, 7)
    for t in range(1, 201):
        assert a.collect_due(t) == b.collect_due(t), f"tick {t}"


def test_random_rate_is_roughly_the_probability() -> None:
    injector = FaultInjector()
    injector.enable_random_faults(0.25, 2024)
    ticks = 4000
    fired = sum(len(injector.collect_due(t)) for t in range(1, ticks + 1))
    assert fired / ticks == pytest.approx(0.25, abs=0.04)


def test_probability_is_clamped() -> None:
    injector = FaultInjector()
    injector.enable_random_faults(7.0, 1)
    assert injector.random_probability == 1.0
    injector.disable_random_faults()
    assert not injector.random_faults_enabled
