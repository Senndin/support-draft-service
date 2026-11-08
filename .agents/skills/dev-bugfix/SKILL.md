---
name: dev-bugfix
description: |
  Investigate a bug or a failing test down to its root cause before any fix is proposed.
  Use when a script crashes, a test fails, or behavior is unexpected; also invoked by change-workflow skills when implementation, acceptance or verification hits an unexpected failure.
---

Investigate a defect until its root cause is named, then fix that cause.

**No fix is proposed before its root cause is named.**
A fix that silences the symptom is a failed run, not a shortcut -- it hides the defect and leaves the next one harder to find.

This skill owns the investigation, not the workflow.
A fix that changes what the system promises is a change, and it goes to `dev-new-change` instead of being applied: on a direct run this skill routes it there, and inside a change workflow it names it for the caller to route.

**Input:** A description of the bug -- an error message, a failing test, or the behavior observed. If omitted, ask for it.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Invocation

This skill runs in two ways, and the investigation below is identical in both.
Only the test scope and the hand that applies the fix differ:

- **Directly.** The user describes a bug. The scope is whatever code the investigation reaches, this skill writes the reproducing test and the fix, the tests widen to the full suite once the fix holds, and the fix is offered for commit with `dev-commit`.
- **From a change-workflow skill.** `dev-apply-change`, `dev-accept-change` or `dev-verify-change` hands over the failure and the change it is working on. Do not select a change again. Only diagnose, as **Caller Mode** describes: stop at the narrow test target, leave the working tree as you found it, and return the diagnosis -- the caller decides what happens to it, and owns its report, its full suite run and its commit.

## Caller Mode

Invoked from a change-workflow skill, this skill names the cause and the cure and applies neither.
The caller is in the middle of its own step, and it decides what happens to the diagnosis.

- **Remember the starting state.** Run `git status --porcelain -uall` before the first edit, so that there is a state to return to.
- **Revert every probe.** An edit made to test a hypothesis is evidence, not a fix: undo it as soon as it has proved or disproved the hypothesis.
- **Name the test and the fix, write neither.** The diagnosis describes the reproducing test ahead of the change to the code, each with its file and line anchor.
- **Name the specification impact, act on none.** Edit no specification and invoke no `dev-new-change`.
- **Check before returning.** Run `git status --porcelain -uall` again: it must list exactly what it listed at the start, and a file that was already modified then must hold no edit of yours.

The diagnosis is one block under four headings, and every caller reads only those:

```md
## Diagnosis: {short symptom}

### Root cause
{what is broken and why} -- `path/to/file.py:42`

### Reproducing test
{the test to write first: where it goes, what it sets up and asserts, and the failure it must show before the fix} -- `path/to/test_file.py:17`

### Fix
{the single change that addresses the cause} -- `path/to/file.py:42`

### Specification impact
{exactly one of: `code-only` | `declared: dev/specs/{domain}/spec.md` | `outside scope: dev/specs/{domain}/spec.md`}
{for the last two: the requirement or scenario that would have to be re-worded, deleted or added}
```

The three values are the three outcomes of **Specification Impact**, in the same order; a specification that does not exist yet is named by the path it would get.

## Execution Steps

1. **Establish the Symptom.**
   - When invoked from a change-workflow skill, take the failure it hands over and skip the gathering below.
   - Otherwise collect the exact error text, the stack trace, the command that produced it, and the name of the failing test.
   - Read the error in full; the line numbers, file paths and error codes it carries are evidence, not noise.
   - Always output: "Investigating: {symptom}".

2. **Reproduce It.**
   - Find the narrowest command that shows the failure, and run the tests with the `dev-test` skill. From a change-workflow skill, say when calling it that the run stops at this narrow target, because the full suite is run by the caller or by the direct run that later applies the fix.
   - Establish whether it fails every time or intermittently; `dev-test` owns the flaky-retry judgement.
   - If it cannot be reproduced, collect more evidence -- never guess at a cause you cannot trigger.

3. **Collect Evidence.**
   - Check what changed recently: `git log` and `git diff` over the code the trace touches, the configuration, and the external systems it depends on.
   - When the failure crosses component boundaries, record what enters and what leaves each one in a single run, then read that evidence to locate the broken component before investigating it.
   - Trace a bad value upstream until you reach where it was produced, and treat that place as the defect -- not where it was finally noticed.

4. **Compare Against What Works.**
   - Find a working analogue in the same project: a sibling module, an adjacent endpoint, a passing test over the same code path.
   - Read any reference implementation in full before assuming the broken code follows it.
   - List every difference between the working and the broken case, however small; do not dismiss one as irrelevant before it is ruled out.

5. **State One Hypothesis.**
   - Write it out concretely: "{X} is the root cause because {Y}".
   - Test it with the smallest change that can prove or disprove it, one variable at a time.
   - If it is not confirmed, state a new hypothesis; never stack a second fix on top of an unconfirmed first.
   - Say plainly what you do not understand rather than proceeding on a guess.

6. **Assess the Specification Impact.**
   - Before writing the fix, decide which of the three outcomes in **Specification Impact** applies.
   - Directly, two of them end the run there; only a code-only defect continues to the next step.
   - From a change-workflow skill, record the outcome and act on none of them; whichever it is, go on to step 7, which in that mode only describes the fix.

7. **Fix the Root Cause.**
   - From a change-workflow skill, write nothing: work out the smallest test that reproduces the bug and the one fix that addresses the cause established in step 5, describe both for the diagnosis, and skip the rest of this step.
   - Write the smallest test that reproduces the bug and run it with the `dev-test` skill, confirming it fails for the right reason before any implementation code.
   - Apply one fix, addressing the cause established in step 5. No "while I am here" improvements and no unrelated refactoring.
   - Clean up with the `dev-refactor` skill when the fix left a smell, and document with the `dev-docs` skill when it moved a public surface.
   - Re-run the tests the bug and its fix touch, and follow `dev-test` through to the full suite once that target is green -- nothing else will run it on this path.

