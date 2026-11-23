# CR-2026-001: Impact analysis

**Based on:** `01_requirements.md` (no client answers yet)
**Codebase:** branch `ai/cr-tooling`, commit `5ed0fbb`

## Summary

| Requirement | Change pattern | Modules | Unit tests | Scenarios (new / affected) | Docs | Rules |
|---|---|---|---|---|---|---|
| REQ-01 | New wash program | programs | test_programs, test_car_wash | 1 / 0 | README, architecture, scenarios, fault-model, CLAUDE.md | OK |
| REQ-02 | New wash program (part of REQ-01) | programs | test_programs | (in REQ-01) / 0 | timelines (with REQ-03) | OK |
| REQ-03 | New wash program (help + docs) | programs, cli | test_programs, test_cli | 0-1 / 0 | HELP_TEXT, README, architecture, scenarios, CLAUDE.md | OK |
| REQ-04 | New fault type | model, cli or car_wash (pump-only check) | test_model, test_cli | 1 / 0 | README, fault-model, architecture, HELP_TEXT | OK |
| REQ-05 | Telemetry / status | devices | test_devices | 0 / 0 | README, architecture, fault-model | OK |
| REQ-06 | Reuse (option a) or small state machine change (option b) | car_wash | test_car_wash | 1-2 / 0 (option b: regression run of abort scenarios) | architecture, fault-model | OK |
| REQ-07 | Chaos / scheduling change | fault_injector, model, (cli) | test_fault_injector | 1 / 0 | fault-model, HELP_TEXT, README | OK (seeded outcomes, see Q-06) |
| REQ-08 | Telemetry / status | devices, (car_wash) | test_devices, test_car_wash | 0-1 / 0 | README, architecture | OK |
| REQ-09 | New CLI command | event_log, cli | test_event_log (new file), test_cli | 0 / 0 | README, scenarios, architecture, HELP_TEXT | OK |
| REQ-10 | Custom: compliant alternative (virtual clock) | event_log, car_wash, cli | test_event_log, test_car_wash, test_cli | 0-1 / 0 | README, architecture, scenarios, HELP_TEXT | CONFLICT: determinism |
| REQ-11 | State machine change (simulated, opt-in) | car_wash, cli, (programs) | test_car_wash, test_cli | 1-2 / 0 (if mandatory: 8 / 8) | architecture, scenarios, README, HELP_TEXT | CONFLICT: stdlib only, determinism (real terminal) |
| REQ-12 | Custom: time-boxed investigation | unknown until target is set | existing tests as regression net | 0 / 0 | README (benchmark) | OK (clock only outside `src/`) |
| REQ-13 | None (schedule constraint) | - | - | - | - | OK |

## REQ-01: `eco` program with rinse and dry steps only

- **Change pattern:** New or changed wash program.
- **Code changes:**
  - `src/carwash/programs.py`: new `ECO = WashProgram("eco", (WashStep("rinse", n, (D.CONVEYOR, D.WATER_PUMP)), WashStep("dry", m, (D.CONVEYOR, D.DRYER))))`, same device tuples as the `rinse` / `dry` steps of `BASIC` (`programs.py:45-46`).
  - No change in `devices.py` or `car_wash.py`: `CHEMICAL_DISPENSER` is in no eco step, so `CarWash._enter_step` never starts it and the tank level stays unchanged.
