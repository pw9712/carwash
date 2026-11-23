# {CR_ID}: Requirements

**Title:** {short title of the change request}
**Source:** `source/{file name}` ({PDF, N pages | e-mail})
**Received:** {date, if stated in the source; otherwise intake date}
**Client contact:** {name/role from the source, if any}

## Summary

{Three to five sentences: what the client wants and why, in plain language.}

## Requirements

| ID | Title | Type | Priority | Rule conflict | Scope |
|---|---|---|---|---|---|
| REQ-01 | ... | functional | Must | - | in |
| REQ-02 | ... | constraint | Should (inferred) | stdlib only | in (see Q-02) |

### REQ-01: {title}

- **Statement:** The emulator shall ...
- **Source:** "{quote in English}" {(translated) if the source is not in English} ({page 2, section 3.1 | e-mail, paragraph 2})
- **Type / priority:** functional / Must
- **Notes:** {mapping to domain terms, related requirements, questions: Q-01}

### REQ-02: {title}

...

## Glossary

| Client term | Project term |
|---|---|
| nozzle | pump (`WaterPump`) |

## Rule conflicts

{Requirements that conflict with CLAUDE.md rules (standard library only, determinism,
Python 3.10, strict typing), with the rule and a short explanation. "None" if none.}

## Out-of-scope candidates

{Requirements that seem to be outside this product, with the reason. "None" if none.}
