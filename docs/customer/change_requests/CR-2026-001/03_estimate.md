# CR-2026-001: Estimate

**Title:** Car wash emulator changes - winter season
**Source:** `source/email.txt`
**Estimate version:** 1 (2026-11-24)
**Unit:** hours (one developer familiar with the codebase)

## Summary

| Measure | Hours |
|---|--:|
| Expected effort (~P50) | 66.1 |
| P90 (90% confidence the work fits) | 76.2 |

The estimate covers all six items of the e-mail. Items 4 and 5 are estimated in their
rule-compliant form (virtual clock, simulated opt-in payment) and item 6 only as a
time-boxed investigation. The main cost drivers are the `frozen` pump fault (abort in
any step and seed-compatible chaos), the simulated payment state machine and the CSV
export with a virtual clock. Most of the P90 margin comes from open questions on these
three packages (Q-03/Q-04/Q-06, Q-19, Q-17/Q-18). The client's priority items 1-3 are
work packages 1.1, 1.2 and 1.3.

## Scope

| Requirement | Title | In scope | Work package |
|---|---|---|---|
| REQ-01 | `eco` program with rinse and dry steps only | yes | 1.1 |
| REQ-02 | `eco` program lasts at most 6 ticks | yes | 1.1 |
| REQ-03 | `eco` available like the other programs | yes | 1.1 |
| REQ-04 | New `frozen` fault type for the pump | yes | 1.2 |
| REQ-05 | Frozen pump has zero pressure | yes | 1.2 |
| REQ-06 | Frozen pump aborts the wash | yes | 1.2 |
| REQ-07 | `frozen` can be raised in chaos mode | yes | 1.2 |
| REQ-08 | Chemical consumption since last refill in status | yes | 1.3 |
| REQ-09 | Event log export to a CSV file | yes | 1.4 |
| REQ-10 | Date and time for each logged event | yes, virtual clock only (see Exclusions) | 1.4 |
| REQ-11 | Wash starts only after payment | yes, simulated opt-in only (see Exclusions) | 1.5 |
| REQ-12 | Emulator runs faster | yes, investigation only (see Exclusions) | 1.6 |
| REQ-13 | Items 1-3 deployed by the end of January | yes | 1.7 |

## Estimate

### Work breakdown structure

Hours: O = optimistic, M = most likely, P = pessimistic, E = PERT expected (O + 4M + P) / 6.

