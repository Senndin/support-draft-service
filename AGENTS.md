# {Project name}

{One or two sentences: what this project is, who it is for and what problem it solves.}

<!--
This file describes the project for AI agents and developers, and at the same time configures DevSkills for it.
Fill in the sections below before applying DevSkills for the first time.
Do not rename the `Running`, `Testing`, `Database migrations`, `Code style` and `Commit style` headings — skills look them up by name.
Delete sections that do not apply to the project and keep the rest short: this file lands in the context of every agent session.
-->

## Key sources

Project description for developers:
{@README.md or another file; delete this line if there is no such document}

Other documents the agent should start from:
{@docs/architecture.md, @docs/domain.md, etc.}

## Stack

{languages, frameworks, database, infrastructure — whatever determines how code should be written}

## Running

**Start:** `{command that starts the dev server, CLI or build}`

**Environment variables:** `{file with the variables and required values}`

**Address:** `{host:port the application is served at}`

**Test data:** `{command that seeds the database, or path to fixtures}`

## Testing

<!-- Source of truth for the dev-test skill: it reads this section before every test run. -->

**Runner:** `{test runner the project uses}`

**Full run:** `{command that runs the whole suite}`

**Targeted run:** `{command that runs a single module or test case}`

**Test location:** `{where tests live and how they are named}`

**Slow or excluded suites:** `{what the default run leaves out and how to run it separately}`

## Database migrations

<!-- Source of truth for the dev-migrate-db skill. Delete this section if the project does not write SQL migrations by hand. -->

**SQL dialect:** `{for example MySQL 8.0, PostgreSQL 16}`

**Database schema:** `{directory holding the database schema, if any}`

**Migration location:** `{directory holding the project's migrations}`

**Naming and up/down pairs:** `{file name pattern and how the forward and reverse scripts are paired}`

Migrations born inside a change are collected by `dev-apply-change` into `dev/changes/{name}/db-migration.up.sql` and `db-migration.down.sql`.

## Code style

Project guide:
<!-- @docs/code_style_guide.md -->

Uncomment the link once the guide exists: it is read by `dev-apply-change`, `dev-refactor`, `dev-docs` and `dev-review`, and through the latter by `dev-verify-change` too.
Without a guide these skills follow the conventions the existing code demonstrates.

## Commit style

<!-- Source of truth for the dev-commit skill: it reads this section before generating every message. -->

**Message language:** `{English or another language; this is not the artifact language — it is the Git history}`

**Types:** `feat, fix, docs, refactor, test, chore, perf, build, ci, style`

**Scope:** `{whether a scope is used and where it comes from — module, directory, domain; or "not used"}`

**Issue number format:** `{one of the patterns below}`

**Maximum subject length:** `72`

**Co-authorship trailer:** `no`

<!-- `yes` appends the co-authorship trailer the agent's environment provides, such as `Co-Authored-By: ...`; `no` keeps it out even when the environment asks for it. -->

Issue number patterns — pick one and keep it in the field above:

| Pattern | Example |
| ------- | ------- |
| `#{issue} {type}: {subject}` | `#345 feat: sync Features section with spec files` |
| `{type}: {subject} (#{issue})` | `feat: sync Features section with spec files (#345)` |
| `{type}: {subject}` + footer `Refs #{issue}` | two lines; incompatible with the single-line message rule |
| `{type}: {subject}` | `feat: sync Features section with spec files` — issue numbers are not used |

Example messages:

```text
feat: add dev-commit skill and wire it into the change workflow
fix(sync_specs): report an unresolved bullet instead of crashing
docs: describe commit rules in the root AGENTS.md
chore: archive change dev-commit-skill
```

Only `dev-archive-change` adds a message body — it describes the whole change in CHANGELOG style.
All other skills generate single-line messages; the co-authorship trailer, when the field above asks for it, is the one line added to any of them.
