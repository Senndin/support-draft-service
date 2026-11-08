#!/usr/bin/env python3

"""
Prints the commit a change started from -- the base of its `<base>..HEAD` window.
Usage: change_base.py <change-name>

The base is the parent of the commit that first added `dev/changes/<name>/.devskills.yaml`.
A change born in the root commit has no parent, so its base is the empty tree object,
which diffs as "every file added".

Skills take the base from here rather than working it out themselves: two descriptions
of this rule would sooner or later select two different windows of history, and the
window decides what gets reviewed and what gets written into an archive commit message.

The base lives in git history, not in the change directory, so an already archived
change still answers. `dev-archive-change` asks for it before moving the directory all
the same: a change without a base stops archiving while nothing has been moved yet.
"""

import sys

from utils import change_base_commit, change_dir, change_not_found, configure_output


def main() -> int:
    configure_output()

    if len(sys.argv) != 2:
        print("Usage: change_base.py <change-name>", file=sys.stderr)
        return 2

    change_name = sys.argv[1]

    base = change_base_commit(change_name)
    if base is not None:
        print(base)
        return 0

    # No base means one of two different things, and they need different answers:
    # a name that matches nothing, or a change whose directory exists but was never
    # committed. The directory is consulted only to tell them apart.
    target = change_dir(change_name)
    if not target.is_dir():
        print(change_not_found(change_name, target), file=sys.stderr)
        return 1

    print(f"Error: change '{change_name}' has no base commit yet.", file=sys.stderr)
    print(
        f"Nothing of it is committed: commit dev/changes/{change_name}/ first.",
        file=sys.stderr,
    )

    return 1


if __name__ == "__main__":
    sys.exit(main())
