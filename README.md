# Car Wash Emulator

A simple, deterministic car wash emulator written in Python, with the ability
to inject faults into one or more devices. The project is meant as a playground
for CI/CD experiments: it comes with unit tests and scenario tests (pytest),
linting (ruff) and type checking (mypy, strict mode). It has no runtime
dependencies outside the standard library.

## Model

**Devices** (`src/carwash/devices.py`)

| CLI name    | Device               | Telemetry                      |
|-------------|----------------------|--------------------------------|
| `pump`      | high-pressure pump   | pressure (80 bar, 15 with `low_pressure`) |
| `chemicals` | chemical dispenser   | tank level, consumption 5%/tick |
| `brushes`   | brushes              | speed (120 rpm, 40 with `blocked`) |
| `dryer`     | dryer                | temperature (heats up / cools down) |
| `conveyor`  | conveyor             | speed (6 m/min, 2 with `blocked`) |

Each device is `idle`, `running` or `fault`, and can carry any number of
faults at the same time:

- **warning** – the device keeps working, but in a degraded way (e.g. lower pressure),
- **critical** – the device shuts down and cannot be started until the fault is cleared.

Fault types: `comm_lost`, `overheat`, `low_pressure`, `blocked`, `low_level`,
`power_failure`, `sensor_error`. The chemical dispenser raises `low_level`
on its own (warning below 15%, critical at 0%).

**Wash programs** (`basic` 9 ticks, `standard` 14, `premium` 19) are sequences
of steps; each step runs only the devices it needs.

**Car wash states:** `idle` → `washing` → `completed`, or `aborted` (critical
fault on a device required by the current step) / `emergency_stop`. To leave
`aborted` or `emergency_stop`, use the `reset` command (faults are not cleared by it).

Time is discrete (ticks), with no threads and no system clock – every run is
fully reproducible, including random fault mode (`chaos`) with the same seed.

## Installation

Requires Python ≥ 3.10.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -e ".[dev]"
```

## Running

```bash
carwash                                   # interactive mode
carwash --script scenarios/happy_path.txt
python -m carwash < commands.txt          # without installing: set PYTHONPATH=src
```

Example session:

```
carwash> start standard
carwash> fault conveyor blocked warning          # fault right now
carwash> fault pump,brushes overheat in 5        # two devices, in 5 ticks
carwash> fault all power_failure at 100          # all devices at t=100
carwash> chaos 0.05 1234                         # random faults, p=5%/tick, seed 1234
carwash> tick 3
carwash> status
=== CAR WASH === t=6  state=washing  completed=0  aborted=0
Program: standard  step 3/5 'brushing'  (3 ticks left)
DEVICE     STATE    FAULTS                            TELEMETRY
pump       RUNNING  -                                 pressure=80.0 bar
chemicals  IDLE     -                                 level=85.0%
brushes    RUNNING  -                                 rpm=120
dryer      IDLE     -                                 temp=20.0 C
conveyor   RUNNING  blocked(W)                        speed=2.0 m/min
carwash> clear all
carwash> reset
```

Full list of commands: `help` or `carwash --help`.

## Tests and code quality

```bash
pytest                    # all tests
pytest -m scenario        # scenarios only
pytest -m "not scenario"  # unit tests only
pytest --cov=carwash      # with code coverage
ruff check .              # lint
ruff format --check .     # formatting
mypy                      # types (strict)
```

## Scenario tests

Files in `scenarios/*.txt` are plain lists of commands with `expect` assertions:

```
start standard
fault pump low_pressure critical at 7
run
expect state aborted
expect device pump fault
expect error start standard     # this command MUST fail
```

In non-interactive mode the emulator exits with code `1` if any assertion
fails or any command returns an error. Every file in `scenarios/` is run
automatically by `tests/test_scenarios.py` – to add a new scenario, just
drop a file into the directory.

## Project layout

```
src/carwash/
  model.py           enums and types (devices, faults, severity)
  devices.py         devices and their simulation
  programs.py        wash programs
  fault_injector.py  scheduled and random faults
  event_log.py       event log
  car_wash.py        car wash controller + status report
  cli.py             command interpreter and entry point
tests/               pytest tests
scenarios/           scenario test scripts
```
