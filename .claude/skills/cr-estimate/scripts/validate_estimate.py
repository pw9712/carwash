"""Validate a change-request ``estimate.json`` and render its WBS as Markdown.

Usage::

    python validate_estimate.py <estimate.json>              # validate only
    python validate_estimate.py <estimate.json> --markdown   # validate and print WBS + totals

Exit codes: 0 = valid, 1 = invalid estimate (errors on stderr), 2 = file or JSON error.

All arithmetic (PERT expected hours, standard deviation, P90) is done here, so the
numbers in ``03_estimate.md`` never depend on the model doing sums by hand.
Uncertainty model: tasks inside a work package are fully correlated, work packages are
independent of each other.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

CATEGORIES = ("analysis", "implementation", "unit-tests", "scenario-tests", "documentation", "review")
CR_ID_RE = re.compile(r"^CR-\d{4}-\d{3}$")
REQ_ID_RE = re.compile(r"^REQ-\d{2,3}$")
WP_ID_RE = re.compile(r"^1\.\d+$")
TASK_ID_RE = re.compile(r"^1\.\d+\.\d+$")
Z_P90 = 1.2816  # one-sided 90% quantile of the standard normal distribution


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    in_scope: bool


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    category: str
    optimistic: float
    most_likely: float
    pessimistic: float

    @property
    def expected(self) -> float:
        """PERT (beta) expected value."""
        return (self.optimistic + 4 * self.most_likely + self.pessimistic) / 6

    @property
    def std_dev(self) -> float:
        """PERT standard deviation."""
        return (self.pessimistic - self.optimistic) / 6


@dataclass(frozen=True)
class WorkPackage:
    id: str
    title: str
    req_ids: tuple[str, ...]
    tasks: tuple[Task, ...]

    @property
    def expected(self) -> float:
        return sum(t.expected for t in self.tasks)

    @property
    def std_dev(self) -> float:
        """Tasks of one package share causes (same requirement, same open questions), so
        they are treated as fully correlated: their standard deviations add up."""
        return sum(t.std_dev for t in self.tasks)


@dataclass(frozen=True)
class Estimate:
    cr_id: str
    title: str
    requirements: tuple[Requirement, ...]
    work_packages: tuple[WorkPackage, ...]

    @property
    def tasks(self) -> tuple[Task, ...]:
        return tuple(t for wp in self.work_packages for t in wp.tasks)

    @property
    def expected(self) -> float:
        return sum(t.expected for t in self.tasks)

    @property
    def std_dev(self) -> float:
        """Work packages are treated as independent: their variances add up."""
        return math.sqrt(sum(wp.std_dev**2 for wp in self.work_packages))

    @property
    def p90(self) -> float:
        return self.expected + Z_P90 * self.std_dev


class EstimateError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


class _Parser:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def err(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def obj(self, value: object, where: str) -> dict[str, object]:
        if isinstance(value, dict) and all(isinstance(k, str) for k in value):
            return {str(k): v for k, v in value.items()}
        self.err(where, "must be an object")
        return {}

    def lst(self, value: object, where: str) -> list[object]:
        if isinstance(value, list):
            return list(value)
        self.err(where, "must be a list")
        return []

    def text(
        self, data: dict[str, object], key: str, where: str, pattern: re.Pattern[str] | None = None
    ) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            self.err(where, f"'{key}' must be a non-empty string")
            return ""
        if pattern is not None and not pattern.match(value):
            self.err(where, f"'{key}' = {value!r} does not match {pattern.pattern}")
        return value

    def hours(self, data: dict[str, object], key: str, where: str) -> float:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            self.err(where, f"'{key}' must be a number >= 0")
            return 0.0
        return float(value)

    def string_list(self, data: dict[str, object], key: str, where: str) -> None:
        if key not in data:
            return
        for i, item in enumerate(self.lst(data[key], f"{where}.{key}")):
            if not isinstance(item, str) or not item.strip():
                self.err(f"{where}.{key}[{i}]", "must be a non-empty string")


def parse_estimate(raw: object) -> Estimate:
    """Turn decoded JSON into an :class:`Estimate`, raising :class:`EstimateError` with all problems."""
    p = _Parser()
    root = p.obj(raw, "estimate")
    cr_id = p.text(root, "cr_id", "estimate", CR_ID_RE)
    title = p.text(root, "title", "estimate")
    if root.get("unit", "hours") != "hours":
        p.err("estimate", "'unit' must be 'hours'")
    for key in ("assumptions", "exclusions", "risks", "open_questions"):
        p.string_list(root, key, "estimate")

    requirements: list[Requirement] = []
    for i, item in enumerate(p.lst(root.get("requirements"), "estimate.requirements")):
        where = f"requirements[{i}]"
        data = p.obj(item, where)
        in_scope = data.get("in_scope", True)
        if not isinstance(in_scope, bool):
            p.err(where, "'in_scope' must be true or false")
            in_scope = True
        requirements.append(
            Requirement(p.text(data, "id", where, REQ_ID_RE), p.text(data, "title", where), in_scope)
        )
    if not requirements:
        p.err("estimate", "'requirements' must not be empty")

    known_reqs = {r.id for r in requirements}
    seen_ids: set[str] = set()

    def unique(item_id: str, where: str) -> None:
        if item_id and item_id in seen_ids:
            p.err(where, f"duplicate id {item_id!r}")
        seen_ids.add(item_id)

    for r in requirements:
        unique(r.id, "requirements")

    packages: list[WorkPackage] = []
    for i, item in enumerate(p.lst(root.get("work_packages"), "estimate.work_packages")):
        where = f"work_packages[{i}]"
        data = p.obj(item, where)
        wp_id = p.text(data, "id", where, WP_ID_RE)
        unique(wp_id, where)
        req_ids: list[str] = []
        for j, req in enumerate(p.lst(data.get("req_ids"), f"{where}.req_ids")):
            if not isinstance(req, str) or req not in known_reqs:
                p.err(f"{where}.req_ids[{j}]", f"unknown requirement {req!r}")
            else:
                req_ids.append(req)
        tasks: list[Task] = []
        for j, task_item in enumerate(p.lst(data.get("tasks"), f"{where}.tasks")):
            twhere = f"{where}.tasks[{j}]"
            tdata = p.obj(task_item, twhere)
            task_id = p.text(tdata, "id", twhere, TASK_ID_RE)
            unique(task_id, twhere)
            if wp_id and task_id and not task_id.startswith(wp_id + "."):
                p.err(twhere, f"task id {task_id!r} is not under work package {wp_id!r}")
            category = p.text(tdata, "category", twhere)
            if category and category not in CATEGORIES:
                p.err(twhere, f"'category' = {category!r}, expected one of {', '.join(CATEGORIES)}")
            o = p.hours(tdata, "optimistic", twhere)
            m = p.hours(tdata, "most_likely", twhere)
            pe = p.hours(tdata, "pessimistic", twhere)
            if not o <= m <= pe:
                p.err(twhere, f"hours must satisfy optimistic <= most_likely <= pessimistic ({o}, {m}, {pe})")
            if pe == 0:
                p.err(twhere, "'pessimistic' must be greater than 0")
            tasks.append(Task(task_id, p.text(tdata, "title", twhere), category, o, m, pe))
        if not tasks:
            p.err(where, "'tasks' must not be empty")
        packages.append(WorkPackage(wp_id, p.text(data, "title", where), tuple(req_ids), tuple(tasks)))
    if not packages:
        p.err("estimate", "'work_packages' must not be empty")

    covered = {req for wp in packages for req in wp.req_ids}
    for r in requirements:
        if r.in_scope and r.id and r.id not in covered:
            p.err("requirements", f"in-scope requirement {r.id} is not covered by any work package")
        if not r.in_scope and r.id in covered:
            p.err("requirements", f"out-of-scope requirement {r.id} is referenced by a work package")

    if p.errors:
        raise EstimateError(p.errors)
    return Estimate(cr_id, title, tuple(requirements), tuple(packages))


def _h(value: float) -> str:
    """Computed hours (expected values, totals), one decimal."""
    return f"{value:.1f}"


def _in(value: float) -> str:
    """Input hours (O/M/P), two decimals so quarter hours are shown exactly."""
    return f"{value:.2f}"


def render_markdown(est: Estimate) -> str:
    """WBS table, breakdown by category and totals, ready to paste into 03_estimate.md."""
    lines = [
        "### Work breakdown structure",
        "",
        "Hours: O = optimistic, M = most likely, P = pessimistic, E = PERT expected (O + 4M + P) / 6.",
        "",
        "| ID | Work item | Category | O | M | P | E |",
        "|---|---|---|--:|--:|--:|--:|",
    ]
    for wp in est.work_packages:
        reqs = ", ".join(wp.req_ids)
        lines.append(f"| **{wp.id}** | **{wp.title}** ({reqs}) | | | | | **{_h(wp.expected)}** |")
        for t in wp.tasks:
            lines.append(
                f"| {t.id} | {t.title} | {t.category} | {_in(t.optimistic)} | {_in(t.most_likely)} "
                f"| {_in(t.pessimistic)} | {_h(t.expected)} |"
            )
    tasks = est.tasks
    lines.append(
        f"| **1** | **Total** | | {_in(sum(t.optimistic for t in tasks))} "
        f"| {_in(sum(t.most_likely for t in tasks))} | {_in(sum(t.pessimistic for t in tasks))} "
        f"| **{_h(est.expected)}** |"
    )

    lines += ["", "### Effort by category", "", "| Category | E (h) | Share |", "|---|--:|--:|"]
    for category in CATEGORIES:
        hours = sum(t.expected for t in tasks if t.category == category)
        if hours:
            share = hours / est.expected * 100 if est.expected else 0.0
            lines.append(f"| {category} | {_h(hours)} | {share:.0f}% |")

    lines += [
        "",
        "### Totals",
        "",
        "| Measure | Hours |",
        "|---|--:|",
        f"| Expected effort (~P50) | **{_h(est.expected)}** |",
        "| Standard deviation (tasks correlated within a package, packages independent) "
        f"| {_h(est.std_dev)} |",
        f"| P90 (90% confidence the work fits) | **{_h(est.p90)}** |",
        f"| Range (all optimistic - all pessimistic) | {_h(sum(t.optimistic for t in tasks))} - "
        f"{_h(sum(t.pessimistic for t in tasks))} |",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a change-request estimate.json.")
    parser.add_argument("path", type=Path, help="path to estimate.json")
    parser.add_argument("--markdown", action="store_true", help="print WBS and totals as Markdown")
    args = parser.parse_args(argv)
    path: Path = args.path
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    try:
        estimate = parse_estimate(raw)
    except EstimateError as exc:
        for line in exc.errors:
            print(f"invalid: {line}", file=sys.stderr)
        return 1
    if args.markdown:
        sys.stdout.write(render_markdown(estimate))
    else:
        print(
            f"OK {estimate.cr_id}: {len(estimate.tasks)} tasks, "
            f"E={_h(estimate.expected)} h, P90={_h(estimate.p90)} h"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
