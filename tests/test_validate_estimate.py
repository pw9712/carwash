"""Tests for the change-request estimate validator (.claude/skills/cr-estimate/scripts)."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "cr-estimate"
EXAMPLE = SKILL_DIR / "templates" / "estimate.example.json"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "validate_estimate", SKILL_DIR / "scripts" / "validate_estimate.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses need the module registered
    spec.loader.exec_module(module)
    return module


ve = _load()


def _minimal() -> dict[str, Any]:
    return {
        "cr_id": "CR-2026-001",
        "title": "Test",
        "requirements": [{"id": "REQ-01", "title": "R1"}],
        "work_packages": [
            {
                "id": "1.1",
                "title": "WP",
                "req_ids": ["REQ-01"],
                "tasks": [
                    {
                        "id": "1.1.1",
                        "title": "T1",
                        "category": "implementation",
                        "optimistic": 1,
                        "most_likely": 2,
                        "pessimistic": 9,
                    },
                    {
                        "id": "1.1.2",
                        "title": "T2",
                        "category": "unit-tests",
                        "optimistic": 1,
                        "most_likely": 1,
                        "pessimistic": 1,
                    },
                ],
            }
        ],
    }


def _errors(data: object) -> list[str]:
    with pytest.raises(ve.EstimateError) as info:
        ve.parse_estimate(data)
    errors: list[str] = info.value.errors
    return errors


def test_example_template_is_valid() -> None:
    est = ve.parse_estimate(json.loads(EXAMPLE.read_text(encoding="utf-8")))
    assert est.cr_id == "CR-2026-001"
    assert len(est.work_packages) == 3


def test_pert_totals() -> None:
    est = ve.parse_estimate(_minimal())
    # T1: (1 + 8 + 9) / 6 = 3, sd = 8/6; T2: 1, sd = 0
    assert est.expected == pytest.approx(4.0)
    assert est.std_dev == pytest.approx(8 / 6)
    assert est.p90 == pytest.approx(4.0 + 1.2816 * 8 / 6)


def test_tasks_correlated_within_package_packages_independent() -> None:
    data = _minimal()
    # second task with sd = 6/6 = 1 in the same package: package sd = 8/6 + 1
    data["work_packages"][0]["tasks"][1].update(optimistic=0, most_likely=1, pessimistic=6)
    # second package with one task, sd = 12/6 = 2
    data["work_packages"].append(
        {
            "id": "1.2",
            "title": "WP2",
            "req_ids": ["REQ-01"],
            "tasks": [
                {
                    "id": "1.2.1",
                    "title": "T3",
                    "category": "review",
                    "optimistic": 0,
                    "most_likely": 3,
                    "pessimistic": 12,
                }
            ],
        }
    )
    est = ve.parse_estimate(data)
    wp1, wp2 = est.work_packages
    assert wp1.std_dev == pytest.approx(8 / 6 + 1)
    assert wp2.std_dev == pytest.approx(2)
    assert est.std_dev == pytest.approx(((8 / 6 + 1) ** 2 + 2**2) ** 0.5)


def test_hours_must_be_ordered() -> None:
    data = _minimal()
    data["work_packages"][0]["tasks"][0]["most_likely"] = 10
    assert any("optimistic <= most_likely <= pessimistic" in e for e in _errors(data))


@pytest.mark.parametrize("value", [-1, "2", True, None])
def test_hours_must_be_non_negative_numbers(value: object) -> None:
    data = _minimal()
    data["work_packages"][0]["tasks"][0]["optimistic"] = value
    assert any("'optimistic' must be a number" in e for e in _errors(data))


def test_zero_task_rejected() -> None:
    data = _minimal()
    task = data["work_packages"][0]["tasks"][1]
    task["optimistic"] = task["most_likely"] = task["pessimistic"] = 0
    assert any("greater than 0" in e for e in _errors(data))


def test_ids_and_category_checked() -> None:
    data = _minimal()
    data["cr_id"] = "CR-1"
    data["work_packages"][0]["tasks"][0]["id"] = "1.2.1"
    data["work_packages"][0]["tasks"][1]["id"] = "1.2.1"
    data["work_packages"][0]["tasks"][1]["category"] = "testing"
    errors = _errors(data)
    assert any("'cr_id'" in e for e in errors)
    assert any("not under work package" in e for e in errors)
    assert any("duplicate id" in e for e in errors)
    assert any("'category'" in e for e in errors)


def test_requirement_coverage() -> None:
    data = _minimal()
    data["requirements"].append({"id": "REQ-02", "title": "R2"})
    assert any("REQ-02 is not covered" in e for e in _errors(data))

    data = _minimal()
    data["requirements"].append({"id": "REQ-02", "title": "R2", "in_scope": False})
    ve.parse_estimate(data)  # out-of-scope requirement needs no work package

    data["work_packages"][0]["req_ids"].append("REQ-02")
    assert any("out-of-scope requirement REQ-02" in e for e in _errors(data))


def test_unknown_requirement_and_bad_types() -> None:
    data = _minimal()
    data["unit"] = "story points"
    data["assumptions"] = ["ok", ""]
    data["requirements"][0]["in_scope"] = "yes"
    data["work_packages"][0]["req_ids"] = ["REQ-99"]
    errors = _errors(data)
    assert any("'unit'" in e for e in errors)
    assert any("assumptions[1]" in e for e in errors)
    assert any("'in_scope'" in e for e in errors)
    assert any("unknown requirement 'REQ-99'" in e for e in errors)


def test_empty_and_wrong_structure() -> None:
    assert any("must be an object" in e for e in _errors([]))
    errors = _errors({"cr_id": "CR-2026-001", "title": "x", "requirements": [], "work_packages": {}})
    assert any("'requirements' must not be empty" in e for e in errors)
    assert any("must be a list" in e for e in errors)
    data = _minimal()
    data["work_packages"][0]["tasks"] = []
    assert any("'tasks' must not be empty" in e for e in _errors(data))


def test_render_markdown() -> None:
    data = _minimal()
    data["work_packages"][0]["tasks"][1].update(optimistic=0.25, most_likely=0.75, pessimistic=1.25)
    quarter = ve.render_markdown(ve.parse_estimate(data))
    assert "| 1.1.2 | T2 | unit-tests | 0.25 | 0.75 | 1.25 | 0.8 |" in quarter
    md = ve.render_markdown(ve.parse_estimate(_minimal()))
    assert "| **1.1** | **WP** (REQ-01) | | | | | **4.0** |" in md
    assert "| 1.1.1 | T1 | implementation | 1.00 | 2.00 | 9.00 | 3.0 |" in md
    assert "| implementation | 3.0 | 75% |" in md
    assert "| Expected effort (~P50) | **4.0** |" in md
    assert "| P90 (90% confidence the work fits) | **5.7** |" in md


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_minimal()), encoding="utf-8")
    assert ve.main([str(good)]) == 0
    assert "OK CR-2026-001: 2 tasks, E=4.0 h, P90=5.7 h" in capsys.readouterr().out
    assert ve.main([str(good), "--markdown"]) == 0
    assert "### Totals" in capsys.readouterr().out

    bad_data = copy.deepcopy(_minimal())
    bad_data["title"] = ""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(bad_data), encoding="utf-8")
    assert ve.main([str(bad)]) == 1
    assert "invalid:" in capsys.readouterr().err

    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert ve.main([str(broken)]) == 2
    assert ve.main([str(tmp_path / "missing.json")]) == 2
