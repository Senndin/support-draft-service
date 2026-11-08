---
name: dev-commit
description: |
  Generate a Conventional Commits message and the ready git command for the work just finished.
  Use when changes are ready to be committed, either standalone or at the end of a change-workflow skill.
---

Turn the work that is already in the working tree into a commit message and the exact git command that records it.

This skill proposes a commit; it does not decide to make one.
The command is shown first and runs only after the user accepts it -- except under `commit.auto_on_apply`, where the option is that acceptance, given in advance.

**Input:** An optional scope -- the files the work just finished produced. If omitted, the scope is everything uncommitted in the working tree.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Invocation

This skill runs in three ways, and the message generation rules below are identical in all of them.
Only the scope, the shape of the message and who agrees to the commit differ:

- **Directly.** The user asks for a commit. The scope is everything uncommitted in the working tree, and the message is a single line.
- **From a change-workflow skill.** The caller has already selected the change and names the work it just finished. When it also names the files that work produced, the scope is those files, not the whole tree. When it names none, the scope is everything uncommitted, exactly as in the direct mode. The caller may also require a body -- only `dev-archive-change` does, and it hands over the entries that make it up.
- **From `dev-apply-change` under `commit.auto_on_apply`.** The caller names the files of the task or group it just finished, and they are the scope. Every step runs as in the mode above, but nothing asks the user: the steps marked *Automatic* say what replaces each question, and the command runs without an answer. The result goes back to the caller, which decides what happens next.

## Execution Steps

1. **Establish the Scope.**
   - Run `git status --porcelain -uall` for the list of uncommitted files, and `git diff` plus `git diff --staged` for their content.
   - The `-uall` matters: without it git collapses a new directory into a single entry, and neither the file count for the header nor the scope comparison below can be made from that.
   - When a change-workflow skill named the files its step produced, narrow that list to them; everything else in the tree stays out of the scope.
   - When no files were named, the whole list is the scope, whichever mode the skill runs in.
   - If nothing is uncommitted, report that there is nothing to commit and stop. Ask nothing.

2. **Load the Commit Rules.**
   - Read the `Commit style` section of the project root `AGENTS.md`: the message language, the allowed types, whether a scope is used, the issue-number template, the maximum subject length, and the `Co-authorship trailer` field, `yes` or `no`.
   - If the section is absent, default to Conventional Commits, in English, with no issue number, a 72-character subject and no co-authorship trailer.
   - Treat a field still holding its `{placeholder}` as unset and fall back to the same default for that field alone -- a project that has not filled the template in yet has not chosen anything, and guessing what the placeholder meant would put an invented convention into its history. Never ask the user to fill the section in; that is their decision, not a precondition for a commit.

3. **Resolve the Issue Number.**
   - Skip this step entirely when the rules carry no issue-number template -- there is nowhere to put a number, so looking for one and asking about it only wastes the user's turn.
   - A template that holds no `{issue}` placeholder, such as `{type}: {subject}`, is no template: it is how a project that does not track issues says so.
   - Try each source in order and stop at the first hit: the branch name (`git rev-parse --abbrev-ref HEAD`), then the change directory's `notes.md`, `proposal.md` and `.devskills.yaml`, then a single question to the user.
   - Read a number out of the branch name only when it stands on its own -- preceded by `#`, `-`, `/` or the start of the name, as in `123-add-auth`, `feature/123-add-auth` or `PROJ-123`. A digit inside a word is part of that word, not an issue: `add-oauth2-login` carries no issue number.
   - Skip the branch name entirely when it equals the name of an active change. Under the DevSkills branch convention the branch *is* the change name, so any number in it names the change, not an issue.
   - Ask at most once, and offer skipping as an explicit option.
   - If the user skips, compose the message without a number.
   - *Automatic:* the question is skipped; with no number from the branch or the change, compose the message without one.
   - **Never invent an issue number.**

