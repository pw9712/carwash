# Scenario scripts

Scenario scripts in `scenarios/*.txt` are end-to-end tests: plain CLI commands mixed with
`expect` assertions. `tests/test_scenarios.py` runs every file in that directory
automatically, so adding a scenario means only adding a file.

```bash
pytest -m scenario                               # all scenarios
pytest -m scenario -k chemical_runout            # one scenario
carwash --script scenarios/chemical_runout.txt   # run directly, prints every step
```

## File format

- One command per line, executed top to bottom.
- `#` starts a comment, also at the end of a line. Empty lines are ignored.
- Commands and arguments are case-insensitive.
- `quit` or `exit` stops the script early.
- Each script starts from a fresh car wash: `t=0`, state `idle`, no faults, chemical tank at 100%.

```text
# A critical pump fault in the middle of the brushing step aborts the wash.
# standard: prewash t1-2, foam t3-5, brushing t6-9, rinse t10-11, dry t12-14
start standard
fault pump low_pressure critical at 7
tick 6
expect state washing
tick 1
expect state aborted
expect device pump fault
expect error start standard     # must reset first
```

## Commands

| Command | Effect |
|---|---|
| `start <program>` | Start `basic`, `standard` or `premium`. |
| `tick [n]` (`t`) | Advance `n` ticks (default 1). |
| `run [max]` | Tick until the wash is no longer `washing` (default max 1000). Error if no wash is running. |
| `fault <devices> <type> [warning\|critical] [at <tick> \| in <ticks>]` | Inject a fault now, at an absolute tick (`at`) or after a delay (`in`). Without a severity, `default_severity` is used. |
| `clear <devices> [type]` | Clear one fault type, or all faults, on the given devices. |
| `refill` | Fill the chemical tank to 100% and clear `low_level`. |
| `chaos <p> [seed]` / `chaos off` | Each tick, with probability `p`, inject one random fault (default seed 42). |
| `estop` | Emergency stop. |
| `reset` | Back to `idle` from `completed`, `aborted`, `emergency_stop`. Faults stay. |
| `status` (`s`), `log [n]`, `programs`, `help` (`?`) | Output only, useful when debugging a script. |

`<devices>` is one device, a comma-separated list without spaces (`pump,brushes`),
or `all`. Aliases are accepted: `water_pump`, `chem`, `chemical_dispenser`, `brush`;
fault aliases `comm`, `power`, `sensor`; severity aliases `w`, `warn`, `c`, `crit`.

`fault ... at <tick>` must be in the future (`> t`), otherwise it is a command error.

## Assertions

| Assertion | Passes when |
|---|---|
| `expect state <state>` | Car wash state is `idle`, `washing`, `completed`, `aborted` or `emergency_stop` (alias `estop`). |
| `expect device <dev> <idle\|running\|fault>` | Device state matches. `fault` means a **critical** fault; a device with only warnings is `idle` or `running`. |
| `expect fault <dev> <type>` | The device has this fault type (any severity). |
| `expect no_faults` | No device has any fault. |
| `expect completed <n>` | Exactly `n` washes completed since the start of the script. |
| `expect log <text...>` | Some event message contains the text (case-sensitive substring, without the `[t=..] LEVEL` prefix). |
| `expect error <command...>` | The command fails with a command error. The command **is executed**, so if it unexpectedly succeeds, its side effects stay. |

`expect error` checks command errors only (`error: ...`). A failed `expect` inside it is not
a command error, so `expect error expect ...` does not work.

## Exit codes

Running a script with `--script` (or piping commands to stdin) is non-interactive:

| Code | Meaning |
|---|---|
| `0` | All assertions passed and no command failed. |
| `1` | At least one `FAIL:` or `error:` line. A `SUMMARY:` line is printed at the end. |
| `2` | The script file cannot be opened. |

The script keeps running after a failure, so one run reports all problems.

## Program timelines

A step of N ticks occupies the next N ticks. `start` at `t=0` gives:

| Program | Timeline |
|---|---|
| `basic` (9) | prewash 1–3, rinse 4–6, dry 7–9 |
| `standard` (14) | prewash 1–2, foam 3–5, brushing 6–9, rinse 10–11, dry 12–14 |
| `premium` (19) | prewash 1–2, foam 3–5, brushing 6–10, rinse 11–12, wax 13–14, dry 15–19 |

If the wash starts later (for example after an earlier `run`), shift the timeline by the
start time, or use `fault ... in <ticks>`, which is relative to the current tick.

## Writing good scenarios

- **One behaviour per file**, with a `snake_case` name that says what it checks
  (`pump_failure_during_wash.txt`, `chemical_refill_recovers.txt`).
- **Start with comments**: what the scenario proves and, if faults are scheduled,
  the program timeline.
- **Check intermediate states**, not only the end: use `tick N` + `expect` right before
  and right after the moment that matters.
- **Use `expect error`** for refused operations (start without reset, reset while washing).
- **Use `chaos` only with an explicit seed.** The run is then fully reproducible.
- **Watch step boundaries.** A fault scheduled for the last tick of a step affects
  the next step in the same tick (see [architecture.md](architecture.md#one-tick)).
- **Remember that `reset` keeps faults.** Clear them (or `refill`) before the next `start`.
- When a scenario fails, run it with `carwash --script <file>`
  (events are printed) and add `status` / `log` lines around the failing step.

## Existing scenarios

| File | Covers |
|---|---|
| `happy_path.txt` | All three programs complete without faults. |
| `pump_failure_during_wash.txt` | Critical pump fault during brushing aborts; reset and repair. |
| `emergency_stop.txt` | Operator `estop` in the middle of a wash and recovery. |
| `multiple_faults.txt` | Warnings on several devices; a critical fault on `all`; partial clearing is not enough to start. |
| `chemical_runout.txt` | The tank empties over consecutive `standard` washes; the 7th runs dry during foam. |
| `chemical_warning_does_not_abort.txt` | A chemical warning does not abort an unrelated `basic` wash. |
| `chemical_critical_during_foam.txt` | A scheduled critical chemical fault aborts `standard` in the foam step. |
| `chemical_refill_recovers.txt` | After six washes leave a warning, `refill` allows a full `premium` wash. |

Claude Code users can generate a new scenario with `/add-scenario <description>`.
