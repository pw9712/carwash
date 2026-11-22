---
name: add-scenario
description: Create a new end-to-end scenario script in scenarios/ for the carwash emulator from a plain-language description, then run it. Use when the user wants a new scenario test, to reproduce a bug as a scenario, or to cover a fault/program combination end to end.
argument-hint: <description of the behaviour to cover>
---

# /add-scenario — new scenario test

Input: `$ARGUMENTS` — what the scenario should demonstrate.

## Steps

1. Read 2–3 existing files in `scenarios/` (e.g. `happy_path.txt`,
   `pump_failure_during_wash.txt`) and the `HELP_TEXT` in `src/carwash/cli.py`
   to use only commands and `expect` forms that actually exist.
2. Check `scenarios/` for a scenario that already covers the behaviour; if one does,
   say so and propose extending it instead.
3. Pick a `snake_case` file name describing the behaviour, e.g.
   `dryer_overheat_aborts_premium.txt`.
4. Write the file:
   - Start with `#` comments: what it checks and, if faults are scheduled, the
     program timeline (see CLAUDE.md, "Program timelines").
   - Use `tick N` + `expect` to assert intermediate states, not only the end state.
   - Use `expect error <command>` for commands that must fail.
   - Use `chaos` only with an explicit seed.
5. Run it: `PY -m pytest -m scenario -k <file stem> -q`
   (`PY` = `.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere).
   On failure, rerun with `PY -m carwash --echo --script scenarios/<file>.txt`
   to see where it diverges.
6. If the scenario fails because of a real bug in `src/`, do not change the
   expectations to make it pass — report the bug and ask how to proceed.

## Report

File path, a short summary of what it covers, and the test result.
No registration is needed: `tests/test_scenarios.py` picks the file up automatically.
