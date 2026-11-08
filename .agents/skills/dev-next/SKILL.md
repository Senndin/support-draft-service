---
name: dev-next
description: |
  Run the next step of the change workflow for an active DevSkills change.
  Use when the user wants to move a change forward without naming the skill that does it.
---

Take the change workflow one step further: read where a change stands, and hand the work to the skill that performs its next step.
This skill dispatches and nothing else -- it writes no artifact, edits no file and proposes no commit of its own.
The one thing it may run first is a commit `dev-commit` already proposed and the user has not answered: moving on is the user's agreement to it, when `commit.auto_on_next` is on.

**Input:** An optional change name. If omitted, use the most recently modified active change.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Invocation

This skill runs in two ways, and the dispatch below is identical in both.
Only the origin of the change name differs:

- **Directly.** The user asks to continue, with or without naming a change.
- **From `dev-status`.** The caller has already shown the report and the user agreed to go on. Take the change name it supplies as given.

## Execution Steps

1. **Commit the Pending Proposal.**
   - Run `uv run dev/scripts/config.py commit`. With `commit.auto_on_next: false`, skip this step entirely and commit nothing.
   - The pending proposal is the **last** `Ready to Commit` block `dev-commit` showed in this session, provided no later turn ran it or declined it. Nothing else is one: not a command the user typed, not an older block, not uncommitted work without a block. With none, skip this step -- in a new session, or once the context has lost the block, there is none.
   - Invoking this skill while that block waits is the user's agreement to it, as `Commit on next` in `dev/AGENTS.md` states; a block the user declined stays declined.
   - Run `git status --porcelain -uall`. With nothing uncommitted, skip this step.
   - Do **not** run the proposal, but say why and go on to step 2, when:
     - it carries a warning about a file that looks like a secret, which the user has not answered;
     - its files no longer match the tree. For `git add -A`, compare the uncommitted files with its `**Files:**` header; for pathspecs, compare `git status --porcelain -uall -- <pathspecs>` with the header. Any difference in count or path -- a new file, a vanished one, an edit `git add -A` would sweep in -- makes it stale; a header collapsed by directory compares by count and by the directories it names.
   - Otherwise run the command exactly as shown, whichever change it belongs to: the commit does not depend on the change this skill goes on to.
   - If the commit fails -- a hook rejects it, git reports an error -- show the error and **stop**: no dispatch, no retry, no edit to the command.

2. **Resolve the Target Change.**
   - With a change name, run `uv run dev/scripts/status.py "{name}"`.
   - Without one, run `uv run dev/scripts/status.py` and take the **first** block of the report: the script lists active changes most recently modified first, so the first block is the change to continue.
   - `No active changes under dev/changes/.` -- say plainly that there are no active changes, suggest `dev-new-change`, and stop.
   - Exit code 1 (`Error: change '{name}' not found ...`) -- say plainly that the argument matches no active change, then run `uv run dev/scripts/status.py` without an argument to show what is active, and stop.
   - Never call `dev/scripts/list_changes.py` here, and never work the state out by hand -- the report is the whole input.
   - Always output: "Using change: {name}".

3. **Map the Next Step to a Skill.**
   - Read the `Next:` line of that change's block and resolve it here. This table is the only place the mapping lives:

     | `Next:` | Skill | Invoked with |
     |---|---|---|
     | `proposal.md`, `specs`, `design.md`, `tasks.md` | `dev-plan-change` | the change name |
     | `implement remaining tasks` | `dev-apply-change` | the change name |
     | `acceptance.md` | `dev-accept-change` | the change name |
     | `verify-report.md` | `dev-verify-change` | the change name |
     | `archive` | `dev-archive-change` | **nothing -- see step 4** |

   - A `Next:` value that is not in the table: say so, show the report, and stop. Never guess a skill.

4. **Hand the Work Over.**
   - Invoke the skill the table names, following its workflow, and let it run to its own end -- it shows its own output and offers its own commit.
   - **Archiving is the exception:** invoke `dev-archive-change` **without** a change name, so that it lists the active changes and asks the user itself. That skill never auto-selects, and this one does not take that decision away from it; name the change in your own output so the user knows which one to pick.

## Guardrails & Constraints

- Never do the work of the step yourself: create no artifact, edit no file, run no test, propose no commit of your own. The dispatched skill owns all of that.
- Never compose a commit message or a command, and never run anything but the pending proposal of step 1, exactly as `dev-commit` showed it.
- A stop at the end of a `group` phase or of a `change` session of `dev-apply-change` is a review point the user leaves on purpose: invoking this skill commits that session's work and dispatches the next session, and nothing short of that invocation does.
- Never pass a change name to `dev-archive-change` -- its "always ask" guardrail stands, whether this skill got a name or resolved one on its own.
- Announce the resolved change before dispatching, so an implicit choice is always visible to the user.
- Never invoke `dev-links` yourself; this skill is on its excluded list. Do not suppress it in the skill you dispatch either -- that skill applies the `Reference links` rule of `dev/AGENTS.md` as if the user had invoked it directly.
- Never invoke more than one skill per run: one step per invocation, then stop.
- Never continue an archived change and never scaffold a new one -- an empty workflow ends in a suggestion, not an action.

## Expected Output Formatting

```md
{Committed: `{the commit command}` -> {short hash} {subject} | Commit skipped: {why} | Commit failed: `{the commit command}` -- only when step 1 found a pending proposal}

Using change: {change-name}
Next step: {the step the report names} -- running the `{skill}` skill.

{the output of the dispatched skill}
```

Without a pending proposal, or with `commit.auto_on_next` off, the first line is left out and nothing is said about commits.
When the commit fails, the first line is `Commit failed:`, the git error follows it in place of everything else, and the skill stops.

When the next step is archiving, say which change is ready and that `dev-archive-change` will ask for it by name.
