---
name: dev-plan-change
description: |
  Plan a DevSkills change in two phases held in a dialog with the user: the business analysis writes proposal.md together with every specification it declares, and the technical design writes design.md together with tasks.md.
  Use when a change needs its proposal, its specifications, its design or its task list, or the user wants to settle what a change does or how it is built before it is implemented.
---

Plan a change in two phases, one per invocation, each settled with the user in a dialog before anything is written.
The **analysis** phase settles why the change is needed, what it changes and which features it adds or changes, then writes `proposal.md` and every specification its Features section declares.
The **design** phase settles how the specifications will be built, then writes `design.md` and `tasks.md`; `dev-apply-change` builds them.

**Input:** An optional change name.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Execution Steps

1. **Select the Target Change.**
   - Select it as `Target change` in `dev/AGENTS.md` describes.

2. **Select the Phase.**
   - Run `uv run dev/scripts/status.py "{name}"` and read its `Next:` line.
   - `proposal.md` or `specs` selects the analysis phase, `design.md` or `tasks.md` the design phase. This invocation runs that phase alone.
   - On any other step, write nothing: name that step, offer the `dev-next` skill to run it, and stop.

3. **Sync the Proposal's Features Section.**
   - Run `uv run dev/scripts/sync_specs.py "{name}"` whenever `proposal.md` exists. The script compares the spec files the change actually touched with the features the proposal declares, resolving both the classification and the section headings itself -- never classify by hand and never assume a heading's wording.
   - Trigger: the report contains any line other than `in-sync`. A report whose only line is `in-sync: N entry(-ies)` means there is nothing to do.
   - Act on `missing-new`, `missing-changed` and `misplaced` as `Features sync` in `dev/AGENTS.md` describes; its rules on the bullet shape and on what may be edited hold for every line below too.
   - This skill reconciles the rest of the report as well:
     - `undeclared-file: <path>` -- a touched file that is not a `dev/specs/<domain>/spec.md`; report it to the user and leave the proposal alone.
     - `declared-unwritten: <path>` -- a declared feature whose spec is still unwritten; leave the bullet in place, it is the contract of the analysis phase.
     - `unresolved-bullet: <text>` -- a bullet whose link has an empty target, so it names no spec; give it the spec file it means, keeping its wording.
     - `non-spec-bullet: <text>` -- a bullet that names no specification at all: prose, or a link pointing outside `dev/specs/`. Report it to the user and leave the proposal alone. It is a declaration only if the user meant it as one; ask before turning it into a bullet with a spec link.
   - This sync is not an artifact of the phase.

4. **Run the Phase.**
   - Run `uv run dev/scripts/config.py artifacts` for the artifact language and the keyword equivalents.
   - Follow **Analysis Phase** or **Design Phase** below, holding the **Dialog** throughout.

5. **Display Progress Summary.**
   - Re-run `uv run dev/scripts/status.py "{name}"` and report what this phase wrote and which step comes next.

6. **Offer to Commit, and Stop.**
   - Offer the user to review the work and commit it: generate the command with the `dev-commit` skill, following its workflow, and tell it which files this phase produced, as its section lists them.
   - Stop there. Never start the design phase in the invocation that finished the analysis: the commit proposal is the review point between what the change does and how it is built, and `dev-next` runs the next phase.

## Analysis Phase

1. **Load the Context.**
   - Read `dev/changes/{name}/notes.md` whole, and `proposal.md` when it exists.
   - Read `references/proposal.md` with `dev/templates/proposal.md`, and `references/spec.md` with `dev/templates/spec.md`.
   - Investigate what the change touches as **Dialog** requires: the existing specifications under `dev/specs/` and the code they describe.

2. **Agree on the Scope** -- on `Next: proposal.md` only.
   - Settle Why, What Changes and the Features list through the **Dialog**.
   - Show the user the drafted Why, What Changes and Features list together, and ask whether this is the scope. Write nothing before an explicit agreement; a correction starts another round.
   - Once the user agrees, write `dev/changes/{name}/proposal.md` from the template, with its Artifacts section copied unchanged.
   - A proposal whose Features section is empty leaves nothing to write after it: skip step 3.

3. **Write the Specifications.**
   - On `Next: specs` this is where the phase resumes: keep `proposal.md` as it stands.
   - Settle the requirements and their scenarios through the **Dialog**: the behavior each requirement states, its edge cases, and what it leaves out.
   - Should the user change the scope while doing so, edit `proposal.md` to match and agree on the scope again, as step 2 does, before any further specification is written.
   - Write every declared specification the change has not written yet -- those `sync_specs.py` reports as `declared-unwritten` -- directly to the file its Features bullet links to, as `references/spec.md` describes: a new file for a new feature, an in-place edit for a changed one. Never write a copy into the change directory.
   - Run `uv run dev/scripts/sync_specs.py "{name}"` again and act on its report as step 3 of **Execution Steps** does.

