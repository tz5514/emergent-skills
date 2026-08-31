# ADR necessity conditions (ADR 必要性條件)

Sole authority for the ADR necessity-condition judgment semantics and shared evidence rules. Consumers — the main agent's necessity self-check and `check-should-write-adr` — load this document as the only source: never copied, summarized, or replaced by memory. (Quality review is not a consumer: it lacks the conversation these conditions require as evidence.) This document defines only what is judged and what passing takes; evidence acquisition, timing, formats, and flow belong to each consumer.

Each condition has four sections — Core concept, Positive evidence required, Explicitly non-qualifying boundaries, Judgment requirements. They govern the judgment's content; they are a reading structure, not a form: filling every section, or surface similarity to some case, is never grounds for passing.

## Shared rules

- **Verifiable facts only.** Judge on established facts: what the user provided, the codebase, still-effective ADR decisions, other verifiable material. Reasonable derivation is allowed; fabricated reactions, behaviors, or predictions are not.
- **Uncertainty fails.** Insufficient evidence or a mere possibility of risk fails the condition. A wrong acceptance costs review/scan/reading maintenance forever; a wrong rejection is recoverable — so the default is strict.
- **Each condition needs its own causal account:** candidate-specific facts and why they make this condition hold. A condition-name restatement, a slogan, or another condition's pass is not a reason.
- **Evaluate every condition in full** once the prerequisite checks pass; report all failing conditions at once. Mark a condition unevaluated only when a prerequisite check blocked entry.
- **Every condition must pass.** One failure disqualifies the candidate.

## Condition: Hard to reverse

### Core concept

Holds only when, by the capabilities verifiable at review time, the party responsible for the change cannot — through actions it alone controls, over a transition with a definite end point — reliably eliminate the dependencies, legacy state, and obligations the choice left behind, or cannot keep satisfying existing requirements it has no authority to relax. The question is whether the transition can reliably end, not how large the work looks.

### Positive evidence required

- Established facts show a dependency, legacy state, or ongoing obligation the responsible party cannot eliminate alone, or an existing requirement it cannot relax alone.
- A business impact counts only when the established-fact sources already make it a constraint the project must obey.
- Released externally visible features and behaviors count as unrelaxable requirements until a role with decision authority explicitly allows them to change or degrade.

### Explicitly non-qualifying boundaries

- File count, code volume, refactor scope, or effort never suffice: if existing methods can transform mechanically and verify all requirements still hold, no amount of work qualifies.
- Release alone does not protect internals: if replacing them can still reliably prove external behavior unchanged, released ≠ hard to reverse.
- Unproven ease of reversal, mere risk possibility, or fabricated predictions (customer reactions, tolerance, future scale) never qualify.

### Judgment requirements

- Judge by the AI, tooling, alternative, and verification capabilities verifiable now; presume no future improvements, and let a capability change re-open the verdict.
- When preserving requirements would need semantic migration whose completeness cannot be proven mechanically plus broad manual verification, judge by the core concept whether that transition can still reliably converge.
- For an unwritten candidate, judge by its explicitly ratified applicable scope, inventing no usage scale, dependents, or undecided implementation; for an existing ADR, judge by what exists now.

## Condition: Surprising without context

### Core concept

Holds only when a reasonable future maintainer, lacking the decision's necessary context, would take another recognizable approach as the default and could therefore mistake the deliberate choice for a problem to fix. Defied expectations and mistaken-correction risk — not preserving discussion history.

### Positive evidence required

- Identify the recognizable alternative a reasonable maintainer would default to, with verifiable established facts grounding that expectation; reasonable inference from confirmed facts is allowed.

### Explicitly non-qualifying boundaries

- Not knowing the rationale, or wanting the backstory, never qualifies.
- Unsupported intuition, preference, or guesswork never supplies the expected-alternative grounds.

### Judgment requirements

- Spell out the causal chain: which context is missing → which alternative a maintainer would default to → how that risks the choice being "corrected". Any missing link fails.

## Condition: real trade-off

### Core concept

Holds only when the user, in the conversation that formed the decision, weighed differing benefits and drawbacks among explicitly raised viable options and chose. The weighing that actually happened — not what the choice could objectively be compared against.

### Positive evidence required

- Before ratification, the conversation explicitly presented viable options with each one's significant benefits and drawbacks, and the user afterwards clearly chose one (without needing to restate what they gave up).
- The options each retain a significant benefit the other cannot provide — weighty enough to affect the decision — so choosing one genuinely forgoes the other's.
- A benefit/drawback is significant only when linked in that conversation to a goal, constraint, risk, or criterion the user previously expressed, or explicitly stated as valued.
- An option is viable only when the conversation already contains confirmed facts supporting that it violates no known non-negotiable constraint (no prototype required).

### Explicitly non-qualifying boundaries

- An alternative discovered after the fact, never raised in the conversation, does not count.
- An option no worse on every significant dimension and better on one is not a trade-off.
- The user delegating the choice to the agent is not the user choosing and proves no weighing; the agent's chosen option never satisfies this alone.
- Without a significance basis, never infer that an objective difference matters to the user.
- A theory-only alternative with no supporting facts is not viable.

### Judgment requirements

- Locate the actual weighing: which options and significant benefits/drawbacks were explicitly presented, and where the user clearly settled on one.
- Earlier delegation does not permanently disqualify: once options and stakes were explicitly presented and the user finally and clearly selects one, the chosen-by-the-user bar is met; viability, significance, and mutual forgoing must still each hold.
