---
name: dev-archive-change
description: |
  Archive a completed change in the workflow.
  Use when the user wants to finalize and archive a change after implementation is complete.
---

Finalize and archive a completed DevSkills change by moving its directory into `dev/changes/archive/`.

Specifications remain in `dev/specs/` and are not touched during archiving.
Spec conflicts between branches are resolved by Git at merge time.

**Input:** An optional change name. If omitted, infer from context or prompt the user.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Execution Steps

1. **Select the Target Change.**
   - Use the provided change name if available.
   - Otherwise list active changes with `uv run dev/scripts/list_changes.py` (it excludes `archive/`) and ask the user to choose.
   - **CRITICAL:** Do not auto-select or guess, even when only one change is active — archiving moves the directory, and undoing a wrong guess is disruptive.
   - Always output: "Using change: {name}".

2. **Verify Task Completion.**
   - Run `uv run dev/scripts/status.py "{name}"` and read its `tasks.md:` line: it carries the tally as `done (X/Y tasks complete)`. Do not count the checkboxes by hand -- the script knows which list markers and which fenced blocks count, and a second tally would disagree with `dev-status` on the same file.
   - If the tally is short of its total, warn with both numbers and ask the user to confirm; halt if declined.
   - If the line reports no tasks file, or a file that lists no tasks, proceed without warning.

3. **Read the Base.**
   - Run `uv run dev/scripts/change_base.py "{name}"`. It prints the base -- the commit the change started from -- and `{base}..HEAD` is everything the change did.
   - That window is the same on a branch and on the main branch, because the base is anchored to the change itself rather than to wherever it is being merged.
   - If the script reports that the change has no base commit yet, nothing of it is committed, so there is no window to compose the entries from: report that, say that `dev/changes/{name}/` has to be committed first, and stop. Nothing has been moved or written at this point, and nothing must be.

4. **Compose the Entries.**
   - Derive them from what the change actually produced, not from what it intended:
     - `git diff {base}..HEAD -- dev/specs/` -- the changes in system behavior, which come first among the entries.
     - `git log --oneline {base}..HEAD` and `git diff --stat {base}..HEAD` -- what was actually done.
     - `dev/changes/{name}/tasks.md` -- the completed tasks in human wording, read where the change still lives.
   - List everything significant the change did, the way a reader of the project's releases needs to hear it: a feature added, behavior that changed, an option removed, a defect fixed. One change usually produces several such entries, and only a change with a single effect produces one.
   - An entry is a CHANGELOG-style record of what the change gave the product, not a retelling of `proposal.md`: the artifacts already sit in the repository next to the code, and the entries answer what a reader of `git log` cannot see from one commit's diff.
   - Put each entry in its own Keep a Changelog category: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed` or `Security`. Several entries may share a category, and a category nothing falls into is simply not used.
   - Word each entry as one sentence, in the commit-message language of the `Commit style` section of the project root `AGENTS.md`, and keep the wording from here on: these entries go into `CHANGELOG.md` and into the body of the archive commit alike, so the changelog and the history say the same thing.
   - Keep double quotes, apostrophes, dollar signs and backslashes out of the wording, because the same sentence must survive as a quoted command argument in both bash and PowerShell; backticks around names are fine, since step 7 passes the entry in single quotes.

5. **Archive.**
   - Run `uv run dev/scripts/archive_change.py "{name}"`.
   - The script moves the directory to `dev/changes/archive/<archived-date>-{name}/`, where `<archived-date>` is today's date (the date of archiving, not of change creation).
   - If the script reports the target already exists, surface the error and ask how to proceed.

6. **Display Summary.**
   - Output the change name and the archive location.

7. **Record the Entries in the CHANGELOG.**
   - Run `uv run dev/scripts/changelog.py "{category}" '{entry}'` once per entry composed in step 4, with its wording unchanged.
   - Keep the entry in single quotes: in double quotes PowerShell reads a backtick as an escape character and bash runs the backticked name as a command, so the entry would reach the script damaged.
   - The script inserts each entry under `## [Unreleased]` of the project's `CHANGELOG.md`, creating that section or a category when either is missing.
   - If it reports that the project has no `CHANGELOG.md`, go on to the commit: a project without one is not missing anything, and the entries still become the commit body.

8. **Offer to Commit.**
   - Offer the user to review the work and commit it: generate the command with the `dev-commit` skill, following its workflow, and tell it which files this step produced -- both sides of the move, the new `dev/changes/archive/{archived-date}-{name}/`, the `dev/changes/{name}/` it left behind, and `CHANGELOG.md` when the previous step wrote into it.
   - Tell it explicitly that this commit needs a body; this is the only caller that asks for one.
   - Hand it the entries of step 4 under their categories, whether or not the project keeps a `CHANGELOG.md`.

## Guardrails & Constraints

- Never auto-select, even with a single active change — this is the one skill that always asks.
- Warn (do not hard-block) on incomplete tasks; let the user decide.
- Never move the directory before the base is read and the entries are composed: a change without a base commit stops archiving with nothing moved and nothing written.
- Compose the entries once and keep their wording: `CHANGELOG.md` and the commit body carry the same entries, and the body exists even where `CHANGELOG.md` does not.
- Preserve `.devskills.yaml` during the move (the script moves the whole directory).
- Never modify `dev/specs/` during archiving — specs are already current.
- Never edit `CHANGELOG.md` by hand — the entry goes in through `dev/scripts/changelog.py`, which owns the structure of the file.
- Never create a `CHANGELOG.md` for a project that has none, and never ask whether to.

## Expected Output Formatting

```md
## Archive Complete

**Change:** {change-name}
**Archived to:** dev/changes/archive/{archived-date}-{change-name}/
**CHANGELOG:** {N} entries — {category}: {entry}; {category}: {entry} <!-- or: no CHANGELOG.md in this project -->

{the commit proposal from the `dev-commit` skill, with the change's entries as its body}

All tasks complete.
```

When the change has no base commit, output none of this: say that the change has no base commit yet, that nothing was moved or written, and that `dev/changes/{change-name}/` has to be committed before it can be archived.
