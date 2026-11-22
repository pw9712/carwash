---
name: check
description: Run the full local quality gate for carwash (ruff lint, ruff format check, mypy strict, pytest with coverage) exactly as CI does, and report results as a table. Use before committing, before opening a PR, or when the user asks to "check", "verify" or "run CI locally".
---

# /check — local CI gate

Run every step below from the repository root, even if an earlier one fails, so the
report is complete. Use the project virtualenv interpreter:
`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere (`PY` below).

| # | Step   | Command                                  |
|---|--------|------------------------------------------|
| 1 | Lint   | `PY -m ruff check .`                     |
| 2 | Format | `PY -m ruff format --check .`            |
| 3 | Types  | `PY -m mypy`                             |
| 4 | Tests  | `PY -m pytest --cov=carwash -q`          |

## Report

Reply with one table: `step | result (PASS/FAIL) | details`.

- Lint / Types: number of errors and the first few `file:line` locations.
- Format: list of files that would be reformatted.
- Tests: passed/failed counts, names of failing tests, total coverage % and
  whether the 90% threshold (`[tool.coverage.report] fail_under`) was reached;
  list files below 90% with their missing lines.

End with a one-line verdict: ready to commit, or what blocks it.

## Rules

- Do **not** fix anything automatically. If something fails, propose the fix and ask
  before applying it (e.g. `ruff format .` or `ruff check --fix .`).
- Do not change thresholds or tool configuration to make a step pass.
