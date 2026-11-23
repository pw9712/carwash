---
name: cr-intake
description: Stage 1 of the change-request flow. Read a customer change request (PDF file or pasted e-mail text), create a CR-YYYY-NNN folder in docs/customer/change_requests/, and turn the prose into numbered, testable requirements plus questions for the client. Use when the user provides a new change request, customer requirements, a PDF spec or an e-mail to analyse.
argument-hint: "<path to .pdf/.txt/.md> | <pasted e-mail text>"
---

# /cr-intake: change request intake

The input is either a path to the customer document or the pasted e-mail text. It is
given once, in the `<input>` block of the **Input** section at the end of this file; the
steps below refer to it as "the input".
Output language is **English**, even when the source is in another language.

## Steps

1. **Detect the input.**
   - The input is a path to an existing `.pdf`, `.txt` or `.md` file: file input.
   - The input is other non-empty text: pasted e-mail.
   - Empty: ask the user to paste the e-mail text or give a file path, then stop.

2. **Create the CR folder.** List `docs/customer/change_requests/`. The new ID is
   `CR-<current year>-<NNN>`, where `NNN` is the highest existing number for that year
   plus one, starting at `001`. Create `docs/customer/change_requests/<CR-ID>/source/`.

3. **Store the source unchanged.**
   - File: copy it into `source/`, keeping its name.
   - Pasted text: write it verbatim to `source/email.txt`. Do not fix typos or
     formatting, and do not drop quoted replies or signatures.
   The source folder is read-only from now on.

4. **Read the source completely.**
   - PDF: use the Read tool. For PDFs longer than 10 pages read them in page ranges
     (`pages: "1-10"`, `"11-20"`, ...) until the end. If a PDF has no text layer
     (scanned), use the `pdf` skill (OCR) if available, otherwise ask the user for a
     text version and stop.
   - Note tables, figures and attachments that carry requirements.

5. **Extract requirements** into `01_requirements.md` using
   [templates/requirements.md](templates/requirements.md):
   - One requirement = one testable behaviour or constraint. Split compound sentences
     ("and", "also", lists) into separate requirements.
   - IDs `REQ-01`, `REQ-02`, ... in the order they appear in the source.
   - For each: a short title, a normalised statement ("The emulator shall ..."), the
     **source quote in English** (verbatim if the source is in English, otherwise a
     faithful translation marked `(translated)`) with its location (page /
     paragraph / e-mail line), type (`functional`, `non-functional`, `documentation`,
     `constraint`) and priority (MoSCoW from the client's wording; if the client does
     not say, use `Should` and mark it `(inferred)`).
   - Use domain terms from `README.md` (device, fault type, severity, program, step,
     tick, scenario). Map the client's words (in English) to them and record the
     mapping in the glossary section, e.g. "nozzle" -> pump.
   - **No non-English text** in any output file: translate quotes, terms, titles and
     job titles. Only `source/` keeps the original wording. Personal and company
     names stay as they are.
   - **Rule check** against `CLAUDE.md` (standard library only, determinism,
     Python 3.10, strict typing). Mark every requirement that conflicts with a rule.
   - Mark requirements that are clearly outside this product (e.g. hardware, other
     systems) as candidates for `out of scope`. Do not drop them.
   - Do not invent requirements. Implicit expectations go to the questions.

6. **Write `questions_for_client.md`** using
   [templates/questions.md](templates/questions.md): one entry per ambiguity,
   contradiction, missing value (numbers, units, limits, error behaviour) or rule
   conflict. IDs `Q-01`, ...; each names the requirement(s) it concerns and why the
   answer matters for the implementation or the estimate.

## Report

CR ID and folder path, number of requirements by type and priority, number of
questions, and any rule conflicts or out-of-scope candidates, in a few lines.
Suggest the next step: `/cr-impact <CR-ID>`.

## Input

<input>
$ARGUMENTS
</input>
