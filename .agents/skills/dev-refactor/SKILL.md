---
name: dev-refactor
description: |
  Improve the structure of existing code without changing its behavior.
  Use when cleaning up after making tests pass, or when code smells make code hard to read, extend, or test.
---

Restructure working code so it reads better and changes more easily, while its externally observable behavior stays exactly the same.

Refactoring is not rewriting: no new features, no bug fixes, no behavior changes.
Those are separate activities -- if one is needed, finish or postpone it, then refactor.

**Input:** The code to clean up (typically the code just written for a task), or a named smell to address.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Source

The catalog below is the code smells and refactoring techniques catalogued at <https://refactoring.guru/refactoring/catalog>, which in turn follows Martin Fowler's *Refactoring*.
Everything this skill needs is reproduced here and in `references/`; do NOT fetch the site while working.

## Source of Truth

The project's code style guide, linked from the project root `AGENTS.md`, decides what "clean" means here: naming, module layout, size limits, and the idioms this codebase prefers.
Read it before restructuring anything, and follow it over any habit or example below.

Where the project documents nothing, follow the conventions the surrounding code already demonstrates.

## Preconditions

- **Tests must exist and pass before you start.** Refactoring without a green suite is guesswork -- if the code is untested, write characterization tests first, or stop and tell the user.
- **The working tree should be clean of unrelated edits**, so the refactoring diff stays reviewable.

## Workflow

1. **Detect the smell.**
   Read the code and name the specific smell from the catalog below. If nothing in the catalog fits, the code may simply be fine -- say so instead of inventing work.
2. **Pick the refactoring.**
   Take the technique the catalog maps the smell to. Prefer the smallest one that removes the smell.
3. **Decide whether the test code has to move with it.**
   A refactoring that stays behind the surface the tests use (extracting a private helper, simplifying a conditional) leaves the tests untouched -- go to step 4.
   A refactoring that changes that surface (a rename, a move to another module, a changed signature, a new collaborator to patch) requires the tests to change too -- follow **Refactorings That Change the Test-Facing Surface** below instead.
4. **Apply it in one small step.**
   One technique at a time, mechanically. Do not fold in a second improvement mid-step.
5. **Re-run the tests.**
   Run the narrowest tests covering the code with the `dev-test` skill; they MUST pass. Assertions and their expected values MUST NOT have changed. If an assertion had to change to make them pass, the behavior changed -- revert and reconsider.
6. **Repeat or stop.**
   Continue while each step clearly pays for itself. Stop when the remaining smells cost more to fix than they cost to live with, and report them instead.

## Refactorings That Change the Test-Facing Surface

Some techniques necessarily reach into the test code: Rename Method, Move Method, Move Field, Extract Class, Inline Class, Add / Remove Parameter, Introduce Parameter Object, Replace Constructor with Factory Method, and any move that changes a module path or a mock's patch target.

Do NOT change the production code first and repair the tests afterwards.
Drive them through a RED -> GREEN cycle -- **tests first, then the code**:

**RED phase (move the tests to the new shape):**

- Edit only the structural coupling in the tests: import paths, module and symbol names, the call shape, constructor arguments, fixture setup, and patch targets.
- Leave every assertion and every expected value **exactly as they are** -- they encode the behavior, which this refactoring does not touch.
- Run the tests with the `dev-test` skill and confirm they **fail for a structural reason** (import error, missing attribute, wrong argument count).
- An assertion failure at this point is a warning, not progress: it means the planned change alters behavior. Stop and reconsider.
- If they still pass, the tests were not coupled to what you are about to change -- undo the test edit and treat the refactoring as an ordinary one (step 4 above).

**GREEN phase (apply the refactoring):**

- Perform the rename, move, or signature change in the production code, plus every call site outside the tests.
- Re-run the same tests and confirm they **all pass with no further edits**.
- If a test still fails, fix the production code, never the assertion. If the only way to green is to change an expected value, the refactoring changed behavior -- revert the whole step.