4. **Compose the Message.**
   - Choose the type from what the diff actually does, not from what the work intended.
   - Write the subject in the imperative mood, with no trailing period, within the maximum length from the rules.
   - Insert the issue number using the template from the rules, if there is one.
   - Write a single line, except when invoked from `dev-archive-change` -- see **Archive Body**. The co-authorship trailer, when there is one, is not part of that line but an `-m` of its own -- see **Co-authorship Trailer**.

5. **Build the Command.**
   - Stage by the rule in **Staging** below, then `git commit -m "{message}"`.
   - In the `dev-archive-change` mode, add the body as a second `-m` carrying one multi-line argument.
   - Add the co-authorship trailer only as **Co-authorship Trailer** below describes.
   - Do not use a heredoc: it does not work in PowerShell, and the command must be copyable into either shell.

6. **Present and Offer to Run.**
   - Output the command in a fenced `bash` block and ask the user whether to run it.
   - Run it only after an explicit yes.
   - With `commit.auto_on_next` on, invoking `dev-next` is the same yes, as `Commit on next` in `dev/AGENTS.md` states.
   - *Automatic:* show the command, run it without asking, and report ``Committed: `{the commit command}` -> {short hash} {subject}``. If the commit fails -- a hook rejects it, git reports an error -- return git's error to the caller as it is, with no retry and no edit to the command.

## Staging

The goal is that nothing outside the scope rides into the commit.
The number of files does not affect that goal, so the command does not have to list every path.

Apply the rules top down; the first one that fits wins:

1. **The whole scope is everything uncommitted.** Compare the scope against `git status --porcelain -uall`; if they match, use `git add -A` and name in the header how many files that stages.
2. **The scope lines up with whole directories.** Use the smallest set of pathspecs that covers the scope and **only** the scope, for example `git add .agents/skills/dev-commit dev/AGENTS.md`. A directory is usable as a pathspec only when no uncommitted file inside it lies outside the scope.
3. **Otherwise, explicit paths**, split across several `git add` lines when that groups them meaningfully.
4. **More than about ten pathspecs that will not collapse.** That is a sign the scope is too broad: show the files grouped by directory, say so, and ask whether to make one commit or several -- generate a separate command for each. *Automatic:* the caller has already bounded the scope to one task or group, so make one commit with explicit paths and ask nothing.

A file that mixes in-scope edits with unrelated ones is **not** split into hunks.
Name that file and ask the user what to do with it.
*Automatic:* commit nothing, and return the file and the reason to the caller; the same holds for a file that looks like a secret.

The file list belongs in the header, not in the command -- a long list must not make the command unreadable.

## Archive Body

Apart from the co-authorship trailer, this is the only mode with a body, and the body is not this skill's to write.

The body is the entries the caller hands over, each under its Keep a Changelog category and already in the message language.
Do not look for them in `CHANGELOG.md`: a project may keep none, and the body exists either way.

Take the entries as they are handed over.
Never derive a body from the history, the task list or the specifications, and never add, drop or re-word an entry.
If the caller asked for a body and handed over no entries, say so and stop rather than composing one here.

Lay the entries out under their categories, in the order they were handed over, listing only the categories that are not empty:

```text
Added:
- dev-commit skill generating a Conventional Commits message and the ready git command
- Commit style section in the project root AGENTS.md as its source of truth

Changed:
- Every change-workflow skill now ends by offering to review and commit the work
```

A multi-line `-m` argument in double quotes is read correctly by both bash and PowerShell, but only while the text contains no double quote, dollar sign, backtick or backslash.
That is the one thing this skill changes in an entry: drop the backticks around file and skill names, and remove any other of those characters with the smallest edit that keeps the sentence.
Use one `-m` for the whole body: splitting it across several `-m` flags turns each into its own paragraph and breaks the list.

## Co-authorship Trailer

