---
name: dev-test
description: |
  Run the tests of the project DevSkills is applied to -- the full suite when called with no target, a narrow target when one is named.
  Use when implementing, fixing, or verifying any change to ensure the affected code and the broader suite still pass.
compatibility: Requires the project's test runner to be installed and configured.
---

Run targeted tests fast for iteration, then run the full suite for safety after completing all the tasks in the change.
Some tests are flaky -- re-run a failure once before treating it as real.

**Input:** An optional target -- a test case, a module, a package, or an application of the project DevSkills is applied to. If omitted, run the project's full test suite.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Invocation

This skill runs in two ways. The source of truth, the runner and the flaky-retry rule are identical in both; only the scope differs:

- **Without a target.** The user invokes the skill with no parameters, or asks for "the tests", "all tests", "the full suite". Run the whole test suite of the project DevSkills is applied to, in one run, and report its outcome. Do NOT narrow the scope: never infer a target from the current diff, the active change, the open file or the last thing discussed, and never ask the user which tests to run -- the absence of a parameter is itself the answer.
- **With a target.** The user or a calling skill names the scope -- a test case, a module, a package, an application, or the code a change touches. Run that target, iterate on it, and leave the full suite to the caller unless the caller asks for it.

## Source of Truth

The `Testing` section of the project root `AGENTS.md` defines the concrete rules: which runner to use, how to invoke it, how tests are laid out, and which suites are slow or excluded by default.
Read that section before running anything, and follow it over any habit or example below.
It is also the authority on what "the full suite" means in this project -- the documented entry point that runs everything, and the suites it deliberately excludes by default.

If `AGENTS.md` has no `Testing` section, or it is still unfilled, infer the runner from the project's manifest and configuration (for example `pyproject.toml`, `package.json`, or `Makefile`), state which command you settled on and why, and suggest the user document it in `AGENTS.md`.

## Workflow

Steps 1 and 2 belong to the targeted mode. Without a target, start at step 3 -- the full suite is the whole run.

1. **Iterate on the narrowest target.**
   Pick the smallest scope that exercises your change, widening only as needed: a single test case, then its module, then its package or application.
2. **Fix until green.**
   Re-run the same narrow target after each edit.
3. **Run the full suite.**
   Without a target, run it immediately: one command, the project's documented full-suite entry point, no narrowing.
   In targeted mode, run it once the narrow target passes, after completing all the tasks in the change.
   Do NOT skip this step -- interactions between modules might cause unrelated tests to fail.
4. **Handle flakiness.**
   If a test fails in the full run and is unrelated to your change, re-run that single test once.
   If it passes on retry, treat it as flaky and proceed. If it fails again, investigate it as a real regression.

## Examples

For a worked example of what a `Testing` section might pin down, read `references/django.md`.
It describes one specific project and is illustrative only; never apply it to a project that does not match it.

## Guardrails

- Treat an invocation with no target as a request for the full suite; never substitute a narrower scope for it, and never ask which tests to run instead.
- Always run the full suite before reporting change completion; passing narrow tests is not sufficient.
- Never dismiss a failure as "unrelated" without first re-running that single test once to confirm flakiness.
- Use the runner the project actually declares; never substitute a different one (for example, never invoke `pytest` in a project built around Django's test runner).
- Prefer the project's documented entry point over calling the underlying runner directly, so that its environment and task definitions apply (for example, `uv run poe test` rather than `python manage.py test`).
