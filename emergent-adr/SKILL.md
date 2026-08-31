---
name: emergent-adr
description: The single entry point for all ADR (Architecture Decision Record) operations — drafting, writing, quality review, supersession scanning, promotion. Use when any skill or agent needs ADR lifecycle work. Invoke as `/emergent-adr <operation-keyword>` with that operation's named inputs; never embed ADR mechanism specs in the consumer.
---

This file is a **dispatcher**: each operation routes to its authority — a spec file or contract script — which you read in full and follow. Rules live in exactly one place; nothing here restates them.

Authorities:

- `ADR-FORMAT.md` — ADR format and the `write` contract.
- `ADR-NECESSITY-CONDITIONS.md` — necessity-condition judgment semantics (consumers: the main agent's self-check and `check-should-write-adr`; quality review never judges necessity).
- `QUALITY-REVIEW-PROMPTS.md` — review modes, report schema, and the **shared dispatch parameters** every reviewer dispatch in this skill uses. Prompt text: `QUALITY-REVIEW-PROMPT-BLOCKS.md`, assembled by `scripts/review_prompt_assembly.py`.
- `SCAN-SUPERSESSION-PROMPT.md` — scanner prompt and scan dispatch.
- `CHECK-SHOULD-WRITE-ADR-PROMPT.md` / `CHECK-ADR-REDUNDANCY-PROMPT.md` — reviewer prompt templates, instantiated by their scripts.
- `scripts/` — mechanical helpers; each operation names its own below. Contract scripts are flow authorities: read their docstrings and top-level constants as spec.

## Invocation contract

The **first arg token is the operation keyword — mandatory, no fallback**: missing or unknown → list the valid keywords and stop.

`produce` · `write` · `revise` · `quality-review` · `scan-supersession` · `promote-draft-to-active` · `finalize-draft-adrs` · `extract-active-adr-desc` · `read-necessity-conditions` · `check-should-write-adr` · `check-adr-redundancy`

Every operation takes its named input schema and returns **structured data**; the consumer renders it with its own templates. `bounded_context_path` is needed only when no target ADR path can derive it. Consumers follow this skill's lifecycle operations — never re-implement or unbundle them.

**Dispatch rule (all sub-agent dispatches in this skill):** foreground-synchronous — wait for and collect the terminal result; a handle is not completion; parallel calls only behind a join barrier. Channel, model, and effort come from the runtime rows in `QUALITY-REVIEW-PROMPTS.md` (scanner tiers: `SCAN-SUPERSESSION-PROMPT.md`). Evidence, reports, and support data live in OS-tmp run directories, never in bounded-context folders.

## Operations

### `produce` — end-to-end draft ADR delivery

Call `write`; if it returns `needs_context_ruling`, stop with that as `final_status` (no draft, no review, no scan). Otherwise drive scan-owning delivery around scan-free `revise` with `quality_review_mode: full_quality_review`. Contracts: `scripts/produce_contract.py`, driving `scripts/scan_driven_delivery_contract.py` over `scripts/scan_cycle_contract.py`. All `revise` calls in one run share one seven-round review budget via `rounds_already_consumed`. `produce` is a human-invoked entry: the user is the ruling authority, so it runs no `check-should-write-adr` gate.

- **Input** — create: `bounded_context_path` + source material; modify: draft `target_adr_path`.
- **Output** — `draft_adr_path`, `structured_report_path`, `final_status`, `needs_user_ruling`, plus a thin wrapper report in the run directory.
- **`final_status` values (authority for `produce` and `revise`):** `passed` | `needs_context_ruling` | `blocked_after_review_limit` | `needs_user_ruling` | `needs_scan_evidence` | `failed`. `needs_scan_evidence` is `revise`'s hand-back, resolved inside the delivery loop; a pending scan surfaces as `needs_user_ruling`.

### `write` — write ADR content

Create or substantively modify a draft ADR per **ADR-FORMAT.md** (which owns the full contract, including the trust-the-caller authorization boundary — necessity is settled before `write`). The executing agent writes the content itself — `write` is not a dispatch point. Run `scripts/atomicity_lint.py` as a non-blocking self-check.

- **Input** — `mode` (`create`|`modify`); `bounded_context_path` (create) or `target_adr_path` (modify); source material.
- **Output** — `status` (`written` | `needs_context_ruling`) plus the fields ADR-FORMAT.md lists.

### `revise` — scan-free draft quality revision

Run the review/repair acceptance loop; never scan, promote, or build a new draft. Flow authority: `scripts/revise_contract.py` (disposition dispatch, budget, terminals, report). Reviewer rules: **QUALITY-REVIEW-PROMPTS.md**; live corpus: `scripts/live_atomic_decision_corpus.py`.

- **Input** — required `draft_adr_path` and `quality_review_mode` (`full_quality_review` | `frozen_glossary_quality_review` — no default, unknown aborts; maps to quality-review's `quality_review` / `frozen_glossary_review`). Optional `source_decision_extract_path`, `source_material`, `scan_state` (enables repetition-finding reclassification; attach the `repeated_live_decision` identity to findings yourself — the reviewer never writes it), `rounds_already_consumed`.
- **Orchestration rules** — every round reviews the current artifacts; rebuild the live corpus fresh each run. One repair write per round, covering that round's `writer_repair` findings; it must not hand-write `supersedes`. That same write may also fix same-round `non_blocking` findings; nothing else ever acts on `non_blocking` — after a pass they are recorded and dropped, never becoming debt or a reopened loop.
- **Output** — `draft_adr_path`, `structured_report_path`, `final_status` (`passed` | `needs_scan_evidence` | `needs_user_ruling` | `blocked_after_review_limit` | `failed`), `needs_user_ruling`, `rounds_consumed`; detailed report per the contract script. `passed` is quality-only — scanning and promotion remain the caller's.

### `quality-review` — independent ADR quality review

Review exactly one ADR (draft, active, or archived); report-only. Everything — modes, schema, dispatch, allowed/forbidden inputs — is in **QUALITY-REVIEW-PROMPTS.md**.

- **Input** — `target_adr_path`; optional `review_mode` (default `quality_review`), support-data paths, bounded-context references.
- **Output** — the persisted JSON report's path.
- **Caller action by lifecycle** — repair a draft via the writer; change active substance only via a new superseding draft; archived is immutable history — report findings, never edit or retro-supersede.

### `scan-supersession` — supersession scanning

Run on every draft creation or modification — never self-judge a change as too small to scan. Pipeline: `scripts/scan_supersession_input.py` (derives context, enumerates all `active/` candidates) → `scripts/scan_supersession_packet.py` (full packets; keep paths) → dispatch per **SCAN-SUPERSESSION-PROMPT.md** → `scripts/scan_supersession_ledger.py` validation against the full packet → your own review of validated rows → `scripts/scan_supersession_result.py` (writes reviewed `supersedes`; needs both validation and review flags).

- No active candidates → `skipped_no_active`, no dispatch. Bias toward recall on topically-related candidates (a missed supersession is silent and worst); unsure between FULL and PARTIAL → PARTIAL; flag low confidence loudly.
- **Partial supersession is never marked directly:** first rewrite the draft to fully restate and replace the old decision, then mark. `## Atomic Decisions` is the decision authority; `description` never filters candidates or decides supersession.
- Statuses: `skipped_no_active` | `completed` | `awaiting_rewrite` | `awaiting_review`. Pending statuses are surfaced to the consumer and stop the flow — the user must see the report to retain the withdrawal right.
- **Write boundary:** writes only reviewed draft-side `supersedes`; `superseded_by`, status recomputation, and archiving belong to `promote-draft-to-active`.
- Timing and the write→rescan loop are owned by the scan-driven delivery layer (`scan_cycle_contract.py`): ordinary scan after acceptance; a scan-evidence finding's scan before acceptance; after an accepted rewrite, `write` then rescan before any further quality-review. Any `## Atomic Decisions` change invalidates a scan — rescan before accepting.
- **Input** — one `draft_adr_path`. **Output** — the structured result `scan_supersession_result.py` builds.

### `promote-draft-to-active` — promote one draft

One call does the whole migration: (i) for each `supersedes` target, re-verify its current state, invert the relationship (`scripts/supersession_converter.py`), apply `superseded_by`, recompute `status` (`scripts/status_calculator.py`; apply/conflict detection: `scripts/supersession_mark_back.py`); fully superseded targets move to `archived/`. (ii) Move the draft into `active/` and recompute its `status` with the same calculator. (iii) Return per-target results plus the after-report.

Conflicts never block (`scripts/conflict_disposition.py`): already-archived or already-superseded target → skip and clear the draft's moot entry; target missing from `active/` → skip and keep the entry. Every conflict lands in the after-report flagged needs-human-review. **The promotion itself is unconditional.**

- **Input** — one `draft_adr_path`. **Output** — per-target applications, the draft's new path and status, the after-report.

### `finalize-draft-adrs` — finalize drafts to terminal states

Flow authority: `scripts/finalize_draft_adrs_contract.py`. Per draft: entry `check-adr-redundancy` once → dispose (delete fully-redundant only when the named decisions are still present AND the caller premise is True; rewrite partially-redundant via `write`; unresolved stops that draft untouched) → frozen-glossary `revise` → same-context exclusivity → fresh scan → promote. One shared review budget per draft per run; exhaustion → `unresolved`. Per-draft failure isolation; terminals `promoted` | `deleted` | `unresolved`.

- **Input** — `draft_adr_paths` (all under `docs/adr/draft/`, no duplicates, non-empty — else structured `invalid_input`) and `disposition_scope_git_recoverable_and_isolated` (bool premise).
- **Output** — per-draft reports + batch summary; direct: `batch_summary_path`, `structured_report_path`, `final_status`, `needs_user_ruling`.

### `extract-active-adr-desc` — active-ADR description index

`scripts/description_index.py`: `{filename → description}` from `active/` frontmatter, bodies never opened. Relevance judgment stays with the consumer.

- **Input** — `bounded_context_path`. **Output** — the index.

### `read-necessity-conditions` — load the necessity authority

`python3 scripts/necessity_conditions_authority.py`: validates structure and prints the complete verbatim authority. Fail closed — on any failure deliver nothing; there is no fallback from memory or copies.

- **Input** — none. **Output** — `authority_full_text`, `source_path`, `structure_validation`.

### `check-should-write-adr` — may this candidate become an ADR?

Pre-write gate: an independent reviewer rules on conversation evidence. Prompt: **CHECK-SHOULD-WRITE-ADR-PROMPT.md**; the whole mechanical layer (evidence cutoff, slot/attempt layout, verdict validation, redispatch accounting) is `scripts/check_should_write_adr.py`. The reviewer loads the necessity authority and the complete `emergent-design` skill itself — never paste authority content.

- **Input** — `session_transcript_path`; `candidates`: `{mode: "create"|"modify", candidate_description, modify_target_path?}`. The description carries two semantic blocks — the decision content, and per condition the facts + causal account + boundary argument. It must carry no evidence locations and no carrier-suitability argument (that judgment is the reviewer's alone); summary-level content is rejected as not reviewable. Create mode supplies prose only — never pre-atomized decisions or decision ids (that writing work belongs to `write`).
- **Flow** — run `extract-transcript` on the transcript (fixed default categories) → `prepare-round` (lays out everything; never hand-write a path) → dispatch one reviewer per candidate (parallel behind a join barrier) → `resolve-reply` per reviewer (validates the report; an `AUTHORITY_INPUT_FAILURE` line means fix the input or stop) → on incidental failure, `prepare-attempt` redispatches; `redispatch_decision` is the stop authority. Never synthesize a report.
- **Output** — per candidate: `approved` | `rejected` | review-not-completed, with the validated report path and `rejected_at`.
- **Consumption boundary** — only a validated `approved` authorizes `write`. On rejection: abandon, resubmit an adjusted whole candidate as a new round, or get the user's explicit scope-named clearance. Never write anyway or extract passing parts.

### `check-adr-redundancy` — which live decisions are carried elsewhere?

Report-only judgment for one draft or active ADR: per live atomic decision — fully/partially redundant against non-ADR long-lived carriers, fully retained, ground-truth mismatch, or indeterminate. Prompt: **CHECK-ADR-REDUNDANCY-PROMPT.md**; mechanical layer: `scripts/check_adr_redundancy.py`. The reviewer loads `emergent-design` itself.

- **Input** — one `adr_path` (archived rejected; no batches).
- **Flow** — `prepare-target` → `prepare-run` → dispatch one fresh-context reviewer → `resolve-reply` → redispatch on incidental failure as above. Optionally render for humans with `render-human <report_path>` (per `CHECK-ADR-REDUNDANCY-HUMAN-REPORT.md`); when `needs_user_ruling`, you write the concrete user question yourself.
- **Output** — `evaluation_report_path` + validated fields; on failure a structured failure with `evaluation_report_path: null`.

## Not in /emergent-adr

Reference-block generation, path-existence checks, and relevance judgment stay with the consumer; CONTEXT.md governance stays with each consumer.
