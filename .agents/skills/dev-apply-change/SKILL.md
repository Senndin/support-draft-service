---
name: dev-apply-change
description: |
  Implement tasks from a DevSkills change.
  Use when the user wants to start implementing, continue implementation, or work through tasks.
---

Implement the tasks defined in a DevSkills change, progressing iteratively until completion or a blocker.

**Input:** An optional change name, and an optional review mode -- `task`, `group` or `change` -- that applies to this invocation only. If the name is omitted, infer it from context or prompt the user.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Review Modes

- **`task`** -- stop for the user's review, with a commit proposal, after every task.
- **`group`** -- work through the current phase, the `## N.` group of `tasks.md` holding the first pending task, without stopping between its tasks. Stop once the phase is complete or the autonomy budget `apply.time_limit` is spent, and propose one commit for the whole session.
- **`change`** -- work through every pending task of `tasks.md`, group by group, without stopping between tasks or between groups. Stop once no task is pending or the budget is spent -- checked only after a group is complete, so a group already started is always finished -- and propose one commit for the whole session.

## Execution Steps

1. **Select the Target Change.**
   - Select it as `Target change` in `dev/AGENTS.md` describes.

2. **Load Context.**
   - Read `dev/changes/{name}/proposal.md`, `design.md` (if present), and `tasks.md`.
   - Read the specifications the proposal's Features section links to, following each bullet's link target rather than rebuilding the path from the feature name; `dev/AGENTS.md` maps that role to the heading the project's templates use.
   - Read the project's code style guide, linked from the project root `AGENTS.md`. You MUST read it before applying any changes, and adhere to it strictly.
   - Run `uv run dev/scripts/config.py apply` for the review mode and the budget, resolved as `Review modes` in `dev/AGENTS.md` describes. Relay any warning the script prints on stderr to the user.
   - Always output: "Review mode: {task|group|change}", followed in `group` and `change` mode by "Autonomy budget: {limit} min".
   - Run `uv run dev/scripts/auto_commit.py` and relay its warning, if any, the same way. Its `auto_commit:` line is the automatic commit mode for the whole session; never read `commit.auto_on_apply` yourself. Output "Automatic commits: {off|task|group}".
   - When that mode is not `off`, record `git status --porcelain -uall` now, before the first task: **Automatic Commits** below scopes every commit against it.

3. **Display Progress Overview.**
   - Output the task progress ("N/M tasks complete") and a brief overview of the pending tasks.
   - In `group` mode, also name the current phase -- the `## N.` group holding the first pending task -- and its pending tasks. Those tasks are the whole scope of this session.
   - In `change` mode, name the groups that still hold pending tasks, in order. Every pending task is in the scope of this session.

4. **Iterative Task Implementation.**
   - In `group` and `change` mode, before the first task, run `uv run dev/scripts/apply_session.py start {name}`. It stamps `apply_started` into `dev/changes/{name}/.devskills.yaml`, replacing the stamp of any earlier session, so every invocation gets a fresh budget.
   - Loop through each pending task in `tasks.md` -- in `group` mode, only the pending tasks of the current phase; in `change` mode, all of them, group by group:
     - Output the active task description.
     - Implement it through the cycle described in **Implementation** below.
     - Mark the task complete in `tasks.md` (`- [ ]` -> `- [x]`).
     - When the task, or the group it completes, is a unit of work the session commits on its own, commit it in the order **Automatic Commits** below fixes, before the budget check.
     - In `task` mode:
       - Unless an automatic commit just recorded this task, or the session commits by group and the group is not complete yet, offer the user to review the work and commit it: generate the command with the `dev-commit` skill, following its workflow, and tell it which files this task produced -- its code, its tests, its documentation and its `tasks.md` checkbox.
       - Stop and request user review before starting the next task.
     - In `group` mode:
       - Run `uv run dev/scripts/apply_session.py check {name}` and output the time it reports.
       - If the phase has a pending task left and the script printed `expired: no`, go straight on to that task: no review request and no commit proposal.
       - Otherwise stop as described in **Stopping a Session** below.
     - In `change` mode:
       - If the task's group still has a pending task, go straight on to it: no budget check, no review request and no commit proposal.
       - Once the group is complete, run `uv run dev/scripts/apply_session.py check {name}` and output the time it reports.
       - If another group has a pending task and the script printed `expired: no`, go straight on to its first pending task.
       - Otherwise stop as described in **Stopping a Session** below.
   - Once every task in a `## N. DB Migrations` group is complete, consolidate that group's migrations as described in **Database Migrations** below. This happens before the automatic commit, the budget check and any stop.
   - Pause immediately and request guidance if a task is unclear, an implementation reveals a design issue (suggesting an artifact update), a blocker/error occurs, or the user interrupts. This holds in every mode: a problem never waits for the phase, the group or the budget to end.
     - When the pause is caused by a failing test or an unexpected error rather than an unclear task, offer the `dev-bugfix` skill as the next step and let the user decide. Tell it the change this session is working on, and act on the diagnosis it returns as **Applying a Diagnosis** below describes.

