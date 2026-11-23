# {CR_ID}: Estimate

**Title:** {title}
**Source:** `source/{source file}`
**Estimate version:** {n} ({date})
**Unit:** hours (one developer familiar with the codebase)

## Summary

| Measure | Hours |
|---|--:|
| Expected effort (~P50) | {E} |
| P90 (90% confidence the work fits) | {P90} |

{Two or three sentences: what is being delivered, the main cost drivers, and what
the P90 margin mostly comes from.}

## Scope

| Requirement | Title | In scope | Work package |
|---|---|---|---|
| REQ-01 | ... | yes | 1.1 |
| REQ-03 | ... | no (see Exclusions) | - |

## Estimate

{Paste the output of `validate_estimate.py estimate.json --markdown` here, unchanged.}

## Assumptions

- ...

## Risks

- ...

## Exclusions

- ...

## Open questions affecting the estimate

See `questions_for_client.md`. Questions that change the numbers above:

- Q-01: ... (affects 1.2.1)

## Method

Three-point estimates per task, PERT expected value `(O + 4M + P) / 6`, totals and P90
computed by `validate_estimate.py`. For the P90, tasks within a work package are treated
as correlated (they share the same requirement and open questions) and work packages as
independent. Baseline hours per building block are in
`.claude/skills/cr-estimate/references/estimation-model.md`.
