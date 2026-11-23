---
name: change-request
description: Run the full change-request flow for the carwash project, from a customer PDF or pasted e-mail to requirements, impact analysis, WBS and hour estimate, stopping for review after each stage. Use when the user brings a new change request from a client and wants it analysed and estimated end to end, or asks to continue an existing CR.
argument-hint: "<path to .pdf/.txt/.md> | <pasted e-mail text> | <CR-ID to continue>"
---

# /change-request: full flow

Orchestrates three stage skills. Each one can also be run on its own.

| Stage | Skill | Output in `docs/customer/change_requests/<CR-ID>/` |
|---|---|---|
| 1 | `/cr-intake` | `source/`, `01_requirements.md`, `questions_for_client.md` |
| 2 | `/cr-impact` | `02_impact.md` (+ new questions) |
| 3 | `/cr-estimate` | `estimate.json`, `03_estimate.md` |

The whole flow is described in `docs/change-requests.md`.

## Steps

1. **Start or continue.**
   The input is given once, in the `<input>` block of the **Input** section at the end
   of this file.
   - The input matches `CR-\d{4}-\d{3}` and the folder exists: continue that CR
     from the first stage whose output file is missing. If all exist, ask which stage
     to re-run (for example after the client answered questions).
   - Otherwise invoke the `cr-intake` skill with the input unchanged as its arguments.

2. **Checkpoint after each stage.** Show the stage report and ask the user whether to
   continue, to correct something first (requirements, scope, an impact finding), or
   to stop. Apply corrections to the stage output file before going on. Never skip a
   checkpoint, because later stages build on the earlier files.

3. **Next stage.** Invoke `cr-impact`, then `cr-estimate`, with the CR ID.

## Final report

CR ID and folder, number of requirements (in / out of scope), expected effort and
P90 in hours, number of open questions for the client, and the list of files created.

## Input

<input>
$ARGUMENTS
</input>
