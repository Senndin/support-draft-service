---
name: dev-verify-change
description: |
  Verify implementation matches change artifacts, and review the code it produced.
  Use when the user wants to validate that implementation is complete, correct, coherent and of sound quality before archiving.
---

Perform a rigorous post-implementation audit to verify that the codebase reflects the requirements, tasks, and architectural decisions of a change.

**Input:** An optional change name. If omitted, infer from context or prompt the user.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Execution Steps

1. **Select the Target Change.**
   - Select it as `Target change` in `dev/AGENTS.md` describes.

2. **Load Context.**
   - Read `dev/changes/{name}/proposal.md`, `design.md` (if present), and `tasks.md`.
   - Determine the affected specs from the proposal's Features section, following each bullet's link target (`dev/AGENTS.md` maps that role to the heading the project's templates use).
   - Run `uv run dev/scripts/sync_specs.py "{name}"` to compare that declaration against the spec files the change actually touched, committed ones included. Keep the report for step 4.
   - Read the changed specs from `dev/specs/`.

3. **Initialize Audit Report.**
   - Prepare a report spanning four dimensions: Completeness (tasks/specs/acceptance), Correctness (requirements/scenarios), Coherence (design/patterns), and Quality (code review).
   - Quality is conditional: it is audited in step 8 only when the first three dimensions and the test run leave no CRITICAL issue behind.
   - Classify issues as CRITICAL, WARNING, or SUGGESTION.

4. **Verify Completeness.**
   - **Tasks:** Read `tasks.md`, tally complete vs. incomplete. Flag incomplete tasks as CRITICAL.

   - **Specs:** For each requirement in the changed specs, search the codebase for corresponding implementation. Flag missing implementations as CRITICAL.

   - **Features drift:** Turn the `sync_specs.py` report into findings. A `declared-unwritten` entry is CRITICAL — the proposal promised a spec that was never written, so nothing downstream verifies it. A `missing-new` or `missing-changed` entry is a WARNING — the change touched a spec its proposal never declared, which is scope carried untracked — recommending the bullet to add under the matching subsection. An `undeclared-file`, `misplaced`, `unresolved-bullet` or `non-spec-bullet` entry is a WARNING too, recommending the specific edit to the proposal's Features section that resolves it.

   - **Acceptance:** Run `uv run dev/scripts/acceptance.py "{name}"` and take every scenario's result from its lines, never from `acceptance.md` by hand.
     - `No acceptance.md in dev/changes/{name}/.` is CRITICAL — the change has not passed its acceptance step — recommending the `dev-accept-change` skill.
     - A `pending:` line is CRITICAL — a scenario the user has not run — recommending the `dev-accept-change` skill to walk the user through it.
     - A `failed:` line is CRITICAL, recommending the `dev-bugfix` skill invoked directly on that failure, with the diagnosis recorded under the scenario as its description, and then the `dev-accept-change` skill to re-run the scenario once the fix is in.
     - A `skipped:` line is a WARNING that repeats the user's reason, as `acceptance.md` records it under the scenario.
     - No line at all means an `acceptance.md` with no scenario for a person to run; nothing is owed.
     - Keep the tally of scenarios with a result for the summary table.

5. **Verify Correctness.**
   - **Implementation Mapping:** For each requirement, assess whether the implementation matches its intent. Flag divergences as WARNINGs with file/line references.
   - **Scenario Coverage:** For each scenario of the changed specs, verify condition handling and look for coverage through either channel: an automated test that exercises it, or a scenario of `acceptance.md` whose **Covers** field names it, by a link to its specification file followed by its name.
     A scenario covered by either channel is covered; flag one covered by neither as a WARNING, recommending the test or the acceptance scenario that would cover it.
   - **Coverage Links:** For each link in the **Covers** field of `acceptance.md`, check that the linked specification holds a scenario of that name. Flag a link that names no existing scenario as a WARNING, recommending the scenario name of that specification it most likely means.

6. **Verify Coherence.**
   - **Design Adherence:** Extract key decisions from `design.md` (skip if absent) and verify the codebase follows them. Flag contradictions as WARNINGs.
   - **Pattern Consistency:** Review new code against existing naming, directory structure, and coding style. Flag deviations as SUGGESTIONs.

7. **Run Tests.**
   - Run the project's tests with the `dev-test` skill, following its workflow.
   - Map the outcome: a real regression is CRITICAL; a failure that passes on retry becomes a SUGGESTION noting flakiness.
   - Offer the `dev-bugfix` skill for a regression, telling it this change.
   - Record the diagnosis it returns with the finding, so that the recommendation names a cause and not a symptom: the reproducing test and the fix it names are the recommendation.
   - When its **Specification impact** reads `outside scope: <spec path>`, recommend a new change instead -- the `dev-new-change` skill, with the diagnosis as its initial description -- because that fix changes a specification this change does not declare.
   - Never apply the fix `dev-bugfix` returns, whatever its impact: the audit reports the regression, and fixing it is implementation work.

8. **Verify Quality.**
   - Count the CRITICAL issues raised by steps 4 to 7. If there is even one, skip the code review entirely and record Quality as "Skipped — N CRITICAL issue(s) must be fixed first". Reviewing code that does not yet satisfy its specs, or that fails its tests, is premature: that code is about to be rewritten.
   - Otherwise review the code of the change with the `dev-review` skill, following its workflow, and tell it that it is invoked from `dev-verify-change` — it reviews the same change and returns its findings instead of writing its own report.
   - Fold the returned findings into the report, keeping each one's severity and its file/line anchor.

9. **Generate Verification Report.**
   - Output a scorecard and grouped lists of issues (CRITICAL, WARNING, SUGGESTION) with actionable, file/line-specific recommendations.
   - Include the test run outcome (narrow target + full suite).
   - State whether the code review ran, and say why when it did not.
   - Conclude with a readiness assessment for archiving.
   - Record that assessment in `dev/changes/{name}/.devskills.yaml` as `verify: clean` when no CRITICAL issue stands, and `verify: blocked` when one does, alongside `verified: {today}`. Replace the previous pair if it is already there.
     A missing `acceptance.md`, and an acceptance scenario that is `pending` or `failed`, are CRITICAL issues, so they always leave the verdict `blocked`.
   - Write it **every time**, whatever the user decides about saving the report in step 10. The verdict is workflow state, not the report: `dev/scripts/status.py` reads it to decide whether the change may move on to archiving, and the consent in step 10 covers the `verify-report.md` file alone.

10. **Offer to Save the Report.**
    - After displaying the report, offer to save it as `dev/changes/{name}/verify-report.md`.
    - Write the file only if the user agrees; save the report verbatim, as displayed.
    - If `verify-report.md` already exists, say so and ask whether to overwrite it or keep the existing one.

11. **Offer to Commit.**
    - Offer the user to review the work and commit it: generate the command with the `dev-commit` skill, following its workflow, and tell it which files this step produced -- `.devskills.yaml` with its verdict, `verify-report.md` if it was saved, together with any fixes made during the audit.
    - If a CRITICAL issue still stands, offer the commit anyway, but say plainly that it records the current state, not a finished change.

## Guardrails & Constraints

- Prompt for change selection whenever more than one change is active; never guess between them.
- Base completeness on objective checklist items; use reasonable inference for correctness.
- Gracefully degrade: if only some artifacts exist, verify those and note skipped checks.
- Default to lower severity when uncertain (SUGGESTION over WARNING, WARNING over CRITICAL).
- Every issue MUST include a specific, actionable recommendation with file/line references. Avoid vague terms like "consider reviewing".
- Never recommend a fix for a failing test without a root cause behind it; offer the `dev-bugfix` skill and carry back the diagnosis it returns.
- Never apply that diagnosis during the audit, and never edit a specification for it; a fix outside the change's declared specifications is a recommendation to start `dev-new-change`.
- Never run `dev-review` while a single CRITICAL issue stands; report the Quality dimension as skipped and name the reason instead.
- Carry the review's findings over at the severity `dev-review` gave them — never soften or sharpen them while merging.
- The review findings belong in this report; `dev-review` writes no `code-review.md` of its own on this path.
- Never write `verify-report.md` without explicit user consent; always show the report first.
- The `verify:` verdict in `.devskills.yaml` is outside that rule -- it is workflow state the next step reads, and it is written every run.
- Never record `verify: clean` while a CRITICAL issue stands; that verdict is what lets the workflow move the change on to archiving.
- Take acceptance results only from `acceptance.py`, and never record, change or re-run an acceptance scenario here; that is the work of `dev-accept-change`.

## Expected Output Formatting

```md
## Verification Report: {change-name}

### Summary
| Dimension    | Status                    |
|--------------|---------------------------|
| Completeness | X/Y tasks, N reqs, A/B acceptance scenarios with a result |
| Correctness  | M/N reqs covered          |
| Coherence    | Followed/Issues           |
| Quality      | X critical, Y warning(s)  |

### CRITICAL (Must fix before archive)
- **Incomplete Task:** {task description}
  - _Recommendation:_ Complete task or mark as done.
- **Missing Requirement:** {requirement name}
  - _Recommendation:_ Implement requirement in relevant module.
- **Failed Acceptance Scenario:** {scenario heading} — `dev/changes/{change-name}/acceptance.md:{line}`
  - _Recommendation:_ Fix it with `dev-bugfix` invoked directly, using the recorded diagnosis, then re-run the scenario with `dev-accept-change`.

### WARNING (Should fix)
- **Design Divergence:** Implementation in `file.py:123` diverges from design decision X.
  - _Recommendation:_ Align implementation or update `design.md`.
- **Skipped Acceptance Scenario:** {scenario heading} — `dev/changes/{change-name}/acceptance.md:{line}`; skipped because {the user's reason}.
  - _Recommendation:_ {run it before archiving, or accept the reason}
- **Security:** {what the review found} — `file.py:88`
  - _Recommendation:_ {the concrete change to make}

### SUGGESTION (Nice to have)
- **Duplication:** {what the review found} — `file.py:15`
  - _Recommendation:_ {the concrete change to make}

### Final Assessment
X critical issue(s) found. Fix before archiving.

{the commit proposal from the `dev-commit` skill}
```

When the code review is skipped, the Quality row reads "Skipped — N CRITICAL issue(s) must be fixed first" and the Final Assessment repeats that the review still owes a run once the change is clean.
