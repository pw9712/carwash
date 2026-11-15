"""Runs every scenarios/*.txt script through the CLI.

A script passes when all its ``expect`` lines hold and no command fails.
Adding a new scenario file is enough - it is picked up automatically.
"""

from pathlib import Path

import pytest

from carwash.cli import main

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios"
SCENARIOS = sorted(SCENARIO_DIR.glob("*.txt"))


def test_scenarios_exist() -> None:
    assert SCENARIOS, f"no scenarios found in {SCENARIO_DIR}"


@pytest.mark.scenario
@pytest.mark.parametrize("script", SCENARIOS, ids=lambda p: p.stem)
def test_scenario(script: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--quiet", "--script", str(script)])
    output = capsys.readouterr().out
    assert exit_code == 0, f"scenario {script.name} failed:\n{output}"
