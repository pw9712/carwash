"""Emulated devices.

A device can be started/stopped and can carry any number of faults.
A critical fault trips the device (it stops and refuses to start) until the
fault is cleared. Warnings only degrade its behaviour.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from carwash.model import DeviceId, DeviceState, Fault, FaultType, Severity


class Device(ABC):
    def __init__(self, device_id: DeviceId) -> None:
        self._id = device_id
        self._running = False
        self._faults: list[Fault] = []

    # --- identity / state ------------------------------------------------
    @property
    def id(self) -> DeviceId:
        return self._id

    @property
    def name(self) -> str:
        return self._id.value

    @property
    def state(self) -> DeviceState:
        if self.has_critical_fault():
            return DeviceState.FAULT
        return DeviceState.RUNNING if self._running else DeviceState.IDLE

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Returns False (and stays stopped) if the device has a critical fault."""
        if self.has_critical_fault():
            self._running = False
            return False
        self._running = True
        return True

    def stop(self) -> None:
        self._running = False
        self._on_stopped()

    # --- faults ------------------------------------------------------------
    @property
    def faults(self) -> tuple[Fault, ...]:
        return tuple(self._faults)

    def inject_fault(self, fault_type: FaultType, severity: Severity) -> None:
        """Adds a fault. Injecting an already present type updates its severity."""
        for i, fault in enumerate(self._faults):
            if fault.type == fault_type:
                self._faults[i] = Fault(fault_type, severity)
                break
        else:
            self._faults.append(Fault(fault_type, severity))
        if severity is Severity.CRITICAL:
            self.stop()  # device trips

    def clear_fault(self, fault_type: FaultType) -> bool:
        """Returns True if the fault was present and has been removed."""
        before = len(self._faults)
        self._faults = [f for f in self._faults if f.type != fault_type]
        return len(self._faults) != before

    def clear_all_faults(self) -> None:
        self._faults.clear()

    def has_fault(self, fault_type: FaultType) -> bool:
        return any(f.type == fault_type for f in self._faults)

    def has_critical_fault(self) -> bool:
        return any(f.severity is Severity.CRITICAL for f in self._faults)

    def has_warning(self) -> bool:
        return any(f.severity is Severity.WARNING for f in self._faults)

    # --- simulation --------------------------------------------------------
    def tick(self) -> None:
        """Advances the device simulation by one time step."""
        self._on_tick(self._running)

    def telemetry(self) -> str:
        """Human readable sensor readout ("n/a" when communication is lost)."""
        if self.has_fault(FaultType.COMMUNICATION_LOST):
            return "n/a (no communication)"
        return self._read_telemetry()

    @abstractmethod
    def _on_tick(self, running: bool) -> None: ...

    @abstractmethod
    def _read_telemetry(self) -> str: ...

    def _on_stopped(self) -> None:  # noqa: B027 - optional hook, intentionally empty
        """Hook for readings that drop instantly when the device stops."""


class WaterPump(Device):
    """High pressure pump. 80 bar nominal; LOW_PRESSURE (warning) gives 15 bar."""

    NOMINAL_PRESSURE_BAR = 80.0
    DEGRADED_PRESSURE_BAR = 15.0

    def __init__(self) -> None:
        super().__init__(DeviceId.WATER_PUMP)
        self.pressure_bar = 0.0

    def _on_tick(self, running: bool) -> None:
        if not running:
            self.pressure_bar = 0.0
        elif self.has_fault(FaultType.LOW_PRESSURE):
            self.pressure_bar = self.DEGRADED_PRESSURE_BAR
        else:
            self.pressure_bar = self.NOMINAL_PRESSURE_BAR

    def _on_stopped(self) -> None:
        self.pressure_bar = 0.0

    def _read_telemetry(self) -> str:
        return f"pressure={self.pressure_bar:.1f} bar"


