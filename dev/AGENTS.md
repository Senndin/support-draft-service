---
name: DevSkills
version: 0.7.0
description: DevSkills — spec-test-driven development framework
---

# DevSkills — Structure and Conventions

This directory holds the system specifications and change artifacts for spec-test-driven development with DevSkills.
Specifications are edited directly, and every change is tracked through Git history.

Everything in this file is framework-level and holds for every project that adopts DevSkills.
Everything that belongs to one particular project is declared by that project: the artifact language, its normative keywords and the other DevSkills options in `dev/options.toml`; the code style guide, the test runner, the SQL dialect and the documentation format in the project root `AGENTS.md` and in the project's own documentation.
When the two disagree, the project wins on its own settings, and this file wins on the workflow.

The project root `AGENTS.md` does not import this file, so it is not in context on its own: every DevSkills skill reads it before it starts.

## Directory layout

- `dev/specs/<domain>/spec.md` — the current system specifications. Edited directly.
- `dev/changes/<name>/` — an active change: `proposal.md`, `design.md`, `tasks.md`, `acceptance.md`, `.devskills.yaml` and additional artifacts.
  `.devskills.yaml` carries the change's workflow state as flat `key: value` scalars: `devskills_version` and `created` from `dev-new-change`, then `verify` (`clean` or `blocked`) and `verified` from `dev-verify-change`, and `apply_started` from `dev-apply-change` in review mode `group` or `change`.
  `dev-accept-change` removes `verify` and `verified` when it records an acceptance result, since a verdict reached before that result no longer holds.
  `devskills_version` is the DevSkills release the change was created with, read from the frontmatter of this file; it is left out when that version cannot be read, so its absence means the version was unknown, never that the change predates it.
  `dev/scripts/status.py` reads `verify` to decide whether the change may move on to archiving.
- `dev/changes/archive/<YYYY-MM-DD>-<name>/` — archived completed changes.
- `dev/templates/` — the structural scaffolds for the artifacts above.
- `dev/scripts/` — the DevSkills tooling the skills invoke.
- `dev/options.toml` — the project's DevSkills options. A missing file or key means the default, and `uv run dev/scripts/config.py [<section>]` prints the effective values; skills read options through that script, never from the file directly.

The difference a change introduces is captured by `git diff` over `dev/specs/`.

## Artifact language

Artifacts are written in the language `artifacts.language` declares in `dev/options.toml`.
If the project declares nothing, write them in English.
Before writing any artifact or report file, run `uv run dev/scripts/config.py artifacts`: it prints the language together with the keyword equivalents the specification rules below use.

Technical terms stay in English regardless of that language (for example, "API", "REST", "GraphQL", "Django").

`dev/templates/` carries the artifact headings in that same language, and the templates are the authority on the exact heading text.
Skills address sections by the canonical role names below and resolve the actual heading from the matching template — never by a heading hardcoded in a skill.
A heading that carries a canonical role is followed by an HTML comment holding that role name and nothing else (`<!-- New features -->`), so the mapping is readable straight from the file.
Anything addressed to the author of the artifact goes in a comment of its own, never on the same line as a role.
`tasks.md` is the exception: its headings are the task groups, which the author names, so they carry no role.

## Dialog language

Skills address the user in the language `dialog.language` declares in `dev/options.toml`.
If the project declares nothing, address the user in English, whatever language the user writes in.
Before the first word to the user, run `uv run dev/scripts/config.py dialog`: it prints `dialog.language: <language>`.

The boundary between the two languages is the medium, not the genre.
Everything a skill says in the chat follows `dialog.language`: questions, step summaries, status reports, commit proposals and reference links.
Everything a skill writes to a file under `dev/` follows `artifacts.language`, `verify-report.md` included, so neither option changes what the other governs.

Technical terms, literal paths, commands, identifiers and the lines scripts print stay as they are in either language.
Commit messages follow the `Commit style` section of the project root `AGENTS.md`, whatever language the proposal around them is in.

## Canonical section roles

| Artifact | Roles |
|---|---|
| `proposal.md` | Why · What Changes · Features (New features, Changed features) · Artifacts |
| `design.md` | Context · Goals · Non-Goals · Decisions · Impact · Risks and Trade-offs · Migration Plan · Deferred to implementation |
| `spec.md` | Purpose · Requirements (Requirement -> Scenario) |
| `tasks.md` | Numbered task groups, each holding checkbox tasks |
| `acceptance.md` | Scope · Scenarios (Scenario) |

`Goals` and `Non-Goals` share one heading in `design.md`; both role comments sit under it, beside the labels that separate the two lists.

Task group headings are the exception to the artifact language: their category names stay in English, so that tooling and skills can match them across projects.
`DB Migrations` is reserved — `dev-apply-change` and `dev-migrate-db` key their behavior off that exact category name.
`Functional Tests` is reserved too — `dev-apply-change` keys its behavior off that exact category name.

## Writing conventions

Write each sentence on its own line.
Consecutive sentences are combined into a single paragraph.
Separate paragraphs with a blank line.
This also applies to list items, unless they are short.

## Specification rules

