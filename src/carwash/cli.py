"""Text command interpreter and console entry point.

Interactive:  python -m carwash
Script mode:  python -m carwash --script scenarios/happy_path.txt
              python -m carwash < commands.txt

In non-interactive mode the exit code is non-zero when any command failed
or any ``expect`` assertion did not hold, so scenario scripts can be used
directly as CI tests.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import TextIO

from carwash import __version__, programs
from carwash.car_wash import CarWash, WashError, WashState, parse_wash_state, render_status
from carwash.event_log import Event
from carwash.model import (
    DeviceId,
    default_severity,
    parse_device_id,
    parse_device_state,
    parse_fault_type,
    parse_severity,
)

HELP_TEXT = """\
Commands:
  help                                  show this help
  status                                show state of the car wash and all devices
  programs                              list available wash programs
  start <program>                       start a wash program (basic|standard|premium)
  tick [n]                              advance simulation by n ticks (default 1)
  run [max]                             tick until the current wash ends (default max 1000)
  fault <dev[,dev...]|all> <type> [warning|critical] [at <tick> | in <ticks>]
                                        inject a fault now or schedule it
  clear <dev[,dev...]|all> [type]       clear one fault type or all faults
  refill                                refill the chemical tank
  chaos <probability> [seed] | chaos off
                                        random faults each tick with given probability
  estop                                 emergency stop
  reset                                 return to idle after completion/abort/estop
  log [n]                               show last n events (default 10)
  expect state <state>                  assertion for scripts (idle|washing|completed|aborted|emergency_stop)
  expect device <dev> <idle|running|fault>
  expect fault <dev> <type>             device has given fault
  expect no_faults                      no device has any fault
  expect completed <n>                  number of completed washes
  expect log <text...>                  event log contains text
  expect error <command...>             command is expected to fail
  quit | exit                           leave

