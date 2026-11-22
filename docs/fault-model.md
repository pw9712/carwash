# Fault model

What faults exist, how they get onto devices, and what they do. Source of truth:
`src/carwash/model.py`, `devices.py`, `car_wash.py`, `fault_injector.py`.

## Severity

| Severity | Device | Wash |
|---|---|---|
| **warning** | Keeps working; some faults degrade telemetry (see table below). Device state stays `idle` / `running`. | Never aborts, never changes step durations. |
| **critical** | Stops immediately and refuses to start. Device state is `fault`. | Aborts the wash when the device is needed by the current step; blocks `start` of any program that uses the device. |

A device can carry many faults at the same time, but **one fault per type**.
Injecting a type that is already present replaces its severity (it can also downgrade
critical to warning; the device then stays stopped until a step starts it again).

## Fault types

Default severity is used when a command or a random fault gives none.

| Type (alias) | Default | Effect |
|---|---|---|
| `comm_lost` (`comm`) | critical | Any device: telemetry shows `n/a (no communication)`, also while idle. |
| `overheat` | critical | `dryer`: heats towards 95 °C instead of 60 °C. Other devices: no specific effect. |
| `low_pressure` | critical | `pump`: 15 bar instead of 80. Other devices: no specific effect. |
| `blocked` | critical | `brushes`: 40 rpm instead of 120. `conveyor`: 2 m/min instead of 6. Other devices: no specific effect. |
| `low_level` | **warning** | `chemicals`: raised and cleared by the dispenser itself (see below). Other devices: no specific effect. |
| `power_failure` (`power`) | critical | No specific effect. Its meaning comes from its severity. |
| `sensor_error` (`sensor`) | **warning** | `dryer`: telemetry shows `temp=?? C (sensor error)`. Other devices: no specific effect. |

"No specific effect" still matters: the fault is listed in `status`, can be asserted with
`expect fault`, and as a critical fault it stops the device and can abort a wash.
Any fault type can be put on any device.

Degraded readings (pressure, rpm, speed, dryer temperature) appear only while the device
runs: a `low_pressure` warning on an idle pump still shows `pressure=0.0 bar`.

## Where faults come from

| Source | How | Log message |
|---|---|---|
| Manual | `fault <dev> <type> [severity]` | `Fault injected [manual]: ...` |
| Scheduled | `fault ... at <tick>` / `fault ... in <ticks>` | `Fault scheduled at t=..`, then `Fault injected [scheduled/random]: ...` |
| Random (chaos) | `chaos <p> [seed]`: each tick, with probability `p`, one random device gets one random fault type with its default severity | `Fault injected [scheduled/random]: ...` |
| Self-raised | The chemical dispenser, based on its tank level | `Device reported fault: ...` |

Faults due at a tick are applied at the start of that tick: first all scheduled ones
(in the order they were scheduled), then at most one random fault. Faults arrive in every
car wash state, not only during a wash.

### Self-raised faults

The chemical dispenser checks its level on every tick, also while idle:

| Level | Fault |
|---|---|
| 15% or more | none raised (an existing `low_level` stays until cleared or refilled) |
| below 15%, above 0% | `low_level` warning, unless `low_level` is already present |
| 0% | `low_level` **critical**: the dispenser stops and the next foam or wax step aborts |

`refill` sets the level to 100% and clears `low_level`. `clear chemicals low_level`
without a refill only lasts until the next tick, when the dispenser raises it again.

Tank usage: 5% per tick while running. `standard` uses 15% per wash, `premium` 25%,
`basic` none. Starting from a full tank, `standard` reaches the warning on the 6th wash
(10% left) and runs dry during the 7th.

## Recovering

| Situation | What to do |
|---|---|
| Critical fault, no wash running | `clear <dev> [type]` (or `refill` for `low_level`), then `start`. |
| Wash `aborted` | Clear the fault **and** `reset` (in any order), then `start`. `reset` alone keeps the fault, and `start` is refused again. |
| `emergency_stop` | `reset`, then `start`. Faults, if any, must also be cleared. |
| Warning only | Nothing is required; clear it to restore nominal telemetry. |

Clearing a fault never restarts a device by itself. The next step that needs the device starts it.

## Determinism

The random generator is `random.Random(seed)`, seeded by `chaos` (default seed 42).
It is consulted only while chaos is enabled. The same script with the same seed always
produces the same faults at the same ticks, on every platform.
