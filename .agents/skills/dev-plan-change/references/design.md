# Design artifact instructions

Create the design document that explains HOW to implement the change.

When to include `design.md` (create only if any apply):

- Cross-cutting change (multiple services/modules) or new architectural pattern.
- New external dependency or significant data model changes.
- Security, performance, or migration complexity.
- Ambiguity that benefits from technical decisions before coding.

## Sections

The roles below are the canonical ones from `dev/AGENTS.md`.
Take the actual headings, in the project's artifact language, from `dev/templates/design.md`.

- **Context:** Background, current state, constraints, stakeholders.
- **Goals / Non-Goals:** What this design achieves and what it explicitly excludes.
- **Decisions:** Key technical choices with rationale (why X over Y?).
  Include alternatives considered.
- **Impact:** The code, APIs, dependencies and systems the change affects.
- **Risks / Trade-offs:** Known limitations. Format: `<Risk>: <Mitigation>.`
- **Migration Plan:** Steps to deploy, rollback strategy (if applicable).
- **Deferred to implementation:** What is consciously left to the implementation phase, each item with the reason it can wait.
  A question that is still open is not deferred: settle it with the user before writing.
  Remove the section when nothing is deferred.

Focus on architecture and approach, not line-by-line implementation.
Reference the proposal for motivation and the specs for requirements.

**Important:** When drawing diagrams (e.g., a request sequence), **always** use Mermaid notation (a code block with the `mermaid` language specifier).
ASCII charts are prohibited in designs.

Strictly adhere to the project's code style guide, linked from the project root `AGENTS.md`.
You MUST read it before drafting the design document, so that the decisions you record are ones the codebase can actually adopt.
