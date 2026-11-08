#!/usr/bin/env python3

"""
Lists the spec files a change touched, committed ones included, with their status.
Usage: changed_specs.py [<change-name>]

Without a change name only the working tree is inspected.
With one, the listing also covers what the change committed since its base commit.
"""

import sys

from utils import SPECS_PATH, configure_output, spec_changes


def main() -> int:
    configure_output()

    if len(sys.argv) > 2:
        print("Usage: changed_specs.py [<change-name>]", file=sys.stderr)
        return 2

    change_name = sys.argv[1] if len(sys.argv) == 2 else None

    specs = spec_changes(change_name)
    print(f"{len(specs)} spec file(s) changed in {SPECS_PATH}/:")
    for path in sorted(specs):
        print(f"  - {path} [{specs[path]}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
