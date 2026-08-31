---
name: emergent-to-tickets
description: Break a plan, spec, or the current conversation into tracer-bullet tickets via the official to-tickets baseline, judged by the emergent-design philosophy.
disable-model-invocation: true
---

1. Read `../to-tickets/SKILL.md` in full, resolved from this skill's own directory. This direct sibling read is the designed load path — never a Skill-tool call for `to-tickets`, whatever a global rule or an in-context refusal says: that guard only blocks autonomous invocation, and a human invoked this wrapper.
2. Load the `emergent-design` skill in full (Skill tool, or read its `SKILL.md`).
3. If either load came back incomplete, stop: report which authority is missing and publish nothing. Memory never stands in for either.
4. Run the loaded baseline process — it owns flow and publication. The loaded philosophy judges ticket content via the constraints below; a ticket is publishable only when it satisfies every applicable one.

## Ticket constraints

- **Sources stay open.** A conversation or plan alone is a valid source; this skill adds no prerequisite document. The parent spec is only a spec the user pointed this run at — handed in, or just written this session. Never hunt the repository for one.
- **Every ticket reaches the spec alone.** With a parent spec, a ticket is finished only when it, read by itself, names a path or link its implementer can actually follow to that spec for the ticket's upstream requirements — each ticket is picked up as one file, with no sibling or batch summary — on top of the ticket's own deliverable, done-check, and blockers.
- **Only settled decisions bind.** Ticket text binds its implementer solely where the conversation ratified the choice, or a declared authority or verified unrelaxable constraint fixes it. Restating a settled decision as checkable work chooses nothing new.
- **Explored design stays out.** Modules, files, data structures, and seams the conversation merely explored stay out of the requirements, however thin the ticket looks; the implementer settles them in code.
