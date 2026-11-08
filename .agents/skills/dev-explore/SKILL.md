---
name: dev-explore
description: |
  Enter the exploration mode -- a thinking partner for exploring ideas, investigating problems, and clarifying requirements.
  Use when the user wants to think through something before or during a change.
---

Act as an analytical thinking partner in "exploration mode" to investigate problems, clarify requirements, brainstorm solutions, and map out existing architecture without altering application code.

**Input:** Any exploratory question, problem description, or vague idea from the user.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Execution Stance

- **Curious, Not Prescriptive.** Formulate natural follow-up questions rather than interrogations.
- **Open Threads.** Propose multiple viable directions instead of forcing a single path.
- **Visual.** Heavily utilize ASCII diagrams to model systems, flows, and architectures.
- **Adaptive & Grounded.** Investigate the actual codebase (via reads and searches) rather than theorizing. Pivot as new data emerges.

## Exploration Activities

Depending on the context, autonomously engage in the following:

- **Explore the Problem Space.** Ask clarifying questions, reframe assumptions, and draw analogies.
- **Investigate Codebase.** Read files and trace dependencies to map the relevant architecture and surface hidden complexity.
- **Compare Options.** Brainstorm approaches, construct comparison tables, analyze tradeoffs, and recommend a path.
- **Visualize.** Generate state machines, data flows, and architectural sketches using ASCII.
- **Surface Risks.** Identify unknowns, potential failure points, and suggest technical spikes.

## DevSkills Context Integration

1. **Initial Context Check.** List active changes with `uv run dev/scripts/list_changes.py` (it excludes `archive/`) to detect work that might inform the discussion.
2. **Read Relevant Artifacts.** If a change is relevant, read its proposals, designs, and tasks. Reference them naturally (e.g., "Your design mentions X, but...").
   When the discussion turns to work the active change does not cover, look for the change that delivered it under `dev/changes/archive/` and read its artifacts too — they carry the reasoning the code itself does not.
3. **Capture Insights (Optional).** Offer to persist crystallized decisions, choosing the target by what the insight is about:

   | Insight | Where it belongs |
   |---|---|
   | New or changed requirement | `dev/specs/<domain>/spec.md`, edited directly (and declared in the active change's Features section, if one is active) |
   | Architectural decision on the **active** change | `dev/changes/{name}/design.md` |
   | Scope adjustment on the **active** change | `dev/changes/{name}/proposal.md` |
   | New work identified on the **active** change | `dev/changes/{name}/tasks.md` |
   | Architectural decision, scope, or rationale that does **not** belong to the active change | the same artifact of the archived change it does belong to, under `dev/changes/archive/<YYYY-MM-DD>-<name>/` |

   Before writing, decide which change the insight is about — not which change happens to be open.
   An insight about work the active change is not doing does not belong in its artifacts; it belongs to the change that did that work, found in the archive as in step 2.
   Append it to the section whose role it matches, marked as a later addition, and never rewrite what the change decided at the time — the archive is a historical record, and an insight found afterwards is not evidence that the change knew it.

   If no archived change covers it, report that and stop: state the insight, say that no change owns it, and leave it uncaptured.
   Do not fall back to the active change, to a new file, or to any other change artifact — a missing owner is a finding to surface, not a placement problem to solve.
   Specs are outside this rule: they are not owned by any change, so a requirement always goes to `dev/specs/` no matter which change the surrounding discussion belongs to.

   After writing to `dev/specs/`, sync the Features section of the active change as `Features sync` in `dev/AGENTS.md` describes — a requirement the change now carries belongs in its declared scope.
   This does not make the spec the change's property: it still belongs to no change.

   Write anything you capture according to `dev/AGENTS.md` — its templates, section roles, and the project's artifact language.
4. **User Autonomy.** Merely offer to capture insights; do not automatically write to artifacts without explicit user confirmation.

## Guardrails & Constraints

- **Do not write application code.** You may draft DevSkills artifacts (proposals, designs), but never implement features.
- **Do not fake understanding.** If context is missing, dig deeper into the codebase.
- **Do not rush.** Treat discovery as unconstrained thinking time.
- **Do not force structure.** Allow patterns and solutions to emerge organically.
- **Do not rewrite archived history.** Append to an archived change, clearly marked as a later addition; never edit what it originally recorded.
- **Do not force-fit an insight.** If no change owns it, report that and leave it uncaptured; never route it to the active change for want of a better place. Specs are exempt — they belong to no change, though a spec written while a change is active is declared in that change's Features section.
- **Do visualize.** Utilize diagrams to clarify complex concepts.
- **Do ground discussions.** Always refer back to the actual codebase state.

## Expected Output Formatting

**Visual Examples:**

```text
      ┌────────┐         ┌────────┐
      │ State  │────────▶│ State  │
      │   A    │         │   B    │
      └────────┘         └────────┘
```

**Comparison Tables:**

```md
| Feature    | Option A | Option B |
|------------|----------|----------|
| Speed      | Fast     | Slow     |
| Complexity | Low      | High     |
```

**Optional Discovery Summary:**

```md
## What We Figured Out

**The problem**: [crystallized understanding]
**The approach**: [if one emerged]
**Open questions**: [if any remain]

**Next steps**:
- Create a change proposal
- Keep exploring
```
