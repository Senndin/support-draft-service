#!/usr/bin/env python3

"""
Reports the artifact status of a DevSkills change, or of every active change.
Usage: status.py [<change-name>]
"""

import re
import sys
from pathlib import Path

from utils import (
    ACTIVE_CHANGES_HEADER,
    FENCE_RE,
    NO_ACTIVE_CHANGES,
    PENDING,
    SPECS_PATH,
    acceptance_scenarios,
    active_changes,
    change_dir,
    change_not_found,
    changed_spec_files,
    configure_output,
    declared_features,
    manifest_values,
)

# The same bullet markers the Features parser in `utils` accepts, so one artifact is
# not read two ways.
TASK_RE = re.compile(r"^\s*[-*+]\s+\[([ xX])\](?:\s|$)")


def task_counts(tasks_file: Path) -> tuple[int, int]:
    """Count the checkbox tasks in `tasks.md`, as `(done, total)`.

    A checklist inside a fenced block is an example of a task, not a task, so the
    fenced blocks are skipped.
    """

    if not tasks_file.exists():
        return (0, 0)

    done = total = 0
    fenced = False
    for line in tasks_file.read_text(encoding="utf-8").splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue

        task = TASK_RE.match(line)
        if not task:
            continue

        total += 1
        if task.group(1) != " ":
            done += 1

    return done, total


def unwritten_specs(proposal: Path, touched: list[str]) -> list[str]:
    """The specs the proposal declares that the change has not touched yet.

    The declaration is read by the parser `sync_specs.py` reports with, so the two
    scripts cannot disagree on what a Features bullet names. A proposal that
    declares nothing owes nothing: a refactoring or a chore may need no
    specification, and waiting for a spec edit would leave such a change stuck.
    The same holds when the template marks no Features role to read the section
    by -- that is a template error, and `sync_specs.py` is the one that reports it.
    """

    if not proposal.is_file():
        return []

    declared, *_ = declared_features(proposal)

    return [path for path in declared if path not in touched]


def next_step(
    has_proposal: bool,
    unwritten: list[str],
    has_design: bool,
    has_tasks: bool,
    done_tasks: int,
    total_tasks: int,
    accepted: bool,
    verified: bool,
) -> str:
    """Name the workflow step the change is waiting for."""

    if not has_proposal:
        return "proposal.md"
    if unwritten:
        return "specs"
    if not has_design:
        return "design.md"
    # A `tasks.md` that lists no task is a file, not a plan: the step that fills it
    # in is unfinished, and treating it as done would send the workflow on to verify
    # work that was never implemented.
    if not has_tasks or total_tasks == 0:
        return "tasks.md"
    if done_tasks < total_tasks:
        return "implement remaining tasks"
    # Acceptance is checked before the verdict on purpose: a change created before
    # this step may already carry `verify: clean`, and it still owes its acceptance.
    if not accepted:
        return "acceptance.md"
    # The report file is saved only with the user's consent, so its presence says
    # nothing about the outcome. The manifest carries the verdict itself: a clean
    # run is what opens archiving, and a blocked one keeps the change here.
    if not verified:
        return "verify-report.md"
    return "archive"


def report(change_name: str) -> None:
    """Print the artifact block of one change, ending with its next step."""

    target = change_dir(change_name)

    has_proposal = (target / "proposal.md").exists()
    has_design = (target / "design.md").exists()
    has_tasks = (target / "tasks.md").exists()
    has_verify_report = (target / "verify-report.md").exists()

    specs = changed_spec_files(change_name)
    unwritten = unwritten_specs(target / "proposal.md", specs)
    done_tasks, total_tasks = task_counts(target / "tasks.md")
    scenarios = acceptance_scenarios(target / "acceptance.md")
    verdict = manifest_values(target / ".devskills.yaml").get("verify", "")
    # A missing file owes the step; a file that lists no scenario has completed it.
    with_result = [result for _, result in scenarios or [] if result != PENDING]
    accepted = scenarios is not None and len(with_result) == len(scenarios)

    print(f"Change: {change_name}")
    print(f"  proposal.md: {'done' if has_proposal else '-'}")
    print(f"  specs: {len(specs)} file(s) changed in {SPECS_PATH}/")
    for spec in specs:
        print(f"    - {spec}")
    print(f"  design.md: {'done' if has_design else '-'}")
    if has_tasks and total_tasks:
        print(f"  tasks.md: done ({done_tasks}/{total_tasks} tasks complete)")
    elif has_tasks:
        print("  tasks.md: written, but it lists no tasks")
    else:
        print("  tasks.md: -")
    if scenarios:
        print(
            f"  acceptance.md: done ({len(with_result)}/{len(scenarios)}"
            " scenarios with a result)"
        )
    elif scenarios is not None:
        print("  acceptance.md: written, with no scenario for a person to run")
    else:
        print("  acceptance.md: -")
    print(f"  verify-report.md: {'done' if has_verify_report else '-'}")
    print(f"  verification: {verdict or 'not run'}")

    step = next_step(
        has_proposal,
        unwritten,
        has_design,
        has_tasks,
        done_tasks,
        total_tasks,
        accepted,
        verdict == "clean",
    )
    print(f"\nNext: {step}")


def main() -> int:
    configure_output()

    if len(sys.argv) > 2:
        print("Usage: status.py [<change-name>]", file=sys.stderr)
        return 2

    if len(sys.argv) == 2:
        change_name = sys.argv[1]
        target = change_dir(change_name)

        if not target.is_dir():
            print(change_not_found(change_name, target), file=sys.stderr)
            return 1

        report(change_name)
        return 0

    changes = active_changes()
    if not changes:
        print(NO_ACTIVE_CHANGES)
        return 0

    print(ACTIVE_CHANGES_HEADER)
    for path in changes:
        print()
        report(path.name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
