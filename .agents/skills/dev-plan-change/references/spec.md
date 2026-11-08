# Spec artifact instructions

Write or update specification files that define WHAT the system should do.
Edit `dev/specs/<domain>/spec.md` **directly**; the change is tracked by Git.
Use `dev/templates/spec.md` as the starting scaffold, and follow the specification rules and artifact language in `dev/AGENTS.md`.

## Where to write

For each feature listed in the proposal's Features section:

- **New feature:** create the file the bullet links to.
- **Changed feature:** open the file the bullet links to and edit the affected requirements and scenarios in place.

Take the path from the bullet's link target, not from the feature name — the link is the authority.
A root-relative target (`/dev/specs/<name>/spec.md`) resolves from the repository root, so it stays valid after the change is archived.
Only if a bullet carries no link, fall back to the convention `dev/specs/<name>/spec.md`, and add the link while you are there.

The proposal's own headings for these subsections come from `dev/templates/proposal.md`, in the project's artifact language.

When adding new behavior, add a new requirement block (a third-level heading, as the template shows).
When behavior changes, edit the existing requirement in place and keep its full, current description.
Every requirement keeps at least one scenario at the fourth heading level.
