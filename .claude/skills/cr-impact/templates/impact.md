# {CR_ID}: Impact analysis

**Based on:** `01_requirements.md`{, client answers of <date>}
**Codebase:** branch `{branch}`, commit `{short sha}`

## Summary

| Requirement | Change pattern | Modules | Unit tests | Scenarios (new / affected) | Docs | Rules |
|---|---|---|---|---|---|---|
| REQ-01 | New fault type | model, devices | test_model, test_devices | 1 / 0 | README, fault-model | OK |
| REQ-02 | Telemetry / status | devices, car_wash | test_devices, test_car_wash | 0 / 3 | README, architecture | OK |

## REQ-01: {title}

- **Change pattern:** ...
- **Code changes:**
  - `src/carwash/model.py` `FaultType`: new member `...`
  - ...
- **Unit tests:** ...
- **Scenarios:** new: ...; may break: ...
- **Docs:** ...
- **Rule check:** OK | {conflict}
- **Complexity notes:** ...

## Cross-cutting effects

{Effects shared by several requirements: the same function changed twice, scenarios
affected by more than one requirement, ordering between work packages.}

## Rule conflicts

{Requirement, rule, explanation, compliant alternative if any. "None" if none.}
