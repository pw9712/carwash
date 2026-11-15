"""Scheduled and random ("chaos") fault generation."""

from __future__ import annotations

import random
from dataclasses import dataclass

from carwash.model import DeviceId, FaultType, Severity, default_severity


@dataclass(frozen=True)
class FaultRequest:
    device: DeviceId
    type: FaultType
    severity: Severity

    def __str__(self) -> str:
        return f"{self.device} {self.type} ({self.severity})"


@dataclass(frozen=True)
class ScheduledFault:
    at_tick: int
    fault: FaultRequest


class FaultInjector:
    """Holds faults scheduled for a given simulation time and an optional
    random fault generator. ``random.Random(seed)`` gives the same sequence
    on every platform, so chaos runs are reproducible."""

    def __init__(self) -> None:
        self._scheduled: list[ScheduledFault] = []
        self._random_probability = 0.0
        self._rng = random.Random(0)

    def schedule(self, at_tick: int, fault: FaultRequest) -> None:
        self._scheduled.append(ScheduledFault(at_tick, fault))
        self._scheduled.sort(key=lambda s: s.at_tick)  # stable: keeps order for same tick

    def collect_due(self, now: int) -> list[FaultRequest]:
        """Removes and returns faults due at ``now`` (scheduled ones first,
        then possibly one random fault)."""
        due = [s.fault for s in self._scheduled if s.at_tick <= now]
        self._scheduled = [s for s in self._scheduled if s.at_tick > now]

        if self.random_faults_enabled and self._rng.random() < self._random_probability:
            device = self._rng.choice(list(DeviceId))
            fault_type = self._rng.choice(list(FaultType))
            due.append(FaultRequest(device, fault_type, default_severity(fault_type)))
        return due

    @property
    def scheduled(self) -> tuple[ScheduledFault, ...]:
        return tuple(self._scheduled)

    def clear_scheduled(self) -> None:
        self._scheduled.clear()

    def enable_random_faults(self, probability_per_tick: float, seed: int) -> None:
        self._random_probability = min(1.0, max(0.0, probability_per_tick))
        self._rng.seed(seed)

    def disable_random_faults(self) -> None:
        self._random_probability = 0.0

    @property
    def random_faults_enabled(self) -> bool:
        return self._random_probability > 0.0

    @property
    def random_probability(self) -> float:
        return self._random_probability
