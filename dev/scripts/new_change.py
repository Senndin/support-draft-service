#!/usr/bin/env python3

"""
Scaffolds a new DevSkills change directory.
Usage: new_change.py <kebab-case-name>
"""

import re
import sys
from datetime import date

from utils import change_dir, configure_output, devskills_version

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def main() -> int:
    configure_output()

    if len(sys.argv) != 2:
        print("Usage: new_change.py <kebab-case-name>", file=sys.stderr)
        return 2

    change_name = sys.argv[1]
    if not KEBAB_RE.fullmatch(change_name):
        print(
            f"Error: '{change_name}' is not valid kebab-case (lowercase letters, digits, single hyphens).",
            file=sys.stderr,
        )
        return 1

    target = change_dir(change_name)
    if target.exists():
        print(
            f"Error: change '{change_name}' already exists at {target}.", file=sys.stderr
        )
        # The change may stand at any step, from its proposal to archiving, and
        # dev-next is the one skill that continues it from wherever it is.
        print("Use the dev-next skill instead.", file=sys.stderr)
        return 1

    # The version the change descends from, recorded as provenance: read from the
    # frontmatter of `dev/AGENTS.md` and simply left out when it is not there, since
    # nothing about creating a change depends on it and an invented number would
    # outlive this run in the archive.
    version = devskills_version()

    target.mkdir(parents=True)
    with (target / ".devskills.yaml").open("w", encoding="utf-8") as file:
        if version:
            file.write(f"devskills_version: {version}\n")
        file.write(f"created: {date.today().isoformat()}\n")

    print(f"Created change '{change_name}':")
    print(f"  dev/changes/{change_name}/")
    if not version:
        print("  Note: the DevSkills version could not be read from dev/AGENTS.md.")
    print("Next: write proposal.md in this directory.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
