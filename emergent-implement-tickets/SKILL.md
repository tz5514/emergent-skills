---
name: emergent-implement-tickets
description: "Implement a dependency graph of tickets strictly one at a time with fresh sub-agents and verified integration."
disable-model-invocation: true
argument-hint: "<tickets-directory>"
---

# Emergent Implement Tickets

Orchestrate the implementation of every ticket in the supplied directory along its `Blocked by` dependency graph: strictly one ticket at a time, one fresh sub-agent per ticket, every integration verified green. Delegate all code writes — the main agent never implements, edits, or fixes. This workflow requires a ticket set that keeps the integration branch green after every ticket; if the set is designed to stay red until a final integration ticket, stop and report instead of executing.

Once Prepare's questions are settled the run is unattended: ask the user nothing more; decide within these rules and put anything needing a human in the final report.

The **parent spec** is the `spec.md` in the tickets directory's parent (feature) directory. The **active tree** is the shared worktree when this run uses one, otherwise the **primary tree** — the working tree Prepare started in.

## Prepare

Read every ticket (identifier, status, `Blocked by`, spec reference) and validate: identifiers unique, every blocker exists, graph acyclic. Stop and report on any failure, before any code changes. Only `ready-for-agent` tickets are scheduled; skip tickets in any other status without executing or waiting on them — their dependents freeze under the frontier rule; report both. A `done` ticket counts as a completed blocker only after the Resume check below.

Ask the user these questions once, then never again this invocation:

1. **Worktree & branch** — does this run use one shared git worktree for ticket git work? Either way, settle the integration branch (suggest names from the directory basename, e.g. `.scratch/foo-bar` → `feature/foo-bar`; avoid collisions). Worktree chosen: the integration branch is a new branch forked from the current one — git refuses one branch checked out in two worktrees — create the worktree checked out on it and do all ticket git work inside it; the primary tree may stay dirty. Declined: the integration branch is the current branch or a new branch forked from it, and ticket git work happens in the primary tree, which must be clean before dispatch — otherwise stop and report.
2. **Uncommitted changes** — if the primary tree holds uncommitted changes, list them (one line each, per file) and let the user rule on each: bring it into this run, or leave it (worktree path) / stash it (declined path). ADR files named by the parent spec's Related Draft ADRs section ride along automatically. Change nothing until the user confirms the final lists. Commit the brought-along files onto the integration branch — the **transplant commit** — leaving no uncommitted copy behind; put stashed files into one stash that then belongs to the user: never touch it again. If Prepare fails later, while the transplant commit exists, move the changes back — restore them uncommitted in the primary tree and drop the commit; if anything looks unexpected, stop and report rather than overwrite, since the commit holds a safe copy.
3. **Push & PR** — on full success, push the integration branch and open a PR? If accepted and the integration branch was forked from the current branch, that branch is the base; otherwise ask for one (no base → push only, skip the PR).

If asking is impossible, invent nothing: integration branch = current branch, no worktree, primary tree must be clean, bring no file along; record this fallback in the report.

Re-invoking in the same session on the same directory reuses these answers (recreate a missing worktree without asking); the uncommitted-changes question alone is re-asked from a fresh scan. A different directory or session starts over.

When the parent spec's Related Draft ADRs section lists drafts, verify after question 2 that each resolves to exactly one lifecycle folder — `draft/` pending; `active/` or `archived/` already complete. Zero folders is also already complete when a commit in the integration branch's history deleted that draft's path; anything else stops the run before dispatch.

### Resume

Re-invoking on the same tickets directory resumes the run. For every `done` ticket, verify its recorded integration commit is in the integration branch history: pass → completed blocker; fail → report it and leave it alone. The completion mark is an index; repository history is the authority. All other tickets, half-finished ones included, dispatch normally from the current tip. Keep leftover branches from earlier runs — reuse or delete none — and list them in the report.

## Run

The **frontier** is every incomplete ticket whose blockers are integrated and verified. Loop: pick one frontier ticket, create a dedicated branch from the integration tip, dispatch one completely fresh sub-agent, integrate, recalculate the frontier. One ticket at a time; one sub-agent per ticket, never reused.

Delegate with the ticket reference, parent spec when present, branch, and base commit:

> Explicitly invoke the `emergent-implement` skill for `<TICKET_REFERENCE>`.
> Implement exactly this ticket on the assigned branch, which starts from `<BASE_COMMIT>` (contains all completed blockers).
> Do not implement sibling, downstream, or unrelated work; do not create or merge branches.
> Commit and return the commit SHA when the ticket completes, or when a user-decision blocker leaves material ruling-independent work; otherwise produce no commit — never fabricate one.
> In every case, return the `Outcome:` line and verification results.

