import pytest

from carwash import programs
from carwash.model import DeviceId
from carwash.programs import WashProgram, WashStep


@pytest.mark.parametrize("program", programs.ALL_PROGRAMS, ids=lambda p: p.name)
def test_built_in_programs_are_valid(program: WashProgram) -> None:
    assert program.is_valid()
    assert program.total_ticks > 0


@pytest.mark.parametrize(
    ("program", "ticks"),
    [(programs.BASIC, 9), (programs.STANDARD, 14), (programs.PREMIUM, 19)],
)
def test_total_ticks(program: WashProgram, ticks: int) -> None:
    assert program.total_ticks == ticks


def test_required_devices_are_unique() -> None:
    assert len(programs.PREMIUM.required_devices()) == 5
    basic = programs.BASIC.required_devices()
    assert len(basic) == 3
    assert DeviceId.BRUSHES not in basic


def test_lookup_by_name() -> None:
    assert programs.by_name("Standard") is programs.STANDARD
    assert programs.by_name("deluxe") is None


def test_invalid_programs() -> None:
    assert not WashProgram("empty", ()).is_valid()
    assert not WashProgram("zero", (WashStep("nothing", 0, (DeviceId.WATER_PUMP,)),)).is_valid()