Handle one such refactoring at a time: the suite is red between the two phases, and stacking a second change makes it impossible to tell which one broke what.
Once green, run the wider suite before moving on -- renames and moves break call sites that the narrow tests never touch.

## Code Smells and Their Refactorings

### Bloaters -- code that has grown beyond a manageable size

| Smell | Signs | Apply |
|---|---|---|
| Long Method | More lines than fit on a screen; comments marking sections; deep nesting | Extract Method; Replace Temp with Query; Introduce Parameter Object; Preserve Whole Object; Decompose Conditional; Replace Method with Method Object |
| Large Class | Too many fields, methods, or responsibilities | Extract Class; Extract Subclass; Extract Interface; Duplicate Observed Data |
| Primitive Obsession | Strings and numbers standing in for domain concepts; type codes as constants | Replace Data Value with Object; Replace Type Code with Class / Subclasses / State-Strategy; Introduce Parameter Object; Replace Array with Object |
| Long Parameter List | More than three or four parameters; flag parameters | Replace Parameter with Method Call; Preserve Whole Object; Introduce Parameter Object |
| Data Clumps | The same group of values travelling together through many signatures | Extract Class; Introduce Parameter Object; Preserve Whole Object |

### Object-Orientation Abusers -- incomplete or wrong use of the object model

| Smell | Signs | Apply |
|---|---|---|
| Switch Statements | A `switch`/`if-elif` chain on a type code, repeated in several places | Extract Method + Move Method; Replace Type Code with Subclasses / State-Strategy; Replace Conditional with Polymorphism; Introduce Null Object; Replace Parameter with Explicit Methods |
| Temporary Field | A field set only in some circumstances and empty otherwise | Extract Class; Introduce Null Object; Replace Method with Method Object |
| Refused Bequest | A subclass uses only a fraction of what it inherits, or overrides it into nothing | Extract Superclass; Replace Inheritance with Delegation; Push Down Method / Field |
| Alternative Classes with Different Interfaces | Two classes do the same job under different names | Rename Method; Move Method; Add / Remove Parameter; Extract Superclass |

### Change Preventers -- structures that make one change require many edits

| Smell | Signs | Apply |
|---|---|---|
| Divergent Change | One class is edited for unrelated reasons | Extract Class; Extract Superclass / Subclass |
| Shotgun Surgery | One conceptual change forces small edits across many classes | Move Method; Move Field; Inline Class |
| Parallel Inheritance Hierarchies | Every new subclass here demands a new subclass there | Move Method; Move Field (collapse the hierarchies into one) |

### Dispensables -- things whose removal makes the code cleaner

| Smell | Signs | Apply |
|---|---|---|
| Duplicate Code | The same fragment in two or more places | Extract Method; Pull Up Method / Field; Form Template Method; Substitute Algorithm; Extract Superclass; Consolidate Duplicate Conditional Fragments |
| Comments | Comments explaining what unclear code does | Extract Method / Variable; Rename Method; Introduce Assertion (keep comments that explain *why*) |
| Lazy Class | A class that no longer earns its keep | Inline Class; Collapse Hierarchy |
| Data Class | Fields with accessors and no behavior, while other classes manipulate them | Encapsulate Field; Encapsulate Collection; Move Method; Extract Method; Remove Setting Method; Hide Method |
| Dead Code | Unreached branches, unused variables, parameters, or classes | Delete it -- version control keeps the history; Inline Class; Collapse Hierarchy; Remove Parameter |
| Speculative Generality | Abstractions built for a future that never arrived | Collapse Hierarchy; Inline Class; Inline Method; Remove Parameter |

### Couplers -- excessive coupling between classes

