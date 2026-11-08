#!/usr/bin/env python3

"""
Prints the effective DevSkills options of the project, one `section.key: value` per line.
Usage: config.py [artifacts|dialog|apply|links|commit]

The values are those of `dev/options.toml` over the defaults: a missing file or key
reads as the default, and an invalid value is replaced by it with a warning on stderr.
Skills read their options from here rather than from the file itself, so a typo in
the file is caught and reported once, the same way for every skill.
"""

import sys

from utils import OPTIONS, configure_output, format_option, load_config

USAGE = f"Usage: config.py [{'|'.join(OPTIONS)}]"


def option_lines(config: dict[str, dict[str, object]], section: str) -> list[str]:
    """Flatten one section into `section.key: value` lines, nested tables included."""

    lines: list[str] = []
    for key, value in config[section].items():
        if isinstance(value, dict):
            for name, item in value.items():
                lines.append(f"{section}.{key}.{name}: {format_option(item)}")
        else:
            lines.append(f"{section}.{key}: {format_option(value)}")

    return lines


def main() -> int:
    configure_output()

    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] not in OPTIONS):
        print(USAGE, file=sys.stderr)
        return 2

    sections = [sys.argv[1]] if len(sys.argv) == 2 else list(OPTIONS)

    config = load_config()
    for section in sections:
        for line in option_lines(config, section):
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
