#!/usr/bin/env python3

"""
Reports the automatic commit mode that holds for a `dev-apply-change` session started now.
Usage: auto_commit.py

Prints `branch: <name>` -- `branch: (detached HEAD)` on a detached HEAD, `branch:
(unknown)` when Git cannot name the branch at all -- and `auto_commit: <mode>`.
The mode is `commit.auto_on_apply` from `dev/options.toml`, except on `main`, on
`master`, on a detached HEAD and on a branch Git cannot read, where it is `off` and
stderr says why whenever the option asked for more. Any of those states means the
session only proposes commits.

The decision lives here and not in the skill: committing without asking on the
default branch is the one mistake this safeguard exists to prevent, and only a script
can be held to it by a test.
"""

import sys

from utils import configure_output, current_branch, detached_head, load_config

USAGE = "Usage: auto_commit.py"
OFF = "off"
DEFAULT_BRANCHES = ("main", "master")
DETACHED = "(detached HEAD)"
UNKNOWN = "(unknown)"


def effective_mode(mode: str, branch: str | None, detached: bool) -> tuple[str, str | None]:
    """The mode `mode` turns into on `branch`, and the warning that explains it, if any.

    `branch` is None on a detached HEAD (`detached` true) and on a branch Git could not
    read (`detached` false); both fail towards `off`. Only an option that asked for
    commits is worth a warning: with `off` nothing is lost, so a session on `master`
    with the default option stays silent. The warning is returned rather than printed,
    so the decision stays a pure function of its inputs.
    """

    if branch is not None and branch not in DEFAULT_BRANCHES:
        return mode, None

    if mode == OFF:
        return OFF, None

    where = branch or ("a detached HEAD" if detached else "a branch Git cannot read")
    warning = (
        f'Warning: commit.auto_on_apply = "{mode}" has no effect on {where}: '
        "commits are only proposed."
    )
    return OFF, warning


def main() -> int:
    configure_output()

    if len(sys.argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2

    mode = load_config()["commit"]["auto_on_apply"]
    branch = current_branch()
    detached = branch is None and detached_head()

    effective, warning = effective_mode(mode, branch, detached)
    if warning:
        print(warning, file=sys.stderr)

    print(f"branch: {branch or (DETACHED if detached else UNKNOWN)}")
    print(f"auto_commit: {effective}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
