# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

Deterministic car wash emulator with fault injection (Python ≥ 3.10, src layout,
package `carwash`). It is a playground for CI/CD experiments, so code quality
gates matter as much as the features. See `README.md` for the domain model and CLI commands.

## Commands

Use the project virtualenv (`.venv`). On Windows the interpreter is
`.venv/Scripts/python.exe`, on Linux/macOS `.venv/bin/python`.

```bash
pip install -e ".[dev]"   # setup
pytest                    # all tests
pytest -m scenario        # scenario scripts only
pytest -m "not scenario"  # unit tests only
pytest --cov=carwash      # coverage, fails below 90% (pyproject.toml)
ruff check .              # lint
ruff format --check .     # formatting
mypy                      # strict type check of src/
carwash --script scenarios/happy_path.txt   # run one scenario through the CLI
```

Before finishing a change, all of the above must pass, exactly as in CI
(`/check` runs them in one go).

## Architecture

Dependencies go one way, top to bottom:

```
model.py           enums and types: DeviceId, FaultType, Severity, parse_* helpers
devices.py         device classes and their per-tick simulation
programs.py        wash programs (BASIC / STANDARD / PREMIUM) as sequences of WashStep
fault_injector.py  scheduled faults and seeded random ("chaos") faults
event_log.py       event log
car_wash.py        CarWash controller (state machine) + render_status
cli.py             command interpreter, `expect` assertions, entry point main()
```

Program timelines (ticks are 1-based; useful when scheduling faults):

- `basic` (9): prewash 1-3, rinse 4-6, dry 7-9
- `standard` (14): prewash 1-2, foam 3-5, brushing 6-9, rinse 10-11, dry 12-14
- `premium` (19): prewash 1-2, foam 3-5, brushing 6-10, rinse 11-12, wax 13-14, dry 15-19

## Rules

- **No runtime dependencies**: standard library only. Dev tools go to `[project.optional-dependencies].dev`.
- **Determinism**: no threads, no system clock, no unseeded `random`. Same input + seed = same output.
- **Typing**: mypy `strict = true`; every function fully annotated, no `Any` leaks, avoid `# type: ignore`.
- **Style**: ruff, line length 110, target py310 (`X | None`, not `Optional[X]`).
- **Tests**: every behaviour change gets a unit test in `tests/test_<module>.py`; user-visible
  behaviour also gets a scenario in `scenarios/` (use `/add-scenario`).
- **Scenarios** are auto-discovered by `tests/test_scenarios.py`; never register them manually.
- Keep `README.md` in sync when CLI commands, devices, faults or programs change.

## Change requests

Customer change requests are analysed with `/change-request` (stages `/cr-intake`,
`/cr-impact`, `/cr-estimate`); see `docs/change-requests.md`. Estimates are in hours only.
CR data (source documents, requirements, impact analyses, estimates) lives in
`docs/customer/change_requests/` and is versioned in git, like the rest of the docs.
Tune estimates in `.claude/skills/cr-estimate/references/estimation-model.md`.

## CI

`.github/workflows/tests.yml` runs three jobs on every push / PR (Python 3.10):
`lint` (ruff check), `mypy`, `pytest` (with coverage threshold).
Local Python may be newer, so avoid syntax or stdlib APIs newer than 3.10.

## Git

- Never commit directly to `main`; work on a branch (`test/...`, `ai/...`) and open a PR.
- Commit messages: English, imperative, short (`Add ...`, `Update ...`, `Fix ...`).
- `prompts/` and `tmp/` are local-only (gitignored).
