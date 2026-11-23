# Estimation model (hours)

The reference model `/cr-estimate` uses to turn an impact analysis into a WBS with
three-point hour estimates. All values are **baseline hours for one developer who
knows this codebase** and works with Claude Code. Adjust them in this file when the
team's real effort differs. The skill always reads the current version.

## Method

- Every WBS task gets three estimates: **O** (optimistic), **M** (most likely),
  **P** (pessimistic), with `0 <= O <= M <= P`.
- Expected effort per task (PERT): `E = (O + 4M + P) / 6`, standard deviation `(P - O) / 6`.
- Uncertainty model: tasks inside one work package share causes (same requirement, same
  open questions), so they are treated as **fully correlated**. Work package SD = sum of
  its task SDs. Work packages are treated as **independent** of each other.
- Project totals: `E = sum(E)`, `SD = sqrt(sum(work package SD^2))`, `P90 = E + 1.2816 * SD`.
- Consequence for the WBS: put tasks that depend on the same open question into the same
  work package; splitting them across packages makes the P90 too optimistic.
- Only hours. No rates or costs, and no percentage overheads: review and delivery
  work are explicit WBS tasks (blocks `R1`, `R2`).
- **Never compute totals by hand.** `scripts/validate_estimate.py --markdown` does it.

## WBS structure

```
1          Change request (CR-YYYY-NNN)
1.N        Work package = one requirement, or a few tightly coupled ones
1.N.M      Task = one building block below, applied to concrete files/symbols
1.last     Integration and delivery (regression, PR, review)
```

Task categories (used by the validator): `analysis`, `implementation`, `unit-tests`,
`scenario-tests`, `documentation`, `review`.

## Building blocks

Each task in `estimate.json` cites the block it starts from in its `basis` field,
for example `"basis": "I2; dryer physics is non-trivial, M raised to 1.5"`.

### Analysis

| Block | Task | O | M | P |
|---|---|--:|--:|--:|
| A1 | Detailed design of one requirement (read code, choose approach) | 0.5 | 1 | 2 |
| A2 | Design of a cross-cutting change (state machine, tick order, CLI grammar) | 1 | 2 | 4 |

### Implementation (`src/carwash/`)

| Block | Task | Files | O | M | P |
|---|---|---|--:|--:|--:|
| I1 | New enum value, alias or parser change | `model.py` | 0.25 | 0.5 | 1 |
| I2 | Fault effect or physics change in one existing device | `devices.py` | 0.5 | 1 | 2 |
| I3 | New device: `Device` subclass, telemetry, `DeviceId`, registration in `CarWash` | `model.py`, `devices.py`, `car_wash.py` | 2 | 3 | 6 |
| I4 | New or changed wash program / step | `programs.py` | 0.5 | 1 | 2 |
| I5 | New CLI command or option, including `HELP_TEXT` | `cli.py` | 1 | 2 | 4 |
| I6 | New `expect` assertion form | `cli.py` | 1 | 1.5 | 3 |
| I7 | State machine or tick-order change | `car_wash.py` | 2 | 4 | 8 |
| I8 | `status` output / `render_status` change | `car_wash.py` | 0.5 | 1 | 2 |
| I9 | Fault injector change (scheduling, chaos) | `fault_injector.py` | 1 | 2 | 4 |
| I10 | Event log change | `event_log.py` | 0.5 | 1 | 2 |

### Tests

| Block | Task | Files | O | M | P |
|---|---|---|--:|--:|--:|
| T1 | Unit tests for a small change in one module | `tests/test_<module>.py` | 0.5 | 1 | 2 |
| T2 | Unit tests for a new device or a state machine change | `tests/test_<module>.py` | 2 | 3 | 5 |
| T3 | New scenario script (`/add-scenario`) | `scenarios/*.txt` | 0.25 | 0.5 | 1 |
| T4 | Update existing scenarios / regression after a timeline, state or output change | `scenarios/*.txt` | 0.5 | 1 | 3 |

### Documentation

| Block | Task | Files | O | M | P |
|---|---|---|--:|--:|--:|
| D1 | README update | `README.md` | 0.25 | 0.5 | 1 |
| D2 | Technical docs update | `docs/architecture.md`, `docs/fault-model.md`, `docs/scenarios.md` | 0.25 | 0.5 | 1.5 |
| D3 | Program timelines | `CLAUDE.md`, `docs/scenarios.md` | 0.1 | 0.25 | 0.5 |

### Review and delivery

| Block | Task | O | M | P |
|---|---|--:|--:|--:|
| R1 | Quality gate (`/check`: ruff, format, mypy strict, pytest + 90% coverage) and fixes, per work package | 0.25 | 0.5 | 1.5 |
| R2 | Branch, PR, code review, review fixes, merge (once per CR) | 0.5 | 1 | 2 |

## Change patterns

Typical block combinations for this codebase. Use them as a checklist so no
Definition-of-Done item from `CLAUDE.md` is forgotten, then add or drop blocks
according to the impact analysis.

| Pattern | Blocks |
|---|---|
| New fault type for existing device(s) | A1, I1, I2 (per affected device), T1, T3, D1, D2, R1 |
| New device | A1, I3, I4 (if programs use it), I8, T2, T3, T4, D1, D2, R1 |
| New or changed wash program | A1, I4, T1, T3, T4 (if timelines change), D1, D2, D3, R1 |
| New CLI command / option | A1, I5, T1, T3, D1, D2, R1 |
| New `expect` form | A1, I6, T1, T3, D2 (`docs/scenarios.md`), R1 |
| State machine / tick-order change | A2, I7, T2, T4, D2 (`docs/architecture.md`), R1 |
| Telemetry or `status` change | A1, I2 and/or I8, T1, T4 (if scenarios assert output), D1, R1 |
| Chaos / scheduling change | A1, I9, T1, T3 (with explicit seed), D2 (`docs/fault-model.md`), R1 |
| Documentation only | D1 and/or D2, R1 |

Every estimate ends with an **Integration and delivery** work package: R2, plus T4 when
several work packages touch the same scenarios.

## Adjustment rules

1. **Ambiguity widens P, not M.** If a requirement has an open question, raise P
   (typically x1.5 to x2) and name the question in `basis`.
2. **Reuse lowers M.** If an existing mechanism already covers most of the change
   (e.g. a fault effect identical to `blocked`), lower M and say why.
3. **Several devices or programs.** Repeat I2 / I4 per item, but use about 60% of M
   from the second item on when the change is mechanical.
4. **Project rule conflicts are not estimated silently.** A requirement that needs a
   runtime dependency, threads, the system clock, unseeded randomness or Python > 3.10
   features breaks `CLAUDE.md`. Mark it in `02_impact.md`, add a question for the
   client, and estimate only a compliant alternative (stated as an assumption) or
   leave the requirement out of scope.
5. **Coverage.** Large new code paths may need extra tests to stay above 90%. Add T1
   when the impact analysis shows branches that scenarios alone will not cover.
6. **Granularity.** No task under 0.1 h, and no task with M above 8 h. Split bigger
   tasks.
