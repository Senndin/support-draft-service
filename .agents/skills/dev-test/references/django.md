# Example: a Django project

An illustration of what a `Testing` section might pin down. It is not a rule for every project -- read the actual `AGENTS.md`.

The project uses Django's built-in test runner, exposed through `poe` tasks defined in `pyproject.toml`.
Always invoke it through `uv run poe`.
Extra positional args and flags are passed through to `manage.py test`.

| Task                   | Scope                                 |
|------------------------|---------------------------------------|
| `uv run poe test`      | Full suite (unit + functional)        |
| `uv run poe test:unit` | Unit only (excludes `functional` tag) |
| `uv run poe test:func` | Functional only (Selenium, slow)      |

Narrowing the target:

- Single test method: `uv run poe test:unit discipline.tests.test_educational_program.SomeTestCase.test_specific_behavior`.
- Single test module: `uv run poe test:unit discipline.tests.test_educational_program`.
- Whole app: `uv run poe test:unit discipline`.
- By tag: `uv run poe test:unit --tag=admin` (or `--exclude-tag=admin`).

Test layout: most apps put tests under `<app>/tests/test_*.py`; a few use a single `<app>/tests.py`.
To find the right target, list the app's `tests/` directory and pick the module whose name matches the code you touched.

Functional (Selenium) tests live in `functional_tests/` and are tagged via `@tag("functional")` in `functional_tests/base.py`.
They are slow; exclude them during rapid iteration unless they are exactly what you changed.
