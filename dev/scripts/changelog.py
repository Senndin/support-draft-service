#!/usr/bin/env python3

"""
Adds the entry of a finished change under `## [Unreleased]` of the project CHANGELOG.
Usage: changelog.py <category> <entry>

The agent chooses the category and the wording; the file structure belongs here, so
that a Keep a Changelog file keeps its shape whoever writes into it. A project
without a `CHANGELOG.md` is not a project that lost one: the script says so and
succeeds, because archiving a change must not depend on a file the project never had.
"""

import sys
from pathlib import Path

from utils import HEADING_RE, configure_output, repo_root

CHANGELOG_PATH = "CHANGELOG.md"
UNRELEASED = "[Unreleased]"

# The categories of Keep a Changelog, in the order the format lists them: a category
# created here is inserted at its place in this order, not appended where it happens
# to be needed first.
CATEGORIES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")

SECTION_LEVEL = 2
CATEGORY_LEVEL = 3

USAGE = f"Usage: changelog.py <{'|'.join(CATEGORIES)}> <entry>"


def section_range(
    lines: list[str], title: str, level: int = SECTION_LEVEL
) -> tuple[int, int] | None:
    """Return the `[start, end)` line range of the section titled `title`, or None.

    `start` is the heading line itself and `end` the first heading of the same level
    or higher after it, so the range covers the whole body including its blank lines.
    The release build imports this to find `## [Unreleased]`, which is why the lookup
    lives in one place rather than in both scripts.
    """

    wanted = title.strip().casefold()

    start: int | None = None
    for index, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if not heading:
            continue

        depth = len(heading.group(1))
        if start is None:
            if depth == level and heading.group(2).strip().casefold() == wanted:
                start = index
        elif depth <= level:
            return start, index

    return None if start is None else (start, len(lines))


def _body_end(lines: list[str], start: int, end: int) -> int:
    """The index just after the last non-blank line of `lines[start:end]`."""

    for index in range(end - 1, start - 1, -1):
        if lines[index].strip():
            return index + 1

    return start


def _categories(lines: list[str], start: int, end: int) -> list[tuple[int, str]]:
    """The `(line, name)` of every category heading inside the section."""

    found: list[tuple[int, str]] = []
    for index in range(start, end):
        heading = HEADING_RE.match(lines[index])
        if heading and len(heading.group(1)) == CATEGORY_LEVEL:
            found.append((index, heading.group(2).strip()))

    return found


def _open_unreleased(lines: list[str]) -> list[str]:
    """Insert an empty `## [Unreleased]` above the latest release section.

    The first section of the file is the newest release, so the new section goes
    before it; a changelog that has never had a release gets it at the end, after
    whatever introduction the file opens with.
    """

    lines = list(lines)

    at = next(
        (
            index
            for index, line in enumerate(lines)
            if (heading := HEADING_RE.match(line))
            and len(heading.group(1)) == SECTION_LEVEL
        ),
        None,
    )

    if at is None:
        lines.extend(["", f"## {UNRELEASED}"])
    else:
        lines[at:at] = [f"## {UNRELEASED}", ""]

    return lines


def _category_range(
    lines: list[str], start: int, end: int, category: str
) -> tuple[int, int] | None:
    """The `[start, end)` range of `category` inside the section, or None."""

    headings = _categories(lines, start, end)
    for position, (index, name) in enumerate(headings):
        if name.casefold() == category.casefold():
            following = headings[position + 1 :]
            return index, following[0][0] if following else end

    return None


def _open_category(
    lines: list[str], start: int, end: int, category: str, entry: str
) -> list[str]:
    """Return `lines` with `category` opened at its place in the canonical order.

    The order is the one `CATEGORIES` lists, so a file written over many changes
    keeps the shape Keep a Changelog describes instead of the order in which the
    categories happened to be needed.
    """

    rank = CATEGORIES.index(category)
    before = next(
        (
            index
            for index, name in _categories(lines, start, end)
            if name in CATEGORIES and CATEGORIES.index(name) > rank
        ),
        None,
    )

    if before is None:
        at = _body_end(lines, start, end)
        block = ["", f"### {category}", "", f"- {entry}"]
    else:
        at = before
        block = [f"### {category}", "", f"- {entry}", ""]

    return [*lines[:at], *block, *lines[at:]]


def add_entry(lines: list[str], category: str, entry: str) -> list[str]:
    """Return `lines` with `- entry` added to `category` under `## [Unreleased]`.

    An absent section or category is opened on the way: a changelog is edited by
    hand between releases, so neither can be assumed to be there, and a released
    section below must never move.
    """

    section = section_range(lines, UNRELEASED)
    if section is None:
        lines = _open_unreleased(lines)
        section = section_range(lines, UNRELEASED)

    start, end = section
    found = _category_range(lines, start, end, category)
    if found is None:
        return _open_category(lines, start, end, category, entry)

    at = _body_end(lines, *found)

    return [*lines[:at], f"- {entry}", *lines[at:]]


def main() -> int:
    configure_output()

    if len(sys.argv) != 3:
        print(USAGE, file=sys.stderr)
        return 2

    wanted = sys.argv[1].strip().casefold()
    category = next(
        (name for name in CATEGORIES if name.casefold() == wanted),
        None,
    )
    if category is None:
        print(f"Error: unknown category '{sys.argv[1]}'.", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    entry = sys.argv[2].strip()
    if not entry:
        # A bare `- ` would reach the next release notes as an empty bullet.
        print("Error: the entry is empty.", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    path: Path = repo_root() / CHANGELOG_PATH
    if not path.is_file():
        print("This project has no CHANGELOG.md; nothing to update.")
        return 0

    # `newline=""` keeps the file's own line endings visible, so a changelog checked
    # out with CRLF is not rewritten line by line into a whole-file diff.
    with path.open(encoding="utf-8", newline="") as file:
        raw = file.read()
    ending = "\r\n" if "\r\n" in raw else "\n"

    lines = add_entry(raw.splitlines(), category, entry)

    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(ending.join(lines) + ending)

    print(f"CHANGELOG.md: entry added under [Unreleased] -> {category}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