Pass no earlier transcripts: repository, ticket, and spec are the source of truth. On a worktree run, every writing sub-agent works inside the worktree; give ticket and spec references as absolute paths (gitignored directories like `.scratch/` stay readable), and every ticket-file write — the sub-agent's checkbox ticks and your own marks — goes to the ticket's original absolute path.

Route each return by its single `Outcome:` line:

**completed** — accept only when the skill succeeded, the active tree is clean, a commit exists from the assigned base, and required checks pass. Integrate into the integration branch, run affected tests and typechecking, confirm green, then write the completion mark: set the ticket's `Status:` to `done` and append exactly one line to its Comments —

`Integrated: <integration-commit-SHA> (base: <base-commit-SHA>)`

Only the orchestrator writes this, and only after verified integration; checked acceptance boxes are never a completion signal. Keep the fixed format: Resume and the review parse it.

**failed** — commit any uncommitted leftovers as-is onto the failed branch (preserve the scene), then re-dispatch exactly once: fresh sub-agent, new branch from the current tip, carrying a failure summary — approaches tried, why each failed, directions to avoid. A second failure freezes the ticket: keep both branches, report them, continue with frontier tickets that don't depend on it.

**user-decision blocker** — the ticket needs a human ruling; its unaffected work is already done and verified. If the report names an unblocked-work commit, integrate it under the same acceptance checks as a completed ticket and append to Comments:

`Integrated unblocked work: <integration-commit-SHA> (base: <base-commit-SHA>)`

If those checks fail (uncommitted leftovers included — snapshot them onto the ticket branch as on the failed path), skip the integration, keep the ticket branch as the preserved scene, and still record the decisions below. An integrated commit is shared progress, never completion: no `done`, and descendants stay out of the frontier. Set `Status:` to `ready-for-human`, append each pending decision verbatim to Comments, and continue with independent tickets; decisions wait for the final report. To resume later, the human writes the ruling into the parent spec (or the ticket) and sets `ready-for-agent`; the ticket then dispatches normally from the current tip.

## Close

When the frontier is empty and tickets remain incomplete, report the blocking failures and decisions.

**Integration review** — runs only when every ticket is complete; otherwise record its passes as skipped, which also blocks ADR finalization and full success. Diff the integration tip against the fixed point: the earliest ancestor among all recorded base SHAs. Dispatch one fresh sub-agent per applicable pass:

- **Spec coverage** — against the parent spec (or, absent one and given multiple tickets, the aggregate of every ticket's What to build and acceptance criteria): check the aggregate change the way the `code-review` skill's Spec axis does. With a single ticket and no parent spec, this pass is not applicable.
- **Cross-ticket consistency** — only with two or more tickets. Brief: "This diff is the combined work of `<N>` tickets implemented by isolated agents. Report ONLY cross-ticket integration issues: (a) duplicated implementations; (b) naming divergence — the same concept named differently; (c) contradictory implicit assumptions between tickets. Cite files and tickets; classify each finding as 'bounded fix' (one mechanical action) or 'needs decision'. Under 400 words."

Record each pass as completed, not applicable (nothing to check), or skipped (set incomplete), with its reason. Route findings: every bounded fix → one fresh sub-agent applies them all and commits, then re-run the affected passes once; everything that re-run finds, and every needs-decision finding, goes into the report — never a second fix round.

**Final verification** — run the repository's full required checks in the active tree; the integration branch must be green.

**ADR finalization** — begins only when every ticket is complete, the review passes are terminal, no review finding remains unfixed, and checks are green; otherwise report the drafts untouched. Collect the still-pending `draft/` ADRs; if any exist, create a finalization branch from the integration tip and invoke the `emergent-adr` skill's finalize-draft-adrs operation exactly once with every pending path, passing `disposition_scope_git_recoverable_and_isolated: true`. Accept only when its summary gives each draft a terminal state — deleted, promoted, or unresolved — and the branch diff touches only ADR lifecycle directories; then merge into the integration branch. On any failure, preserve the finalization branch as the scene, restore the integration branch tip, and report — resolve or edit nothing.

**Report** — completed tickets and commits; failed, frozen, and skipped tickets with the chains they interrupt; every pending decision and where its ruling belongs; unblocked-work commits; the transplant commit and stash contents; each review pass's status and findings (fixed / needs decision); final verification result; the integration branch and final commit; ADR terminal states; preserved branches and worktrees needing follow-up. Declare **full success** only when every ticket is complete, the integration branch is green, and every draft ADR ended deleted or promoted; anything less is **partial completion**. On an accepted push & PR question and full success, push and open the PR (repository PR conventions apply) before the closing report.

**Cleanup** — after final verification, and ADR finalization when it ran, remove the shared worktree: that deletes only the directory, never a branch or commit. Keep it and report its path if it still holds the only copy of anything.
