# ADR Format

An ADR records one architecture decision (what + why). Three folders under a bounded context's `docs/adr/`; **the folder is the single signal of state and mutability**:

- `draft/` — not yet implemented; freely editable.
- `active/` — implemented and in force (including partially superseded); **immutable**.
- `archived/` — fully superseded; **immutable**.

Create folders lazily. Changing an `active`/`archived` decision means writing a new draft that supersedes it — never editing in place. Supersession scans compare a draft only against `active/`. Legacy four-digit filenames stay valid.

## Template

```md
---
status: not_implemented_yet
description: {retrieval trigger — required; must not reveal the decision result}
---

# {Short title}

## Background

{The problem and its drivers. Historical framing only — not the answer, not current ground truth. Optional/brief when self-evident.}

## Atomic Decisions

- **a.** {One atomic decision: a single, independently-comparable unit of new decision content.}
- **b.** {The second, if compound.}

## Rationale

{Why this answer, how the decisions relate, trade-offs. The *why* — never restates the *what*.}
```

Body order is fixed; the three English headings are machine anchors. Decision content appears exactly once, in `## Atomic Decisions`. Truth test for everything else (`description`, Background, Rationale): if every atomic decision here were later superseded, it must still read as true history.

## `write` operation contract

`write` creates a new draft or substantively modifies an existing draft — no review loop, scan, or promotion (the caller orchestrates those).

**Authorization:** necessity is settled before `write` — an agent flow holds a valid `check-should-write-adr` approval or the user's explicit scope-named clearance; a human-invoked entry carries the user's own ruling. `write` trusts the caller and never re-judges. One authorization covers later same-draft repairs that keep the decisions' meaning; substantively changing the reviewed scope stops the write and requires a new review round. Turning create-mode prose into atomic decisions is `write`'s job, within the authorized candidate only.

**Inputs:** `mode` (`create`|`modify`); `bounded_context_path` (create) or `target_adr_path` (modify — verify it belongs to its bounded context); source material (informs the ADR and support data, never copied wholesale).

**New draft:** get the id from `generate_adr_id` in `scripts/adr_id.py`; name the file `{id}-{slug}.md` (you choose the slug, never the id). Active/archived rewrites happen only on the user's explicit one-time migration request.

**Terminals (the only two):**

- `written` — returns `target_adr_path`, `adr_id`, `created_or_modified`, `created_or_changed_atomic_decision_ids`, `source_decision_extract_path`, `writer_self_check_evidence_status`.
- `needs_context_ruling` — the write needs a new/changed CONTEXT.md term: stop without inventing vocabulary.

**Source Decision Extract:** support data for a later blind review — a compact accounting of what the ADR must preserve (candidate decisions, supersession intent, boundaries, material exclusions), written to the run directory. Keep transcript content, expected wording, writer intent, and implementation detail out of it.

**Writer self-check evidence:** record (status + path only, never reviewer input) that you checked extract closure, `description` leakage, section roles, atomicity, eligibility, same-file id use, vocabulary, and support-data placement.

## Frontmatter

Only `status` and `description` are always present. `supersedes` / `superseded_by` appear **only when a real relationship exists**.

```yaml
status: not_implemented_yet   # DERIVED, never hand-set — see Status enum
description: 管轄議題一句。觸發詞：詞1、詞2、詞3   # ≤300 chars — see below
superseded_by:                # on the superseded file
  - adr: <other file's stable id/filename>       # resolves across active/ + archived/
    atomic_decisions:
      - { ours: <old id in THIS file>, theirs: <new id or [ids] in the OTHER file> }
supersedes:                   # on the superseding file — the mirror view
  - adr: <other file's stable id/filename>
    atomic_decisions:
      - { ours: <new id or [ids] in THIS file>, theirs: <old id in the OTHER file> }
```

- **Symmetric schema:** the two keys are one relationship seen from each side — convert by swapping `ours`↔`theirs` and the `adr` pointer. `ours`/`theirs` are file-relative. The old side is scalar; the new side is scalar or an id array when several new decisions jointly replace one old one (single replacement stays scalar).
- Both keys are lists; many-to-many is normal. Every replaced atomic decision is listed individually.
- `adr` links resolve across `active/` + `archived/` and never point at a draft.
- No per-entry status field — aggregate `status` is computed, never stored twice.

### Status enum

Derived from folder + supersession record; recompute at creation, promotion, and each applied mark:

- `not_implemented_yet` — in `draft/`.
- `fully_ground_truth` — in `active/`, nothing superseded.
- `partially_superseded` — in `active/`, some decisions superseded.
- `fully_superseded` — all superseded; exactly the condition for `archived/`.

## The `description` field — a retrieval trigger

Written only while a draft; locks forever at promotion. Consumers may load only `active/` descriptions to decide which ADRs to open — the field's one job is to make a future discussion pull this ADR up.

**A trigger, not a summary.** `## Atomic Decisions` is the only decision authority; a description a reader can act on is how a binding decision gets silently skipped.

One string ≤300 chars, form `管轄議題一句。觸發詞：詞1、詞2、…` (ceiling informational, never enforced):