5. **Finalize Status.**
   - On completion or pause, summarize tasks completed this session, overall progress, and next steps: explain the pause, or, once every task is done, name the acceptance step that comes next and offer the `dev-next` skill to run it.
   - Never read, write or run `acceptance.md`: the acceptance step belongs to `dev-accept-change`, so name the step without saying anything about its scenarios.
   - Offer the user to review the work and commit it: generate the command with the `dev-commit` skill, following its workflow, and tell it which files this session left uncommitted. In `group` and `change` mode this is the single commit proposal of the session; **Stopping a Session** lists what it covers.
   - Work an automatic commit already recorded is not proposed again, so with automatic commits on, the proposal holds only what a spent budget or a pause left uncommitted; with nothing of the session left, propose nothing.

## Stopping a Session

A `group` or `change` session stops at the first of two events:

1. **The scope is complete** -- in `group` mode, no pending task is left in the current `## N.` group; in `change` mode, none is left in `tasks.md`.
2. **The budget is spent** -- `apply_session.py check` printed `expired: yes`.

In `group` mode both are checked only after a task is complete: a task already started is always finished, however long it takes, and a spent budget only forbids starting the next one.
In `change` mode both are checked only after a group is complete: a group already started is always finished, and a spent budget only forbids starting the next group.

When stopping:

- Consolidate the migrations first if the last group the session worked on is a completed `## N. DB Migrations` group.
- Finalize the status as in step 5. Its commit proposal is the only one of the session, and it names every file the session produced: the code, tests and documentation of all its tasks, their `tasks.md` checkboxes, any migration files, and `dev/changes/{name}/.devskills.yaml`, which now carries `apply_started`.
- Never start anything further without the user's request: not the next phase or the rest of an unfinished one in `group` mode, not the next group in `change` mode. The next invocation starts a new session, with a fresh budget, on the group holding the first pending task.

## Automatic Commits

The mode `auto_commit.py` reported decides when the session commits without asking, as `Commit on apply` in `dev/AGENTS.md` states, and never when it stops.

**The end of a unit of work.** After a task is checked off, keep this order, so that everything a commit should carry exists before it runs:

1. If the task completes its group and that is a `## N. DB Migrations` group, consolidate the migrations.
2. If this is the end of a unit the session commits -- the task with `task`, the completed group with `group` -- resolve the scope and commit it.
3. Only then run the budget check, where the review mode runs one, and stop or go on as that mode says.

**The scope.** Resolve it here; `dev-commit` stages exactly what it is given.

- A file the session produced for this task or group is in scope, and so is `dev/changes/{name}/.devskills.yaml` while it has uncommitted edits.
- When the group's earlier tasks ran in an earlier invocation, compare each remaining uncommitted file through `git diff` with the group's checked tasks in `tasks.md`: a file that belongs to them is in scope, a file plainly unrelated to them stays out.
- A file the session edited that already held edits in the snapshot taken in `Load Context`, or a file you can tell neither way, is a mixed file: commit nothing, name it and stop as below.
- A task that is not complete is never in scope.

