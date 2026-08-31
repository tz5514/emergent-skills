---
name: emergent-to-spec
description: Turn the current conversation into a spec published to the project issue tracker — official to-spec baseline plus emergent-design philosophy, then dual-axis review and repair until it settles, with one batched ask for what only the user can decide.
disable-model-invocation: true
---

## Load authorities

1. Read `../to-spec/SKILL.md` in full, resolved from this skill's own installed directory — the only load path; never ask the runtime's skill-loading mechanism for `to-spec`. A Skill-tool refusal for `to-spec` already in context does not stop the run: that guard blocks autonomous invocation, and this run was started by an explicit human command.
2. Load the complete `emergent-design` skill (the Skill tool where available, otherwise read its `SKILL.md` in full).

Both loads are fail-closed: if either is incomplete, report which authority is missing and end the run without a spec — never run this overlay alone, and never substitute a summary, paraphrase, or memory for a loaded authority.

Then execute the baseline process as written, under the overlay below.

## Related ADRs

If the conversation created or modified an ADR via emergent-adr, or named an ADR this spec implements or must follow, follow [ADR-REFERENCE-HANDLING.md](ADR-REFERENCE-HANDLING.md): selection and path validation before the baseline's repository exploration, the rest before publishing.

## Overlay: what the spec may bind

The loaded `emergent-design` skill is the philosophy; apply it as loaded, with no local summary. It changes what the spec says, never when the baseline acts — the seam check, publication, and `ready-for-agent` marking keep their baseline positions.

- The seam check is the only pre-spec question: confirm the highest seam at which the intended behaviour can be observed, and never ask the user to settle mocks, private interfaces, or any other implementation choice.
- A sentence binds implementers only when the conversation ratified it, a declared authority or verified unrelaxable constraint fixes it, or it restates one of those in verifiable form without choosing anything new.
- Everything nobody fixed — explored ideas, this agent's preferences, internal structure — stays non-binding, however unfinished a template section looks without it.

## Post-publication review

The published spec is the first Candidate. Loop until done:

1. **Dual review.** Build this round's conversation artifact fresh: run the installed `transcript-path` skill's `scripts/main.py` locator, feed the path it prints to `extract-transcript` (default selection), then cut the artifact with this skill's `scripts/crop_review_conversation.py`. Invoke `emergent-spec-review` with the Candidate path, the cropped path the script prints, and only the documents the Candidate formally lists — nothing else. Proceed only when both axes return valid reports on this exact Candidate text.
2. **Dispose of every finding, in order, per axis.** A finding is a problem claim to verify, not a mutation order. Verify it against the text, the code, and the authorities, then close it as exactly one of:
   - **Repair** — the claim holds and existing authority already answers it: make the smallest edit that removes the failure, update the references that edit breaks, and let nothing else ride along.
   - **Reject** — the claim does not hold: record the concrete reason and the evidence checked.
   - **Frontier** — the claim holds but only the user can answer it (an observable behaviour, shared commitment, or unsettled constraint): park the question, never invent the answer. A missing internal design choice goes to the implementer, not the frontier.

   If a finding stands only because of the last repair, re-examine the finding that repair answered instead of patching on top.
3. **Any edit spends both reports.** Finish the disposition pass against the text the reviewers read, then return to step 1 with the new Candidate; nothing from this round reaches the next round's reviewers.
4. **One ask.** Only when nothing can advance without the user, send the whole frontier — deduplicated, still-live questions only — in a single ask, land the answers in the Candidate, and return to step 1. Tell the user answers can surface new questions.

**Done** when both axes hold valid reports on the latest text, every finding is closed, the frontier is empty, and no edit followed. Then pens down: any later change starts a new cycle.
