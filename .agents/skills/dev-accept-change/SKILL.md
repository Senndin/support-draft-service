---
name: dev-accept-change
description: |
  Write the acceptance scenarios of a change from the code that was built, then walk the user through them and record what the user reports.
  Use when every task of a change is done and the parts only a person can confirm still need a run before verification.
---

Own the acceptance step of a change: write `acceptance.md` once the code exists, then present its scenarios to the user one at a time and record the result the user reports for each.

**This skill never runs a scenario.**
A scenario is in `acceptance.md` because the agent cannot observe its outcome, so the user runs every step and the skill records what the user saw -- nothing more.

**Input:** An optional change name. If omitted, infer it from context or prompt the user.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## What the Skill Reads and Hands Over

Every fact about the scenarios comes from the scripts, and every hand-over has a fixed shape:

- **`uv run dev/scripts/status.py "{name}"`** gives the step the change is at and the tally on its `acceptance.md:` line. Never count scenarios yourself.
- **`uv run dev/scripts/acceptance.py "{name}"`** gives one line per scenario in file order, `<result>: <heading>`, where the result is `passed`, `failed`, `skipped` or `pending`. It is the only source of a scenario's result: never read a result out of the file by hand, and never decide that one is recorded until this listing says so.
- **To `dev-bugfix`** go the change name and the failed scenario, as the description of the failure: its heading, its steps, its expected outcome, and what the user observed. It runs in caller mode and returns its diagnosis block under the headings **Root cause**, **Reproducing test**, **Fix** and **Specification impact**.
  Record that block in `acceptance.md` as indented sub-items under the `- [failed]` line, one per heading, keeping every anchor:

  ```md
  - [failed] the summary table is cut off after the third column
    - Root cause: the renderer truncates every row at 80 characters -- `src/report.py:40`
    - Reproducing test: render a five-column table and assert that every column is present -- `tests/test_report.py:12`
    - Fix: wrap the row instead of truncating it -- `src/report.py:40`
    - Specification impact: code-only
  ```

- **To `dev-commit`** go the files this run produced: `dev/changes/{name}/acceptance.md`, plus `dev/changes/{name}/.devskills.yaml` when the run removed the verdict from it, plus `dev/templates/acceptance.md` when the run copied the template there.

## Execution Steps

1. **Select the Target Change.**
   - Select it as `Target change` in `dev/AGENTS.md` describes.
   - Run `uv run dev/scripts/config.py artifacts` for the language and keywords `acceptance.md` is written in.

2. **Read Where the Change Stands.**
   - Run `uv run dev/scripts/status.py "{name}"`.
   - A `Next:` step before acceptance -- `proposal.md`, `specs`, `design.md`, `tasks.md` or `implement remaining tasks` -- means the code a scenario would be taken from does not exist yet. Write nothing, name that step, offer the `dev-next` skill to run it, and stop.
   - `acceptance.md: -` -- go on to step 3 and write the file.
   - Any other `acceptance.md:` line -- the file exists; go straight to the walk in step 6. That holds whatever the `Next:` line says, so a failed scenario can be run again once it has received its fix.

3. **Find the Template.**
   - Use `dev/templates/acceptance.md` when it exists.
   - When it does not -- a project whose artifact language the package does not bundle -- never write the artifact without a template, since the scripts find the scenarios by its headings.
     Offer the English template `dev/locales/en/templates/acceptance.md` instead, and on the user's consent copy it into `dev/templates/acceptance.md` unchanged.
   - When the user declines, or the English template is missing too, write nothing, name the missing template, and stop.

4. **Write `acceptance.md`.**
   - Read `proposal.md`, `design.md` and `tasks.md` for context, and the changed specifications the proposal's Features section links to, following each bullet's link target, for the scenarios to cover.
   - Read the code the change built: run `uv run dev/scripts/change_base.py "{name}"` for its base, then `git diff <base>` and `git status --porcelain -uall` for every file the change touched, committed or not. Take the commands, flags, paths and expected messages of every scenario from that code, never from `design.md` or `tasks.md` alone -- the plan may name a flag the code spells differently.
   - Hold only what needs a person: what an agent shows, how a document or a report reads, how the system behaves in the user's own environment.
     A check the agent can execute and judge itself belongs among the `Functional Tests` of `tasks.md`, so it gets no scenario; when such a check has no test there either, say so in the output and leave `tasks.md` alone.
   - Write `dev/changes/{name}/acceptance.md` from the template. Keep every heading and role comment exactly as the template writes them, drop the comments addressed to the author, and write the scope, the field labels' content and the scenarios in the artifact language.
   - Give each scenario a third-level heading `### N. {name}` and fill its fields in the template's order:
     - the covered specification scenarios, each as a root-relative link `/dev/specs/<domain>/spec.md` followed by the scenario's name as the specification writes it;
     - the preconditions, or an explicit "none";
     - the exact steps and commands, numbered;
     - the expected outcome, as what the user should see;
     - the cleanup, or an explicit "none";
     - the result, left as `- [ ]` for the walk to fill in.
   - When nothing in the change needs a person, say so in the scope section with the reason, and leave the scenarios section with no scenario.
   - Run `uv run dev/scripts/acceptance.py "{name}"` and confirm that it lists every scenario written, each as `pending`. A scenario it does not list has a heading the template does not resolve: fix the heading before going on.