**The commit.** Invoke the `dev-commit` skill under `commit.auto_on_apply`, following its workflow, with the files of the scope.
It owns the message, the staging and the secret and mixed-file checks, and either commits and reports ``Committed: ...``, or returns what stopped it.
An automatic commit replaces the commit proposal of the work it records.

**The repair loop.** When `dev-commit` returns an error whose output clearly attributes the failure to a linter or a formatter:

1. Fix the failure in files of the scope only; never touch the configuration of the linter or the formatter.
2. Run the tests of the task or group again with the `dev-test` skill.
3. Repeat the command `dev-commit` showed, unchanged: it stages the same pathspecs again, which picks up what a formatter rewrote.

Repeat at most twice.
Stop as below on any other failed commit, on a fix that needs a file outside the scope, on tests that fail after the fix, and on a commit still rejected after the second repeat.

**A stop on a commit.** A secret-looking file, a mixed file and a commit that cannot be repaired each stop the session at once, whatever the review mode and the budget say.
Show the file or the last error, say that the task is complete but uncommitted, and name what to do next: resolve it, then commit through `dev-commit` directly.
Propose no commit: a `Ready to Commit` block would repeat the failure, and `dev-next` could run it.

## Implementation

**The cycle below is mandatory for every task, except tasks in a `## N. DB Migrations` or a `## N. Functional Tests` group.**
Follow RED -> GREEN -> REFACTOR -> DOCUMENT strictly.
Tasks of those two groups follow **Database Migrations** and **Functional Tests** below instead.

**RED phase (tests first):**

- Write or update the test(s) that encode the acceptance criteria for this specific task.
- Cover the happy path AND at least one edge or error case, where applicable.
- Run them with the `dev-test` skill and confirm they **fail for the right reason** before writing any implementation code.
- If they pass before any implementation exists, pause and ask the user -- either the task is already done, or the tests are wrong.
- If they fail for the wrong reason, or a test that used to pass breaks, that is a defect to investigate rather than an obstacle to code around: stop and offer the `dev-bugfix` skill.

**GREEN phase (minimal implementation):**

- Write the minimum code needed to make the failing tests pass.
- Do not add behavior that no test covers.
- Re-run the tests and confirm **all new tests pass**.

**REFACTOR phase (clean up):**

- Clean up the code this task produced using the `dev-refactor` skill: name the smells it left behind and apply the matching techniques.
- Improve readability, remove duplication, and apply the project's conventions -- without changing external behavior.
- If a technique changes the surface the tests bind to (a rename, a move, a changed signature), update the tests first and watch them fail structurally, then apply it -- `dev-refactor` describes that cycle.
- Re-run only this task's tests and confirm they **still pass**, with their assertions and expected values unchanged. If an assertion had to change, the behavior changed -- revert and reconsider.

**DOCUMENT phase (docs with the code):**

- Document the code this task produced using the `dev-docs` skill, applying it automatically -- documentation is part of the task, not a follow-up.
- Cover the public surface the task added or modified, and refresh any module overview, docstring, or README the task made wrong.
- Report what was documented, or state that nothing needed documenting and why.
- Do not re-run the tests unless the documentation touched executable content (for example, doctests).

## Applying a Diagnosis

Applying the fix that the diagnosis returned by `dev-bugfix` names is this skill's work, and it starts only after the user accepts it.

1. Show the diagnosis and ask the user whether to apply the fix. Write nothing before an explicit yes.
2. Read its **Specification impact**. It is exactly one of three values, and it decides the path:
   - `code-only` -- the fix touches no specification. Go to step 3.
   - `declared: <spec path>` -- the fix changes a specification the change's Features section declares. Edit that file in `dev/specs/` directly, sync the Features section as `Features sync` in `dev/AGENTS.md` describes, then go to step 3.
   - `outside scope: <spec path>` -- the fix changes a specification the change does not declare, or adds one. Do NOT edit `dev/specs/` and do not apply the fix: stop, and offer the `dev-new-change` skill with a kebab-case name derived from the bug and the diagnosis as its initial description, which it saves verbatim to `notes.md`.
