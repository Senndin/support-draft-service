---
name: dev-migrate-db
description: |
  Write forward (up) and rollback (down) SQL migration scripts by hand.
  Use when a change modifies the database schema and the migration is authored manually rather than generated.
---

Write a matched pair of hand-authored SQL migration scripts: a forward script that applies a schema modification and a rollback script that undoes it exactly.

**Input:** A description of the schema change, or the DB migration tasks of an active change.

**Context:** Read `dev/AGENTS.md` before anything else, unless a calling skill already has.

## Invocation

This skill runs in two ways, and the SQL rules below are identical in both:

- **Directly.** The user asks for a migration. Establish the schema change from their description and the current schema, and place the scripts where the project's conventions put them.
- **From `dev-apply-change`.** A `## N. DB Migrations` task group has just been completed. Consolidate the statements that group produced and write them to `dev/changes/{name}/db-migration.up.sql` and `dev/changes/{name}/db-migration.down.sql`.
  When the change has several such groups, append each forward block to the `.up.sql` file and **prepend** each rollback block to the `.down.sql` file, so that rollback happens in reverse chronological order.

If the caller is unclear, ask before writing any file -- the two paths differ only in where the scripts land, and writing to the wrong place is the one mistake this skill can make silently.

## Source of Truth

The project's documentation defines the concrete rules: which SQL dialect to write, where migration files live, how they are named, and how forward and rollback scripts are paired.
File placement is the exception when invoked from `dev-apply-change`, which fixes the two paths above.
Read the `Database migrations` section of the project root `AGENTS.md`, together with any conventions it links to.
Follow those over any habit or example below.

If the project documents none of this, infer the dialect and layout from its configuration, its existing migrations, or a schema dump, state what you settled on and why, and suggest the user document it in `AGENTS.md`.

## Execution Steps

1. **Establish the Schema Change.**
   - If the work belongs to an active change, read the **DB Migrations** tasks in `dev/changes/{name}/tasks.md` and `design.md` (if present) to determine the exact modification required.
   - When invoked from `dev-apply-change`, gather every statement the completed task group produced and treat them as one consolidated change.
   - If the intent is ambiguous, ask the user rather than guessing at column types, nullability, or defaults.

2. **Inspect the Current Schema.**
   - Consult the existing schema (dump, migration history, or models) for the current definition of every table you touch.
   - Note the existing names of indexes and constraints -- the rollback needs them to drop the right objects.

3. **Write the Forward Migration.**
   - Apply the change in dependency order: create tables before the indexes and constraints that reference them.

4. **Write the Rollback Migration.**
   - Undo each forward statement in reverse order.
   - Drop dependent objects (indexes, constraints) before the tables they belong to.

5. **Deliver the Scripts.**
   - When invoked from `dev-apply-change`, write both files at the paths above, appending and prepending as described in **Invocation**.
   - When invoked directly, output both scripts; write them to files only where the project's conventions place them.
   - Either way, state which tables and objects each script touches.

## Examples

For a worked forward/rollback pair, read `references/mysql.md`.
It is written in one specific dialect and is illustrative only; never carry its syntax into a project that uses a different one.

## Guardrails & Constraints

- Write in the dialect the project actually uses, and never mix in syntax from another one.
- Wrap the whole of each script in a single transaction, using that dialect's syntax.
- Do NOT add comments to the SQL; the statements must be self-explanatory on their own.
- The rollback MUST undo exactly what the forward migration does -- no more, no less.
- Keep each pair to one logical change; never fold unrelated schema modifications into the same migration.
- Never overwrite an existing `.up.sql` or `.down.sql` -- follow the append/prepend rule in **Invocation**.
- Limit the statements to the tables, columns, constraints, and indexes the change actually needs.
- When referencing an existing database dump, omit the extra syntax it carries:
  - directives emitted by the dump tool;
  - storage engine declarations;
  - default character set and collation definitions;
  - auto-increment or sequence seed values;
  - constraints and attributes unrelated to the logical change being made.