| ID | Work item | Category | O | M | P | E |
|---|---|---|--:|--:|--:|--:|
| **1.1** | **eco wash program** (REQ-01, REQ-02, REQ-03) | | | | | **5.1** |
| 1.1.1 | Design eco timeline (rinse/dry split, dryer warm-up) | analysis | 0.25 | 0.50 | 1.50 | 0.6 |
| 1.1.2 | Add ECO program and register it in ALL_PROGRAMS | implementation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.1.3 | Add eco to the program list in HELP_TEXT | implementation | 0.10 | 0.25 | 0.50 | 0.3 |
| 1.1.4 | Unit tests: total ticks, no chemicals, lookup, help, start eco | unit-tests | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.1.5 | Scenario eco_wash.txt (steps, chemicals idle, completion boundary) | scenario-tests | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.1.6 | README program list | documentation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.1.7 | architecture.md, scenarios.md, fault-model.md (programs, tank usage) | documentation | 0.25 | 0.50 | 1.50 | 0.6 |
| 1.1.8 | Program timelines | documentation | 0.10 | 0.25 | 0.50 | 0.3 |
| 1.1.9 | Quality gate | review | 0.25 | 0.50 | 1.50 | 0.6 |
| **1.2** | **frozen pump fault (fault type, pressure, abort, chaos)** (REQ-04, REQ-05, REQ-06, REQ-07) | | | | | **18.9** |
| 1.2.1 | Design severity, pump-only rule, abort in any step, chaos pool | analysis | 1.00 | 2.00 | 6.00 | 2.5 |
| 1.2.2 | Add FaultType.FROZEN (critical by default) | implementation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.2.3 | Pump-only rule: allowed_devices helper and fault command check | implementation | 0.50 | 1.00 | 3.00 | 1.2 |
| 1.2.4 | WaterPump: 0 bar while frozen, before low_pressure | implementation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.2.5 | Abort on frozen in any step (_apply_fault), single abort count | implementation | 1.00 | 1.50 | 4.00 | 1.8 |
| 1.2.6 | Chaos: explicit fault pool, separate frozen draw keeping old seeds | implementation | 1.00 | 2.00 | 6.00 | 2.5 |
| 1.2.7 | chaos command: optional frozen probability, HELP_TEXT | implementation | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.2.8 | Unit tests: model, pump pressure, fault command validation | unit-tests | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.2.9 | Unit tests: abort in pump, foam and dry steps, start refused | unit-tests | 1.00 | 2.00 | 4.00 | 2.2 |
| 1.2.10 | Unit tests: chaos pump-only, frozen appears, golden seed test | unit-tests | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.2.11 | Scenarios: frozen in pump step, frozen in dry, chaos with seed | scenario-tests | 0.50 | 1.25 | 2.50 | 1.3 |
| 1.2.12 | Regression run of abort scenarios after abort rule change | scenario-tests | 0.25 | 0.50 | 2.00 | 0.7 |
| 1.2.13 | README fault list and pump telemetry | documentation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.2.14 | fault-model.md (types, chaos, determinism), architecture.md (abort rule) | documentation | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.2.15 | Quality gate | review | 0.25 | 0.50 | 1.50 | 0.6 |
| **1.3** | **Chemical consumption since last refill in status** (REQ-08) | | | | | **4.5** |
| 1.3.1 | Design counter vs derived value, placement in status | analysis | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.3.2 | Consumption since refill in ChemicalDispenser | implementation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.3.3 | Show consumption in status (telemetry or render_status line) | implementation | 0.25 | 0.50 | 1.50 | 0.6 |
| 1.3.4 | Unit tests: counting, refill reset, clamping, status text | unit-tests | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.3.5 | Smoke scenario running status after a wash and refill | scenario-tests | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.3.6 | README status example and devices table, architecture.md | documentation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.3.7 | Quality gate | review | 0.25 | 0.50 | 1.50 | 0.6 |
| **1.4** | **Event log CSV export with virtual clock** (REQ-09, REQ-10) | | | | | **13.5** |
| 1.4.1 | Design export trigger, CSV columns, clock model | analysis | 1.00 | 1.50 | 4.00 | 1.8 |
| 1.4.2 | EventLog.write_csv(stream) with stdlib csv | implementation | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.4.3 | export command (file open, newline, OSError), HELP_TEXT | implementation | 1.00 | 2.00 | 4.00 | 2.2 |
| 1.4.4 | Virtual clock: start datetime and tick duration, tick to datetime mapping | implementation | 0.50 | 1.00 | 3.00 | 1.2 |
| 1.4.5 | clock command with Python 3.10 compatible parsing | implementation | 1.00 | 2.00 | 4.00 | 2.2 |
| 1.4.6 | New tests/test_event_log.py (CSV quoting, with and without clock) | unit-tests | 0.50 | 1.50 | 3.00 | 1.6 |
| 1.4.7 | CLI tests: export and clock with tmp_path, error paths | unit-tests | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.4.8 | Scenario: export and clock argument errors | scenario-tests | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.4.9 | README commands and determinism wording | documentation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.4.10 | scenarios.md command table, architecture.md event log and principles | documentation | 0.25 | 0.50 | 1.50 | 0.6 |
| 1.4.11 | Quality gate | review | 0.25 | 0.50 | 1.50 | 0.6 |
| **1.5** | **Simulated payment before start (opt-in)** (REQ-11) | | | | | **15.7** |
| 1.5.1 | Design payment lifecycle (abort, estop, reset, failed start) | analysis | 1.00 | 2.00 | 6.00 | 2.5 |
| 1.5.2 | Payment state, pay(), start check, lifecycle rules | implementation | 1.50 | 3.00 | 8.00 | 3.6 |
| 1.5.3 | Payment state in render_status | implementation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.5.4 | pay and payment on/off commands, HELP_TEXT | implementation | 1.00 | 2.00 | 4.00 | 2.2 |
| 1.5.5 | Unit tests: payment state machine | unit-tests | 2.00 | 3.00 | 5.00 | 3.2 |
| 1.5.6 | CLI tests: pay and payment commands, errors | unit-tests | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.5.7 | Scenarios: start refused without payment, pay then start | scenario-tests | 0.40 | 0.80 | 1.60 | 0.9 |
| 1.5.8 | architecture.md state diagram, scenarios.md commands | documentation | 0.25 | 0.50 | 1.50 | 0.6 |
| 1.5.9 | README states paragraph and commands | documentation | 0.25 | 0.50 | 1.00 | 0.5 |
| 1.5.10 | Quality gate | review | 0.25 | 0.50 | 1.50 | 0.6 |
| **1.6** | **Performance investigation (time-boxed)** (REQ-12) | | | | | **4.4** |
| 1.6.1 | Agree measurable target and benchmark cases with the client | analysis | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.6.2 | Benchmark script outside src/ (perf_counter), baseline run | implementation | 1.00 | 1.50 | 3.00 | 1.7 |
| 1.6.3 | Profile, report findings and optimisation proposal | analysis | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.6.4 | Mention benchmark in README | documentation | 0.10 | 0.25 | 0.50 | 0.3 |
| 1.6.5 | Quality gate (ruff on the script) | review | 0.10 | 0.25 | 0.50 | 0.3 |
| **1.7** | **Integration and delivery** (REQ-01, REQ-02, REQ-03, REQ-04, REQ-05, REQ-06, REQ-07, REQ-08, REQ-09, REQ-10, REQ-11, REQ-12, REQ-13) | | | | | **4.0** |
| 1.7.1 | Consistency pass over shared docs and HELP_TEXT | documentation | 0.25 | 0.50 | 1.50 | 0.6 |
| 1.7.2 | Full regression of all scenarios after merging packages | scenario-tests | 0.50 | 1.00 | 3.00 | 1.2 |
| 1.7.3 | Delivery 1 (items 1-3): PR, review, fixes, merge | review | 0.50 | 1.00 | 2.00 | 1.1 |
| 1.7.4 | Delivery 2 (items 4-6): PR, review, fixes, merge | review | 0.50 | 1.00 | 2.00 | 1.1 |
| **1** | **Total** | | 29.80 | 58.05 | 134.60 | **66.1** |

