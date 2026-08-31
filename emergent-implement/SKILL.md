---
name: emergent-implement
description: "Implement exactly one settled ticket or spec only when the current task explicitly names the emergent-implement skill and identifies one concrete unit of work. Do not use for general coding requests, planning, or multiple tickets."
argument-hint: "<single ticket, issue URL, file path, or settled unit of work>"
---

# Emergent Implement

Implement exactly one settled unit of work. Its scope and decisions were ratified upstream; everything the settled input leaves unspecified emerges through code, tests, and integration feedback.

Proceed only when the task explicitly names `emergent-implement` and identifies one ticket or spec with clear scope and acceptance criteria; otherwise report what is missing and stop without editing code.

## Workflow

1. Read the ticket or spec in full — parent context and comments included — plus repository instructions, the domain glossary, and relevant ADRs.
2. Verify the ticket's declared blockers are done in the current repository state; a missing one is a failure to report, never work to do.
3. Search the codebase for existing implementations and conventions; reuse before writing.
4. Load the authorities (below); hard stop on failure.
5. Implement only this unit — the `tdd` loop when loaded, otherwise tests at the ticket's seam or per repository convention. Run focused tests and typechecks as you go.
6. Run the full relevant test suite.
7. Review with the `code-review` skill against repository standards and the originating ticket; fix every finding within this unit's scope.
8. Commit to the current branch. Never create, switch, merge, or delete branches or worktrees.

## Authorities

Formally load — the complete skill body brought into context by the runtime's own skill mechanism (the Skill tool here, with a full-file Read of its `SKILL.md` only as fallback after the tool fails; that same Read on runtimes without one); memory or a summary never counts:

- **`emergent-design`** — the sole engineering-philosophy authority: it draws the human-decision boundary and says what may emerge.
- **`codebase-design`** — subordinate method: the module／interface／seam vocabulary and principles.
- **`tdd`** — subordinate method; load when the run will use it.

If `emergent-design` or `codebase-design` fails to load, fail closed: report exactly what you tried (runtime, path or registry key) and stop with no code edits — a restatement never replaces the loaded body.

## Binding and free

- **Binding** — every ratified commitment in the settled ticket or Spec, internal implementation requirements included: implement as written; never re-review, weaken, or reopen.
- **Free** — everything unspecified: owned by code, tests, and integration feedback; improve it whenever implementation evidence exposes a better answer.

Build in thin end-to-end slices; each slice's evidence steers the next, and no slice waits for sign-off.

When the unit creates or reshapes a module, interface, or seam — internal ones included — apply the loaded `codebase-design` guidance deliberately to depth, seam placement, and testability; otherwise keep its vocabulary at hand without turning the unit into a design exercise. Reuse settled seams and contracts. For seam-placement or replaceable-adapter work, also read `DEEPENING.md` beside the loaded skill — and only that file: never `DESIGN-IT-TWICE.md` nor its parallel alternative-interface workflow.

## user-decision blocker

Return a question to the human only when all three hold:

1. A settled obligation cannot be fulfilled without the answer, and no in-scope route sidesteps it.
2. No authority answers it: ticket, parent Spec, ADRs, domain language, repository state, loaded skills.
3. Answering it yourself would create a commitment reserved for humans — the standing example is an unsettled caller-visible contract or replaceable seam. Never invent one.

Hard problems, low confidence, and internal design choices fail this test and are yours to solve in the free space.

On a confirmed blocker, freeze only the work whose correctness depends on the ruling. Finish and verify everything else, commit it as an **unblocked-work commit** (none when nothing material exists), keep ruling-dependent edits out of the tree, and return every pending decision in one report. That commit is shared progress, never ticket completion.

## Output

Let each carrier own its information: tests preserve the required observable behavior at the agreed seams; code carries every intent names, types, and structure can make evident; a comment only where code cannot — the fence question: did this deliberately avoid a more obvious approach? Then one line on why, stating the decision itself. Never cite the spec, ticket, issue, or ADR in anything you produce.

Stay inside the unit: no sibling or downstream tickets, no reopening settled decisions, no speculative features or unrelated refactors. Scheduling, integration, and completion status belong to the calling orchestrator.

## Completion

Start the return with exactly one line — `Outcome: completed` ／ `Outcome: user-decision blocker` ／ `Outcome: failed` — then:

- **completed** (every acceptance criterion met, suite green): summary, acceptance-criteria status, checks run, review findings and fixes, commit SHA, unresolved risk.
- **user-decision blocker**: per decision — the concrete question, why it is human-side, the work it blocks; plus the verification performed on the finished work and the unblocked-work commit SHA (or that none existed).
- **failed** (no pending ruling explains it): approaches tried, why each failed, directions not to retry.
