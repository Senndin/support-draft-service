---
name: dev-links
description: |
  Give the user three reference links on the technology the task ahead touches, to read while the work runs.
  Use automatically at the start of a long step of another skill when the project enables it, or manually when the user asks for sources.
compatibility: Requires an agent with a web search tool; without one the skill is inert.
---

Hand the user a short block of external reading -- at most three links -- on the technology, standard or domain concept the task ahead touches.
This is output for the person waiting on a long step, not input for the agent: the pages are never opened, never quoted into the work, and never influence any decision of the calling skill.
Print the block before the work starts and continue without waiting for a reply.

**Input:** The task the calling skill has already understood and is about to perform. Do NOT analyze the task again -- the plan the caller has already made is the entire input.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Invocation

This skill runs in two ways. The rules for depersonalizing the query, choosing the links and formatting the block are identical in both; only the gating differs:

- **Automatically**, from the `Reference links` rule in `dev/AGENTS.md`. Both conditions must hold: the project has switched the skill on, and the work ahead passes both filters of **Estimating the Work Ahead**.
- **Manually**, when the user asks for sources on the task at hand. The enable switch and the duration threshold do NOT apply -- an explicit request is the consent those two stand in for. Every other rule still applies, depersonalization included.

## Source of Truth

Read the `[links]` options before anything else with `uv run dev/scripts/config.py links`: `links.enabled` decides whether this skill runs automatically, and `links.threshold_seconds` from which duration of the work ahead.
Never ask the user to switch the skill on.

## Preconditions

The gate is the `Reference links` rule of `dev/AGENTS.md`.
Read it there rather than from a copy: its checks and the skills it never fires for are normative exactly as that file writes them.
**Estimating the Work Ahead** below is only how the threshold check is judged.
In manual mode the switch and the threshold do not apply; every other check does.

When any check fails, produce nothing and say nothing about it.

## Estimating the Work Ahead

Both filters are judged from the plan the calling skill has **already** made. Do not perform any extra analysis to answer them.

**Filter 1 -- the cost band.** The band of the calling skill is the starting verdict. Bands, rather than seconds, so the table survives a change of threshold.

| Calling skill (the outer one) | Band |
|---|---|
| `dev-new-change`, `dev-commit`, `dev-refactor`, `dev-docs`, `dev-test` (targeted) | short |
| `dev-archive-change`, `dev-migrate-db`, `dev-review` (a single object) | about a minute |
| `dev-test` (full suite), `dev-review` (a whole change), `dev-extract-specs`, `dev-bugfix`, `dev-apply-change`, `dev-accept-change`, `dev-verify-change` | minutes |
| `dev-explore`, `dev-plan-change`, `dev-status`, `dev-next` | never triggers -- dialogue, report or dispatch |

`short` is up to about half a minute, `about a minute` is roughly 30-90 seconds, `minutes` is substantially more than a minute.
The filter passes when the lower bound of the band reaches `links.threshold_seconds`.

Each of these modifiers raises the verdict by one band: more than about five files to read before starting, a full test run in the plan, a whole artifact or specification to read, more than one file to edit, behavior to trace across modules, a technology this session has not touched yet.
One modifier lowers it by one band: everything needed is already in the context.

**Filter 2 -- is there anything to read.** Even above the threshold, skip when the task names no technology, standard, protocol, library or domain concept outside the project's own code.
Moving a directory, renaming a symbol and composing a commit message have none, however long they take.

**The tie rule:** when you cannot tell, treat the threshold as not reached.
A block that was skipped costs the user nothing; a block that was not worth reading costs them attention.
The bias toward under-triggering is deliberate.

## Depersonalizing the Query

Search for the general technology behind the task, never for the task itself.
Rewrite what the caller is doing into the topic a stranger would search for:

| The task at hand | The query |
|---|---|
| `import_orders.py` exits 0 on a malformed CSV row | `python csv error handling` |
| adding a UNIQUE index to the `orders` table in the payments migration | `mysql unique index migration` |
| the change `add-dev-links` reorganizes skill frontmatter | `yaml frontmatter conventions` |

Never put any of these into a query: file or directory paths, module, class or function names, text from specifications or change artifacts, change and branch names, issue numbers, product or client names, and code of any kind.

A query is 2-6 general words.
**If the topic cannot be phrased without a project-specific term, produce nothing at all.**

## Choosing the Links

Work down this ladder and stop as soon as it yields three worthy pages:

1. The official documentation of the technology.
2. The reference for the language, runtime or standard -- a PEP, MDN, an RFC, the standard itself.
3. A maintained, authoritative reference work.
4. A high-quality article, only when the first three yielded nothing.

Never link SEO listicles, content farms or paywalled pages.

All three links cover **one** topic -- the hardest part of the task -- rather than one link each for three technologies the task merely mentions.
Fewer than three worthy pages: show the ones there are. None: show nothing.

## Guardrails & Constraints

- **Only URLs that appeared verbatim in the search results.** Never construct, guess, extend, shorten, "fix" or complete a URL, and never add anchors or version segments to one. A plausible dead link destroys trust in the whole feature.
- **Never write a link from memory** -- least of all when there is no search tool. Without search, this skill produces nothing.
- Prefer stable documentation roots over blog posts, and `/stable/` over a pinned version, unless the project itself pins that version.
- Pages are not opened -- that would consume exactly the time this skill saves. Annotations must therefore stay honest: "the official reference for X", never "the answer to your problem".
- What is found is **output for the user, not input for the agent**: it is never cited into the work and never changes a decision of the calling skill.
- Never use this skill to reach a source another skill is forbidden to fetch.
- One round of search, no page fetches, no follow-up queries, no snippets quoted into the context. Discard the results once three links are picked.
- The block is at most five lines, and never repeats itself: one per turn, one per topic per session.
- Never change what the calling skill does, in what order it does it, or ask the user anything. Where this skill does not apply, it stays silent.

## Expected Output Formatting

```md
**Reference reading for this task: {topic, generalized}**

- [{page title}]({url}) -- {what it is good for, one line}
- [{page title}]({url}) -- {what it is good for, one line}
- [{page title}]({url}) -- {what it is good for, one line}
```

Write the heading and the annotations in the project's dialog language, and spell each page title exactly as the page itself spells it.
Print the block, then start the work in the same turn.
