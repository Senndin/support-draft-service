---
name: dev-status
description: |
  Report where every active DevSkills change stands in the workflow.
  Use when the user asks which changes are in flight, how far one has progressed, or what is left to do on it.
---

Report the workflow state of the active DevSkills changes: which artifacts are formed, how many tasks are implemented, how many acceptance scenarios have a result, and whether the verification report is written.
This skill only reads and reports -- it changes nothing and runs no workflow step itself.

**Input:** An optional change name. If omitted, report every active change.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Execution Steps

1. **Read the Workflow State.**
   - With a change name, run `uv run dev/scripts/status.py "{name}"`.
   - Without one, run `uv run dev/scripts/status.py` -- it reports every active change, most recently modified first, and excludes `archive/`.
   - The script is the whole input of this skill.
     It names the artifacts that exist (`proposal.md`, the changed spec files under `dev/specs/`, `design.md`, `tasks.md`, `acceptance.md`, `verify-report.md`), the task completion count, the count of acceptance scenarios with a result, the recorded verification verdict, and the next step of the workflow.
   - Never call `dev/scripts/list_changes.py` here -- the report above already covers what is active.

2. **Handle the Empty and the Unknown Change.**
   - `No active changes under dev/changes/.` -- say plainly that there are no active changes, and stop. Offer no next step and never fall back to the archive.
   - Exit code 1 (`Error: change '{name}' not found ...`) -- say plainly that the argument matches no active change, then run `uv run dev/scripts/status.py` without an argument to show what is active, and stop.

3. **Render the Report.**
   - Report each change by the first thing it still owes.
     While artifacts are outstanding, name the ones already formed; once they are all formed, the task count is the answer; once every task is implemented, the acceptance scenarios are the answer; once every scenario has a result, the verify report is the answer.
   - Take every fact from the script output. Do not open artifacts, run git, or re-derive any of it.
   - Acceptance owes the user's own run of the scenarios, not more implementation.
     `acceptance.md: done (X/Y scenarios with a result)` with X below Y means Y - X scenarios still wait for that run -- say how many; `acceptance.md: -` means the scenarios are not written yet; `acceptance.md: written, with no scenario for a person to run` owes nothing more.
   - `verify-report.md` is saved only with the user's explicit consent, so its absence means the report was not saved -- not necessarily that `dev-verify-change` never ran. The `verification:` line is what answers that: `clean`, `blocked`, or `not run`.
   - A change whose verification reads `blocked` is waiting on the CRITICAL issues that run found, not on another audit for its own sake. Say so rather than only naming the step.

4. **Offer the Next Step.**
   - Offer to run the `dev-next` skill on the change named by the argument, or -- without an argument -- on the first change in the report, which is the most recently modified one.
   - Name the step the report gives, so the offer says what would happen.
     For `acceptance.md`, say that the acceptance scenarios would be written or walked through with the user.
   - Offer only; `dev-next` runs after the user agrees.

## Guardrails & Constraints

- Read-only: never create, edit, move or delete a file, and never stage or commit anything.
- Never work out the next step by hand and never invoke the skill that performs it -- that mapping lives in `dev-next` alone.
- Never invoke `dev-links`: this skill is on its excluded list, because it reports and finishes before there is anything to read.
- Never propose a commit -- this skill produces no files.
- Never name a change the report does not name, and never report on an archived change.

## Expected Output Formatting

```md
## Change Status

{status.py output}

**{change-name}:** {what is formed so far, or the task count, or the acceptance scenarios still waiting for the user's run, or the state of the verify report}.

Next: {the step the report names}.
Want me to take it? The `dev-next` skill runs that step for `{change-name}`.
```

With a change name, the report covers that change alone; without one, every active change appears, and the offer applies to the first -- the most recently modified.
