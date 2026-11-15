import io

import pytest

from carwash.car_wash import CarWash, WashState
from carwash.cli import CommandProcessor, main, run
from carwash.model import DeviceId, DeviceState, FaultType


class Cli:
    """Small helper: executes a command and returns its output."""

    def __init__(self) -> None:
        self.wash = CarWash()
        self.out = io.StringIO()
        self.processor = CommandProcessor(self.wash, self.out)
        self.keep_going = True

    def __call__(self, line: str) -> str:
        self.out.seek(0)
        self.out.truncate()
        self.keep_going = self.processor.execute(line)
        return self.out.getvalue()

    @property
    def errors(self) -> int:
        return self.processor.error_count

    @property
    def failed(self) -> int:
        return self.processor.failed_expectations


@pytest.fixture
def cli() -> Cli:
    return Cli()


def test_empty_lines_and_comments_are_ignored(cli: Cli) -> None:
    assert cli("") == ""
    assert cli("   ") == ""
    assert cli("# just a comment") == ""
    assert cli.errors == 0


def test_unknown_command_is_error(cli: Cli) -> None:
    assert "unknown command" in cli("fly")
    assert cli.errors == 1


@pytest.mark.parametrize("command", ["quit", "EXIT"])
def test_quit(cli: Cli, command: str) -> None:
    cli(command)
    assert not cli.keep_going


def test_help_and_programs(cli: Cli) -> None:
    assert "Commands:" in cli("help")
    output = cli("programs")
    assert "basic" in output and "premium" in output


def test_start_and_run(cli: Cli) -> None:
    assert "started" in cli("start standard")
    assert cli.wash.state is WashState.WASHING
    cli("run")
    assert cli.wash.state is WashState.COMPLETED
    assert cli.errors == 0


def test_start_errors(cli: Cli) -> None:
    cli("start")
    cli("start turbo")
    assert cli.errors == 2
    cli.wash.inject_fault(DeviceId.WATER_PUMP, FaultType.POWER_FAILURE)
    assert "cannot start" in cli("start basic")
    assert cli.errors == 3


def test_tick_advances_time(cli: Cli) -> None:
    cli("tick")
    assert cli.wash.time == 1
    cli("tick 10")
    assert cli.wash.time == 11
    cli("tick -3")
    assert cli.errors == 1


def test_run_without_wash_is_error(cli: Cli) -> None:
    cli("run")
    assert cli.errors == 1


def test_inject_fault_with_default_severity(cli: Cli) -> None:
    cli("fault pump overheat")
    assert cli.wash.pump.has_critical_fault()
    cli("fault chemicals low_level")
    assert cli.wash.chemicals.has_warning()


def test_inject_fault_on_multiple_devices(cli: Cli) -> None:
    assert "on 3 device(s)" in cli("fault pump,dryer,conveyor blocked warning")
    for device in (DeviceId.WATER_PUMP, DeviceId.DRYER, DeviceId.CONVEYOR):
        assert cli.wash.device(device).has_fault(FaultType.BLOCKED)
    assert not cli.wash.brushes.has_fault(FaultType.BLOCKED)
    assert not cli.wash.any_critical_fault()


def test_inject_fault_on_all_devices(cli: Cli) -> None:
    cli("fault all power_failure")
    assert all(d.state is DeviceState.FAULT for d in cli.wash.devices)


def test_schedule_fault_absolute_and_relative(cli: Cli) -> None:
    cli("tick 2")
    cli("fault pump low_pressure at 5")
    cli("fault dryer overheat warning in 1")
    assert len(cli.wash.fault_injector.scheduled) == 2
    cli("tick")
    assert cli.wash.dryer.has_fault(FaultType.OVERHEAT)
    assert not cli.wash.pump.has_fault(FaultType.LOW_PRESSURE)
    cli("tick 2")
    assert cli.wash.pump.has_fault(FaultType.LOW_PRESSURE)
    assert cli.errors == 0


def test_schedule_in_the_past_is_error(cli: Cli) -> None:
    cli("tick 5")
    cli("fault pump overheat at 3")
    assert cli.errors == 1
    assert cli.wash.fault_injector.scheduled == ()


