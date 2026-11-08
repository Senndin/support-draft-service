#!/usr/bin/env python3

"""
Tracks the autonomy budget of a `dev-apply-change` session in review mode "group" or
"change".
Usage: apply_session.py start|check <change-name>

`start` stamps `apply_started` into `dev/changes/<name>/.devskills.yaml`, replacing
the stamp of an earlier session. `check` measures the time since that stamp against
`apply.time_limit` from `dev/options.toml`. Both modes use the same two commands: the
skill decides when to call `check` -- after a task in "group" mode, after a group in
"change" mode -- so the script never needs to know which mode is running.

The clock lives here and not in the skill: an agent has no reliable sense of elapsed
time, and a budget it estimates for itself is a budget it can talk itself past.
"""

import math
import sys
from datetime import datetime, timedelta

from utils import (
    change_dir,
    change_not_found,
    configure_output,
    load_config,
    manifest_values,
    set_manifest_value,
)

MANIFEST = ".devskills.yaml"
STARTED_KEY = "apply_started"
USAGE = "Usage: apply_session.py start|check <change-name>"


def now() -> datetime:
    """The current local time with its UTC offset; the tests replace it."""

    return datetime.now().astimezone()


def start(change_name: str) -> int:
    """Stamp the start of a session and print when its budget runs out."""

    limit = load_config()["apply"]["time_limit"]
    started = now().replace(microsecond=0)
    deadline = started + timedelta(minutes=limit)

    set_manifest_value(change_dir(change_name) / MANIFEST, STARTED_KEY, started.isoformat())

    # No review mode here: the skill may run in "group" or "change" mode on its own
    # input while the options still say "task", and the file's value would contradict
    # the session.
    print(f"started: {started.isoformat()}")
    print(f"deadline: {deadline.isoformat()}")

    return 0


def check(change_name: str) -> int:
    """Print the time spent and left in the session, and whether the budget is gone."""

    manifest = change_dir(change_name) / MANIFEST
    stamp = manifest_values(manifest).get(STARTED_KEY, "")

    if not stamp:
        print(f"Error: change '{change_name}' has no apply session.", file=sys.stderr)
        print(f"Run `apply_session.py start {change_name}` first.", file=sys.stderr)
        return 1

    try:
        started = datetime.fromisoformat(stamp)
    except ValueError:
        print(
            f"Error: {STARTED_KEY} '{stamp}' in {manifest} is not an ISO-8601 timestamp.",
            file=sys.stderr,
        )
        print(f"Run `apply_session.py start {change_name}` again.", file=sys.stderr)
        return 1

    if started.tzinfo is None:
        # A stamp edited by hand may lose its offset; read it as local time.
        started = started.astimezone()

    limit = load_config()["apply"]["time_limit"] * 60
    # A stamp in the future (a skewed clock, a hand edit) counts as just started.
    elapsed = max(0.0, (now() - started).total_seconds())
    remaining = max(0.0, limit - elapsed)

    # Elapsed rounds down and remaining rounds up, so `remaining: 0 min` appears
    # exactly when `expired: yes` does.
    print(f"elapsed: {int(elapsed // 60)} min")
    print(f"remaining: {math.ceil(remaining / 60)} min")
    print(f"expired: {'yes' if elapsed >= limit else 'no'}")

    return 0


COMMANDS = {"start": start, "check": check}


def main() -> int:
    configure_output()

    if len(sys.argv) != 3 or sys.argv[1] not in COMMANDS:
        print(USAGE, file=sys.stderr)
        return 2

    command, change_name = sys.argv[1], sys.argv[2]

    target = change_dir(change_name)
    if not target.is_dir():
        print(change_not_found(change_name, target), file=sys.stderr)
        return 1

    return COMMANDS[command](change_name)


if __name__ == "__main__":
    sys.exit(main())
