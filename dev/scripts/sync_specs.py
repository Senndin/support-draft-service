#!/usr/bin/env python3

"""
Compares the spec files a change actually touched with the features its proposal declares.
Usage: sync_specs.py <change-name>

Report lines:
  missing-new / missing-changed  spec file touched but not declared -- add a bullet
  misplaced                      declared under the wrong subsection -- move the bullet
  undeclared-file                touched file that is not a `dev/specs/<domain>/spec.md`
  declared-unwritten             declared feature whose spec was never written or changed
  unresolved-bullet              declared bullet whose link has no target -- fix the link
  non-spec-bullet                bullet that names no spec at all -- report only
  in-sync                        count of declared entries that match reality

The script never edits `proposal.md`: it settles classification and placement, while
the bullet's prose is written from the spec's own content by the calling skill.
A report whose only line is `in-sync` means there is nothing to do.
"""

import sys

from utils import (
    CANONICAL_RE,
    PROPOSAL_TEMPLATE,
    TEMPLATES_PATH,
    change_dir,
    change_not_found,
    configure_output,
    declared_features,
    repo_root,
    spec_changes,
    template_section_headings,
)


def main() -> int:
    configure_output()

    if len(sys.argv) != 2:
        print("Usage: sync_specs.py <change-name>", file=sys.stderr)
        return 2

    change_name = sys.argv[1]
    target = change_dir(change_name)
    if not target.is_dir():
        print(change_not_found(change_name, target), file=sys.stderr)
        return 1

    proposal = target / "proposal.md"
    if not proposal.is_file():
        print(f"Error: no proposal.md in {target}", file=sys.stderr)
        print("Write the proposal before syncing its Features section.", file=sys.stderr)
        return 1

    for role in ("New features", "Changed features"):
        if not template_section_headings(PROPOSAL_TEMPLATE, role):
            print(
                f"Error: {TEMPLATES_PATH}/{PROPOSAL_TEMPLATE} marks no '{role}' heading.",
                file=sys.stderr,
            )
            return 1

    actual = spec_changes(change_name, repo_root())
    declared, duplicates, unresolved, non_spec = declared_features(proposal)

    report: list[str] = []
    in_sync = 0

    for path in sorted(actual):
        if path in declared:
            continue
        if CANONICAL_RE.match(path):
            report.append(f"missing-{actual[path]}: {path}")
        else:
            report.append(f"undeclared-file: {path}")

    for path in sorted(declared):
        if path in duplicates:
            continue
        status = declared[path]
        if path not in actual:
            report.append(f"declared-unwritten: {path}")
        elif actual[path] != status:
            report.append(
                f"misplaced: {path} (declared {status}, actually {actual[path]})"
            )
        else:
            in_sync += 1

    for path in sorted(set(duplicates)):
        seen = actual.get(path, "untouched")
        report.append(
            f"misplaced: {path} (declared in both subsections, actually {seen})"
        )

    for bullet in unresolved:
        report.append(f"unresolved-bullet: {bullet}")

    for bullet in non_spec:
        report.append(f"non-spec-bullet: {bullet}")

    for line in report:
        print(line)
    print(f"in-sync: {in_sync} entry(-ies)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
