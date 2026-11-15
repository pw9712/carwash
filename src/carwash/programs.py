"""Wash programs: sequences of steps, each step runs a set of devices."""

from __future__ import annotations

from dataclasses import dataclass

from carwash.model import DeviceId

D = DeviceId


@dataclass(frozen=True)
class WashStep:
    name: str
    duration_ticks: int
    devices: tuple[DeviceId, ...]


@dataclass(frozen=True)
class WashProgram:
    name: str
    steps: tuple[WashStep, ...]

    @property
    def total_ticks(self) -> int:
        return sum(step.duration_ticks for step in self.steps)

    def required_devices(self) -> list[DeviceId]:
        """All devices used by any step (no duplicates, stable order)."""
        result: list[DeviceId] = []
        for step in self.steps:
            for device in step.devices:
                if device not in result:
                    result.append(device)
        return result

    def is_valid(self) -> bool:
        return bool(self.steps) and all(step.duration_ticks > 0 for step in self.steps)


BASIC = WashProgram(
    "basic",
    (
        WashStep("prewash", 3, (D.CONVEYOR, D.WATER_PUMP)),
        WashStep("rinse", 3, (D.CONVEYOR, D.WATER_PUMP)),
        WashStep("dry", 3, (D.CONVEYOR, D.DRYER)),
    ),
)

STANDARD = WashProgram(
    "standard",
    (
        WashStep("prewash", 2, (D.CONVEYOR, D.WATER_PUMP)),
        WashStep("foam", 3, (D.CONVEYOR, D.CHEMICAL_DISPENSER)),
        WashStep("brushing", 4, (D.CONVEYOR, D.BRUSHES, D.WATER_PUMP)),
        WashStep("rinse", 2, (D.CONVEYOR, D.WATER_PUMP)),
        WashStep("dry", 3, (D.CONVEYOR, D.DRYER)),
    ),
)

PREMIUM = WashProgram(
    "premium",
    (
        WashStep("prewash", 2, (D.CONVEYOR, D.WATER_PUMP)),
        WashStep("foam", 3, (D.CONVEYOR, D.CHEMICAL_DISPENSER)),
        WashStep("brushing", 5, (D.CONVEYOR, D.BRUSHES, D.WATER_PUMP)),
        WashStep("rinse", 2, (D.CONVEYOR, D.WATER_PUMP)),
        WashStep("wax", 2, (D.CONVEYOR, D.CHEMICAL_DISPENSER, D.WATER_PUMP)),
        WashStep("dry", 5, (D.CONVEYOR, D.DRYER)),
    ),
)

ALL_PROGRAMS: tuple[WashProgram, ...] = (BASIC, STANDARD, PREMIUM)


def by_name(name: str) -> WashProgram | None:
    lowered = name.strip().lower()
    return next((p for p in ALL_PROGRAMS if p.name == lowered), None)