class ChemicalDispenser(Device):
    """Detergent / wax dispenser with a finite tank.

    Below LOW_LEVEL_THRESHOLD it raises a LOW_LEVEL warning by itself,
    at 0% it raises a critical LOW_LEVEL fault. ``refill()`` fixes both.
    """

    LOW_LEVEL_THRESHOLD = 15.0
    DEFAULT_CONSUMPTION_PER_TICK = 5.0

    def __init__(self, consumption_per_tick: float = DEFAULT_CONSUMPTION_PER_TICK) -> None:
        super().__init__(DeviceId.CHEMICAL_DISPENSER)
        self._consumption = consumption_per_tick
        self._level = 100.0

    @property
    def level_percent(self) -> float:
        return self._level

    def set_level_percent(self, level: float) -> None:
        self._level = min(100.0, max(0.0, level))
        self._update_level_faults()

    def refill(self) -> None:
        self._level = 100.0
        self.clear_fault(FaultType.LOW_LEVEL)

    def _on_tick(self, running: bool) -> None:
        if running:
            self._level = max(0.0, self._level - self._consumption)
        self._update_level_faults()

    def _update_level_faults(self) -> None:
        if self._level <= 0.0:
            self.inject_fault(FaultType.LOW_LEVEL, Severity.CRITICAL)
        elif self._level < self.LOW_LEVEL_THRESHOLD and not self.has_fault(FaultType.LOW_LEVEL):
            self.inject_fault(FaultType.LOW_LEVEL, Severity.WARNING)

    def _read_telemetry(self) -> str:
        return f"level={self._level:.1f}%"


class Brushes(Device):
    """Rotating brushes. 120 rpm nominal; BLOCKED (warning) slows them to 40 rpm."""

    NOMINAL_RPM = 120
    DEGRADED_RPM = 40

    def __init__(self) -> None:
        super().__init__(DeviceId.BRUSHES)
        self.rpm = 0

    def _on_tick(self, running: bool) -> None:
        if not running:
            self.rpm = 0
        elif self.has_fault(FaultType.BLOCKED):
            self.rpm = self.DEGRADED_RPM
        else:
            self.rpm = self.NOMINAL_RPM

    def _on_stopped(self) -> None:
        self.rpm = 0

    def _read_telemetry(self) -> str:
        return f"rpm={self.rpm}"


class Dryer(Device):
    """Hot air dryer: heats up while running, cools down when idle.
    OVERHEAT (warning) makes it run away to OVERHEAT_TEMP."""

    AMBIENT_TEMP = 20.0
    WORKING_TEMP = 60.0
    OVERHEAT_TEMP = 95.0
    HEATING_RATE = 10.0
    COOLING_RATE = 5.0

    def __init__(self) -> None:
        super().__init__(DeviceId.DRYER)
        self.temperature_c = self.AMBIENT_TEMP

    def _on_tick(self, running: bool) -> None:
        if running:
            target = self.OVERHEAT_TEMP if self.has_fault(FaultType.OVERHEAT) else self.WORKING_TEMP
            if self.temperature_c < target:
                self.temperature_c = min(target, self.temperature_c + self.HEATING_RATE)
            else:
                self.temperature_c = max(target, self.temperature_c - self.COOLING_RATE)
        else:
            self.temperature_c = max(self.AMBIENT_TEMP, self.temperature_c - self.COOLING_RATE)

    def _read_telemetry(self) -> str:
        if self.has_fault(FaultType.SENSOR_ERROR):
            return "temp=?? C (sensor error)"
        return f"temp={self.temperature_c:.1f} C"


class Conveyor(Device):
    """Moves the car through the tunnel. 6 m/min nominal, 2 m/min when BLOCKED (warning)."""

    NOMINAL_SPEED = 6.0
    DEGRADED_SPEED = 2.0

    def __init__(self) -> None:
        super().__init__(DeviceId.CONVEYOR)
        self.speed_m_per_min = 0.0

    def _on_tick(self, running: bool) -> None:
        if not running:
            self.speed_m_per_min = 0.0
        elif self.has_fault(FaultType.BLOCKED):
            self.speed_m_per_min = self.DEGRADED_SPEED
        else:
            self.speed_m_per_min = self.NOMINAL_SPEED

    def _on_stopped(self) -> None:
        self.speed_m_per_min = 0.0

    def _read_telemetry(self) -> str:
        return f"speed={self.speed_m_per_min:.1f} m/min"
