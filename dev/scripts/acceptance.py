#!/usr/bin/env python3

"""
Lists the acceptance scenarios of a change, one per line, with the result the user reported.
Usage: acceptance.py <change-name>

Each line reads `<result>: <heading text>`, where the result is `passed`, `failed`,
`skipped`, or `pending` for a scenario the user has not reported on yet.

`status.py` prints only how many scenarios have a result, while `dev-accept-change`
needs each one to find where its walk resumes and `dev-verify-change` needs each one to
tell a failure from a skip. Both read through the one parser in `utils`, so the
tally and this listing cannot disagree.
"""

import sys

from utils import acceptance_scenarios, change_dir, change_not_found, configure_output


def main() -> int:
    configure_output()

    if len(sys.argv) != 2:
        print("Usage: acceptance.py <change-name>", file=sys.stderr)
        return 2

    change_name = sys.argv[1]
    target = change_dir(change_name)
    if not target.is_dir():
        print(change_not_found(change_name, target), file=sys.stderr)
        return 1

    scenarios = acceptance_scenarios(target / "acceptance.md")
    if scenarios is None:
        print(f"No acceptance.md in dev/changes/{change_name}/.")
        return 0

    for heading, result in scenarios:
        print(f"{result}: {heading}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