**Files for the commit:** `proposal.md` when this phase wrote or edited it, `notes.md` when the dialog appended to it, and every spec file under `dev/specs/` this phase touched.

## Design Phase

1. **Load the Context.**
   - Read `dev/changes/{name}/proposal.md`, `notes.md` whole, and `design.md` when it exists.
   - Read every specification the change touched, following the links of the proposal's Features section; `git diff` over `dev/specs/` shows what each of them changes.
   - Read the code style guide linked from the project root `AGENTS.md`, so that every decision is one the codebase can adopt.
   - Read `references/design.md` with `dev/templates/design.md`, and `references/tasks.md` with `dev/templates/tasks.md`.
   - Investigate the code the specifications reach, as **Dialog** requires.

2. **Write the Design** -- on `Next: design.md` only.
   - Settle every design question through the **Dialog** before writing: the decisions and their alternatives, the impact, the risks, the migration, and anything consciously left to implementation.
   - When an answer changes what the change does, edit `proposal.md` or the specification it concerns to match, as the user agreed, before writing on. After any edit under `dev/specs/`, run `uv run dev/scripts/sync_specs.py "{name}"` again and act on its report as step 3 of **Execution Steps** does.
   - Write `dev/changes/{name}/design.md` from the template, as `references/design.md` describes.

3. **Write the Tasks.**
   - On `Next: tasks.md` this is where the phase resumes: keep `design.md` as it stands.
   - Settle through the **Dialog** any question the task list raises -- an order, a contract between two parts, a split into phases -- that the design does not answer. An answer that changes what the change does is applied as step 2 describes.
   - Write `dev/changes/{name}/tasks.md` from the template, as `references/tasks.md` describes.

**Files for the commit:** `design.md` when this phase wrote it, `tasks.md`, `notes.md` when the dialog appended to it, and `proposal.md` and every spec file under `dev/specs/` the dialog led it to edit.

## Dialog

The artifacts this skill writes carry no open question: every question about them is settled with the user before they are written.

- **Investigate before asking.** Read the code, the specifications, the change's artifacts and its `notes.md` first, and never ask what they already answer.
- **Ask in small batches.** Ask at most three related questions at a time, each standing on its own, so the user can answer one without scrolling back for its context.
- **"Your call" is a decision.** When the user leaves a choice to this skill, make it and record it as `Assumed: <the choice>`, so it stays visible as the skill's choice and not the user's.
- **Record every answer at once.** Append each answer to `notes.md` before asking the next batch, so an interrupted dialog resumes without asking a recorded question again.

The record lives in `dev/changes/{name}/notes.md`, under a section of the phase holding the dialog -- `Analysis dialog` or `Design dialog` -- with the heading and the text in the artifact language.
Create the section on the first answer of its phase, and `notes.md` itself when the change has none yet, as a `| Question | Answer |` table, and only ever append rows to it: an earlier answer is never rewritten, and a changed mind is a new row.
Before the first question, read the whole of `notes.md`: a question it already records is answered, whichever phase recorded it.

## Guardrails & Constraints

- Run one phase per invocation and stop after its commit proposal; never chain the design onto the analysis.
- Never write a specification before the user has agreed on the scope; a proposal already on disk is that agreement, until the user changes the scope.
- Never rewrite an artifact on resume: `proposal.md` is edited only for a scope the user changed, and `design.md` only when the user changes a decision the task list reopens.
- Never leave an open question in an artifact: a question still open is asked, never written down, and what is consciously left to implementation goes under Deferred to implementation with the reason it can wait.
- Never list the code, APIs or systems a change affects in the proposal: they are the Impact of `design.md`.
- In the design phase, edit `proposal.md` beyond its Features sync, or a specification, only as the dialog agreed with the user: what the change does is never changed on this skill's own judgment.
- Keep the Features section of `proposal.md` consistent with the report from `sync_specs.py`, with every bullet linking to its spec file.
- Write diagrams as Mermaid code blocks, never as ASCII.
- Write every artifact according to `dev/AGENTS.md`: its canonical section roles, the reserved task group names, the specification rules, the project's artifact language and the writing conventions.

## Expected Output Formatting

After the analysis phase:

```md
## Analysis Complete: {change-name}

Written: {proposal.md, and every specification written or edited, as links}

{status.py output}

{if the Features section was synced: Updated the Features section in proposal.md: {added/moved entries}}

{the commit proposal from the `dev-commit` skill}

Next comes the design phase -- `dev-next` runs `dev-plan-change` again to write `design.md` and `tasks.md`.
```

After the design phase:

```md
## Design Complete: {change-name}

Written: {design.md and tasks.md, as links}

{status.py output}

{if the Features section was synced: Updated the Features section in proposal.md: {added/moved entries}}

{the commit proposal from the `dev-commit` skill}

Next comes the implementation -- the `dev-apply-change` skill works through `tasks.md`, and `dev-next` runs it.
```

When a phase resumes at its second artifact, the `Written:` line names only what this invocation wrote.
