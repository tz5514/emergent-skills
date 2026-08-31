# check-adr-redundancy human report

Fixed Markdown shape for one validated evaluation report — presentation only: copy validated fields without accepting, rejecting, or rewriting any result. Omit empty sections. The renderer presents ruling context; the main agent writes the actual user-facing question itself.

## ADR conclusion (first)

- **ADR path:** `…`
- **ADR evaluation result:** `…`
- **Needs user ruling:** true|false

## Atomic decisions by result

Group live decisions by `evaluation_result`, sections in this order, emitted only when non-empty: Fully redundant, Partially redundant, Fully retained, Ground-truth mismatch, Indeterminate.

Per decision: **Decision `id`** → Result, Reason (`evaluation_reasoning`), Evidence (`source`: finding). Partially redundant also lists **Redundant portion** and **Retained portion**.

## User ruling requests

Only when `needs_user_ruling` is true: one bullet per request (indeterminate ones also list the missing decisive fact, decision impact retained-if/redundant-if, and resolution path).

## JSON report

Always end with the evaluation report path.
