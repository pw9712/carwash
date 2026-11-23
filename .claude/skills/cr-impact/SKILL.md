---
name: cr-impact
description: Stage 2 of the change-request flow. Map each requirement of a change request (01_requirements.md) to the carwash modules, symbols, tests, scenarios and docs it affects, check it against the project rules, and write 02_impact.md. Use after /cr-intake, or when the user asks what a change request affects in the code.
argument-hint: "[CR-ID] (default: the most recent CR)"
---

# /cr-impact: impact analysis

Input: `$ARGUMENTS`, a CR ID such as `CR-2026-001`. If empty, use the folder in
`docs/customer/change_requests/` with the highest ID and say which one you picked.

## Steps

1. **Load the CR.** Read `<CR folder>/01_requirements.md` and
   `questions_for_client.md`. If `01_requirements.md` is missing, tell the user to run
   `/cr-intake` first and stop. If the Answers section of the questions file has
   content, take the answers into account.

2. **Delegate the code analysis** to the `cr-impact-analyst` subagent (Agent tool,
   `subagent_type: "cr-impact-analyst"`). Pass the full requirement sections and the
   client answers. With more than 8 requirements, split them into groups by area
   (devices and faults / programs / CLI and output) and run one subagent per group in
   parallel.

3. **Verify the result.** Spot-check the file and symbol names it reports with Grep,
   especially the ones that drive effort (new device, state machine, scenarios that
   may break). Fix wrong references. Do not copy unverified claims.

4. **Write `02_impact.md`** using [templates/impact.md](templates/impact.md):
   summary table, one section per requirement, cross-cutting effects, rule conflicts.

5. **New questions.** Append questions found during the analysis to
   `questions_for_client.md`, continuing the `Q-xx` numbering.

Do not edit anything outside the CR folder.

## Report

Per requirement: change pattern and main files, in one table. Then rule conflicts,
the number of scenarios likely to break, and new questions. Suggest the next step:
`/cr-estimate <CR-ID>`.
