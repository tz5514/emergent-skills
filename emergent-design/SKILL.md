---
name: emergent-design
description: Shared engineering philosophy of emergent design. Use when deciding what humans must settle before implementation versus what should emerge through code, tests, and integration feedback; when deciding which carrier should own a piece of information, including whether an ADR is appropriate at all; or when another skill needs the emergent-design model.
---

# Emergent Design

Emergent design treats implementation as a design-and-learning stage, not transcription of a completed blueprint: humans settle the commitments only they can own, and the rest forms through code, tests, and integration feedback, kept on course by the engineering control system below. It rejects both failure extremes:

- **Complete up-front design** raises the floor but lowers the ceiling on implementation-time judgment, and its detailed plans go stale the moment real code diverges.
- **Unconstrained improvisation** — vibe coding — loses predictability, understandability, and maintainability.

Design knowledge has layers of sayability: some can be stated reliably before any code exists; much becomes sayable only once implementation evidence — real code, callers, tests, integration — exists. Forcing the unsayable to be settled up front produces guesses dressed as decisions, and guesses are what go stale; implementation is where that missing design knowledge is learned.

## The human-decision boundary

A decision needs humans up front when it creates a shared commitment or requires human authority, risk ownership, or cross-boundary coordination:

- externally observable or caller-visible contracts
- cross-ticket dependencies and shared seams
- non-negotiable product, compatibility, security, or legal constraints
- choices the user explicitly fixes
- testing seams that need prior agreement, so intended behavior can be exercised and the TDD/implementation feedback loop can begin — private and internal replacement seams remain free to emerge

Labels do not decide: calling a choice "architecture", "prototype", or "implementation detail" does not by itself make it an up-front human decision. A choice that creates none of the commitments above remains eligible to form through the codebase, tests, and implementation feedback.

## The engineering control system

Engineering disciplines keep the free implementation space inside the intended context; they are what separates emergent design from vibe coding:

- **Vertical slices and short feedback loops** expose real behavior, integration constraints, and design information incrementally, so evidence replaces up-front guessing.
- **TDD through agreed testing seams** keeps observable behavior executable and stable while internal structure keeps emerging and being refactored.
- **Deep modules and narrow interfaces** contain complexity, minimize what callers must know, and preserve the freedom to replace internal design.
- **Ubiquitous language and `CONTEXT.md`** keep local implementation choices aligned with the shared domain model.
- **Selective ADRs** preserve only the lasting decision context no long-lived carrier below can appropriately hold.

## Information-carrier responsibility

Give each meaning one authoritative home in the closest durable carrier that can make it evident. At planning time, judge each carrier by what it will be able to express once it exists, not by what happens to exist today — absence of code is not evidence that future code cannot express a decision.

### Long-lived carriers — ground truth

- **Code** owns concrete implementation and every implementation intent expressible through structure, types, naming, and behavior.
- **Tests** own the observable behavior the user stories require — the durable record of it, in place of a duplicate long-lived user-story document.
- **Interfaces** own the caller contract: everything a caller must know to use a module correctly.
- **Local comments** own only local intent that code cannot make evident.
- **`CONTEXT.md`** owns the shared domain language.
- **ADR** enters consideration only for lasting decision context that none of the carriers above can appropriately carry — and such a candidate must still pass independent necessity review.

### One-shot carriers — goals in transit

- **The spec** is the required handoff layer from ratified conversation into implementation: it records all ratified needs and design and forwards them to implementers. It may instruct that specific long-lived carriers must eventually hold specific information; fulfilling that instruction completes its one-shot responsibility.
- **Tickets** split the spec's work into the current round's units.

Both describe goals and intended work only; before, during, and after implementation — even when the code momentarily matches them — ground truth lives exclusively in the long-lived carriers.
