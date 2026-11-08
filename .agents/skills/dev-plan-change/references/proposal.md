Create the proposal document that establishes WHY this change is needed.

## Sections

The roles below are the canonical ones from `dev/AGENTS.md`.
Take the actual headings, in the project's artifact language, from `dev/templates/proposal.md`.

- **Why:** 1-2 sentences on the problem or opportunity.
  What problem does this solve? Why now?
- **What Changes:** Bullet list of changes.
  Be specific about new features, modifications, or removals.
  Mark breaking changes with **BREAKING**.
- **Features:** Identify which specs will be created or modified.
  Every bullet names the feature and links to its spec file, in the shape `dev/templates/proposal.md` defines:
  a root-relative link (`/dev/specs/<name>/spec.md`) so it resolves from the repository root and survives archiving.
  The link is what every later step follows to reach the spec, so write it even for a file that does not exist yet.
  A change that alters no requirement leaves both subsections empty, and the workflow then goes from `proposal.md` straight to `design.md`.
    - **New features:** Features being introduced.
      Each becomes a new `dev/specs/<name>/spec.md`.
      Use kebab-case names (e.g., `user-auth`, `data-export`).
    - **Changed features:** Existing features whose REQUIREMENTS change.
      Only include if spec-level behavior changes (not just implementation details).
      The spec is edited directly in `dev/specs/<name>/spec.md`; the difference is visible in `git diff`.
      Check `dev/specs/` for existing names.
      Leave empty if no requirement changes.
- **Artifacts:** Copy the section from `dev/templates/proposal.md` unchanged.
  Its relative links lead from the proposal to the rest of the change, and they are written before those files exist.

**IMPORTANT:** The Features section is the contract between the proposal and the spec-writing phase.
Research existing specs in `dev/specs/` before filling it in.
It stays that contract for the whole change: `uv run dev/scripts/sync_specs.py <change-name>` reports every spec file the change touched that the section does not declare, and every entry it declares whose spec was never written.

Keep it concise.
Focus on the "why", not the "how" — implementation details belong in `design.md`.