- Each requirement (a third-level heading, `###`) MUST have at least one scenario.
- Scenarios MUST use exactly four hashes (`####`).
- Use the RFC 2119 keywords MUST / MUST NOT for normative requirements, written in the artifact language. The `artifacts.keywords` table of `dev/options.toml` declares the equivalents when that language is not English.
- Each scenario is a potential functional (end-to-end) test case, expressed as GIVEN / WHEN / THEN steps (with AND / OR / BUT where needed), in the same language and with the same equivalents.

## Target change

A skill that works on a change uses the change name it was given.
Without one, it lists the active changes with `uv run dev/scripts/list_changes.py`, which excludes `archive/`: when exactly one is active, it uses that one, and when several are, it asks the user to choose, marking the most recently modified as "(Recommended)".
It outputs "Using change: {name}" before any work.
A skill invoked by another skill takes the change its caller selected and does not select it again.

`dev-archive-change` and `dev-next` are the exceptions: each describes its own selection.

## Features sync

The Features section of a change's `proposal.md` declares the specifications that change creates or edits, and it is kept in line with the files the change actually touched.
After any edit to a file under `dev/specs/` while a change is active, run `uv run dev/scripts/sync_specs.py <name>` for that change and act on its report.
The rule holds for every skill that edits specifications, so no skill is exempt by being left off a list.

- `missing-new: <path>` — add a bullet for that spec under the New features subsection.
- `missing-changed: <path>` — add a bullet for that spec under the Changed features subsection.
- `misplaced: <path> (declared X, actually Y)` — move the existing bullet into the subsection matching Y, keeping its wording.

A bullet that is added keeps the shape `dev/templates/proposal.md` defines, with a root-relative link to the spec file (`/dev/specs/<domain>/spec.md`) and a description taken from the spec's own content.
Edit only the Features section, and never remove a bullet the user wrote.
A report whose only line is `in-sync: N entry(-ies)` leaves nothing to do, and any other line is left to `dev-plan-change`, which reconciles the whole report at the start of each phase.
With no active change there is nothing to sync: the specification is written, and every proposal stays untouched.

## Review modes

`apply.review` in `dev/options.toml` selects the review mode of `dev-apply-change`: `task` (the default), `group` or `change`.
A review mode given when the skill is invoked overrides `apply.review` for that invocation only.
`apply.time_limit` is the autonomy budget of a `group` or `change` session, in minutes: an integer greater than 0, 45 by default.
Its deprecated name `apply.group_time_limit` is still read, with a warning, and `apply.time_limit` wins when both are set.

## Commit on next

`commit.auto_on_next` in `dev/options.toml` is a boolean, `true` by default.
While it is on, invoking `dev-next` is the user's agreement to the commit proposal `dev-commit` showed last in the session and the user has not answered: `dev-next` runs that command unchanged before it dispatches, and composes none of its own.
A declined proposal, a stale one and one with an unanswered warning about a secret are never run.
`false` restores dispatch without any commit.

## Commit on apply

`commit.auto_on_apply` in `dev/options.toml` is `"off"` (the default), `"task"` or `"group"`.
It lets `dev-apply-change` commit without asking: never with `off`, after every completed task with `task`, after every completed `## N.` group with `group`.
It changes when a session commits and never when it stops, which `apply.review` alone decides.
Whether it holds on the current branch is decided by `uv run dev/scripts/auto_commit.py`, which turns it `off` on `main`, `master` and a detached HEAD; skills read the mode from that script, never from the option itself.

## Changelog entry

A finished change leaves its entries in the project's `CHANGELOG.md`, written by `dev-archive-change` through `uv run dev/scripts/changelog.py <category> <entry>`, one invocation per entry.
A change is recorded by everything significant it did, not by one summary of it: a feature added, behavior changed, an option removed and a defect fixed are four entries in four Keep a Changelog categories under `## [Unreleased]`, and only a change with a single effect leaves a single entry.
The entries are the body of the archive commit, under the same categories, so the changelog and the history say the same thing.
The script owns the structure of the file, so no skill edits `CHANGELOG.md` by hand.

A project without a `CHANGELOG.md` keeps none: the script writes nothing, reports that, and archiving goes on.

## Reference links

`dev-links` gives the user reference links on the technology a task touches, for every skill, and stays off until `links.enabled` in `dev/options.toml` switches it on.
Once a skill has decided what it will do, and before it starts, check in order and stop at the first unmet item:

1. the session has a web search tool;
2. `links.enabled` in `dev/options.toml` is `true`;
3. the work ahead reaches the threshold `links.threshold_seconds` **and** touches a technology, standard or domain concept outside the project's own code;
4. no block was emitted in this turn, and none on the same topic in this session;
5. the turn does not end with a question to the user.

All five met: run `dev-links`, then continue the work without waiting for the user to reply.
A manual request, where the user asks `dev-links` for sources, bypasses item 2 and the threshold of item 3: the request is the consent those two stand in for, and everything else still applies, the other half of item 3 included.
Only the skill the user invoked applies this rule -- a skill invoked by another skill does not, and `dev-links` does not apply it to itself.
`dev-next` is the exception to that: it only dispatches, so the skill it hands the work to applies the rule as if the user had invoked it directly.
`dev-explore` and `dev-plan-change` never apply it, however long the work: each holds a dialogue with the user, and a link block would compete with that conversation.
`dev-status` and `dev-next` never apply it either: they report the state of a change or hand the work over, and finish before there is anything to read.
The rule never changes what work is done or in what order, never asks anything, and stays silent where it does not apply; links are never written from memory.
