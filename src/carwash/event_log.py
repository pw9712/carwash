"""Append-only log of what happened in the car wash."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class EventLevel(Enum):
    INFO = "INFO"
    WARNING = "WARN"
    ERROR = "ERROR"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Event:
    time: int
    level: EventLevel
    message: str

    def __str__(self) -> str:
        return f"[t={self.time}] {self.level} {self.message}"


Listener = Callable[[Event], None]


class EventLog:
    """Stores events; an optional listener is notified about each new one (used by the CLI)."""

    def __init__(self) -> None:
        self._events: list[Event] = []
        self.listener: Listener | None = None

    def add(self, time: int, level: EventLevel, message: str) -> None:
        event = Event(time, level, message)
        self._events.append(event)
        if self.listener is not None:
            self.listener(event)

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def count(self, level: EventLevel) -> int:
        return sum(1 for e in self._events if e.level is level)

    def contains(self, fragment: str) -> bool:
        return any(fragment in e.message for e in self._events)

    def clear(self) -> None:
        self._events.clear()