- **Unit tests:** `tests/test_programs.py` (`test_total_ticks` entry, chemicals not in `ECO.required_devices()`); `tests/test_car_wash.py` (eco wash completes, `chemicals.level_percent == 100.0`).
- **Scenarios:** new `scenarios/eco_wash.txt` (devices running per step, `expect device chemicals idle`, `expect state completed`). None break.
- **Docs:** see REQ-03.
- **Rule check:** OK.
- **Complexity notes:** easier than the pattern; pure data. The `architecture.md` "Extending" section already describes the steps. Two code-level observations became questions:
  - `CarWash._check_can_start` checks only devices of the chosen program, so `start eco` works with an empty / critically faulted chemical tank (as `basic` does today) - Q-13.
  - `Dryer` heats 10 C per tick from 20 C to 60 C, so a dry step shorter than 4 ticks never reaches working temperature (basic's 3-tick dry peaks at 50 C) - Q-14.

## REQ-02: `eco` program lasts at most 6 ticks

- **Change pattern:** part of REQ-01 (same `WashProgram` literal); estimate in the same work package.
- **Code changes:** only the `duration_ticks` values in `ECO`. `WashProgram.total_ticks` derives the total; `is_valid` requires each step > 0 ticks (minimum 2 ticks).
- **Unit tests:** assert `programs.ECO.total_ticks <= 6 < programs.BASIC.total_ticks`.
- **Scenarios:** boundary check in `eco_wash.txt` (`tick <total-1>` -> `washing`, `tick 1` -> `completed`).
- **Docs:** timeline row (see REQ-03).
- **Rule check:** OK.
- **Complexity notes:** depends on Q-01 / Q-14 only.

## REQ-03: `eco` available like the other programs

- **Change pattern:** New or changed wash program (help and docs part).
- **Code changes:**
  - `src/carwash/programs.py:73` `ALL_PROGRAMS`: add `ECO`. There is no program enum or `parse_*` helper; `programs.by_name()` resolves names from `ALL_PROGRAMS`, so `start eco`, faults, abort, `estop`, `reset` and the `completed_washes` / `aborted_washes` counters work without changes.
  - `src/carwash/cli.py:36` `HELP_TEXT`: the program list `(basic|standard|premium)` is hard-coded; add `eco` (optionally derive it from `ALL_PROGRAMS`). `HELP_TEXT` is also the argparse epilog, so `--help` changes too.
- **Unit tests:** `tests/test_programs.py::test_lookup_by_name` (`by_name("ECO")`); `tests/test_cli.py::test_help_and_programs` extended with `eco`, plus `start eco`.
- **Scenarios:** no scenario asserts the program list or help output; nothing breaks. Optional `eco_pump_failure_aborts.txt`. Keep `happy_path.txt` unchanged (one behaviour per file).
- **Docs:** `README.md:31` (program list), `docs/architecture.md` (mermaid line 22, programs table 126-130), `docs/scenarios.md` (commands table, timelines 86-90, existing scenarios table), `docs/fault-model.md:64-65` (tank usage per program), `CLAUDE.md` (architecture line and program timelines), `HELP_TEXT`.
- **Rule check:** OK.
- **Complexity notes:** most of the effort is documentation in six places. Per-program statistics (Q-02) do not exist today (`completed_washes` is a single counter); if wanted, they add `car_wash.py` + `render_status` work and possibly a new `expect` form.

## REQ-04: New `frozen` fault type for the pump

- **Change pattern:** New fault type for existing device(s).
- **Code changes:**
  - `src/carwash/model.py` `FaultType`: new member `FROZEN = "frozen"`. `default_severity` falls back to `CRITICAL` (`model.py:109-113`), so no change if frozen is critical (Q-03).
  - Pump-only restriction (if Q-05 = pump only): today any fault type can go on any device and there is no per-device check. New helper (e.g. `allowed_devices(fault_type)`) in `model.py`, checked in `cli.py` `CommandProcessor._cmd_fault` or in `CarWash.inject_fault` / `schedule_fault`. Layering OK.
  - Clearing: `clear` works unchanged (`Device.clear_fault`). Self-thawing would need a counter in `WaterPump._on_tick`, and `CarWash._log_new_faults` logs only new faults, so a thaw would need extra logging.
- **Unit tests:** `tests/test_model.py` (`test_fault_type_round_trip` is parametrised over `FaultType` and covers it automatically; extend `test_default_severity`); `tests/test_cli.py` (`fault pump frozen`, rejection of other devices if pump-only).
- **Scenarios:** new `scenarios/pump_frozen_during_wash.txt`. None break.
- **Docs:** `README.md:27-28` (fault list), `docs/fault-model.md` (type table; line 33 "any fault type on any device" if pump-only), `docs/architecture.md:118`, `HELP_TEXT` `Faults:` line.
- **Rule check:** OK.
- **Complexity notes:** the enum value is trivial; the work is the device restriction and its error path (Q-05, Q-15) and optional self-thawing.

## REQ-05: Frozen pump has zero pressure

- **Change pattern:** Telemetry / status change.
- **Code changes:** `src/carwash/devices.py` `WaterPump._on_tick`: new branch setting `pressure_bar = 0.0` when `FROZEN` is present, checked before `LOW_PRESSURE`. If frozen is critical, 0 bar already happens today (a critical fault stops the pump and `_on_stopped` sets 0 bar); the branch is needed for a warning frozen (Q-03).
- **Unit tests:** `tests/test_devices.py`: 0.0 while running; frozen + `low_pressure` gives 0.0; frozen + `comm_lost` shows `n/a`.
- **Scenarios:** none break. There is no `expect` form for telemetry, so a scenario cannot assert `pressure=0.0 bar`; covered by unit tests (see Cross-cutting).
- **Docs:** `README.md:15` (pump telemetry), `docs/architecture.md:118`, `docs/fault-model.md` effect column.
- **Rule check:** OK.
- **Complexity notes:** reuses the `LOW_PRESSURE` branch layout; below the pattern average.

## REQ-06: Frozen pump aborts the wash

- **Change pattern:** depends on Q-03 / Q-04.
  - **(a)** critical, current rule: reuse, no code change.
  - **(b)** abort immediately in any step: small state machine change.
  - **(c)** warning that still aborts: larger state machine change, contradicts "warnings never abort".
- **Code changes (`src/carwash/car_wash.py`):**
  - **(a)** `CarWash._apply_fault` calls `_check_step_devices`, which aborts in steps that use the pump (prewash, brushing, rinse, wax). During `foam` the abort happens when `brushing` starts. **During the final `dry` step no later step needs the pump, so the wash ends `completed` with a frozen pump** (basic t7-9, standard t12-14, premium t15-19, eco dry). This does not meet REQ-06 as written. `_check_can_start` already refuses `start` with a frozen pump for all programs.
  - **(b)** in `_apply_fault`, while washing, abort when the fault is `FROZEN` (or a generic "aborts in any step" rule). It covers manual, scheduled and chaos faults, which all go through `_apply_fault`. The abort must fire only once (`aborted_washes` +1). Adds an exception to the documented rule in `docs/architecture.md:99-101`.
  - **(c)** new rule in `_check_step_devices` and `_check_can_start`, which today look only at `has_critical_fault()`; pump would show `running` with 0 bar.
- **Unit tests:** `tests/test_car_wash.py`: abort in a pump step; behaviour in `foam` / `dry` per chosen option; `start` refused with a frozen pump; single increment of `aborted_washes`.
- **Scenarios:** new one in a pump step (`expect state aborted`, `expect log frozen`, `expect device pump fault`); for (b) a second one with the fault in `dry` (e.g. `fault pump frozen at 8` on basic). Option (b) touches the shared abort path, so existing abort scenarios (`pump_failure_during_wash`, `multiple_faults`, `chemical_critical_during_foam`, `chemical_runout`) need a regression run; no edits expected.
- **Docs:** (b) state diagram and consequences in `docs/architecture.md`, severity table in `docs/fault-model.md`; (a) document the dry-step caveat.
- **Rule check:** OK.
- **Complexity notes:** (a) almost no code; (b) about 1-2 h code plus tests; (c) most expensive. Q-04 is the key question for the estimate.

## REQ-07: `frozen` can be raised in chaos mode

- **Change pattern:** Chaos / scheduling change.
- **Code changes:**
  - `src/carwash/fault_injector.py` `FaultInjector.collect_due` (`:47-50`) draws `self._rng.choice(list(DeviceId))` and `self._rng.choice(list(FaultType))` independently. Adding `FROZEN` to the enum with no other change:
    - changes every seeded chaos run from the first random fault on (pool size 7 -> 8 changes the bits `random.choice` consumes, so all later draws shift);
    - puts `frozen` on non-pump devices about 4 times out of 5.
  - Replace `list(FaultType)` with an explicit pool constant. Two variants:
    - **keep existing seeds:** the generic pool stays the current 7 types in order; `frozen` is drawn separately with its own probability (default 0 = no extra RNG calls), needing a new argument to `enable_random_faults` and to the `chaos` command;
    - **single pool** of valid (device, type) pairs: simpler, but changes all existing seeded outcomes.
  - Pump-only filtering uses the `model.py` helper from REQ-04 (layering OK).
- **Unit tests:** `tests/test_fault_injector.py`: never `frozen` on a non-pump device (p=1.0, many ticks); `frozen` appears for some seed; a "golden" test pinning the first N faults for one seed.
- **Scenarios:** no scenario uses `chaos`; existing chaos tests check counts / determinism / rate only and keep passing. New scenario with an explicit seed that freezes the pump (seed found by running the code).
- **Docs:** `docs/fault-model.md:44` and Determinism section, `HELP_TEXT` `chaos` line and `docs/scenarios.md:44` if a new option is added, README chaos example (`README.md:67`, illustrative).
- **Rule check:** OK as long as the single seeded `random.Random` is used.
- **Complexity notes:** small diff, but keeping old seeds needs a deliberate design, pinning tests and probably a CLI grammar change (Q-06).

## REQ-08: Chemical consumption since last refill in status

- **Change pattern:** Telemetry / status change.
- **Code changes:**
  - `src/carwash/devices.py` `ChemicalDispenser`: either a counter `_consumed_since_refill` (add the amount actually removed in `_on_tick`, since the level is clamped at 0; reset in `refill()`), or the derived value `100 - level_percent` (identical, because the tank starts at 100 and `refill()` sets 100; also answers Q-07 as "since start"). `set_level_percent` is used only in tests and should not count as consumption.
  - Display: option A in `ChemicalDispenser._read_telemetry` (`level=85.0% used=15.0%`, hidden as `n/a` under `comm_lost`), or option B as a new line in `render_status` (`car_wash.py:293`), visible regardless (Q-16).
- **Unit tests:** `tests/test_devices.py` (increases only while running, reset by refill, clamping); `tests/test_car_wash.py` (`render_status` contains 15.0 after one standard wash). Existing status tests use substring checks and do not break.
- **Scenarios:** no scenario runs `status`; none break. A new scenario can only be a smoke test (no `expect` form for telemetry).
- **Docs:** `README.md:74` (example status) and devices table, `docs/architecture.md:119`.
- **Rule check:** OK.
- **Complexity notes:** easier than the pattern; no regressions.

## REQ-09: Event log export to a CSV file

- **Change pattern:** New CLI command (plus event log change).
- **Code changes:**
  - `src/carwash/event_log.py`: new `EventLog.write_csv(stream: TextIO)` with stdlib `csv`; columns from `Event` (`time`, `level`, `message`). Writing to a stream keeps the module free of file I/O.
  - `src/carwash/cli.py`: new `_cmd_export` in `CommandProcessor._commands`, opens the file with `newline=""` (otherwise blank lines on Windows) and `encoding="utf-8"`, maps `OSError` to `CommandError`; `HELP_TEXT` line. If "at exit" is wanted: `--export-log FILE` in `main()`.
- **Unit tests:** new `tests/test_event_log.py` (does not exist today), with messages containing commas and quotes (abort reasons do); `tests/test_cli.py` with `tmp_path`, error path, usage error.
- **Scenarios:** none break. File-writing scenarios would write into the repo root (scenarios run from there) and no `expect` form checks files; cover with unit tests, at most `expect error export <bad path>`.
- **Docs:** README commands, `docs/scenarios.md` command table, `docs/architecture.md` (`event_log.py` row, CLI section), `HELP_TEXT`.
- **Rule check:** OK.
- **Complexity notes:** small and isolated. Separate device / fault columns would need structured `Event` fields and changes at all 13 `self.log.add(` call sites in `car_wash.py` (Q-17).

## REQ-10: Real date and time for each logged event

- **Change pattern:** Custom. The real clock is a rule conflict; estimate only the compliant alternative: configurable start datetime + fixed duration per tick (close to New CLI command + event log change).
- **Code changes:**
  - `src/carwash/event_log.py`: keep `Event.time: int`; map ticks to datetimes at export (`write_csv(stream, start, tick)`) or stamp at `add()` (Q-18).
  - `src/carwash/car_wash.py` `CarWashConfig` (`:48`): `start_datetime: datetime | None`, `tick_duration: timedelta`; `CarWash.set_clock(...)` for a runtime command.
  - `src/carwash/cli.py`: `clock <ISO datetime> [seconds_per_tick]` command, `HELP_TEXT`, optional `--clock` in `main()`.
- **Unit tests:** `tests/test_event_log.py` (with / without clock), `tests/test_car_wash.py`, `tests/test_cli.py` (`clock` parsing and errors).
- **Scenarios:** none break; new one only for `clock` argument errors.
- **Docs:** `README.md:38` and `docs/architecture.md:9` ("no system clock" wording stays true), `HELP_TEXT`, `docs/scenarios.md`.
- **Rule check:** real clock = CONFLICT (determinism). Alternative OK. Python 3.10: `datetime.fromisoformat` rejects a trailing `Z` and some ISO forms (3.11+ only); use formats 3.10 accepts or `strptime`.
- **Complexity notes:** several events share one tick (e.g. `Wash started` and `Step 1/..` at t=0) and get the same timestamp (Q-18).

## REQ-11: Wash starts only after payment at a terminal

- **Change pattern:** State machine change (simulated payment) plus new CLI command. A real terminal is out of scope (external hardware / protocol).
- **Code changes:**
  - `src/carwash/car_wash.py`: `CarWashConfig.payment_required: bool = False` (opt-in); paid / credit state and `pay()` with a log event; new check in `_check_can_start` after the existing state checks; `start_wash` consumes the payment; payment rules for `_abort`, `emergency_stop`, `reset` (Q-19); payment state in `render_status`.
  - `src/carwash/cli.py`: `_cmd_pay`, `payment on|off` (or `--payment`), `HELP_TEXT`, optional `expect paid`.
  - `src/carwash/programs.py`: only if prices per program are needed.
- **Unit tests:** `tests/test_car_wash.py` (state machine), `tests/test_cli.py` (`pay` / `payment` and errors).
- **Scenarios:** opt-in: 0 affected, 1-2 new. **Mandatory payment would break all 8 scenarios (26 `start` lines) and 21 of 23 tests in `tests/test_car_wash.py` (31 `start_wash(` calls) plus 4 tests in `tests/test_cli.py`**, and 5 `expect error start` lines would pass for the wrong reason.
- **Docs:** `docs/architecture.md` (state diagram 51-69, start-refused list), `docs/scenarios.md`, `README.md:34`, `HELP_TEXT`.
- **Rule check:** simulation OK; real terminal CONFLICT (stdlib only, determinism).
- **Complexity notes:** the check itself is one condition; the real work is the payment lifecycle on abort / estop / reset.

## REQ-12: Emulator runs faster

- **Change pattern:** Custom: time-boxed investigation (benchmark + baseline) until Q-11 gives a target.
- **Code changes:** none identified yet. No obvious hotspot; per-tick work is small and fixed. Minor candidates: `CarWash.devices` builds a list on each access, `Device.faults` copies a tuple per tick, `FaultInjector.collect_due` rebuilds `_scheduled` every tick and `schedule()` re-sorts, `EventLog.events` copies and `contains` scans linearly, and verbose CLI output prints every event (I/O and interpreter start-up likely dominate short runs).
- **Unit tests:** existing tests as regression net; no wall-clock assertions in pytest (flaky CI).
- **Scenarios:** none affected if output stays identical.
- **Docs:** benchmark mention in README if added.
- **Rule check:** OK if timing (`time.perf_counter`) is used only in a benchmark script outside `src/carwash`; inside the package it conflicts with determinism.
- **Complexity notes:** open-ended until Q-11 / Q-20. If "faster" means shorter programs, it becomes a timeline change affecting most scenarios (they hard-code tick counts).

## REQ-13: Items 1-3 deployed by the end of January

- **Change pattern:** none; no code impact.
- **Ordering:** REQ-01..03 are independent and can ship first; REQ-04..08 next. Phasing items 4-6 later means a second pass over the same docs.

## Cross-cutting effects

- **Work packages:** REQ-01/02/03 (eco) form one package; REQ-04/05/06/07 (frozen) one package (shared `FaultType`, pump-only helper, Q-03/Q-05/Q-06); REQ-09/10 one package (shared `write_csv`, new `tests/test_event_log.py`).
- **Shared files:** `HELP_TEXT` (`cli.py:31-59`) and `CommandProcessor._commands` change for eco, frozen, `export`, `clock`, `pay`; `CarWashConfig` hosts REQ-10 clock and REQ-11 payment switch; `render_status` may change for REQ-08, REQ-10, REQ-11. One combined documentation pass over README, `docs/*.md`, `CLAUDE.md` and `HELP_TEXT` is cheaper than one per requirement.
- **Scenario regression risk is low:** no existing scenario asserts `status`, telemetry, help, the program list, `chaos` or `frozen`. Only REQ-06 option (b) (regression run of abort scenarios) and mandatory payment in REQ-11 (all 8 scenarios) affect existing scenarios.
- **Scenario harness limits (internal decision):** there is no `expect` form for telemetry, status, files or payment, so REQ-05, REQ-08, REQ-09 can only be asserted in unit tests or smoke scenarios. Adding e.g. `expect telemetry <device> <text>` would serve REQ-05 and REQ-08 at once.
- **Chaos determinism (internal decision):** regardless of the client's answer to Q-06, an explicit fault pool and a golden seed test would prevent future enum additions from silently changing chaos runs.
- **Coverage:** new code is small and testable; a benchmark script must stay outside `src/`.

## Rule conflicts

- **REQ-10 - determinism (no system clock):** real date/time makes output depend on when the run happens. Compliant alternative: configurable start datetime + fixed tick duration (virtual clock). Estimate only the alternative (Q-09, Q-18).
- **REQ-11 - standard library only / determinism:** a real payment terminal needs external I/O and likely a third-party protocol library. Compliant alternative: simulated, opt-in `pay` command. Estimate only the alternative (Q-10, Q-19).
