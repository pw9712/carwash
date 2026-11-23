# CR-2026-001: Requirements

**Title:** Car wash emulator changes - winter season
**Source:** `source/email.txt` (e-mail)
**Received:** 2026-11-23 (intake date; no date stated in the source)
**Client contact:** Jan Kowalski, Maintenance Manager

## Summary

Ahead of the winter season the client asks for six changes to the emulator. The three
they rank highest are a new short `eco` program (rinse and dry only, no chemicals), a new
`frozen` fault type for the pump that drops pressure to zero and aborts the wash (also
in chaos mode), and total chemical consumption since the last refill in the status
report. Lower-ranked items are a CSV export of the event log with real date and time,
integration with a payment terminal, and a generally faster emulator. Items 1-3 must
be deployed by the end of January.

## Requirements

| ID | Title | Type | Priority | Rule conflict | Scope |
|---|---|---|---|---|---|
| REQ-01 | `eco` program with rinse and dry steps only | functional | Must | - | in |
| REQ-02 | `eco` program lasts at most 6 ticks | constraint | Must | - | in (see Q-01) |
| REQ-03 | `eco` available like the other programs | functional | Must | - | in (see Q-02) |
| REQ-04 | New `frozen` fault type for the pump | functional | Must | - | in (see Q-03, Q-05) |
| REQ-05 | Frozen pump has zero pressure | functional | Must | - | in |
| REQ-06 | Frozen pump aborts the wash | functional | Must | - | in (see Q-03, Q-04) |
| REQ-07 | `frozen` can be raised in chaos mode | functional | Must | - | in (see Q-06) |
| REQ-08 | Chemical consumption since last refill in status | functional | Must | - | in (see Q-07) |
| REQ-09 | Event log export to a CSV file | functional | Could (inferred) | - | in (see Q-08) |
| REQ-10 | Real date and time for each logged event | functional | Could (inferred) | determinism | in, conflicts (see Q-09) |
| REQ-11 | Wash starts only after payment at a terminal | functional | Could (inferred) | stdlib only, determinism (if real hardware) | out-of-scope candidate (see Q-10) |
| REQ-12 | Emulator runs faster | non-functional | Could (inferred) | - | in, not measurable (see Q-11) |
| REQ-13 | Items 1-3 deployed by the end of January | constraint | Must | - | in (see Q-12) |

### REQ-01: `eco` program with rinse and dry steps only

- **Statement:** The emulator shall provide a wash program `eco` that consists only of
  rinse and dry steps and does not use the chemical dispenser.
- **Source:** "A new "eco" program - shorter than basic, no chemicals, rinsing and
  drying only" (e-mail, line 7, item 1)
- **Type / priority:** functional / Must
- **Notes:** "no chemicals" = the `chemicals` device is never started and the tank
  level does not change during `eco`. Steps map to the existing `rinse` and `dry`
  steps of `programs.py`. Questions: Q-01.

### REQ-02: `eco` program lasts at most 6 ticks

- **Statement:** The `eco` program shall last at most 6 ticks in total, which is shorter
  than `basic` (9 ticks).
- **Source:** "shorter than basic, ... at most 6 ticks" (e-mail, line 7, item 1)
- **Type / priority:** constraint / Must
- **Notes:** The exact length and the split between rinse and dry are not given.
  Questions: Q-01.

### REQ-03: `eco` available like the other programs

- **Statement:** The `eco` program shall be selectable and behave in the same way as
  `basic`, `standard` and `premium` (`start eco`, help text, faults, abort, statistics).
- **Source:** "It must be available in the same way as the other programs." (e-mail,
  line 7, item 1)
- **Type / priority:** functional / Must
- **Notes:** Implies README and CLI help updates. Questions: Q-02.

### REQ-04: New `frozen` fault type for the pump

- **Statement:** The emulator shall support a new fault type `frozen` that can be
  injected into the pump (`fault pump frozen ...`).
- **Source:** "In frost the pump nozzles freeze. We ask for a new fault type "frozen"
  for the pump" (e-mail, line 8, item 2)
- **Type / priority:** functional / Must
- **Notes:** New `FaultType.FROZEN` in `model.py`. Whether other devices may freeze and
  how the fault is cleared is open. Questions: Q-03, Q-05.

### REQ-05: Frozen pump has zero pressure

- **Statement:** While the pump carries a `frozen` fault, its pressure telemetry shall
  be 0 bar.
- **Source:** "the pressure should drop to zero" (e-mail, line 8, item 2)
- **Type / priority:** functional / Must
- **Notes:** Compare `low_pressure` (15 bar). Visible in `status`. Related: REQ-04.

### REQ-06: Frozen pump aborts the wash

- **Statement:** When the pump gets a `frozen` fault during a wash, the car wash shall
  go to state `aborted`.