1. **The governed issue, one sentence** — the *question* this ADR settles ("the issue of when/whether/how X"), in CONTEXT.md's ratified vocabulary.
2. **Trigger keywords** — glossary headwords first (exact wording), then discriminating synonyms; never an `_Avoid_` term. Over-listing a discriminating synonym is cheap; missing one loses the retrieval.

**Two leak tests, applied to the sentence and every noun phrase:**

- **Conclusion leak:** could a reader state the decision from the description alone? Then rewrite to name only the question. ✗ "推翻標記延後到搬入 active 才套用、schema 改為對稱" → ✓ "推翻標記何時套用、以及 supersession schema 採什麼形式的議題".
- **Axis vs value:** name the open *axis*, never the chosen *value* — including values hidden as adjectives (`不可竄改`), framing nouns (`雙讀者設計取向`), or presuppositions. `可變性判準` is safe; `不可竄改性質` leaks.

**Also never in a `description`:** code-level implementation names (they go stale); rationale, trade-offs, or background narrative (they belong in `## Rationale`); ADR ids, ADR decision citations, or file paths as durable content — describe the old state directly.

**Discrimination test (every keyword):** would it pull up a large fraction of this context's ADRs? Then cut it — generic words (`ADR`, `決策`, `流程`) never work as triggers.

**Survives supersession by construction:** an issue stays the issue after its decision dies, so a correctly axis-framed description never needs the edit it can never get. Never scope it to currently-live decisions. Use today's ratified vocabulary even when the body uses a retired term.

**Self-check before done:** (a) would another session open this ADR from the description alone — yes; (b) could it state the decision without opening — no; (c) still correct if all decisions were superseded — yes.

## `## Atomic Decisions` — the single source of truth

- Each decision has a stable id (`a.`, `b.`, …). **Ids freeze once written:** additions take the next unused letter; deleted letters are never recycled; never reorder — cross-file `{ours, theirs}` references must resolve forever.
- A single-decision ADR still lists its one decision. A compound decision stays in one ADR with prose relating its parts.
- Background/Rationale may cite same-file ids but never restate or contradict a decision.
- **New decision content only:** existing facts, old decisions, process notes, implementation details, examples, and rationale prose belong elsewhere.

### Splitting — the partial-supersession test

An atomic decision is the unit a future ADR could plausibly supersede on its own.

- **One question, one answer.** Split only where a future ADR could credibly replace one part while the rest stands. Logical decomposability alone is not a split reason.
- **Convergence floor:** facets that would change together (one contract's input/output/scope) stay one decision.
- **A decided relationship is its own decision:** a binding conditional/causal link between decisions ("a, under X, causes b") is decision content — give it its own atomic decision. Explanatory relations stay prose.
- **Ids carry references, not payload:** the sentence must still state the condition/default/exception in domain language; if deleting the id deletes understanding, rewrite the payload into the sentence.
- Defaults and their conditional overrides split when the condition could be superseded alone. Binding dependencies and decided endpoints (readiness thresholds, stop conditions) are decision content, never only prose.
- Atomicity is your judgment at write time; `scripts/atomicity_lint.py` flags structural suspects (table rows, multi-item enumerations in one bullet) without deciding.

### Eligibility — the future-replacement test

Keep a candidate only when a future replacement could state a **different trade-off conclusion with new reasons** about the same question.

- A concrete value stays eligible when changing it necessarily reopens the trade-off.
- A **remeasurable parameter value** (a change just reruns the same measurement) is not a decision — the implementation owns the value; name only the stable contract layer.
- A **completed one-time act** (migration, bootstrap) is historical prose — but first extract any still-binding rule inside it into an atomic decision, and when a measured value's evidence rejected a real alternative, keep the protection as a change-procedure decision.
- Prospective only: never initiate supersession just to reclassify old content.

## `## Background` and `## Rationale` — history, never current truth

Supersession tracks only `## Atomic Decisions`; these two sections are never updated when a decision dies, so they are defined as point-in-time history. Every current fact or binding relationship belongs in `## Atomic Decisions`. Write them to survive supersession ("the premise *was*…", "we *weighed*…"). Reader rule: for the present, read only `## Atomic Decisions` plus statuses. A selected behaviour, threshold, default, or endpoint mentioned in Rationale must also live as an atomic decision — Rationale explains the why, never solely records the what.

## Supersession lives only in frontmatter

A relationship counts only when recorded in `supersedes`/`superseded_by`. Body prose never creates one.

## Self-sufficiency

A shipped file is read without its conversation: delete the conversation — the file must stay fully meaningful. Legal references: descriptive text (naming by content), the frontmatter `adr:` links, and external source links. Option codes, deictic phrases ("the approach we discussed"), and plan-stage labels are violations.

## No ADR-id prose citations

Body prose never cites ADR ids/filenames/other ADRs' decision ids as durable content — describe the old state directly. Frontmatter `adr:` keys are exempt; conversation output is exempt; frozen citations in immutable ADRs stay as-is.

## Prose conventions

Name stable contracts (documents, formats, fields, process rules), never code-level identifiers — they drift. Name recurring output blocks by role, never by emoji glyph.

## When to offer an ADR

Necessity is judged before writing, by `ADR-NECESSITY-CONDITIONS.md` alone — load it and judge by it. This file deliberately carries no condition text.
