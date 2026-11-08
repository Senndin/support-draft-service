---
name: dev-docs
description: |
  Write and improve code documentation.
  Use when writing or improving docstrings, module overviews, ADRs, READMEs, or inline comments.
---

Document code so the next reader learns why it exists and how to use it, without reading its implementation.

**Input:** The code to document, or a request to improve existing documentation.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Source of Truth

The project's code style guide, linked from the project root `AGENTS.md`, defines the concrete rules: which docstring format to use, which natural language documentation is written in, where module overviews and decision records live, and how a documentation site (if any) is generated from the source.
Read it before writing anything, and follow it over any habit or example below.

If the project documents none of this, infer the conventions from the existing documentation in the codebase -- the docstring format most files already use, the language they are written in, and where overviews are kept.
State what you settled on and why, and suggest the user document it.

## Principles

**Philosophy**

- **Document why, not what** -- code shows what happens; docs explain why it exists and when to use it.
- **Close to code** -- keep docs next to the code they describe; external docs go stale faster.
- **Audience-aware** -- docstrings for developers using the code; READMEs for those evaluating or setting it up.
- **Update with code** -- documentation changes are part of the code change, not a follow-up task.

**What to Document**

- **All public APIs** -- every exported function, class, method, and endpoint.
- **Complex logic** -- non-obvious algorithms, business rules, and workarounds.
- **Decisions and tradeoffs** -- why this approach over the alternatives.
- **Skip the obvious** -- do not document self-evident code.

**Style**

- **One format per project** -- use the docstring format the project already uses; never mix two in the same codebase.
- **Consistent voice** -- use the mood the project's docstring format prescribes; default to descriptive third person ("Returns the user"), and switch to imperative ("Return the user") only where the project follows PEP 257. Never mix the two within one docstring.
- **Examples over explanation** -- show usage when behavior is not obvious.
- **Keep it current** -- wrong documentation is worse than no documentation.

## Workflow

1. **Establish the conventions.**
   Resolve the format, language, and placement rules as described in **Source of Truth** before writing.
2. **Document the public surface.**
   Cover every public API the change adds or modifies, at the level the project's tooling extracts documentation from.
3. **Explain the non-obvious.**
   Add inline comments only where intent cannot be read off the code, and record significant decisions where the project keeps them.
4. **Refresh what the change invalidated.**
   Update docstrings, overviews, and READMEs that the change made wrong -- stale documentation is a defect, not debt.

## Module Overview

Each module or package gets one high-level overview, placed wherever the language and the project's documentation generator expect it (a package initializer's docstring, a dedicated documentation file, or a folder-level README).

The overview contains only high-level context:

- **Purpose** -- what problem the module solves and when to use it.
- **Key public API** -- a brief list of the main functions, classes, or models it exposes.
- **Important notes** -- non-obvious constraints, integration points, or required setup.

Avoid implementation details, internal file structure, and dependency lists -- those are unstable and are read more reliably from the source.
Files inside the module document their own contents and do not repeat module-level context.

## Architecture Decision Records

Record a significant design decision where the project keeps its decision records -- in the module overview, or in a dedicated ADR directory if the project has one.

Each entry states the decision made, the context that drove it, and its consequences.
Keep entries concise, and only record decisions that are non-obvious or that future maintainers are likely to question.

## Inline Comments

Comment on intent, not mechanics.

```text
GOOD: why this approach
  # Binary search: the list is always sorted and can hold 100k+ items.

GOOD: non-obvious external constraint
  # The payment provider expects the amount in cents, not in the major unit.

GOOD: a documented workaround
  # HACK: delay to avoid a race condition in the legacy API (see issue #1234).

BAD: restating the code
  # Increment the counter by 1.

BAD: obvious from context
  # Check whether the user is missing.
```

Tag markers consistently:

```text
# TODO(username): add retry logic for transient failures
# FIXME: breaks when the timezone is not UTC (issue #567)
# HACK: temporary workaround until the upstream bug is fixed
# NOTE: must run before the database migrations
```

## API Documentation

For an HTTP endpoint, document what it does, its parameters, what it returns, and every error status it can produce -- callers cannot read the implementation.

Where the framework generates a schema from typed models, put the description and an example on each field so that the generated reference is usable on its own, rather than describing the fields again in prose.

## Examples

For worked examples in one stack, read `references/python-django.md`.
It describes one specific project and is illustrative only; never carry its format, language, or layout into a project that does not match it.

## Guardrails & Constraints

- Write documentation in the natural language the project's existing documentation uses, keeping technical terms in English.
- Document the code the change actually touches; do not backfill documentation for untouched code unless asked.
- Never describe behavior the code does not have -- verify a docstring against the implementation before writing it.
- Delete or fix documentation the change made wrong instead of leaving it to contradict the code.
