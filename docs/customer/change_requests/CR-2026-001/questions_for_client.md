# CR-2026-001: Questions for the client

Answers to these questions may change the scope or the estimate.

| ID | Requirement | Question | Why it matters |
|---|---|---|---|
| Q-01 | REQ-01, REQ-02 | How many ticks exactly should `eco` last, and how are they split between rinse and dry (e.g. 3 + 3)? Should the conveyor run as in the other programs? | Defines the program timeline used in tests and scenarios. |
| Q-02 | REQ-03 | Does "available in the same way" mean anything beyond `start eco`, help text and documentation (e.g. a separate counter of completed `eco` washes)? | Extra reporting would add work. |
| Q-03 | REQ-04, REQ-06 | Is `frozen` always a critical fault, or can it also be injected as a warning? If a warning is allowed, what should happen to pressure and the wash? | Today only critical faults abort a wash; this drives the fault model change. |
| Q-04 | REQ-06 | If the pump freezes during a step that does not use it (e.g. drying), should the wash abort immediately or only when a step needs the pump? | Current rule aborts only on devices required by the current step; a change affects the controller. |
| Q-05 | REQ-04 | Is `frozen` allowed only for the pump, or for other devices too? How is it cleared: with `clear` like other faults, or should it thaw on its own? | Validation, clearing logic and tests. |
| Q-06 | REQ-07 | In chaos mode, should `frozen` be one more fault in the same random pool, or have its own probability? Is it acceptable that existing chaos runs with the same seed give different results after the change? | Adding a fault type can change outcomes of existing seeded runs and scenarios. |
| Q-07 | REQ-08 | What should the consumption show before the first refill: consumption since the emulator started? Where and in what format should it appear in the status report? | Defines the counter's start value and the expected status output. |
| Q-08 | REQ-09 | How should the CSV be produced: a command (e.g. `export log.csv`), automatically at exit, or both? Which columns, delimiter and encoding? | Defines the CLI and file format. |
| Q-09 | REQ-10 | The emulator must stay deterministic and cannot use the system clock. Would it be acceptable to set a start date/time (e.g. `clock 2027-01-15T08:00`) and map each tick to a fixed duration? How long is one tick in real time? | Using the real clock breaks a core project rule; the alternative needs these values. |
| Q-10 | REQ-11 | What does payment integration mean for an emulator: a simulated payment step (e.g. a `pay` command before `start`), or a connection to a real terminal? If real, which device and protocol? | A real terminal is likely out of scope and conflicts with project rules; a simulation is small. |
| Q-11 | REQ-12 | What is too slow today: which command or scenario, how long does it take, and what is the target? Or does "faster" mean shorter wash programs? | Without a measurable target the item cannot be implemented or estimated. |
| Q-12 | REQ-13 | Is the deadline the end of January 2027? Does it apply only to items 1-3, and does "deployment" mean a released version delivered to you? | Planning and possible phasing of items 4-6. |
| Q-13 | REQ-01 | Since `eco` uses no chemicals, it will start even when the chemical tank is empty or the dispenser has a critical fault (as `basic` does today). Is that intended? | Confirms the start rules; a different rule would need a controller change. |
| Q-14 | REQ-01, REQ-02 | The dryer needs 4 ticks to reach its working temperature (60 C). A shorter dry step (e.g. 3 ticks, as in `basic`) ends at 50 C. Is that acceptable for `eco`, or should dry last at least 4 ticks (e.g. rinse 2 + dry 4)? | Fixes the eco timeline (Q-01). |
| Q-15 | REQ-04 | If `frozen` is pump-only: should `fault all frozen` (or a device list containing the pump) be rejected as a whole, or apply to the pump and skip the others? | Defines the error path of the `fault` command. |
| Q-16 | REQ-08 | Should the consumption stay visible when the chemical dispenser has lost communication (`comm_lost`), where its telemetry shows `n/a`? | Decides whether it is part of the device telemetry or a separate status line. |
| Q-17 | REQ-09 | Is one text column for the event message enough, or do you need separate columns (e.g. device, fault type, severity)? Should an existing file be overwritten? | Separate columns require restructuring all log entries (larger change). |
| Q-18 | REQ-10 | With a configurable clock: which time zone / UTC offset should the output use? Is the same timestamp for several events in one tick acceptable? Should the date/time also appear in `log` and `status`, or only in the CSV? | Defines the format and where the clock is used. |
| Q-19 | REQ-11 | If payment is simulated: what happens to a payment when the wash is aborted, stopped with `estop`, or `start` fails? Can several washes be prepaid? Do prices differ per program? Should payment be optional per script so existing scripts keep working? | Drives the state machine design; mandatory payment would break all existing scenarios. |
| Q-20 | REQ-12 | Is the slowness seen in interactive mode (every event printed), with `--quiet`, or in CI test runs? | Tells whether output, start-up or the simulation loop needs work. |

## Answers

{Fill in when the client answers: `Q-01: <answer> (<date>, <source>)`.
Then re-run `/cr-impact` and `/cr-estimate` for this CR.}
