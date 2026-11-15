"""Basic enums and value types shared by the whole emulator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DeviceId(Enum):
    """Devices present in the car wash. The value is the CLI name."""

    WATER_PUMP = "pump"
    CHEMICAL_DISPENSER = "chemicals"
    BRUSHES = "brushes"
    DRYER = "dryer"
    CONVEYOR = "conveyor"

    def __str__(self) -> str:
        return self.value


class DeviceState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAULT = "fault"

    def __str__(self) -> str:
        return self.value


class FaultType(Enum):
    COMMUNICATION_LOST = "comm_lost"
    OVERHEAT = "overheat"
    LOW_PRESSURE = "low_pressure"
    BLOCKED = "blocked"
    LOW_LEVEL = "low_level"
    POWER_FAILURE = "power_failure"
    SENSOR_ERROR = "sensor_error"

    def __str__(self) -> str:
        return self.value


class Severity(Enum):
    """WARNING: device keeps working (degraded). CRITICAL: device trips and stops."""

    WARNING = "warning"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Fault:
    type: FaultType
    severity: Severity


_DEVICE_ALIASES = {
    "water_pump": DeviceId.WATER_PUMP,
    "chem": DeviceId.CHEMICAL_DISPENSER,
    "chemical_dispenser": DeviceId.CHEMICAL_DISPENSER,
    "brush": DeviceId.BRUSHES,
}
_FAULT_ALIASES = {
    "comm": FaultType.COMMUNICATION_LOST,
    "power": FaultType.POWER_FAILURE,
    "sensor": FaultType.SENSOR_ERROR,
}
_SEVERITY_ALIASES = {
    "warn": Severity.WARNING,
    "w": Severity.WARNING,
    "crit": Severity.CRITICAL,
    "c": Severity.CRITICAL,
}


def parse_device_id(text: str) -> DeviceId | None:
    """Case-insensitive, accepts a few aliases (e.g. ``chem``)."""
    s = text.strip().lower()
    for device in DeviceId:
        if device.value == s:
            return device
    return _DEVICE_ALIASES.get(s)


def parse_device_state(text: str) -> DeviceState | None:
    s = text.strip().lower()
    return next((st for st in DeviceState if st.value == s), None)


def parse_fault_type(text: str) -> FaultType | None:
    s = text.strip().lower()
    for fault in FaultType:
        if fault.value == s:
            return fault
    return _FAULT_ALIASES.get(s)


def parse_severity(text: str) -> Severity | None:
    s = text.strip().lower()
    for severity in Severity:
        if severity.value == s:
            return severity
    return _SEVERITY_ALIASES.get(s)


def default_severity(fault_type: FaultType) -> Severity:
    """Severity used when the user does not give one explicitly."""
    if fault_type in (FaultType.LOW_LEVEL, FaultType.SENSOR_ERROR):
        return Severity.WARNING
    return Severity.CRITICAL