3. Apply the fix as RED and GREEN of the current task:
   - **RED:** write the reproducing test the diagnosis names, run it with the `dev-test` skill and confirm it **fails for the right reason** -- the root cause the diagnosis names.
   - **GREEN:** only then write the fix, re-run the test and confirm it passes together with the task's other tests.
4. Take the task up where it paused, and let its REFACTOR and DOCUMENT phases cover the fix too.

If the reproducing test passes before the fix, or still fails after it, the diagnosis does not hold: pause again and offer `dev-bugfix` with what the attempt showed, never a second fix on top of the first.

## Database Migrations

Task group category names stay in English in every project (see `dev/AGENTS.md`), so `## N. DB Migrations` matches literally regardless of the artifact language.

Once every task in such a group is complete, consolidate the SQL statements it produced into two files in the change directory:

1. `dev/changes/{name}/db-migration.up.sql` -- the forward migration.
2. `dev/changes/{name}/db-migration.down.sql` -- the rollback migration.

Do not create these files until every DB migration task in the group is done.

Write them with the `dev-migrate-db` skill, which owns their layout and the ordering rules for a change with several DB Migrations groups.

## Functional Tests

`## N. Functional Tests` matches literally, just as `## N. DB Migrations` does.

A task of such a group writes the end-to-end tests of the scenarios it names.
The cycle does not apply to it: the behavior those tests exercise was built by the groups before it, so there is no failing test to see first and no production code to clean up or document.

1. Write the end-to-end test(s) of the scenarios the task names, asserting what each scenario states.
2. Run them with the `dev-test` skill.
3. Mark the task complete only when they pass.

When a functional test fails, tell where the failure lies before changing anything:

- **In the test itself** -- its setup, its data, or the way it drives the system. Fix the test within the task and run it again; the fixed test still asserts what the scenario states.
- **In the code already built.** That is a defect in work the change already delivered: pause as step 4 describes, with the `dev-bugfix` skill as the first option, and never change the test's assertions to make it pass.
- **The cause cannot be told.** Pause and ask the user; change neither the test nor the code.

## Guardrails & Constraints

- Iterate systematically until complete or blocked.
- Always read the context files before implementing.
- Never write implementation code before a test for it fails.
- Never mark a task complete before its code is documented with the `dev-docs` skill.
- Tasks in a `## N. DB Migrations` or a `## N. Functional Tests` group are the only exceptions to those two rules -- the migration scripts carry no tests and no comments, and a functional test exercises code the earlier groups already built and documented.
- Never change the assertions of a functional test to make it pass: fix the test only when the failure lies in its setup, its data or the way it drives the system, and offer the `dev-bugfix` skill when it lies in the code.
- Invoke `dev-refactor` and `dev-docs` automatically as part of the cycle; do not ask the user whether to clean up or document.
- Write the migration scripts with the `dev-migrate-db` skill; never hand-roll them inline.
- Never patch a failing test into passing without a root cause; offer the `dev-bugfix` skill and let it name the cause first.
- Never apply the fix `dev-bugfix` returns before the user accepts it and before its reproducing test fails for the right reason.
- Never edit a specification the change does not declare to make a fix fit; stop and offer `dev-new-change` with the diagnosis.
- Never change a test's assertions or expected values to accommodate a refactoring; refactoring MUST preserve behavior. Re-pointing a test at a renamed or moved surface is allowed, and always happens before the production code changes.
- In `task` mode, stop and request user review after each task; never chain into the next task unprompted.
- In `group` mode, chain only the tasks of the current phase, and propose no commit until the stop; never chain into the next phase unprompted.
- In `change` mode, chain every pending task, group by group, and propose no commit until the stop; never start a group after a check printed `expired: yes`, and never leave a started group unfinished because of the budget.
- Only `apply_session.py check` decides whether the budget is spent. Never estimate elapsed time yourself, never skip the check after a task in `group` mode or after a group in `change` mode, and never stop early or run on because the work feels long or short.
- Never edit a linter's or a formatter's configuration to get an automatic commit through, and repeat the command `dev-commit` showed only unchanged.
- Never commit a task that is not complete.
- Keep modifications strictly scoped to the current task.
- Update the task checkbox immediately upon completion.
- Do not assume requirements; pause and clarify ambiguous tasks rather than guessing.
- If a design issue emerges, pause and recommend updating the relevant artifact (or the spec in `dev/specs/`).
- After any edit to a file under `dev/specs/`, sync the Features section as `Features sync` in `dev/AGENTS.md` describes before continuing. A spec the implementation touched but the proposal never declared is scope the change is carrying untracked.

