import pytest

from carwash.model import (
    DeviceId,
    FaultType,
    Severity,
    default_severity,
    parse_device_id,
    parse_fault_type,
    parse_severity,
)


@pytest.mark.parametrize("device", list(DeviceId))
def test_device_id_round_trip(device: DeviceId) -> None:
    assert parse_device_id(str(device)) is device


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("CHEM", DeviceId.CHEMICAL_DISPENSER),
        ("Brush", DeviceId.BRUSHES),
        ("water_pump", DeviceId.WATER_PUMP),
        ("toaster", None),
        ("", None),
    ],
)
def test_device_aliases_and_case(text: str, expected: DeviceId | None) -> None:
    assert parse_device_id(text) is expected


@pytest.mark.parametrize("fault", list(FaultType))
def test_fault_type_round_trip(fault: FaultType) -> None:
    assert parse_fault_type(str(fault)) is fault


def test_fault_aliases() -> None:
    assert parse_fault_type("comm") is FaultType.COMMUNICATION_LOST
    assert parse_fault_type("explosion") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("warning", Severity.WARNING),
        ("W", Severity.WARNING),
        ("critical", Severity.CRITICAL),
        ("crit", Severity.CRITICAL),
        ("meh", None),
    ],
)
def test_severity_parsing(text: str, expected: Severity | None) -> None:
    assert parse_severity(text) is expected


def test_default_severity() -> None:
    assert default_severity(FaultType.LOW_LEVEL) is Severity.WARNING
    assert default_severity(FaultType.SENSOR_ERROR) is Severity.WARNING
    assert default_severity(FaultType.POWER_FAILURE) is Severity.CRITICAL
    assert default_severity(FaultType.OVERHEAT) is Severity.CRITICAL
