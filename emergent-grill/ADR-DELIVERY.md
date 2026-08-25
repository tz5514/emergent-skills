# ADR delivery — from a passed self-check to a written draft

Loaded by emergent-grill's documentation gate the moment an ADR necessity self-check passes every condition, under that skill's fail-closed authority-load rule. It carries the mechanism only; whether a candidate enters this flow is the gate's own routing decision.

## Independent review

Dispatch the frozen candidate input by **invoking `/emergent-adr` with the `check-should-write-adr` operation keyword** — mode `create` for a new decision, mode `modify` with the target draft path for a delta to an existing draft. The operation's input schema also requires `session_transcript_path`: resolve the current session's transcript file yourself and pass it with the dispatch — supplying it is the caller's responsibility, and `/emergent-adr` never infers it. A review round is whatever candidates are ready now: a single candidate dispatches directly, several dispatch in parallel behind the operation's join barrier; never wait for candidates that do not exist yet and never dispatch an empty round.
## Write authorization

Only a validated `approved` result from `check-should-write-adr`, or the user's explicit clearance naming a rejected scope, authorizes writing that candidate; consume the round's results through the section below. The write itself is `/emergent-adr write`, executed by you in the foreground — a grill records decisions that are not yet implemented, so a new ADR is written into **`docs/adr/draft/`** with `status: not_implemented_yet` and its required `description` (it moves to `active/` only when implemented, the last task of the downstream build); a delta to an existing draft goes through `write`'s modify mode. One authorization also covers later structural or wording fixes that keep the decision's meaning unchanged; a change to the substance of the reviewed scope stops the write and goes back through `check-should-write-adr` in modify mode.

## Consume the round's results

After the review round's join, first write every approved candidate in the foreground with `/emergent-adr write`, sequentially — never in parallel and never through a sub-agent — without waiting on rejected candidates' adjustments or rulings. A rejected candidate has exactly two exits, and the reviewer's report stays a rejection either way — never write anyway and never extract just the passing parts:
  - **Rejection accepted** → abandon the candidate, or adjust the request input and resubmit: every candidate whose adjusted input is ready joins one next `check-should-write-adr` round; a single adjusted candidate resubmits immediately, never waiting for other possible adjustments. Changed input is a new review version, never a retry of the old one.
  - **Rejection not accepted** → accumulate a user-ruling item carrying the rejected scope, the reviewer's reasons, your specific disagreement, and the risk of writing anyway; write only on the user's explicit clearance naming that scope.
## One merged ruling stop point, itemized rulings

Present all accumulated ruling items — non-accepted rejections, `needs_context_ruling` returned by `write`, and the failure items below — together at the next user-ruling stop point, after every write and resubmission wave that needs no user input has finished: one report, itemized so the user rules on each item separately, never an all-or-nothing bundle. A single pending item is raised directly, never delayed to collect more.
## Three failure classes

Each must appear in the visible output; no candidate is ever silently dropped.
  - **Review not completed** — the redispatch budget is exhausted without a valid report, or the operation itself failed (for example the conversation-evidence cutoff could not be produced): the candidate becomes a user-ruling item carrying the failure reason and the candidate content; the user either abandons it or has you repair and resubmit. Until that ruling the candidate is neither written nor abandoned, and the preflight barrier keeps waiting.
  - **Foreground write failure** — the draft cannot be produced or the tool fails: the candidate keeps its review authorization and stays neither written nor abandoned. Retry the write in the foreground on incidental failure under the same stop rule as review redispatch — the redispatch stop semantics defined by `/emergent-adr check-should-write-adr`, applied here to write attempts — then surface the failure information and merge it into the ruling stop point above. `write`'s normal terminals are `written` and `needs_context_ruling`; an execution failure is the operation failing, not a status value.
  - **Preflight-round failure** — a preflight reviewer is interrupted or its report is invalid: that is a tool failure, not a finding and not a rejection — do not modify the ADR; rerun that ADR's preflight with a fresh reviewer under the same redispatch stop semantics, and when the stop rule is reached without a valid result, that ADR's preflight status becomes a user-ruling item.
## Preflight barrier, then the preflight round

Only after every candidate of the round is written or explicitly abandoned — none awaiting resubmission, a ruling, or a valid report — run `/emergent-adr quality-review` with `review_mode: context_glossary_approval_preflight` over the drafts actually written this round: one reviewer per draft in parallel, aggregating only after all complete; a single written draft runs directly; zero written drafts skips the preflight round entirely.
## Incremental handling after preflight

A preflight result affects only its own ADR. Fix structural or wording findings in the foreground through `write`'s modify mode and rerun the preflight only for the modified ADR; glossary-approval needs go to the user itemized, at the merged ruling stop point above. The preflight never produces a finding that demands a change to decision content.
## Two layers stay visible

Whenever an independent review was dispatched, the visible output keeps both the 🧭 self-check result and the reviewer's final result — approved, rejected with the stage that stopped it (the report's `rejected_at`) and its failing judgment, or not completed; the reviewer's result never overwrites or hides the self-check.