An agent's environment may ask for a line naming the agent on every commit it records, such as `Co-Authored-By: Claude <noreply@anthropic.com>`, sometimes with a "Generated with" line beside it.
Whether the project's history carries it is decided by the `Co-authorship trailer` field of `Commit style`, and by nothing else: the project root `AGENTS.md` is the user's own instruction for this project, so it wins over the environment's.

- **`no`, a missing field, or a placeholder.** The command carries no co-authorship trailer and no "Generated with" line, whatever the environment asks. Say nothing about the omission; the message is simply the one the rules describe.
- **`yes`.** Append the trailer exactly as the environment provides it, as the last `-m` argument -- after the body in the `dev-archive-change` mode. When the environment provides none, append nothing: a trailer is never invented, and its wording is never changed.

The trailer follows the quoting rule of **Archive Body**, so the command still runs unchanged in bash and PowerShell; a usual `Co-Authored-By: Name <email>` line already does.

## Guardrails & Constraints

- Never run `git commit` without the user's explicit consent -- the command is a proposal until they accept it. The one exception is the invocation from `dev-apply-change` under `commit.auto_on_apply`, whose option is that consent; it never extends to any other caller.
- Never `git push`, create, switch or delete a branch, amend, rebase, reset or revert -- this skill only records work that already exists.
- Never stage a file outside the scope of the work just finished -- an unrelated edit must not ride along on someone else's commit. `git add -A` is allowed only after confirming against `git status --porcelain -uall` that the whole working tree *is* the scope.
- Warn before staging a file that looks like a secret (`.env`, `*.pem`, `*.key`, credential paths) and stage it only if the user insists. An automatic invocation never stages one: there is no user to insist.
- Never bypass hooks (`--no-verify`) or signing -- a project that configured them wants them.
- Never invent an issue number; a message without one is better than a message pointing at the wrong issue.
- Write a one-line message with no body, except when invoked from `dev-archive-change` and for the co-authorship trailer.
- Add a co-authorship trailer only when `Commit style` sets `Co-authorship trailer` to `yes`, and then only the one the agent's environment provides -- never because the environment asks for it, and never one of your own.
- Never compose the archive body: it is the entries `dev-archive-change` handed over, changed only where a character would break the command.
- The commit-message language comes from the project root `AGENTS.md`, not from the artifact language -- commits are Git history, not artifacts.

## Expected Output Formatting

````md
## Ready to Commit

**Change:** {change-name}
**Files:** {N} — {the list, or collapsed by directory when there are many}

```bash
git add {pathspecs per the Staging rule}
git commit -m "{message}"
```

Review the changes and tell me whether to run this command.
````

Drop the `**Change:**` line when the skill was invoked directly and no change is involved.

In the automatic invocation the header and the command are the same, the closing question gives way to the result, and the caller takes it from there:

````md
## Committing

**Change:** {change-name}
**Files:** {N} — {the list}

```bash
git add {pathspecs per the Staging rule}
git commit -m "{message}"
```

{Committed: `{the commit command}` -> {short hash} {subject} | Not committed: {the file} -- {looks like a secret | mixes in unrelated edits} | Commit failed: {git's error}}
````

On `Not committed` the command block is left out, since no command was going to run.
The heading is never `Ready to Commit`: nothing here waits for an answer, so `dev-next` must not find a proposal in it.

With `Co-authorship trailer` set to `yes` and a trailer provided by the environment, it is the last argument of the command:

```bash
git commit -m "{message}" -m "{the trailer, as the environment provides it}"
```

In the `dev-archive-change` mode the header is the same, and only the command carries the body:

```bash
git add {pathspecs per the Staging rule}
git commit -m "{one-line subject}" -m "{the entries handed over, under their categories}"
```

Staging is not special in this mode: an archive move is usually the only uncommitted work in the tree, so rule 1 applies and the command is `git add -A`.
Both sides of the move -- the new `dev/changes/archive/{date}-{name}/` and the emptied `dev/changes/{name}/` -- must end up staged, whichever rule wins; a commit that records the additions but not the deletions leaves the change sitting in two places at once.