Devices: pump, chemicals, brushes, dryer, conveyor
Faults:  comm_lost, overheat, low_pressure, blocked, low_level, power_failure, sensor_error
"""


class CommandError(Exception):
    """A command was malformed or refused."""


def _parse_uint(text: str) -> int | None:
    return int(text) if text.isdigit() else None


class CommandProcessor:
    """Drives a :class:`CarWash` with text commands. Output goes to ``out``."""

    def __init__(self, wash: CarWash, out: TextIO) -> None:
        self.wash = wash
        self.out = out
        self.error_count = 0
        self.failed_expectations = 0
        self._commands: dict[str, Callable[[list[str]], None]] = {
            "help": self._cmd_help,
            "?": self._cmd_help,
            "status": self._cmd_status,
            "s": self._cmd_status,
            "programs": self._cmd_programs,
            "start": self._cmd_start,
            "tick": self._cmd_tick,
            "t": self._cmd_tick,
            "run": self._cmd_run,
            "fault": self._cmd_fault,
            "clear": self._cmd_clear,
            "refill": self._cmd_refill,
            "chaos": self._cmd_chaos,
            "estop": self._cmd_estop,
            "reset": self._cmd_reset,
            "log": self._cmd_log,
            "expect": self._cmd_expect,
        }

    def _print(self, text: str) -> None:
        self.out.write(text + "\n")

    def execute(self, line: str) -> bool:
        """Executes one line. Returns False when the user asked to quit."""
        tokens = line.split("#", 1)[0].split()
        if not tokens:
            return True
        cmd, args = tokens[0].lower(), tokens[1:]
        if cmd in ("quit", "exit"):
            return False

        handler = self._commands.get(cmd)
        try:
            if handler is None:
                raise CommandError(f"unknown command '{tokens[0]}' (type 'help')")
            handler(args)
        except CommandError as exc:
            self.error_count += 1
            self._print(f"error: {exc}")
        return True

    # --- helpers -----------------------------------------------------------
    def _parse_devices(self, text: str) -> list[DeviceId]:
        if text.lower() == "all":
            return list(DeviceId)
        result: list[DeviceId] = []
        for part in filter(None, text.split(",")):
            device = parse_device_id(part)
            if device is None:
                raise CommandError(f"unknown device '{part}'")
            if device not in result:
                result.append(device)
        if not result:
            raise CommandError("no device given")
        return result

    # --- commands ----------------------------------------------------------
    def _cmd_help(self, args: list[str]) -> None:
        self.out.write(HELP_TEXT)

    def _cmd_status(self, args: list[str]) -> None:
        self.out.write(render_status(self.wash))

    def _cmd_programs(self, args: list[str]) -> None:
        for program in programs.ALL_PROGRAMS:
            steps = " ".join(f"{s.name}[{s.duration_ticks}]" for s in program.steps)
            self._print(f"{program.name} ({program.total_ticks} ticks): {steps}")

    def _cmd_start(self, args: list[str]) -> None:
        if len(args) != 1:
            raise CommandError("usage: start <program>")
        program = programs.by_name(args[0])
        if program is None:
            raise CommandError(f"unknown program '{args[0]}' (see 'programs')")
        try:
            self.wash.start_wash(program)
        except WashError as exc:
            raise CommandError(f"cannot start: {exc}") from exc
        self._print(f"started program '{program.name}'")

    def _cmd_tick(self, args: list[str]) -> None:
        n = 1
        if args:
            value = _parse_uint(args[0])
            if value is None:
                raise CommandError("usage: tick [n]")
            n = value
        self.wash.advance(n)
        self._print(f"t={self.wash.time} state={self.wash.state}")

    def _cmd_run(self, args: list[str]) -> None:
        max_ticks = 1000
        if args:
            value = _parse_uint(args[0])
            if value is None:
                raise CommandError("usage: run [max]")
            max_ticks = value
        if self.wash.state is not WashState.WASHING:
            raise CommandError("no wash in progress")
        used = self.wash.run_until_done(max_ticks)
        self._print(f"ran {used} ticks, t={self.wash.time} state={self.wash.state}")

    def _cmd_fault(self, args: list[str]) -> None:
        usage = "usage: fault <dev[,dev...]|all> <type> [warning|critical] [at <tick> | in <ticks>]"
        if len(args) < 2:
            raise CommandError(usage)
        devices = self._parse_devices(args[0])
        fault_type = parse_fault_type(args[1])
        if fault_type is None:
            raise CommandError(f"unknown fault type '{args[1]}'")

        severity = None
        at_tick: int | None = None
        rest = iter(args[2:])
        for word in rest:
            word = word.lower()
            parsed = parse_severity(word)
            if parsed is not None:
                severity = parsed
            elif word in ("at", "in"):
                value = _parse_uint(next(rest, ""))
                if value is None:
                    raise CommandError(usage)
                at_tick = value if word == "at" else self.wash.time + value
            else:
                raise CommandError(usage)

        if at_tick is not None and at_tick <= self.wash.time:
            raise CommandError(f"tick {at_tick} is not in the future (now t={self.wash.time})")

        for device in devices:
            if at_tick is not None:
                self.wash.schedule_fault(at_tick, device, fault_type, severity)
            else:
                self.wash.inject_fault(device, fault_type, severity)

        sev = severity or default_severity(fault_type)
        when = f" at t={at_tick}" if at_tick is not None else ""
        verb = "scheduled" if at_tick is not None else "injected"
        self._print(f"{verb} {fault_type} ({sev}) on {len(devices)} device(s){when}")

    def _cmd_clear(self, args: list[str]) -> None:
        if not 1 <= len(args) <= 2:
            raise CommandError("usage: clear <dev[,dev...]|all> [type]")
        devices = self._parse_devices(args[0])
        if len(args) == 2:
            fault_type = parse_fault_type(args[1])
            if fault_type is None:
                raise CommandError(f"unknown fault type '{args[1]}'")
            cleared = sum(self.wash.clear_fault(d, fault_type) for d in devices)
            self._print(f"cleared {fault_type} on {cleared} device(s)")
        else:
            for device in devices:
                self.wash.clear_faults(device)
            self._print(f"cleared all faults on {len(devices)} device(s)")

    def _cmd_refill(self, args: list[str]) -> None:
        self.wash.refill_chemicals()
        self._print("chemical tank refilled")

    def _cmd_chaos(self, args: list[str]) -> None:
        if len(args) == 1 and args[0].lower() == "off":
            self.wash.fault_injector.disable_random_faults()
            self._print("random faults disabled")
            return
        if not 1 <= len(args) <= 2:
            raise CommandError("usage: chaos <probability> [seed] | chaos off")
        try:
            probability = float(args[0])
        except ValueError:
            probability = -1.0
        if not 0.0 <= probability <= 1.0:
            raise CommandError("probability must be in range 0..1")
        seed = 42
        if len(args) == 2:
            value = _parse_uint(args[1])
            if value is None:
                raise CommandError("seed must be a non-negative integer")
            seed = value
        self.wash.fault_injector.enable_random_faults(probability, seed)
        self._print(f"random faults enabled: p={probability} seed={seed}")

    def _cmd_estop(self, args: list[str]) -> None:
        self.wash.emergency_stop()
        self._print("EMERGENCY STOP")

    def _cmd_reset(self, args: list[str]) -> None:
        try:
            self.wash.reset()
        except WashError as exc:
            raise CommandError(str(exc)) from exc
        self._print("reset to idle")

    def _cmd_log(self, args: list[str]) -> None:
        n = 10
        if args:
            value = _parse_uint(args[0])
            if value is None:
                raise CommandError("usage: log [n]")
            n = value
        events = self.wash.log.events
        for event in events[len(events) - min(n, len(events)) :]:
            self._print(str(event))

    def _cmd_expect(self, args: list[str]) -> None:
        usage = "usage: expect <state|device|fault|no_faults|completed|log|error> ..."
        if not args:
            raise CommandError(usage)
        what = args[0].lower()
        wash = self.wash

        if what == "state" and len(args) == 2:
            expected_state = parse_wash_state(args[1])
            if expected_state is None:
                raise CommandError(f"unknown wash state '{args[1]}'")
            ok = wash.state is expected_state
            description = f"state == {args[1]} (actual: {wash.state})"
        elif what == "device" and len(args) == 3:
            device = parse_device_id(args[1])
            if device is None:
                raise CommandError(f"unknown device '{args[1]}'")
            expected_dev_state = parse_device_state(args[2])
            if expected_dev_state is None:
                raise CommandError(f"unknown device state '{args[2]}'")
            actual = wash.device(device).state
            ok = actual is expected_dev_state
            description = f"{args[1]} == {args[2]} (actual: {actual})"
        elif what == "fault" and len(args) == 3:
            device = parse_device_id(args[1])
            if device is None:
                raise CommandError(f"unknown device '{args[1]}'")
            fault_type = parse_fault_type(args[2])
            if fault_type is None:
                raise CommandError(f"unknown fault type '{args[2]}'")
            ok = wash.device(device).has_fault(fault_type)
            description = f"{args[1]} has fault {args[2]}"
        elif what == "no_faults" and len(args) == 1:
            ok = all(not d.faults for d in wash.devices)
            description = "no faults on any device"
        elif what == "completed" and len(args) == 2:
            expected_count = _parse_uint(args[1])
            if expected_count is None:
                raise CommandError("usage: expect completed <n>")
            ok = wash.completed_washes == expected_count
            description = f"completed washes == {args[1]} (actual: {wash.completed_washes})"
        elif what == "log" and len(args) >= 2:
            text = " ".join(args[1:])
            ok = wash.log.contains(text)
            description = f'log contains "{text}"'
        elif what == "error" and len(args) >= 2:
            command = " ".join(args[1:])
            errors_before = self.error_count
            self.execute(command)
            ok = self.error_count > errors_before
            self.error_count = errors_before  # the error was expected, do not count it
            description = f"command fails: {command}"
        else:
            raise CommandError(usage)

        if ok:
            self._print(f"PASS: {description}")
        else:
            self.failed_expectations += 1
            self._print(f"FAIL: {description}")


def run(lines: TextIO, out: TextIO, *, interactive: bool, quiet: bool, echo: bool) -> int:
    """Runs commands from ``lines``. Returns the process exit code."""
    wash = CarWash()
    if not quiet:

        def on_event(event: Event) -> None:
            out.write(f"  {event}\n")

        wash.log.listener = on_event

    processor = CommandProcessor(wash, out)
    if interactive:
        out.write(f"Car wash emulator {__version__} - type 'help' for commands\n")

    while True:
        if interactive:
            out.write("carwash> ")
            out.flush()
        line = lines.readline()
        if not line:
            break
        stripped = line.strip()
        if echo and stripped and not stripped.startswith("#"):
            out.write(f"> {stripped}\n")
        if not processor.execute(line):
            break

    if interactive:
        return 0
    if processor.failed_expectations or processor.error_count:
        out.write(
            f"\nSUMMARY: {processor.failed_expectations} failed expectation(s), "
            f"{processor.error_count} command error(s)\n"
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="carwash",
        description="Car wash emulator with fault injection.",
        epilog=HELP_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--script", metavar="FILE", help="read commands from file instead of stdin")
    parser.add_argument("-q", "--quiet", action="store_true", help="do not print events as they happen")
    parser.add_argument("--echo", action="store_true", help="print each command before executing it")
    parser.add_argument("-v", "--version", action="version", version=f"carwash {__version__}")
    args = parser.parse_args(argv)

    if args.script:
        try:
            with open(args.script, encoding="utf-8") as script:
                return run(script, sys.stdout, interactive=False, quiet=args.quiet, echo=True)
        except OSError as exc:
            print(f"cannot open script: {exc}", file=sys.stderr)
            return 2

    return run(sys.stdin, sys.stdout, interactive=sys.stdin.isatty(), quiet=args.quiet, echo=args.echo)


if __name__ == "__main__":
    sys.exit(main())
