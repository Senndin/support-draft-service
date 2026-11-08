---
name: dev-new-change
description: |
  Start a new DevSkills change using the spec-test-driven workflow.
  Use when the user wants to create a new feature, fix, or modification with a structured step-by-step approach.
---

Scaffold a new DevSkills change directory and prepare for writing its proposal.

**Input:** A kebab-case change name or a natural language description of the objective. A calling skill may supply both, together with the description to save.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Invocation

This skill runs in two ways, and the scaffolding below is identical in both.
Only the origin of the initial description differs:

- **Directly.** The user states an objective. The description saved to `notes.md` is their own words, gathered by step 1.
- **From `dev-bugfix` or `dev-apply-change`.** The caller supplies the change name and the description: the investigation report of `dev-bugfix`, or the diagnosis block `dev-apply-change` holds -- either way a fix that was found but not applied, because applying it would change what a specification promises. Take both as given, and save that description as the initial description.

## Execution Steps

1. **Clarify Intent.**
   - When a calling skill supplied the name and the description, take them as given and skip to step 2; the objective is already established.
   - If the user's input is vague or lacks a clear objective, ask an open-ended question to ascertain what they wish to build.
   - Derive a kebab-case name from their description (e.g., "add user authentication" -> `add-user-auth`).
   - **CRITICAL:** Do not proceed without a clear understanding of the user's goal.

2. **Scaffold the Change.**
   - Run `uv run dev/scripts/new_change.py "{name}"`.
   - This command generates the change directory at `dev/changes/{name}/`.

3. **Save the Initial Description.**
   - Write the user's initial description (their raw objective, as provided) to `dev/changes/{name}/notes.md`.
   - When a calling skill supplied the description, write that instead, and write it whole -- it is the reason this change exists.
   - Keep it verbatim; do not rewrite, summarize, or interpret it.
   - If the description came from a clarifying exchange, include the user's answers as well.

4. **Present the Proposal Template.**
   - Read `dev/templates/proposal.md` for the structure; how to fill it is the business of `dev-plan-change`, which writes it in its analysis phase.
   - Show the user a short summary: the change name and that the proposal is ready to be drafted.

5. **Pause for Direction.**
   - Do **not** create `proposal.md`.
   - Prompt the user to describe the change further or to continue: the analysis phase of the `dev-plan-change` skill settles the scope with the user and writes the proposal, and `dev-next` runs it.

6. **Create the Change Branch.**
   - Read the current branch with `git rev-parse --abbrev-ref HEAD`.
   - If it already equals `{name}`, the branch is in place: say so and propose nothing.
   - Otherwise propose `git switch -c "{name}"` -- the branch name is the change name -- and run it **only after the user explicitly agrees**. The command is a proposal until they accept it.
   - The change's uncommitted files travel to the new branch with the switch, so no `git stash` is needed.
   - If the working tree carries uncommitted edits unrelated to this change, say so and do not switch; those edits would travel too, and settling them is the user's call.
   - One change lives on one branch: this is what makes `git diff dev/specs/` answer what *this* change altered. Create the branch before the first commit of the change, so that commit does not land on the base branch.

7. **Offer to Commit.**
   - Offer the user to review the work and commit it: generate the command with the `dev-commit` skill, following its workflow, and tell it which files this step produced -- `dev/changes/{name}/` with its `notes.md` and `.devskills.yaml`.

## Guardrails & Constraints

- Only scaffold during this phase; never write `proposal.md`, which `dev-plan-change` writes once the scope is agreed.
- Enforce valid kebab-case naming; if invalid, request correction.
- Never create, switch or delete a branch without the user's explicit agreement, and never `git push`. Branch creation belongs to this skill alone; `dev-commit` never touches branches.

## Expected Output Formatting

```md
## Change Initialized: {change-name}

Created `dev/changes/{change-name}/`.
Saved your initial description to `dev/changes/{change-name}/notes.md`.

{the branch proposal, or a note that `{change-name}` is already the current branch}

{the commit proposal from the `dev-commit` skill}

Ready to draft the proposal?
Describe what this change is about, or ask me to continue: the `dev-plan-change` skill agrees the scope with you and writes it, and `dev-next` runs it.
```