- **Source:** "and the wash must be aborted" (e-mail, line 8, item 2)
- **Type / priority:** functional / Must
- **Notes:** Today only a critical fault on a device required by the current step
  aborts the wash. Open: is `frozen` always critical, and does it abort during a step
  that does not use the pump. Questions: Q-03, Q-04.

### REQ-07: `frozen` can be raised in chaos mode

- **Statement:** The random fault mode (`chaos`) shall be able to raise a `frozen` fault
  on the pump.
- **Source:** "The fault should also be possible in chaos mode." (e-mail, line 8, item 2)
- **Type / priority:** functional / Must
- **Notes:** Must stay deterministic for a given seed. Questions: Q-06.

### REQ-08: Chemical consumption since last refill in status

- **Statement:** The status report shall show the total chemical consumption, in
  percent of the tank, since the last refill.
- **Source:** "In the status report we want to see the total chemical consumption (in
  percent of the tank) since the last refill." (e-mail, line 9, item 3)
- **Type / priority:** functional / Must
- **Notes:** "status report" = `status` command (`render_status`); "refill" = the
  existing `refill` command. Behaviour before the first refill is open. Questions: Q-07.

### REQ-09: Event log export to a CSV file

- **Statement:** The emulator shall save the event log to a CSV file.
- **Source:** "The event log should be saved to a CSV file" (e-mail, line 10, item 4)
- **Type / priority:** functional / Could (inferred: the client ranks only items 1-3 as
  most important)
- **Notes:** Trigger (command or automatic), file path and columns are not given.
  Questions: Q-08.

### REQ-10: Real date and time for each logged event

- **Statement:** Each event in the CSV export shall carry a date and time that service
  staff can compare with the on-site recorder.
- **Source:** "with the real date and time of each event, so that service staff can
  compare it with the on-site recorder" (e-mail, line 10, item 4)
- **Type / priority:** functional / Could (inferred: the client ranks only items 1-3 as
  most important)
- **Notes:** Conflicts with the determinism rule (no system clock). A deterministic
  alternative is a configurable start date/time plus a fixed duration per tick.
  Questions: Q-09.

### REQ-11: Wash starts only after payment at a terminal

- **Statement:** The emulator shall start a wash only after a payment has been
  confirmed by a payment terminal.
- **Source:** "Integration with a payment terminal - the wash should start only after
  payment." (e-mail, line 11, item 5)
- **Type / priority:** functional / Could (inferred: the client ranks only items 1-3 as
  most important)
- **Notes:** A real terminal is an external system/hardware: out-of-scope candidate.
  A simulated payment step (e.g. a `pay` command) would fit the product. Questions: Q-10.

### REQ-12: Emulator runs faster

- **Statement:** The emulator shall run faster (target to be defined).
- **Source:** "In general, the emulator should run faster." (e-mail, line 12, item 6)
- **Type / priority:** non-functional / Could (inferred: the client ranks only items 1-3
  as most important)
- **Notes:** Not testable as written: no operation, baseline or target is given; it may
  mean wall-clock performance or shorter programs. Questions: Q-11.

### REQ-13: Items 1-3 deployed by the end of January

- **Statement:** REQ-01 to REQ-08 shall be delivered and deployed by the end of January.
- **Source:** "Items 1-3 are the most important for us; the deployment deadline is the
  end of January." (e-mail, line 14)
- **Type / priority:** constraint / Must
- **Notes:** Year not stated (assumed January 2027). Unclear whether the deadline also
  covers items 4-6. Questions: Q-12.

## Glossary

| Client term | Project term |
|---|---|
| pump nozzles | pump (`WaterPump`, CLI `pump`) |
| chemicals | chemical dispenser (`ChemicalDispenser`, CLI `chemicals`) |
| program | wash program (`programs.py`) |
| rinsing, drying | steps `rinse`, `dry` |
| fault type "frozen" | new `FaultType.FROZEN` (CLI `frozen`) |
| wash aborted | car wash state `aborted` |
| chaos mode | random fault mode (`chaos` command, `fault_injector.py`) |
| status report | `status` command (`render_status`) |
| refill | `refill` command (`CarWash.refill_chemicals`) |
| event log | event log (`event_log.py`) |
| percent of the tank | tank level in % (`level_percent`) |

## Rule conflicts

- **REQ-10 - determinism** ("no system clock"): stamping events with the real date and
  time makes the output depend on when the run happens; the same script and seed would
  no longer give the same output. Needs a deterministic alternative (see Q-09).
- **REQ-11 - standard library only / determinism**: integrating a real payment terminal
  would need a driver or network protocol (likely a third-party dependency) and
  external, non-reproducible input. A simulated payment command has no conflict
  (see Q-10).

## Out-of-scope candidates

- **REQ-11**: a real payment terminal is an external system/hardware outside this
  emulator. Proposed: out of scope, or replaced by a simulated payment step.
- **REQ-12**: not out of the product, but cannot be scoped or estimated until a
  measurable target is agreed (Q-11).
