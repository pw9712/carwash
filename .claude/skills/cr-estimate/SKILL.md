---
name: cr-estimate
description: Stage 3 of the change-request flow. Build a work breakdown structure (WBS) with three-point hour estimates for a change request from its requirements and impact analysis, validate it with a script that computes PERT totals and P90, and write estimate.json and 03_estimate.md. Use after /cr-impact, or when the user asks for an hour estimate or WBS of a change request.
argument-hint: "[CR-ID] (default: the most recent CR)"
---

# /cr-estimate: WBS and hour estimate

Input: `$ARGUMENTS`, a CR ID such as `CR-2026-001`. If empty, use the folder in
`docs/customer/change_requests/` with the highest ID and say which one you picked.
`PY` below is `.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere.
Estimates are in **hours only**: no story points, rates or costs.

## Steps

1. **Load inputs.** Read `01_requirements.md`, `02_impact.md` and
   `questions_for_client.md` from the CR folder, and
   [references/estimation-model.md](references/estimation-model.md). If
   `02_impact.md` is missing, tell the user to run `/cr-impact` first and stop.

2. **Decide the scope.** Every requirement goes to `requirements` in `estimate.json`.
   Set `"in_scope": false` for requirements left out (rule conflicts without a
   compliant alternative, out-of-product items) and give the reason in `exclusions`.

3. **Build the WBS** following the model:
   - One work package `1.N` per in-scope requirement, or per small group of tightly
     coupled requirements; `req_ids` lists them.
   - Tasks `1.N.M` from the change pattern named in `02_impact.md`, made concrete with
     the files and symbols from the impact analysis (`files`).
   - Last work package: **Integration and delivery** (R2, plus T4 when needed),
     referencing all in-scope requirements.

4. **Estimate each task** with `optimistic`, `most_likely`, `pessimistic` hours. Start
   from the building block values and apply the adjustment rules. Record the block
   and every adjustment in `basis` (e.g. `"I2; P x1.5 because of Q-03"`).

5. **Write `estimate.json`** in the CR folder. Follow the structure of
   [templates/estimate.example.json](templates/estimate.example.json): `cr_id`,
   `title`, `unit: "hours"`, `requirements`, `work_packages`, `assumptions`, `risks`,
   `exclusions`, `open_questions`.

6. **Validate:**
   `PY .claude/skills/cr-estimate/scripts/validate_estimate.py <CR folder>/estimate.json`
   Fix every reported error and run it again until it prints `OK`.

7. **Render:** run the same command with `--markdown`. Do not compute or round any
   totals yourself; use the script output as is.

8. **Write `03_estimate.md`** using [templates/estimate.md](templates/estimate.md):
   put the `--markdown` output unchanged in the Estimate section, copy E and P90 into
   the Summary table, and fill in scope, assumptions, risks, exclusions and the open
   questions that affect the numbers. If the file already exists, increase the
   estimate version and keep the old one as `03_estimate.v<n>.md`.

## Report

Expected effort and P90 in hours, the three work packages with the highest expected
hours, excluded requirements, and open questions that could change the estimate the
most. Give the path to `03_estimate.md`.
