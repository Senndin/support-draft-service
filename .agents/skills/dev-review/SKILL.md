---
name: dev-review
description: |
  Review code quality against the project's stack and conventions.
  Use when the user wants a code review of a change, of a path, file, class or function; also invoked by dev-verify-change as its Quality dimension.
---

Review code as a senior engineer on the project's stack, and report actionable findings.

This skill judges code quality. It does not audit whether the change satisfies its artifacts -- that is `dev-verify-change`.

**Input:** An optional target -- a change name, or a code object: a path, a file, a class, a function. If omitted, infer from context or prompt the user.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Invocation

This skill runs in three ways, and the review dimensions below are identical in all of them. Only the scope and the fate of the report differ:

- **Directly, on a change.** The user names a change, or names nothing. The scope is the change's cumulative diff, and the review is offered for saving to `dev/changes/{name}/code-review.md`.
- **Directly, on a code object.** The user names a path, a file, a class or a function. The scope is that code as it currently stands, not a diff -- a class or a function may have no diff at all. Output the review; write a file only if the user names a path for it.
- **From `dev-verify-change`.** The change is already selected by the caller; do not select it again. The scope is the change's diff, as above. Do NOT write a file and do NOT offer to save the review -- the findings are returned to the caller, which folds them into its verification report as the Quality dimension.

If it is unclear whether the target is a change or a code object, ask before producing the scope -- the two paths review different code, and reviewing the wrong one wastes the whole run.

## Execution Steps

1. **Establish the Target.**
   - When invoked from `dev-verify-change`, take the change it selected and skip the rest of this step.
   - If the user named a code object, resolve it: a path or file directly, a class or function by searching the repository for its definition. This is the code-object mode for every step below.
   - Otherwise select the change as `Target change` in `dev/AGENTS.md` describes.
   - In code-object mode, output "Reviewing: {target}" in place of the change line.

2. **Load Context.**
   - In change mode, read `dev/changes/{name}/proposal.md` and `design.md` (if present) to understand what the code is meant to do.
   - Read the project's code style guide, linked from the project root `AGENTS.md`, if there is one.
   - Identify the stack actually in use (languages, frameworks, libraries) from the project root `AGENTS.md`, the project's manifest, and the existing code -- review against those idioms, not assumed ones.

3. **Establish the Review Scope.**
   - In change mode, take the base from `uv run dev/scripts/change_base.py "{name}"` and review `git diff {base}..HEAD` together with whatever is still uncommitted (`git diff` and `git diff --staged`) -- the work under review is rarely committed in full.
   - That base is the commit the change started from, so the window holds this change and nothing else, whether the work sits on a branch or on the main one. A base branch guessed instead would decide the review scope by luck.
   - Only if the script gives no base -- nothing of the change is committed yet -- fall back to the working tree alone, and ask the user for a base branch only when even that leaves the scope unclear.
   - Review the diff itself; read the surrounding files whenever a hunk cannot be judged in isolation.
   - In code-object mode, read the object's current code in full, together with the surrounding code needed to judge it -- its callers, its tests, the module it lives in. Do not produce a diff.

4. **Review the Code.**
   - Assess each of the following, skipping any that the scope does not touch:
     - **Style guide adherence:** deviations from the project's documented conventions.
     - **Best practices:** idiomatic use of the stack's languages, frameworks, and libraries.
     - **Correctness:** logic errors, edge cases, error handling.
     - **Consistency:** naming, structure, and patterns matching the surrounding code.
     - **Duplication:** repeated logic and needless abstraction.
     - **Testing:** what is not covered, and why that coverage matters.
     - **Security:** injection, secrets, authorization, input validation.
     - **Performance:** N+1 queries, redundant allocations, blocking calls, IO.
   - Anchor every finding to a specific file and line.
   - Classify each finding as **CRITICAL**, **WARNING**, or **SUGGESTION**.
   - Give every finding a concrete fix, not a direction to investigate.

5. **Report the Findings.**
   - Output the review grouped by severity, most severe first.
   - If nothing was found in a dimension worth reporting, say so rather than padding the report.

6. **Deliver the Review.**
   - When invoked from `dev-verify-change`, stop here: hand the findings back with their severities intact and write nothing.
   - In change mode, offer to write the review to `dev/changes/{name}/code-review.md`, so it lives alongside the change's other artifacts. Write the file only after the user accepts.
   - In code-object mode, the review is output only; write it to a file solely when the user names the path.
   - Follow the artifact conventions in `dev/AGENTS.md` whenever you do write it, including the artifact language.

## Guardrails & Constraints

- Prompt for change selection whenever more than one change is active; never guess between them.
- Never guess a base branch, and never ask for one, while `change_base.py` can name the base -- the scope of the review is not the user's to remember.
- In change mode, review only what the diff changes; do not report pre-existing issues in untouched code as findings of this change.
- In code-object mode, review the object as it currently stands, whatever its history -- there is no diff to limit the findings to.
- Every finding MUST carry a file/line reference and a specific fix. Avoid vague terms like "consider reviewing".
- Default to lower severity when uncertain (SUGGESTION over WARNING, WARNING over CRITICAL).
- Judge the code against the project's actual stack and conventions, never against a stack it does not use.
- Do not fix the findings; reviewing and applying are separate steps the user decides between.
- Never write `code-review.md` without the user's consent, and never write any file when invoked from `dev-verify-change` -- there the caller owns the report.

## Expected Output Formatting

```md
## Code Review: {target}

**Base:** {base}..HEAD, plus the uncommitted working tree
**Reviewed:** N file(s), M insertion(s), K deletion(s)

### CRITICAL
- **{Short title}** — `path/to/file.py:42`
  {What is wrong and what it breaks.}
  - _Recommendation:_ {the concrete change to make}

### WARNING
- **{Short title}** — `path/to/file.py:88`
  {What is suboptimal and why it matters.}
  - _Recommendation:_ {the concrete change to make}

### SUGGESTION
- **{Short title}** — `path/to/file.py:15`
  {The optional improvement.}
  - _Recommendation:_ {the concrete change to make}

### Summary
X critical, Y warning(s), Z suggestion(s).
Save this review to `dev/changes/{change-name}/code-review.md`?
```

The `**Base:**` and `**Reviewed:**` lines belong to change mode; in code-object mode replace them with the object reviewed and the files it spans.
Drop the closing save question in code-object mode, and drop the whole trailing `### Summary` block when invoked from `dev-verify-change` -- that report carries its own summary.