| Smell | Signs | Apply |
|---|---|---|
| Feature Envy | A method is more interested in another object's data than its own | Move Method; Extract Method (then move the extracted part) |
| Inappropriate Intimacy | Two classes reach deep into each other's internals | Move Method; Move Field; Extract Class; Hide Delegate; Change Bidirectional Association to Unidirectional; Replace Inheritance with Delegation |
| Message Chains | `a.b().c().d()` walking a graph of objects | Hide Delegate; Extract Method + Move Method |
| Middle Man | A class that only delegates onward | Remove Middle Man; Inline Method; Replace Delegation with Inheritance |
| Incomplete Library Class | A third-party class lacks a method you need and cannot be edited | Introduce Foreign Method; Introduce Local Extension |

## Refactoring Techniques

**Composing Methods** -- Extract Method; Inline Method; Extract Variable; Inline Temp; Replace Temp with Query; Split Temporary Variable; Remove Assignments to Parameters; Replace Method with Method Object; Substitute Algorithm.

**Moving Features Between Objects** -- Move Method; Move Field; Extract Class; Inline Class; Hide Delegate; Remove Middle Man; Introduce Foreign Method; Introduce Local Extension.

**Organizing Data** -- Self Encapsulate Field; Replace Data Value with Object; Change Value to Reference; Change Reference to Value; Replace Array with Object; Duplicate Observed Data; Change Unidirectional Association to Bidirectional; Change Bidirectional Association to Unidirectional; Replace Magic Number with Symbolic Constant; Encapsulate Field; Encapsulate Collection; Replace Type Code with Class; Replace Type Code with Subclasses; Replace Type Code with State/Strategy; Replace Subclass with Fields.

**Simplifying Conditional Expressions** -- Decompose Conditional; Consolidate Conditional Expression; Consolidate Duplicate Conditional Fragments; Remove Control Flag; Replace Nested Conditional with Guard Clauses; Replace Conditional with Polymorphism; Introduce Null Object; Introduce Assertion.

**Simplifying Method Calls** -- Rename Method; Add Parameter; Remove Parameter; Separate Query from Modifier; Parameterize Method; Replace Parameter with Explicit Methods; Preserve Whole Object; Replace Parameter with Method Call; Introduce Parameter Object; Remove Setting Method; Hide Method; Replace Constructor with Factory Method; Replace Error Code with Exception; Replace Exception with Test.

**Dealing with Generalization** -- Pull Up Field; Pull Up Method; Pull Up Constructor Body; Push Down Field; Push Down Method; Extract Subclass; Extract Superclass; Extract Interface; Collapse Hierarchy; Form Template Method; Replace Inheritance with Delegation; Replace Delegation with Inheritance.

## Examples

For worked before/after examples of the most common techniques, read `references/python.md`.
They are written in one language and are illustrative only; the techniques themselves are language-agnostic, so never carry Python idioms into a codebase written in another language.

## Guardrails & Constraints

- Behavior MUST NOT change. No new features, no bug fixes, no changed error messages or return shapes as a side effect.
- Never refactor without passing tests covering the code; write characterization tests first or stop.
- Assertions and their expected values MUST NOT change. Everything else in a test -- imports, names, call shape, fixtures, patch targets -- may change when the refactoring moves the surface the test binds to.
- When test code must change, change it **first** and watch it fail structurally; never patch a red test after the fact to match what the production code now does.
- One technique per step, with a test run after each; never batch unrelated restructurings into one edit.
- Do NOT fetch <https://refactoring.guru> or any other external source **for the refactoring itself**; this skill is self-contained.
- Name the smell before applying a technique; a refactoring with no smell behind it is churn.
- Keep the change scoped to the code at hand; do not refactor untouched modules along the way.
- Respect the project's documented style over generic "clean code" instincts.
- If a smell needs a change too large for the current scope, report it as a follow-up instead of starting it.

## Expected Output Formatting

```md
## Refactoring: {file or component}

- **{Smell}** in `path/to/file.py:42` -> _{Technique}_: {what moved where}.
- **{Smell}** in `path/to/file.py:88` -> _{Technique}_: {what moved where} (test-facing: tests updated first, then the code).

Tests: {narrow target} -- passing. Assertions unchanged; {test files re-pointed, or "no test edits"}.

**Left alone:** {smell and why it is not worth fixing now, or "nothing"}
```
