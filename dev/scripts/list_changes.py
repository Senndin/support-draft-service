#!/usr/bin/env python3

"""
Lists active DevSkills changes (excluding the archive), most recently modified first.
Usage: list_changes.py
"""

import sys

from utils import (
    ACTIVE_CHANGES_HEADER,
    NO_ACTIVE_CHANGES,
    active_changes,
    configure_output,
)


def main() -> int:
    configure_output()

    if len(sys.argv) != 1:
        print("Usage: list_changes.py", file=sys.stderr)
        return 2

    changes = active_changes()
    if not changes:
        print(NO_ACTIVE_CHANGES)
        return 0

    print(ACTIVE_CHANGES_HEADER)
    for path in changes:
        print(f"  - {path.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
