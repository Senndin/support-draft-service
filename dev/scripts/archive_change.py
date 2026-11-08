#!/usr/bin/env python3

"""
Moves a completed change into the archive under its archival date.
Usage: archive_change.py <change-name>
"""

import shutil
import sys
from datetime import date

from utils import (
    ARCHIVE_DIR,
    change_dir,
    change_not_found,
    changes_dir,
    configure_output,
)


def main() -> int:
    configure_output()

    if len(sys.argv) != 2:
        print("Usage: archive_change.py <change-name>", file=sys.stderr)
        return 2

    change_name = sys.argv[1]

    source = change_dir(change_name)
    if not source.is_dir():
        print(change_not_found(change_name, source), file=sys.stderr)
        return 1

    archived = date.today().isoformat()

    archive_dir = changes_dir() / ARCHIVE_DIR
    target = archive_dir / f"{archived}-{change_name}"
    if target.exists():
        print(f"Error: archive target already exists: {target}", file=sys.stderr)
        print(
            "Rename the existing archive before archiving this change.",
            file=sys.stderr,
        )
        return 1

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    print(f"Archived '{change_name}' -> dev/changes/archive/{archived}-{change_name}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