5. **Show the Scenarios.**
   - With no scenario written, go to step 8: the step is complete as soon as the file is written.
   - Otherwise list the scenarios -- heading and covered specification scenarios -- and ask the user whether to start the walk or to reword any of them first. A scenario the user wants changed is changed now, before its first run.

6. **Walk the Scenarios Without a Result.**
   - Run `uv run dev/scripts/acceptance.py "{name}"` and take the `pending` scenarios in the order it lists them. With none left, go to step 7.
   - Present the first one: its heading, preconditions, steps, expected outcome and cleanup, as the file writes them. Then ask for the user's report: `passed`, `failed` with what the user observed, `skipped` with the reason, or a stop.
   - Wait for the report. Never run a step of the scenario yourself, not even one that looks harmless or read-only.
   - Record the report as **Recording a Result** below describes, then present the next `pending` scenario.
   - When the user stops, go to step 8.

7. **Re-run the Failed Scenarios.**
   - Only once no scenario is `pending`: list the `failed` scenarios from `acceptance.py`, and ask the user which of them the project has received a fix for. With no `failed` scenario, go to step 8.
   - Present again only the scenarios the user names, as in step 6, and record each new report. A `failed` scenario the user does not name keeps its result.
   - Whether a fix has arrived is the user's word. Never decide it yourself from a commit after the failure or from a change to the files the diagnosis names: those say that code moved, not that it fixed what the user saw.

8. **Finish the Run.**
   - Run `uv run dev/scripts/status.py "{name}"` and `uv run dev/scripts/acceptance.py "{name}"`.
   - A scenario still `pending` -- the user stopped: say how many scenarios still wait for a run and that the next invocation resumes at the first of them. Offer no commit.
   - Every scenario has a result, or the file lists no scenario: for every scenario still `failed`, name its route -- `dev-bugfix` invoked directly on that failure, which writes the reproducing test and the fix and offers its own commit, then this skill again to re-run the scenario.
     Then offer the user to review the work and commit it: generate the command with the `dev-commit` skill, following its workflow, and tell it which files this run produced, as **What the Skill Reads and Hands Over** lists them.
   - Offer the `dev-next` skill for the step the report names next.

## Recording a Result

Write each result to `acceptance.md` the moment the user reports it, so that a run stopped at any point loses nothing and the next one resumes from `acceptance.py` alone.

- **The marker.** A result is an unindented list item under the scenario's result field: `- [passed]`, `- [failed] <what the user observed>` or `- [skipped] <the user's reason>`. The token in brackets stays in English in every artifact language; the observation and the reason are written in the artifact language.
- **The first result** replaces the `- [ ]` placeholder.
- **A re-run** adds its result as a new unindented item below the previous result and its diagnosis, which stay as the history of the scenario. The scripts read the last item as the result.
- **A skip needs a reason.** When the user skips without one, ask for it, and record nothing until it is given.
- **A failure is diagnosed, not fixed.** Record `- [failed]` with the observation first. Then offer the `dev-bugfix` skill to name the root cause, and invoke it only on the user's yes, handing it the failure as **What the Skill Reads and Hands Over** describes. Record the diagnosis it returns under the `- [failed]` line, and name the route of step 8 for it. When its specification impact is `outside scope`, say that `dev-bugfix` invoked directly routes that fix to a new change through `dev-new-change`.
- **The verdict goes with the first result of the run.** When `dev/changes/{name}/.devskills.yaml` holds `verify` or `verified`, delete both lines by hand as soon as the run records its first result, leaving every other key as it is. That verdict judged an acceptance that no longer stands.

## Guardrails & Constraints

- Never execute a step of a scenario, and never record a result the user did not report.
- Never write `acceptance.md` before every task of the change is done, and never without a template.
- Never read a result or count scenarios by hand: `acceptance.py` and `status.py` are the only sources.
- Never record `skipped` without the user's reason, and never replace a result without a new report from the user.
- Never present a `failed` scenario again before every `pending` one has a result, and never one the user has not named as fixed.
- Never apply a fix, edit code or tests, or check a task of `tasks.md`: the only files this skill changes are `acceptance.md`, the `verify` and `verified` keys of `.devskills.yaml`, and `dev/templates/acceptance.md` when the user agreed to the English template.
- Never offer a commit while a scenario still has no result.
- Never put a check the agent can run and judge itself into `acceptance.md` -- it is an automated test.

## Expected Output Formatting

After writing:

```md
## Acceptance Written: {change-name}

**Scope:** {one sentence from the scope section}

1. {scenario heading} -- covers {specification scenario names}
2. ...

{checks the agent could run that have no Functional Test yet, if any}

Shall I start the walk, or do you want any scenario reworded first?
```

Presenting a scenario:

```md
## Scenario {N}/{total}: {scenario heading}

**Preconditions:** {as written}

**Steps:**
1. {as written}

**Expected:** {as written}

**Cleanup:** {as written}

Run the steps and tell me the result: passed, failed (and what you saw), skipped (and why), or stop.
```

At the end of a run:

```md
## Acceptance: {change-name}

{acceptance.py output}

{when a scenario is still pending: "{K} scenario(s) still wait for a run; the next invocation resumes at {heading}." -- and no commit}
{when every scenario has a result: the route for each failed scenario, then the commit proposal from the `dev-commit` skill}

Next: {the step status.py names} -- the `dev-next` skill runs it.
```
