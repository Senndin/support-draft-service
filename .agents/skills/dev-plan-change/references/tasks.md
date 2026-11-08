# Tasks artifact instructions

Create the task list that breaks down the implementation work.

**IMPORTANT:** Follow the template format exactly.
The apply phase and `dev-status` report progress from the checkboxes, so a task written as prose is a task nobody is counting.
Write every task as `- [ ]`: that is the template's convention, and one marker throughout keeps every task list in the project reading the same way.

## Guidelines

- Organize tasks into category groups that match the project's actual architecture.
  A web application typically uses **DB Migrations**, **Backend**, **Frontend**, **Functional Tests**; a library, a CLI, or a service will need different ones.
- Category names stay in English even when the artifacts are written in another language, and two of them are reserved, as `dev/AGENTS.md` states.
  Use `DB Migrations` only for schema work, and `Functional Tests` only for the end-to-end tests of specification scenarios.
- Omit categories that have no tasks for this change.
- If a category requires work across multiple implementation phases, split it into separate numbered groups (e.g., `## 2. Backend: Phase 1 – Models`, then `## 3. Backend: Phase 2 – API`).
- Each task MUST be a checkbox using the format: `- [ ] X.Y Task description`.
- Tasks should be small enough to complete in one session.
- Order groups by dependency, so that no group depends on work scheduled after it.
- Whenever two parts of the system meet, state the contract between them explicitly, and do it before the tasks that consume it.
  Name the exact interface, never "integrate with the backend".
  Which elements make up that contract depends on the stack: route and its parameters, request and response shapes, function or class signatures, event names and payloads, CLI flags, message formats.
- Every task carries its own tests: `dev-apply-change` writes them in the task's RED phase, before the code.
  Outside `Functional Tests`, never write a task that exists only to write the tests of another.
  Such a task has nothing to make green, and the task it was written for finds its tests already there.
- Put the end-to-end tests of the specification scenarios in a `Functional Tests` group, after every group whose behavior they exercise.
  Write one task per set of scenarios, and name the scenarios it covers.
  Its tasks skip RED: the code they exercise is already built, so each test is expected to pass as soon as it is written.

Example:

```markdown
## 1. Backend: Phase 1 – Domain

- [ ] 1.1 Implement the Invoice total calculation.
- [ ] 1.2 Implement the discount rules.

## 2. Backend: Phase 2 – Public Interface

- [ ] 2.1 Define the contract consumed by the client: `render_invoice(invoice_id: int) -> InvoiceView`, where `InvoiceView` exposes `total`, `lines`, and `applied_discounts`.
- [ ] 2.2 Implement render_invoice.

## 3. Functional Tests

- [ ] 3.1 Write an end-to-end test for the scenarios "An invoice is created" and "A discount is applied to an invoice".
```

For a worked example in one specific stack, read `tasks-web-django.md`.
It is illustrative only; never carry its categories or its interface vocabulary into a project with a different architecture.

Reference the specs for what needs to be built and the design for how to build it.
Each task should be verifiable (you know when it's done).
