---
name: emergent-spec-review
description: Dual-axis review of one frozen spec document — two context-isolated reviewers judge the same text in parallel: one holds the complete conversation and checks decision fidelity, one holds no conversation and checks whether an implementer could build and verify it. Use when a spec needs review before implementers receive it, when a spec-production pipeline dispatches a review round, or when the user asks to review a spec document.
---

Reviews exactly one frozen Candidate per invocation, along two isolated axes in parallel:

- **conversation decisions reviewer** — receives the complete conversation evidence and checks both directions: every user-ratified decision landed in the Candidate, and every commitment the Candidate binds traces to an authority allowed to create it.
- **implementation ready reviewer** — receives no conversation and judges one question: could an implementer build and verify the Candidate from it alone.

Report only: both reviewers return blocker findings and never write repairs; this skill edits nothing. Merging the reports, adjudicating, repairing, and re-dispatching a failed round belong to the caller.

## Inputs

- **Candidate path** — the one frozen document, the same file for both axes.
- **Conversation artifact** (conversation axis) — caller-prepared JSONL, one record object per line, already selected and cut by the caller; the assembler rejects a missing, unreadable, or non-JSONL file. A prose summary or decision checklist is not a conversation artifact.
- **Declared authorities / documents** — the ADRs, `CONTEXT.md` files, and external references the Candidate formally declares, passed per the axis flags below.

The implementation ready axis gets no conversation and no account of it — the assembler refuses a run directory holding one. That absence is the instrument: what this reviewer cannot determine, an implementer cannot either.

## Workflow

1. Create one **fresh, empty run directory per axis** under the OS tmp area or the session scratchpad.

2. Assemble both prompts, each command naming the same Candidate path:

   ```
   python3 <this skill>/scripts/prompt_assembly.py conversation_decisions \
     --candidate <candidate path> --run-dir <conversation decisions run dir> \
     --conversation <conversation artifact> \
     [--authority <path> ...]
   ```

   ```
   python3 <this skill>/scripts/prompt_assembly.py implementation_ready \
     --candidate <candidate path> --run-dir <implementation ready run dir> \
     [--allowed-doc <path> ...]
   ```

   Each command writes the complete prompt file and prints run metadata JSON. Equal `candidate_digest` values across the two commands prove both axes hold one version; unequal means the Candidate moved — re-freeze it and restart. The written prompt file is the **sole authority**: dispatch it as-is, never transcribe, summarize, or amend it.

3. Dispatch both reviewers in parallel per the rules below, and wait for both terminal replies before touching either result.

4. Save each reviewer's reply to its own file; the validator extracts its `REVIEW_REPORT_PATH:` line.

5. Validate both rounds, passing the assembler's printed values back exactly:

   ```
   python3 <this skill>/scripts/report_validation.py conversation_decisions \
     --from-reply <saved conversation decisions reply> \
     --expected-report <assembler report_path> --candidate <assembler candidate_path> \
     --input-digest <assembler input_digest> \
     --conversation-artifact <assembler conversation_artifact_path> \
     [--authority <each assembler authority_docs value> ...]
   ```

   ```
   python3 <this skill>/scripts/report_validation.py implementation_ready \
     --from-reply <saved implementation ready reply> \
     --expected-report <assembler report_path> --candidate <assembler candidate_path> \
     --input-digest <assembler input_digest> \
     [--allowed-doc <each assembler allowed_docs value> ...]
   ```

   Only `valid <report path>` accepts an axis; any `invalid: …` output discards that report whole. The invocation passes only when both axes are valid — a missing or invalid report is never read as zero findings.

6. Return both reports side by side, role-labelled: each axis's findings in reviewer order, its per-check conclusions, and its report path. Keep the axes separate — no merged list, no cross-axis ranking.

## Dispatch

- Issue both dispatches before awaiting either, then join both. Foreground only — never background a reviewer, never use a CLI.
- Each reviewer runs in a fresh context and receives only a one-line bootstrap: read the assembled prompt file and follow it. Nothing else reaches it — no conversation context, intent, or history.
- **Claude Code:** two Agent tool calls in one batch, each with `subagent_type: general-purpose`, `model: opus`, `run_in_background: false`; no effort, no tool set. Each Agent's terminal reply is that axis's reply.
- **Other runtimes:** the native sub-agent facility, both calls in one batch. Codex: `fork_turns: "none"`, model `gpt-5.6-sol` + `xhigh`. Cursor: `cursor-grok-4.6` + `xhigh`. Elsewhere: the strongest instruction-following model available.
