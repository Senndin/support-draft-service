---
name: dev-extract-specs
description: |
  Extract the knowledge from the codebase and task documentation to write initial specifications for a requested module, process, or use case.
  Use when the user wants to document baseline specifications for this brownfield project.
---

Reverse-engineer DevSkills specifications from an existing codebase and historical task documentation.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Philosophy

- **Archaeology over Creativity:** Document what the code ACTUALLY does, not what you imagine it should do.
- **Evidence-based:** Every requirement and scenario must trace back to actual code or documented tasks.
- **DevSkills-native:** Output follows the conventions in `dev/AGENTS.md` exactly -- the artifact language, its normative keywords, and the specification rules.
- **Collaborative:** The user will provide the initial request, describe the module/process/use case, and guide you during drafting. Work together iteratively.

## Process

### Phase 1: Context Gathering

When provided with a request from the user:

1. **Clarify Scope:** Confirm the specific module, process, or use case you need to document.
2. **Review Codebase:**
   - Locate the relevant units of code in whatever form this project organizes them -- packages, modules, apps, services, components, handlers.
   - Extract data structures (fields, relations), business logic (methods, hooks, validations, background jobs), and the UI/API surface.
3. **Review Task History:**
   - Find where the project keeps its written history -- a documentation directory, an issue or ticket export, design notes, a changelog -- and search it, including all subdirectories, for context on the scope at hand.
   - Also read the archived changes under `dev/changes/archive/`, whose directory names carry the date the change was created.
   - If the project numbers or dates its task files, use that ordering to tell newer intent from older; a later document overrides an earlier one.
   - Use these documents to understand _why_ features were built and the intended business rules.
   - Note: Tasks might be incomplete, obsolete, or not fully match the current codebase. Code is the ultimate source of truth.
   - If the project keeps no such history, say so and work from the code alone.

### Phase 2: Draft DevSkills Specifications

Once you understand the context, write the specification files directly in Markdown.
Use `dev/templates/spec.md` as the structural foundation, and follow the specification rules and the artifact language in `dev/AGENTS.md`.

### Phase 3: Review and Refine

1. Present the drafted specification to the user.
   **Important:** Provide the technical details (such as the list of analyzed source files, implementation paths, and related task files) directly in the conversation.
   Do NOT write this information into the `spec.md` document.
2. The user will provide feedback or guide you to adjust the requirements or scenarios.
3. Refine the specification based on this feedback until it is approved.

### Phase 4: Save and Finalize

1. Create the necessary directories under `dev/specs/{domain}/`.
2. Write the approved Markdown content to `dev/specs/{domain}/spec.md`.
3. Sync the Features section of the active change.
   - With no active change, stop here.
   - Otherwise select the change as `Target change` in `dev/AGENTS.md` describes; with several active, the question to the user is which change the extracted specs belong to.
   - Sync its Features section as `Features sync` in `dev/AGENTS.md` describes: a spec written while a change is active is scope that change now carries, and an undeclared one would pass through the rest of the workflow untracked.

## Guardrails & Constraints

- **Direct Editing:** Write the markdown files directly into `dev/specs/`.
- **Declared scope:** Never leave a spec written while a change is active out of that change's Features section.
- **No invented behavior:** Every requirement and scenario traces to code or to a project document; never document intent the codebase does not implement.
- **Project conventions win:** Follow `dev/AGENTS.md` and the project root `AGENTS.md` over any habit; never assume a stack, a directory layout, or a ticket naming scheme the project does not use.