## Expected Output Formatting

**During Implementation (`task` mode):**

```md
## Implementing: {change-name}

Working on task 3/7: {task description}
RED: {test(s) written} -- failing as expected.
GREEN: {implementation} -- tests passing.
REFACTOR: {smell -> technique applied, or "none needed"} -- tests still passing.
DOCS: {what was documented, or "none needed"}.
Task complete.

{the commit proposal from the `dev-commit` skill}

Please review before I start task 4/7.
```

**During Implementation (`group` mode):**

```md
## Implementing: {change-name}, phase {N}. {group title}

Working on task 3/7: {task description}
RED: {test(s) written} -- failing as expected.
GREEN: {implementation} -- tests passing.
REFACTOR: {smell -> technique applied, or "none needed"} -- tests still passing.
DOCS: {what was documented, or "none needed"}.
Task complete. Budget: {elapsed} min used, {remaining} min left.
```

**During Implementation (`change` mode):**

```md
## Implementing: {change-name}, every open group

Working on task 3/7 of {N}. {group title}: {task description}
RED: {test(s) written} -- failing as expected.
GREEN: {implementation} -- tests passing.
REFACTOR: {smell -> technique applied, or "none needed"} -- tests still passing.
DOCS: {what was documented, or "none needed"}.
Task complete.
```

When a `change` session goes on past a completed group:

```md
Group complete: {N}. {group title}. Budget: {elapsed} min used, {remaining} min left.
```

**On Phase Complete (`group` mode):**

```md
## Phase Complete: {N}. {group title}

**Change:** {change-name}
**Progress:** 5/7 tasks complete (phase {N}: 3/3)
**Time:** {elapsed} of {limit} min

{the commit proposal from the `dev-commit` skill}

Please review before I start phase {N+1}.
```

**On Budget Reached (`group` or `change` mode):**

```md
## Autonomy Budget Reached

**Change:** {change-name}
**Progress:** 4/7 tasks complete (phase {N}: 2/3 | groups complete this session: {list})
**Time:** {elapsed} of {limit} min

{the commit proposal from the `dev-commit` skill}

Please review. The next invocation continues {phase {N} | with group {N+1}} with a fresh budget.
```

**On Completion:**

```md
## Implementation Complete

**Change:** {change-name}
**Progress:** 7/7 tasks complete
**Time:** {elapsed} of {limit} min <!-- `group` and `change` mode only -->

{the commit proposal from the `dev-commit` skill}

All tasks complete. Next comes the acceptance step -- want me to take it? The `dev-next` skill runs it for `{change-name}`.
```

When the budget runs out on the task that completes the phase, or on the group that completes the whole change, the phase or completion block applies: the stop is the same either way.

**On Pause (Issue Encountered):**

```md
## Implementation Paused

**Change:** {change-name}
**Progress:** 4/7 tasks complete

### Issue Encountered
{description of the issue}

**Options:**
1. {option 1}
2. {option 2}
3. Other approach

What would you like to do?
```

When the issue is a failing test or an unexpected error, the first option is investigating it with the `dev-bugfix` skill.

**On Automatic Commit Stopped:**

```md
## Automatic Commit Stopped

**Change:** {change-name}
**Progress:** 4/7 tasks complete
**Uncommitted:** {task {N.M} | group {N}. {group title}} -- complete, not committed

{the file and why: looks like a secret | mixes in unrelated edits} | {the last error of the commit}

Resolve it, then commit the work through the `dev-commit` skill directly.
```