### Effort by category

| Category | E (h) | Share |
|---|--:|--:|
| analysis | 10.2 | 15% |
| implementation | 24.3 | 37% |
| unit-tests | 13.4 | 20% |
| scenario-tests | 5.8 | 9% |
| documentation | 6.8 | 10% |
| review | 5.6 | 8% |

### Totals

| Measure | Hours |
|---|--:|
| Expected effort (~P50) | **66.1** |
| Standard deviation (tasks correlated within a package, packages independent) | 7.9 |
| P90 (90% confidence the work fits) | **76.2** |
| Range (all optimistic - all pessimistic) | 29.8 - 134.6 |

## Assumptions

No client answers have been received yet; each assumption names the question that
confirms it.

- REQ-01/02: `eco` is rinse + dry with the same devices as in `basic`, at most 6 ticks in total; exact split per Q-01 / Q-14.
- REQ-03: no per-program statistics are needed (Q-02).
- REQ-04: `frozen` is pump-only, critical by default, cleared with the existing `clear` command, no self-thawing (Q-03, Q-05).
- REQ-06: a frozen pump aborts the wash in any step, including `dry` (option b in `02_impact.md`) (Q-04).
- REQ-07: chaos draws `frozen` separately with its own probability (default 0), so existing seeded chaos runs keep their results (Q-06).
- REQ-08: consumption is counted since emulator start until the first refill (Q-07).
- REQ-09: export is an explicit CLI command; columns are time, level, message (Q-08, Q-17).
- REQ-10: date and time come from a configurable virtual clock (start datetime + fixed tick duration), never from the system clock (Q-09, Q-18).
- REQ-11: payment is simulated with a `pay` command and is opt-in (off by default), so existing scripts keep working (Q-10, Q-19).
- REQ-12: only a time-boxed investigation (benchmark, baseline, proposal) is estimated (Q-11, Q-20).
- REQ-13: delivery is phased: items 1-3 by the end of January 2027, items 4-6 in a second delivery (Q-12).
- Scenarios cannot assert telemetry, so the REQ-05 and REQ-08 values are covered by unit tests.

## Risks

- Q-03 / Q-04: if `frozen` must abort as a warning (option c), the state machine change grows and contradicts the "warnings never abort" rule.
- Q-06: if the client wants `frozen` in the same chaos pool, all existing seeded chaos runs change; client scripts relying on seeds may break.
- Q-19: if payment must be mandatory, all 8 scenarios and about 25 tests must be updated (large T4, not estimated).
- Q-17: separate CSV columns (device, fault type) require structured events and changes at all 13 log call sites in `car_wash.py`.
- REQ-12: optimisation effort is open-ended until a target is agreed; it may become a separate change request.
- Several packages edit `HELP_TEXT`, `CarWashConfig` and `render_status`; parallel work may cause merge conflicts.

## Exclusions

- REQ-10 with the real system clock: conflicts with the determinism rule; only the virtual clock alternative is estimated.
- REQ-11 with a real payment terminal: external hardware/protocol, conflicts with the standard-library-only and determinism rules; only the simulated alternative is estimated.
- REQ-12 optimisation work beyond the investigation: to be estimated once a measurable target exists.
- Per-program statistics (Q-02), structured CSV columns (Q-17) and new `expect` forms for telemetry/status are not included.

## Open questions affecting the estimate

See `questions_for_client.md`. Questions that change the numbers above:

- Q-03, Q-04: severity of `frozen` and abort in steps that do not use the pump (affects 1.2.1, 1.2.5, 1.2.9)
- Q-06: chaos seed compatibility (affects 1.2.6, 1.2.7, 1.2.10)
- Q-05, Q-15: pump-only rule and `fault all` behaviour (affects 1.2.3)
- Q-10, Q-19: simulated payment and its lifecycle (affects 1.5.1, 1.5.2, 1.5.5)
- Q-08, Q-09, Q-17, Q-18: CSV trigger, columns and clock model (affects 1.4.1, 1.4.3, 1.4.4)
- Q-11, Q-20: performance target (affects 1.6 and possibly a follow-up CR)
- Q-01, Q-14: eco timeline (affects 1.1.1)
- Q-07, Q-16: consumption start value and placement (affects 1.3.3)
- Q-12: deadline and phasing (affects 1.7.4)

## Method

Three-point estimates per task, PERT expected value `(O + 4M + P) / 6`, totals and P90
computed by `validate_estimate.py`. For the P90, tasks within a work package are treated
as correlated (they share the same requirement and open questions) and work packages as
independent. Baseline hours per building block are in
`.claude/skills/cr-estimate/references/estimation-model.md`.
