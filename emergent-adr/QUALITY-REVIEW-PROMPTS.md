# ADR Quality Review

`quality-review` reviews exactly one target ADR at a time and **only reports** — it never edits, asks questions, accepts author intent or repair history, or reads hidden answers. It always returns the path of a persisted JSON report generated mechanically from the reviewer's verdict payload by `scripts/review_verdict_report.py`.

## Prompt assembly

Each mode's prompt is assembled by `scripts/review_prompt_assembly.py` from the single-authority fragments in `QUALITY-REVIEW-PROMPT-BLOCKS.md`: framework blocks, one block per gate (the `@gate:` marker order is the formal gate order; `quality_review_contract.GATE_COVERAGE_IDS` derives from it), mode rule blocks, one manifest per mode. A gate off a mode's manifest is **structurally absent** from that prompt. The assembler numbers gates, fills placeholders, prepends a per-run random integrity marker, and writes the file to the run directory — the sole prompt authority at dispatch. Never rewrite, add, or reorder fragment content.

**Smoke discipline:** any fragment or manifest change — including rewording — requires re-running that mode's reviewer smoke material through the real delivery channel before use.

## The three review modes

Narrowing is carried by the mode name; callers never choose gate sets.

- `quality_review` — every gate.
- `context_glossary_approval_preflight` — structural check + glossary approval need check, then stop. Not a complete review: `review_status` is never `pass` (a clean preflight is `not_evaluated`, outcome in `preflight_status`); it runs no reference-closure work and its verdict omits `reference_closure`.
- `frozen_glossary_review` — every gate except the glossary approval need check, with the CONTEXT.md glossary frozen. May report `pass`; the report notes the frozen-out check did not run. Undefined term-like wording routes to `context_glossary_usage_discipline_check` as writer-fixable; degradation from a glossary-gap rewrite is recorded in `scope_limitations`.

## Dispatch parameters (shared by every reviewer dispatch in this skill)

These rows also govern `check-should-write-adr` and `check-adr-redundancy` dispatches (dispatch policy only — their prompts, verdicts, and path lines live in their own files).

- **Foreground:** wait for and collect each terminal result; a handle is not completion; parallel only behind a join barrier. Never background or detach. A timeout returns `reviewer_close_status: tool_failed`, never a silent pass.
- **Delivery:** the assembler-written prompt file is the authority. A runtime with a non-LLM channel brings the file content in directly; otherwise send only the mechanically generated bootstrap line — never transcribe prompt or authority content. The reviewer echoes the integrity marker; after the round, `review_verdict_report.py` verifies marker and `review_mode` — a mismatch invalidates the round.
- **Preflight authority bundle** (`context_glossary_approval_preflight` only): run `python3 scripts/preflight_authority_bundle.py prepare --runtime <codex|claude-code|cursor> --target-adr <path> --run-dir <dir>`, then its `emit`. It freezes prompt + ADR-FORMAT.md + CONTEXT.md + target ADR into one verified bundle; pass the returned runtime adapter fields **verbatim** and require the reviewer to echo `AUTHORITY_BUNDLE_COMPLETE: <nonce>`. Any emit/validation failure makes the round `tool_failed` — no serial-reread fallback.
- **Runtime rows** (apply exactly the row for the prepared dispatch's runtime):
  - **Codex:** `gpt-5.6-sol`, `xhigh` effort, native sub-agent facility (`spawn_agent`, no parent-conversation inheritance) — never a CLI.
  - **Cursor:** `cursor-grok-4.6`, `xhigh` effort, native `Task` facility — never the CLI.
  - **Claude Code — standalone attempt-prompt operations** (`check-should-write-adr`, `check-adr-redundancy`): native `Agent`, `subagent_type: general-purpose`, `model: opus`, `run_in_background: false`, the attempt's `dispatch_bootstrap` verbatim as the prompt; fresh context for `check-adr-redundancy`. No CLI, no bundle helper.
  - **Claude Code — quality-review modes:** CLI (a temporary patch until in-harness dispatch can set effort): pipe the bundle emitter into `claude -p --model opus --effort high --permission-mode auto --allowedTools "Read Write Bash" --tools Read Write Bash`, executing the helper's returned `pipeline_command` verbatim (`pipefail` rejects emitter failure; the reviewer gets everything before its first turn and must not reread). Never `dontAsk` or `bypassPermissions` — they strip the approval gate. One tier (opus + high) serves all three modes.
  - **Other runtimes:** strongest instruction-following model that has re-passed reviewer smoke; native sub-agent facility, never a CLI.
- **Allowed reviewer inputs:** review mode, target ADR, ADR-FORMAT.md, CONTEXT.md, bounded-context ADR references for reference resolution, Source Decision Extract and live corpus when provided. **Forbidden:** writer self-check evidence, session transcripts, author intent, repair history, answer keys, tests, smoke artifacts — anything not in the allowed set.
- **Retention:** reports live in OS-tmp run directories, never in bounded-context folders or shipped docs.

## Verdict and report

The reviewer writes only a minimal verdict payload (spec: the output-contract fragments in `QUALITY-REVIEW-PROMPT-BLOCKS.md`), runs `review_verdict_report.py`, and replies with one `REVIEW_REPORT_PATH: <path>` line — other prose is ignored. No path line or no valid report file invalidates the round. The script validates the payload (marker included), derives every bookkeeping field, persists the report, and prints its path.

Report fields (script-generated JSON): `target_adr_path`, `review_mode`, `review_status` (`pass|fail|degraded|not_evaluated`), `terminal_result` (null except preflight's `blocked_by_structural_unreadability`), `preflight_status`, `full_quality_review_completed`, `full_quality_review_notice`, the three support-data statuses (`provided|missing|degraded|not_applicable`), `blocking` / `non_blocking` (findings: `issue`, `evidence_location`, `why_it_matters`, `suggested_fix`, `gate_id`, `action_data`), `gate_coverage` (one key per canonical gate id → `evaluated|degraded|not_evaluated|skipped`), `reference_closure`, `scope_limitations`, `skipped_gate_reasons`, `reviewer_close_status` (`completed|tool_failed|scope_limited`).

Semantics: `fail` = any blocking finding; `pass` = all covered gates evaluated, none blocking; `degraded` = missing/degraded support data blocked a support-dependent gate (never mark such a gate cleanly evaluated). Every finding's `gate_id` must be canonical (`review_prompt_assembly.gate_ids()`) and in-mode — anything else invalidates the round before report generation.