8. **Report the Outcome.**
   - Directly, output the report, then offer the user to review the work and commit it: generate the command with the `dev-commit` skill, following its workflow, and tell it which files this fix produced -- the code, the test that reproduces the bug, and any documentation it moved.
   - From a change-workflow skill, confirm that the working tree is as you found it, then hand back the diagnosis block of **Caller Mode** and nothing else: no file, no commit proposal and no other skill of the change workflow.

## Specification Impact

A fix either restores behavior the specifications already describe, or it changes what they describe.
The test that separates the two: if a written scenario would have to be re-worded, deleted, or added for the fixed behavior to be correct, the fix changes a specification.

- **Code-only defect.** The implementation contradicts a specification that is already right. Fix the code and continue; no artifact changes.
- **A specification the active change already declares.** The fix requires editing a specification the change's Features section links to. Edit `dev/specs/{domain}/spec.md` directly, sync the Features section as `Features sync` in `dev/AGENTS.md` describes, then continue -- that change already owns this specification.
- **A specification outside any declared scope, or a new one.** Do NOT edit `dev/specs/`. Propose a new change instead: invoke the `dev-new-change` skill, following its workflow, giving it a kebab-case name derived from the bug and telling it that the initial description is this skill's analysis, which it saves verbatim to `notes.md`. Then stop -- the fix proceeds through the change workflow, where it gets a proposal, a specification and tasks like any other.

Check the declaration against the proposal's Features section, following each bullet's link target rather than rebuilding the path from the feature name; `dev/AGENTS.md` maps that role to the heading the project's templates use.
When no change is active, every specification is outside the declared scope.

The actions above belong to a direct run.
From a change-workflow skill, only name the outcome -- `code-only`, `declared: <spec path>` or `outside scope: <spec path>` -- and leave the action to the caller.

## When the Fix Does Not Hold

Count the fixes attempted for this bug.

- Fewer than three: return to step 3 and re-read the evidence with what the failed attempt just taught you.
- Three or more: stop, and question the architecture with the user before attempting a fourth.

The signals that the design, and not the code, is the problem: every fix surfaces a new problem elsewhere, or the fix only works alongside a large refactoring.
Raise that with the user as a question about the pattern, never as another patch.

## Red Flags

Each of these thoughts means the investigation was skipped; return to step 1.

| Rationalization | Reality |
|---|---|
| "The problem is simple, the process is overkill." | Simple problems have root causes too, and the process is short for them. |
| "There is no time for an investigation." | Guessing costs more than investigating; every wrong fix still has to be found and undone. |
| "I will try something and see what happens." | A change made to see what happens is evidence only when you decided in advance what it would prove. |
| "I can see the problem, I will just fix it." | Seeing the symptom is not understanding the cause. |
| "One more attempt." (after two) | Three failed fixes is a design problem; the fourth fails the same way. |

## Examples

For a worked example of collecting evidence across component boundaries, read `references/python-django.md`.
It describes one specific project and is illustrative only; never carry its format, language, or layout into a project that does not match it.

## Guardrails & Constraints

- Never propose a fix before a root cause is named; a fix to the symptom is a failed run.
- Never stack a second fix on an unconfirmed first; revert it and state a new hypothesis.
- Change one thing at a time, and keep the fix to the cause -- no adjacent cleanups, no unrelated refactoring.
- Write the test that reproduces the bug before the fix, and confirm it fails for the right reason. From a change-workflow skill, name that test ahead of the fix instead, and write neither.
- Never change a test's assertions to make it pass; if the expected value is wrong, that is a specification question, not a test edit.
- Never leave a direct run without the full suite, and never spend one inside a change-workflow caller that runs it anyway.
- Never edit a file under `dev/specs/` unless the active change's Features section already declares it.
- Never scaffold a change silently; `dev-new-change` asks the user, and this skill hands it the analysis rather than writing `notes.md` itself.
- Never write a file, edit a specification, invoke `dev-new-change` or propose a commit when invoked from a change-workflow skill -- there the caller decides what happens to the diagnosis, and owns the report and the commit.
- Never return to a caller with a probe still in the working tree: revert every edit made to test a hypothesis, and check with `git status --porcelain -uall` against the state the investigation started from.
- Stop after three failed fixes and question the architecture with the user.

## Expected Output Formatting

```md
## Bug Investigation: {short symptom}

**Symptom:** {the failure, verbatim from the error or the failing test}
**Reproduced:** {the command, and whether it fails every time}

### Root Cause
{what is broken and why} -- `path/to/file.py:42`

### Evidence
- {observation} -> {what it rules in or out}

### Fix
{the single change that addresses the cause}
**Test:** {the test that reproduces the bug, written first, and its result after the fix}
**Tests re-run:** {the narrow target the bug and the fix touch, and the full suite in direct mode -- outcomes from the `dev-test` skill}

### Specification Impact
{None -- code-only defect. | Edits `dev/specs/{domain}/spec.md`, already declared by change {name}. | Changes or adds `dev/specs/{domain}/spec.md` -- this needs its own change.}

{the commit proposal from the `dev-commit` skill}
```

When the impact routes the fix to a new change, the `### Fix` section states the fix that was **not** applied and why, and it is followed by the proposed change name and the note that this report becomes its `notes.md`.
When invoked from a change-workflow skill, output the diagnosis block of **Caller Mode** instead of this report -- it goes back to the caller, which decides what happens to it.