@pytest.mark.parametrize(
    "command",
    [
        "fault",
        "fault pump",
        "fault toaster overheat",
        "fault pump explosion",
        "fault pump overheat sometimes",
        "fault pump overheat at soon",
        "fault pump overheat at",
    ],
)
def test_fault_argument_errors(cli: Cli, command: str) -> None:
    assert "error" in cli(command)
    assert cli.errors == 1
    assert cli.wash.pump.faults == ()


def test_clear_specific_and_all(cli: Cli) -> None:
    cli("fault pump overheat")
    cli("fault pump low_pressure warning")
    cli("clear pump overheat")
    assert not cli.wash.pump.has_fault(FaultType.OVERHEAT)
    assert cli.wash.pump.has_fault(FaultType.LOW_PRESSURE)

    cli("fault all comm_lost")
    cli("clear all")
    assert all(not d.faults for d in cli.wash.devices)
    assert cli.errors == 0


def test_chaos_on_and_off(cli: Cli) -> None:
    cli("chaos 0.5 7")
    assert cli.wash.fault_injector.random_faults_enabled
    cli("chaos off")
    assert not cli.wash.fault_injector.random_faults_enabled
    cli("chaos 2")
    cli("chaos abc")
    assert cli.errors == 2


def test_estop_and_reset(cli: Cli) -> None:
    cli("start basic")
    cli("estop")
    assert cli.wash.state is WashState.EMERGENCY_STOP
    cli("reset")
    assert cli.wash.state is WashState.IDLE
    cli("start basic")
    cli("reset")  # refused while washing
    assert cli.errors == 1


def test_status_shows_state(cli: Cli) -> None:
    cli("fault brushes blocked warning")
    status = cli("status")
    assert "blocked(W)" in status
    assert "state=idle" in status


def test_log_shows_last_events(cli: Cli) -> None:
    cli("start basic")
    cli("run")
    output = cli("log 1")
    assert "Wash completed" in output
    assert output.count("\n") == 1


def test_expect_pass_and_fail(cli: Cli) -> None:
    for line in ("expect state idle", "expect no_faults", "expect completed 0", "expect device pump idle"):
        assert "PASS" in cli(line)
    assert cli.failed == 0

    assert "FAIL" in cli("expect state washing")
    assert "FAIL" in cli("expect device pump running")
    assert cli.failed == 2


def test_expect_fault_and_log(cli: Cli) -> None:
    cli("fault dryer overheat")
    cli("expect fault dryer overheat")
    cli("expect log Fault injected")
    assert cli.failed == 0
    cli("expect fault pump overheat")
    assert cli.failed == 1


def test_expect_error_does_not_count_as_error(cli: Cli) -> None:
    cli("expect error start turbo")
    assert cli.failed == 0
    assert cli.errors == 0
    cli("expect error status")  # status succeeds -> expectation fails
    assert cli.failed == 1


@pytest.mark.parametrize("command", ["expect", "expect state flying", "expect device pump sleeping"])
def test_expect_bad_syntax_is_error(cli: Cli, command: str) -> None:
    cli(command)
    assert cli.errors == 1
    assert cli.failed == 0


# --------------------------------------------------------- run() / main()


def test_run_returns_nonzero_on_failure() -> None:
    out = io.StringIO()
    code = run(
        io.StringIO("start basic\nrun\nexpect state aborted\n"),
        out,
        interactive=False,
        quiet=True,
        echo=False,
    )
    assert code == 1
    assert "SUMMARY" in out.getvalue()


def test_run_returns_zero_on_success() -> None:
    out = io.StringIO()
    code = run(
        io.StringIO("start basic\nrun\nexpect state completed\nquit\nbogus\n"),
        out,
        interactive=False,
        quiet=False,
        echo=True,
    )
    assert code == 0  # 'bogus' is after quit, never executed
    assert "> start basic" in out.getvalue()
    assert "[t=0] INFO Wash started" in out.getvalue()


def test_main_with_missing_script_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--script", "does/not/exist.txt"]) == 2
    assert "cannot open script" in capsys.readouterr().err
