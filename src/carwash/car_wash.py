"""Controller of the whole car wash.

Time is discrete: one call to :meth:`CarWash.tick` advances the simulation
by one step, which makes the emulator fully deterministic and easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from carwash.devices import (
    Brushes,
    ChemicalDispenser,
    Conveyor,
    Device,
    Dryer,
    WaterPump,
)
from carwash.event_log import EventLevel, EventLog
from carwash.fault_injector import FaultInjector, FaultRequest
from carwash.model import DeviceId, Fault, FaultType, Severity, default_severity
from carwash.programs import WashProgram, WashStep


class WashState(Enum):
    IDLE = "idle"  # ready, nothing happening
    WASHING = "washing"  # a program is running
    COMPLETED = "completed"  # last program finished (can start again)
    ABORTED = "aborted"  # a critical fault stopped the wash (needs reset)
    EMERGENCY_STOP = "emergency_stop"  # operator pressed e-stop (needs reset)

    def __str__(self) -> str:
        return self.value


def parse_wash_state(text: str) -> WashState | None:
    s = text.strip().lower()
    if s == "estop":
    return WashState.EMERGENCY_STOP
    return next((st for st in WashState if st.value == s), None)


class WashError(Exception):
    """Raised when an operation is refused (start, reset)."""


@dataclass
class CarWashConfig:
    chemical_consumption_per_tick: float = ChemicalDispenser.DEFAULT_CONSUMPTION_PER_TICK


class CarWash:
    def __init__(self, config: CarWashConfig | None = None) -> None:
        config = config or CarWashConfig()
        self.pump = WaterPump()
        self.chemicals = ChemicalDispenser(config.chemical_consumption_per_tick)
        self.brushes = Brushes()
        self.dryer = Dryer()
        self.conveyor = Conveyor()
        self._devices: dict[DeviceId, Device] = {
            d.id: d for d in (self.pump, self.chemicals, self.brushes, self.dryer, self.conveyor)
        }

        self.fault_injector = FaultInjector()
        self.log = EventLog()

        self._state = WashState.IDLE
        self._time = 0
        self._program: WashProgram | None = None
        self._step_index = 0
        self._ticks_left_in_step = 0
        self.completed_washes = 0
        self.aborted_washes = 0
        self.last_abort_reason = ""

    # --- devices -----------------------------------------------------------
    def device(self, device_id: DeviceId) -> Device:
        return self._devices[device_id]

    @property
    def devices(self) -> list[Device]:
        return [self._devices[d] for d in DeviceId]

    # --- observation -------------------------------------------------------
    @property
    def state(self) -> WashState:
        return self._state

    @property
    def time(self) -> int:
        return self._time

    @property
    def current_program(self) -> WashProgram | None:
        return self._program

    @property
    def current_step(self) -> WashStep | None:
        if self._program is None or self._state is not WashState.WASHING:
            return None
        return self._program.steps[self._step_index]

    @property
    def current_step_index(self) -> int:
        return self._step_index

    @property
    def ticks_left_in_step(self) -> int:
        return self._ticks_left_in_step

    def any_critical_fault(self) -> bool:
        return any(d.has_critical_fault() for d in self.devices)

    # --- washing -----------------------------------------------------------
    def start_wash(self, program: WashProgram) -> None:
        """Starts a program or raises :class:`WashError` with the reason."""
        try:
            self._check_can_start(program)
        except WashError as exc:
            self.log.add(self._time, EventLevel.WARNING, f"Cannot start '{program.name}': {exc}")
            raise

        self._program = program
        self._state = WashState.WASHING
        self.log.add(
            self._time,
            EventLevel.INFO,
            f"Wash started: program '{program.name}' ({program.total_ticks} ticks)",
        )
        self._enter_step(0)

    def _check_can_start(self, program: WashProgram) -> None:
        if self._state is WashState.WASHING:
            raise WashError("a wash is already in progress")
        if self._state in (WashState.ABORTED, WashState.EMERGENCY_STOP):
            raise WashError(f"system needs reset (state: {self._state})")
        if not program.is_valid():
            raise WashError("invalid program")
        for device_id in program.required_devices():
            if self.device(device_id).has_critical_fault():
                raise WashError(f"device '{device_id}' has a critical fault")

    def tick(self) -> None:
        self._time += 1

        for request in self.fault_injector.collect_due(self._time):
            self._apply_fault(request, "scheduled/random")

        for dev in self.devices:
            before = dev.faults
            dev.tick()
            self._log_new_faults(dev, before)

        if self._state is not WashState.WASHING or not self._check_step_devices():
            return

        self._ticks_left_in_step -= 1
        if self._ticks_left_in_step > 0:
            return

        assert self._program is not None
        if self._step_index + 1 < len(self._program.steps):
            self._enter_step(self._step_index + 1)
        else:
            self._stop_all_devices()
            self._state = WashState.COMPLETED
            self.completed_washes += 1
            self.log.add(self._time, EventLevel.INFO, f"Wash completed: program '{self._program.name}'")

    def advance(self, ticks: int) -> None:
        for _ in range(ticks):
            self.tick()

    def run_until_done(self, max_ticks: int = 10_000) -> int:
        """Ticks until the wash is no longer WASHING. Returns ticks used."""
        used = 0
        while self._state is WashState.WASHING and used < max_ticks:
            self.tick()
            used += 1
        return used

    def emergency_stop(self) -> None:
        self._stop_all_devices()
        if self._state is WashState.WASHING:
            self.aborted_washes += 1
        self._state = WashState.EMERGENCY_STOP
        self.log.add(self._time, EventLevel.ERROR, "EMERGENCY STOP activated")

    def reset(self) -> None:
        """Back to IDLE from COMPLETED/ABORTED/EMERGENCY_STOP. Faults are NOT cleared."""
        if self._state is WashState.WASHING:
            raise WashError("cannot reset while washing (use estop first)")
        self._stop_all_devices()
        self._state = WashState.IDLE
        self._program = None
        self._step_index = 0
        self._ticks_left_in_step = 0
        self.log.add(self._time, EventLevel.INFO, "System reset to idle")

    # --- faults ------------------------------------------------------------
    def inject_fault(
        self, device_id: DeviceId, fault_type: FaultType, severity: Severity | None = None
    ) -> None:
        severity = severity or default_severity(fault_type)
        self._apply_fault(FaultRequest(device_id, fault_type, severity), "manual")

    def schedule_fault(
        self,
        at_tick: int,
        device_id: DeviceId,
        fault_type: FaultType,
        severity: Severity | None = None,
    ) -> None:
        request = FaultRequest(device_id, fault_type, severity or default_severity(fault_type))
        self.fault_injector.schedule(at_tick, request)
        self.log.add(self._time, EventLevel.INFO, f"Fault scheduled at t={at_tick}: {request}")

    def clear_fault(self, device_id: DeviceId, fault_type: FaultType) -> bool:
        removed = self.device(device_id).clear_fault(fault_type)
        if removed:
            self.log.add(self._time, EventLevel.INFO, f"Fault cleared: {device_id} {fault_type}")
        return removed

    def clear_faults(self, device_id: DeviceId) -> None:
        dev = self.device(device_id)
        if dev.faults:
            dev.clear_all_faults()
            self.log.add(self._time, EventLevel.INFO, f"All faults cleared on {device_id}")

    def clear_all_faults(self) -> None:
        for device_id in DeviceId:
            self.clear_faults(device_id)

    def refill_chemicals(self) -> None:
        self.chemicals.refill()
        self.log.add(self._time, EventLevel.INFO, "Chemical tank refilled")

    # --- internals ---------------------------------------------------------
    def _apply_fault(self, request: FaultRequest, origin: str) -> None:
        self.device(request.device).inject_fault(request.type, request.severity)
        level = EventLevel.ERROR if request.severity is Severity.CRITICAL else EventLevel.WARNING
        self.log.add(self._time, level, f"Fault injected [{origin}]: {request}")
        if self._state is WashState.WASHING:
            self._check_step_devices()

    def _enter_step(self, index: int) -> None:
        assert self._program is not None
        self._step_index = index
        step = self._program.steps[index]
        self._ticks_left_in_step = step.duration_ticks

        for dev in self.devices:
            if dev.id not in step.devices:
                dev.stop()
        self.log.add(self._time, EventLevel.INFO, f"Step {index + 1}/{len(self._program.steps)}: {step.name}")
        for device_id in step.devices:
            self.device(device_id).start()
        self._check_step_devices()

    def _check_step_devices(self) -> bool:
        step = self.current_step
        if step is None:
            return False
        for device_id in step.devices:
            dev = self.device(device_id)
            if dev.has_critical_fault():
                faults = ", ".join(str(f.type) for f in dev.faults if f.severity is Severity.CRITICAL)
                self._abort(f"critical fault on '{device_id}' ({faults}) during step '{step.name}'")
                return False
        return True

    def _abort(self, reason: str) -> None:
        self._stop_all_devices()
        self._state = WashState.ABORTED
        self.aborted_washes += 1
        self.last_abort_reason = reason
        self.log.add(self._time, EventLevel.ERROR, f"Wash ABORTED: {reason}")

    def _stop_all_devices(self) -> None:
        for dev in self.devices:
            dev.stop()

    def _log_new_faults(self, dev: Device, before: tuple[Fault, ...]) -> None:
        for fault in dev.faults:
            if fault in before:
                continue
            level = EventLevel.ERROR if fault.severity is Severity.CRITICAL else EventLevel.WARNING
            request = FaultRequest(dev.id, fault.type, fault.severity)
            self.log.add(self._time, level, f"Device reported fault: {request}")


def render_status(wash: CarWash) -> str:
    """Multi-line, human readable status of the whole system."""
    lines = [
        f"=== CAR WASH === t={wash.time}  state={wash.state}  "
        f"completed={wash.completed_washes}  aborted={wash.aborted_washes}"
    ]
    step = wash.current_step
    if step is not None and wash.current_program is not None:
        lines.append(
            f"Program: {wash.current_program.name}  step {wash.current_step_index + 1}/"
            f"{len(wash.current_program.steps)} '{step.name}'  "
            f"({wash.ticks_left_in_step} ticks left)"
        )
    elif wash.state is WashState.ABORTED:
        lines.append(f"Abort reason: {wash.last_abort_reason}")

    lines.append(f"{'DEVICE':<11}{'STATE':<9}{'FAULTS':<34}TELEMETRY")
    for dev in wash.devices:
        faults = " ".join(f"{f.type}({'C' if f.severity is Severity.CRITICAL else 'W'})" for f in dev.faults)
        lines.append(f"{dev.name:<11}{dev.state.value.upper():<9}{faults or '-':<34}{dev.telemetry()}")

    injector = wash.fault_injector
    chaos = f"on (p={injector.random_probability}/tick)" if injector.random_faults_enabled else "off"
    lines.append(f"Scheduled faults: {len(injector.scheduled)}   Random faults: {chaos}")
    return "\n".join(lines) + "\n"
