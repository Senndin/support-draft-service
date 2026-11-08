"""Shared helpers for the DevSkills tooling scripts."""

import re
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

DEV_DIR = "dev"
CHANGES_DIR = "changes"
ARCHIVE_DIR = "archive"
SPECS_PATH = "dev/specs"
TEMPLATES_PATH = "dev/templates"
OPTIONS_PATH = "dev/options.toml"
AGENTS_PATH = "dev/AGENTS.md"

# The empty tree object, present in every Git repository: diffing against it
# reports every file as added, which is what a change created in the root commit needs.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# The lines the skills match on. `dev-status` and `dev-next` branch on
# NO_ACTIVE_CHANGES verbatim, and both read the `not found` message as a prefix, so
# every script that can print one of these takes it from here rather than spelling
# it out again -- two wordings of the same message are two behaviors for the skill.
NO_ACTIVE_CHANGES = "No active changes under dev/changes/."
ACTIVE_CHANGES_HEADER = "Active changes (most recently modified first):"

HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
ROLE_COMMENT_RE = re.compile(r"^\s*<!--\s*(.*?)\s*-->\s*$")
# Opens or closes a fenced block. Both artifact counters skip what lies inside: a
# checklist or a scenario written as an example is not one.
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")


def configure_output() -> None:
    """Emit UTF-8 on stdout and stderr, whatever encoding the console defaults to.

    `_git` decodes git's output as UTF-8, so a non-ASCII spec path survives the way
    in. The way out is the console codepage -- cp1251 on a Russian/Ukrainian Windows
    -- which mangles Cyrillic into question marks and raises `UnicodeEncodeError` on
    anything outside it. The reader of this output is an agent acting on the paths it
    names, and a mangled path matches no file.

    A stream that cannot be reconfigured is left as it is: the scripts must still run
    under a test harness or a wrapper that replaced it.
    """

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            continue


def change_not_found(name: str, target: Path) -> str:
    """The message a script prints when a change name matches no directory."""

    return f"Error: change '{name}' not found at {target}"


def _git(args: list[str], root: Path | None = None) -> str | None:
    """Run a git command and return its stdout, or None if it failed.

    Git writes paths as UTF-8 on every platform, so the output is decoded as
    UTF-8 explicitly. Letting Python fall back to the locale encoding mangles
    every non-ASCII path on Windows, and the mangled path then matches nothing.

    `core.quotePath=false` stops git from escaping those same paths as octal
    byte sequences (`"dev/specs/\\321\\200..."`), which no caller here decodes.
    """

    root = root or repo_root()
    try:
        out = subprocess.run(
            ["git", "-c", "core.quotePath=false", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        return None

    return out.stdout


def repo_root() -> Path:
    """Return the repository root, falling back to the current directory."""

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        return Path.cwd()


def current_branch(root: Path | None = None) -> str | None:
    """The name of the checked-out branch, or None on a detached HEAD or a git failure.

    `symbolic-ref` rather than `rev-parse --abbrev-ref HEAD`: it also names the branch
    of a repository with no commits yet, and it fails outright on a detached HEAD
    instead of printing `HEAD`. Every state it cannot read comes back as None, which
    callers deciding whether to commit unasked treat as the unsafe case.
    """

    out = _git(["symbolic-ref", "--short", "-q", "HEAD"], root)
    branch = out.strip() if out else ""
    return branch or None


def detached_head(root: Path | None = None) -> bool:
    """Whether HEAD points straight at a commit rather than at a branch.

    `current_branch` returns None both here and when git cannot be read at all; this
    tells the two apart, so a report never calls a broken repository a detached HEAD.
    A repository with no commits is never detached: its HEAD still names a branch.
    """

    if _git(["symbolic-ref", "-q", "HEAD"], root) is not None:
        return False
    return _git(["rev-parse", "--verify", "-q", "HEAD"], root) is not None


def uncommitted_paths(paths: list[str], root: Path | None = None) -> list[str]:
    """Which of `paths` have edits that are not committed, in the order given.

    Staged, unstaged and untracked all count as uncommitted: the caller asks this
    before rewriting a file, and any of the three means the rewrite would bury work
    that Git cannot give back. A repository Git cannot read reports nothing, which
    leaves the caller no worse off than it was without the check.
    """

    root = root or repo_root()

    out = _git(["status", "--porcelain", "-uall", "--", *paths], root)
    if not out:
        return []

    reported = {
        line[3:].strip().strip('"') for line in out.splitlines() if len(line) > 3
    }

    return [path for path in paths if path in reported]


def changes_dir(root: Path | None = None) -> Path:
    """Return the active-changes directory (`dev/changes`)."""

    root = root or repo_root()
    return root / DEV_DIR / CHANGES_DIR


def change_dir(name: str, root: Path | None = None) -> Path:
    """Return the directory of a single change by name."""

    return changes_dir(root) / name


def _manifest_pair(line: str) -> tuple[str, str] | None:
    """The `(key, value)` of a top-level manifest line, or None if it holds none."""

    if line.startswith((" ", "\t", "#")):
        return None
    key, separator, value = line.partition(":")
    if not separator:
        return None
    return key.strip(), value.strip()


def manifest_values(manifest: Path) -> dict[str, str]:
    """Read `.devskills.yaml` as flat `key: value` pairs.

    The manifest is a handful of scalars, so it is read directly rather than through
    a YAML parser: DevSkills brings no runtime dependencies into a project. Lines
    without a colon, and anything nested, are ignored.
    """

    if not manifest.is_file():
        return {}

    values: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        pair = _manifest_pair(line)
        if pair:
            values[pair[0]] = pair[1]

    return values


def set_manifest_value(manifest: Path, key: str, value: str) -> None:
    """Set a top-level `key: value` in `.devskills.yaml`, keeping every other line.

    The first line holding the key is rewritten in place and any later duplicate is
    dropped, so `manifest_values` reads back exactly the value written here; a key
    not there yet is appended. The file keeps its own line endings, so the rewrite
    shows up in a diff as the one line it changed.
    """

    lines: list[str] = []
    if manifest.is_file():
        with manifest.open(encoding="utf-8", newline="") as file:
            lines = file.read().splitlines(keepends=True)

    ending = next(
        (line[len(line.rstrip("\r\n")) :] for line in lines if line.endswith("\n")),
        "\n",
    )
    entry = f"{key}: {value}{ending}"

    result: list[str] = []
    written = False
    for line in lines:
        pair = _manifest_pair(line)
        if pair and pair[0] == key:
            if not written:
                result.append(entry)
                written = True
            continue
        result.append(line)

    if not written:
        if result and not result[-1].endswith(("\n", "\r")):
            result[-1] += ending
        result.append(entry)

    with manifest.open("w", encoding="utf-8", newline="") as file:
        file.write("".join(result))


def devskills_version(root: Path | None = None) -> str | None:
    """Read the DevSkills version from the frontmatter of `dev/AGENTS.md`.

    That frontmatter is the runtime source of the version in every project, the
    installer's and `new_change.py`'s alike. `pyproject.toml` is not: in a target
    project it carries the version of that project, not of DevSkills.

    Only the block between the leading `---` markers is read, and only top-level
    `key: value` lines in it, at the level of `manifest_values` -- DevSkills brings
    no YAML parser into a project. A file, a frontmatter or a key that is not there
    yields None, because an invented version in a change manifest would be worse
    than a missing one.
    """

    root = root or repo_root()

    try:
        # `utf-8-sig`: an editor that saved a byte-order mark must not hide the
        # opening `---` behind it and turn the version into "not declared".
        lines = (root / AGENTS_PATH).read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return None

    if not lines or lines[0].strip() != "---":
        return None

    for line in lines[1:]:
        if line.strip() == "---":
            break
        pair = _manifest_pair(line)
        if pair and pair[0] == "version":
            return pair[1] or None

    return None


def _mtime(path: Path) -> float:
    """The path's modification time, or 0.0 if it is gone or unreadable."""

    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _recent_mtime(path: Path) -> float:
    """The newest modification time of a directory or of anything directly inside it.

    A directory's own mtime moves only when an entry is added or removed, never when
    an existing file is edited. Checking a task off in `tasks.md` -- the most common
    way to work on a change -- would therefore leave the change looking untouched.
    Looking one level in makes "most recently modified" mean what the skills promise.
    """

    try:
        entries = list(path.iterdir())
    except OSError:
        entries = []

    return max([_mtime(path), *(_mtime(entry) for entry in entries)])


def active_changes(root: Path | None = None) -> list[Path]:
    """Return active change directories, newest first, excluding the archive.

    Ties break on the name. A fresh clone stamps every file with the checkout time,
    so ties are the rule there, and without the tiebreak the order would be whatever
    the filesystem happened to return.
    """

    base = changes_dir(root)
    if not base.is_dir():
        return []

    changes = [p for p in base.iterdir() if p.is_dir() and p.name != ARCHIVE_DIR]

    return sorted(changes, key=lambda p: (-_recent_mtime(p), p.name))


def change_base_commit(name: str, root: Path | None = None) -> str | None:
    """Return the commit a change started from, or None if it is not committed yet.

    The anchor is the commit that first added `dev/changes/<name>/.devskills.yaml`;
    the base is its parent, so everything the change committed lies in
    `<base>..HEAD`. This binds the window to the change itself, without guessing a
    base branch, and works the same whether the work happens on a branch or
    directly on the main one.
    """

    root = root or repo_root()
    manifest = f"{DEV_DIR}/{CHANGES_DIR}/{name}/.devskills.yaml"

    out = _git(["log", "--diff-filter=A", "--format=%H", "--", manifest], root)
    if out is None:
        return None

    commits = [line.strip() for line in out.splitlines() if line.strip()]
    if not commits:
        return None

    # `git log` is newest first, so the oldest commit that added the manifest is last.
    creation = commits[-1]

    parent = _git(["rev-parse", "--verify", "--quiet", f"{creation}^"], root)
    if parent is None or not parent.strip():
        # The change was created in the root commit: diff against the empty tree.
        return EMPTY_TREE

    return parent.strip()


def _status_from_committed(base: str, root: Path) -> dict[str, str]:
    """Classify spec files committed between `base` and HEAD."""

    out = _git(["diff", "--name-status", base, "HEAD", "--", SPECS_PATH], root)
    if out is None:
        return {}

    found: dict[str, str] = {}
    for line in out.splitlines():
        if not line.strip():
            continue

        fields = line.split("\t")
        code = fields[0].strip()
        # A rename carries both the old and the new path; the new one is last.
        path = fields[-1].strip()
        if not code or not path:
            continue

        if code.startswith("D"):
            continue
        if code.startswith("A"):
            found[path] = "new"
        else:
            found[path] = "changed"

    return found


def _status_from_worktree(root: Path) -> dict[str, str]:
    """Classify spec files changed in the working tree, the index, or untracked."""

    # `-uall` expands untracked directories into files; without it an untracked
    # `dev/specs/<domain>/` collapses into a single `dev/specs/` entry.
    out = _git(["status", "--porcelain", "-uall", "--", SPECS_PATH], root)
    if out is None:
        return {}

    found: dict[str, str] = {}
    for line in out.splitlines():
        if len(line) < 4:
            continue

        code = line[:2]
        path = line[3:].strip()
        # A rename is reported as `old -> new`; the new path is what exists now.
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        path = path.strip('"')
        if not path:
            continue

        if code == "??" or "A" in code:
            found[path] = "new"
        else:
            found[path] = "changed"

    return found


def spec_changes(
    change_name: str | None = None, root: Path | None = None
) -> dict[str, str]:
    """Map each spec file the change touched to `"new"` or `"changed"`.

    Two sources are merged: what the change committed since its base commit, and
    what is still uncommitted in the working tree. Committing specs therefore no
    longer hides them. Where the sources disagree, `"new"` wins — a file added
    within the change and edited afterwards is still new to the change.

    Without a change name only the working tree is inspected, which is also the
    behavior when the change directory itself is not committed yet.
    """

    root = root or repo_root()

    found: dict[str, str] = {}
    if change_name:
        base = change_base_commit(change_name, root)
        if base:
            found.update(_status_from_committed(base, root))

    for path, status in _status_from_worktree(root).items():
        if found.get(path) == "new":
            continue
        found[path] = status

    # A spec the change deleted is not a spec the change carries.
    return {path: status for path, status in found.items() if (root / path).is_file()}


def changed_spec_files(
    change_name: str | None = None, root: Path | None = None
) -> list[str]:
    """Spec file paths the change touched, sorted; see `spec_changes`."""

    return sorted(spec_changes(change_name, root))


def template_section_headings(
    artifact: str, role: str, root: Path | None = None
) -> tuple[str, ...]:
    """Return the headings of `artifact` marked with `role`, as its template writes them.

    `dev/AGENTS.md` makes `dev/templates/` the authority on heading text. A heading
    that carries a canonical role is followed by a comment holding that role and
    nothing else (`<!-- New features -->`); anything addressed to the author of the
    artifact is a separate comment, which this simply passes over. Resolving the
    heading from that marker keeps the tooling working in any artifact language,
    with nothing hardcoded.

    `artifact` names a file in `dev/templates/`, for example `proposal.md`. Each
    returned item is the full heading line (`### New Features`), so the caller
    knows both the level and the text.
    """

    root = root or repo_root()
    template = root / TEMPLATES_PATH / artifact
    if not template.is_file():
        return ()

    wanted = role.strip().casefold()

    headings: list[str] = []
    current: str | None = None
    for line in template.read_text(encoding="utf-8").splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            current = line.strip()
            continue

        comment = ROLE_COMMENT_RE.match(line)
        if comment and comment.group(1).casefold() == wanted and current:
            headings.append(current)

    return tuple(headings)


def heading_level(heading: str) -> int:
    """Return the `#` depth of a heading line, or 0 if it is not a heading."""

    match = HEADING_RE.match(heading)
    return len(match.group(1)) if match else 0


# The Features parser: which spec each bullet of a proposal declares. It lives here
# because two scripts read that declaration -- `sync_specs.py` to compare it with the
# files the change touched, `status.py` to tell whether the `specs` step is still owed
# -- and two readings of one section would sooner or later disagree.
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
# The target is either wrapped in angle brackets -- the CommonMark form for a path
# holding spaces -- or runs to the first space or closing parenthesis.
LINK_RE = re.compile(r"\[[^\]]*\]\(\s*(?:<([^>]*)>|([^)\s]*))")
CODE_RE = re.compile(r"`([^`]+)`")
CANONICAL_RE = re.compile(rf"^{re.escape(SPECS_PATH)}/([^/]+)/spec\.md$")
# `https:`, `mailto:`, `file:` -- anything with a URI scheme addresses the world
# outside this repository, so it can never be a specification path.
SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
# A spec directory name, as `dev/specs/<domain>/` spells it.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

PROPOSAL_TEMPLATE = "proposal.md"
ROLES = (("New features", "new"), ("Changed features", "changed"))

# What a Features bullet turned out to be.
SPEC = "spec"  # a declaration resolving to `dev/specs/<domain>/spec.md`
PLACEHOLDER = "placeholder"  # untouched template text -- not a declaration at all
UNRESOLVED = "unresolved"  # a written link whose target is empty
NON_SPEC = "non-spec"  # a written bullet that names no specification


def section_bullets(lines: list[str], heading: str) -> list[str]:
    """Return the bullet texts under `heading`, stopping at the next heading of its level."""

    level = heading_level(heading)
    wanted = heading.strip()

    bullets: list[str] = []
    inside = False
    for line in lines:
        current = heading_level(line)
        if current:
            if inside and current <= level:
                break
            inside = line.strip() == wanted
            continue

        if inside:
            bullet = BULLET_RE.match(line)
            if bullet:
                bullets.append(bullet.group(1).strip())

    return bullets


def resolve_relative(target: str) -> str | None:
    """Resolve a link written relative to `dev/changes/<name>/` into a repo-relative path.

    Returns None when the target climbs above the repository root: such a link
    addresses something outside the project and names no specification.
    """

    parts: list[str] = []
    for part in f"dev/changes/_/{target}".split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
            continue
        parts.append(part)

    return "/".join(parts) or None


def link_target(bullet: str) -> str | None:
    """Return the bullet's link target, `""` when the link has none, None without a link."""

    link = LINK_RE.search(bullet)
    if not link:
        return None

    # Group 1 is the angle-bracket form, group 2 the bare one; exactly one matches.
    target = link.group(1) if link.group(1) is not None else link.group(2)

    return target.split("#", 1)[0].strip()


def classify_bullet(bullet: str) -> tuple[str, str | None]:
    """Classify a Features bullet and, for a declaration, resolve the spec it names.

    Returns one of `SPEC` (with the path), `PLACEHOLDER` (untouched template text,
    ignored), `UNRESOLVED` (a written link pointing nowhere) or `NON_SPEC` (a written
    bullet that names no specification -- prose, or a link outside `dev/specs/`).

    Only a path that reads exactly as `dev/specs/<domain>/spec.md` counts as a
    declaration. Everything else is reported rather than declared: inventing a spec
    path out of prose would make the proposal promise a file nobody meant to write.
    """

    target = link_target(bullet)
    if target is not None:
        if not target:
            return UNRESOLVED, None
        if "{" in target or "}" in target:
            return PLACEHOLDER, None
        # An external URL or a protocol-relative one addresses no file in this repo.
        if SCHEME_RE.match(target) or target.startswith("//"):
            return NON_SPEC, None

        path = target.lstrip("/") if target.startswith("/") else resolve_relative(target)
        if not path or not CANONICAL_RE.match(path):
            return NON_SPEC, None

        return SPEC, path

    name = CODE_RE.search(bullet)
    if name:
        raw = name.group(1)
    else:
        # The bare-name form is `<name>: <description>`, so the name is the whole of
        # what precedes the colon. A sentence there is prose, not a declaration.
        head, _, described = bullet.partition(":")
        if not described and not head.strip():
            return PLACEHOLDER, None
        words = head.split()
        if not described or len(words) != 1:
            return NON_SPEC, None
        raw = words[0]

    raw = raw.strip().strip("*_`")
    if not raw:
        return PLACEHOLDER, None
    if "{" in raw or "}" in raw:
        return PLACEHOLDER, None
    if not SLUG_RE.match(raw):
        return NON_SPEC, None

    return SPEC, f"{SPECS_PATH}/{raw}/spec.md"


def bullet_path(bullet: str) -> str | None:
    """Resolve the spec path a proposal bullet declares, or None if it declares none."""

    kind, path = classify_bullet(bullet)

    return path if kind == SPEC else None


def declared_features(
    proposal: Path,
) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """Map each declared spec path to `"new"` / `"changed"`.

    Also returns the paths declared under both subsections, the bullets whose link
    has no target, and the bullets that name no specification at all.
    """

    lines = proposal.read_text(encoding="utf-8").splitlines()

    declared: dict[str, str] = {}
    duplicates: list[str] = []
    unresolved: list[str] = []
    non_spec: list[str] = []
    for role, status in ROLES:
        for heading in template_section_headings(PROPOSAL_TEMPLATE, role):
            for bullet in section_bullets(lines, heading):
                kind, path = classify_bullet(bullet)
                if kind == UNRESOLVED:
                    # A link with an empty target names no spec, yet it is a written
                    # declaration rather than an untouched placeholder -- say so.
                    unresolved.append(bullet)
                    continue
                if kind == NON_SPEC:
                    non_spec.append(bullet)
                    continue
                if kind != SPEC or not path:
                    continue
                if path in declared and declared[path] != status:
                    duplicates.append(path)
                    continue
                declared.setdefault(path, status)

    return declared, duplicates, unresolved, non_spec


# The acceptance parser: which scenarios `acceptance.md` holds, and the result the
# user reported for each. It lives here because `status.py` counts the results and
# `acceptance.py` lists them, and the count and the listing must never disagree.
ACCEPTANCE_TEMPLATE = "acceptance.md"
# The results stay in English in every artifact language, so they are matched as
# written rather than resolved from a template like a heading.
ACCEPTANCE_RESULTS = ("passed", "failed", "skipped")
PENDING = "pending"
# A result is an unindented list item that opens with a bracket: `- [passed]`. The
# lookahead keeps out a link such as the Covers bullet, `- [`auth`](/dev/specs/...)`,
# and the indent keeps out the diagnosis recorded under a failure.
RESULT_RE = re.compile(r"^[-*+]\s+\[([^\]]*)\](?!\()")
SCENARIO_LEVEL = 3


def acceptance_scenarios(
    path: Path, root: Path | None = None
) -> list[tuple[str, str]] | None:
    """List the scenarios of an `acceptance.md` as `(heading text, result)` pairs.

    A missing file is `None`, kept apart from an empty list: a change with no
    `acceptance.md` still owes its acceptance, while one whose file lists no scenario
    has said there is nothing for a person to observe.

    A scenario is a third-level heading under the heading the template marks with
    the role Scenarios, so a project whose templates hold no `acceptance.md` reads
    no scenario at all. Its result is the last unindented list item of its section
    that opens with a bracket, and anything but `ACCEPTANCE_RESULTS` there is
    `PENDING`: the scenario is presented again rather than passed by a typo.
    """

    if not path.is_file():
        return None

    # Headings are compared as (level, text), not as raw lines: a heading reformatted
    # by hand, `##  Scenarios` or `## Scenarios ##`, would otherwise hide every
    # scenario, and an acceptance read as having none passes its step unrun.
    wanted = {
        (len(match.group(1)), match.group(2))
        for heading in template_section_headings(ACCEPTANCE_TEMPLATE, "Scenarios", root)
        if (match := HEADING_RE.match(heading))
    }

    scenarios: list[tuple[str, str]] = []
    section_level = 0
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        # A fenced block is an example of a scenario or a result, not one.
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            if section_level and level <= section_level:
                section_level = 0
            if (level, heading.group(2)) in wanted:
                section_level = level
            elif section_level and level == SCENARIO_LEVEL:
                scenarios.append((heading.group(2), PENDING))
            continue

        result = RESULT_RE.match(line)
        if section_level and scenarios and result:
            # The last bracketed item wins, so a re-run recorded below a failure
            # replaces it; anything but a known result presents the scenario again.
            token = result.group(1).strip()
            outcome = token if token in ACCEPTANCE_RESULTS else PENDING
            scenarios[-1] = (scenarios[-1][0], outcome)

    return scenarios


# The English originals the keyword table of `dev/options.toml` translates. A project
# that sets no table, or leaves a keyword out, writes that keyword in English.
DEFAULT_KEYWORDS = {
    "MUST": "MUST",
    "MUST_NOT": "MUST NOT",
    "GIVEN": "GIVEN",
    "WHEN": "WHEN",
    "THEN": "THEN",
    "AND": "AND",
    "OR": "OR",
    "BUT": "BUT",
}

REVIEW_MODES = ("task", "group", "change")
# The units of work `dev-apply-change` may commit on its own; "off" leaves every
# commit to the user's agreement.
AUTO_COMMIT_MODES = ("off", "task", "group")


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_bool(value: object) -> bool:
    # Only a TOML boolean is a switch: a quoted "no" is a typo, not a way to say off.
    return isinstance(value, bool)


def _is_positive_int(value: object) -> bool:
    # `bool` is an `int` in Python, and `true` minutes is not a limit anyone meant.
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


# section -> key -> (default, validator, what a valid value is). The keyword table
# is the one nested option and is read on its own in `load_config`.
OPTIONS: dict[str, dict[str, tuple[object, Callable[[object], bool], str]]] = {
    "artifacts": {
        "language": ("en", _is_text, "a non-empty string"),
    },
    # The language of the conversation, apart from that of the files: a skill needs
    # it before its first word to the user, and the artifact language only before
    # it writes a file.
    "dialog": {
        "language": ("en", _is_text, "a non-empty string"),
    },
    "apply": {
        "review": (
            "task",
            lambda value: value in REVIEW_MODES,
            '"task", "group" or "change"',
        ),
        "time_limit": (45, _is_positive_int, "an integer greater than 0"),
    },
    "links": {
        "enabled": (False, _is_bool, "true or false"),
        "threshold_seconds": (60, _is_positive_int, "an integer greater than 0"),
    },
    # Whether invoking `dev-next` agrees to the commit `dev-commit` proposed and the
    # user has not answered yet, and which unit of work `dev-apply-change` commits
    # without asking. A section of its own, not of either skill.
    "commit": {
        "auto_on_next": (True, _is_bool, "true or false"),
        "auto_on_apply": (
            "off",
            lambda value: value in AUTO_COMMIT_MODES,
            '"off", "task" or "group"',
        ),
    },
}

# section -> deprecated key -> the key that replaced it. Not in `OPTIONS`: a deprecated
# key is read but neither printed, seeded nor described.
DEPRECATED_OPTIONS: dict[str, dict[str, str]] = {
    "apply": {"group_time_limit": "time_limit"},
}


def format_option(value: object) -> str:
    """Render an option value as `dev/options.toml` spells it, minus string quotes."""

    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def _replace_deprecated(section: str, table: dict[str, object]) -> dict[str, object]:
    """Return a copy of `table` with every deprecated key moved onto its successor.

    A renamed key must keep working in projects that never touched their file, or the
    rename would silently reset their setting. The successor wins when both are set,
    and the warning is printed either way, so a stale key never goes unnoticed. The
    moved value then takes the ordinary validation, reported under the new name.
    """

    table = dict(table)
    for old, new in DEPRECATED_OPTIONS.get(section, {}).items():
        if old not in table:
            continue
        _warn(f"{section}.{old} in {OPTIONS_PATH} is deprecated; use {section}.{new}.")
        value = table.pop(old)
        table.setdefault(new, value)
    return table


def load_config(root: Path | None = None) -> dict[str, dict[str, object]]:
    """Return the effective DevSkills options of the project, section by section.

    Every option starts at its default, and `dev/options.toml` overrides what it sets.
    A missing file is the ordinary state of a project that changed nothing, so it is
    silent. Anything the file gets wrong -- broken TOML, a value of the wrong type, a
    key nobody reads -- falls back to the default with a warning on stderr: a typo
    must not stop the workflow, but it must not pass for a setting either. A deprecated
    key is still read, under the name that replaced it, with a warning of its own.
    """

    root = root or repo_root()

    config: dict[str, dict[str, object]] = {
        section: {key: default for key, (default, _, _) in keys.items()}
        for section, keys in OPTIONS.items()
    }
    keywords = dict(DEFAULT_KEYWORDS)
    config["artifacts"]["keywords"] = keywords

    path = root / OPTIONS_PATH
    if not path.is_file():
        return config

    try:
        # `utf-8-sig`: `tomllib` rejects a byte-order mark, and an editor that saves
        # one must not silently reset every option.
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as error:
        _warn(f"{OPTIONS_PATH} is not valid TOML ({error}); using the defaults.")
        return config

    for section in data:
        if section not in OPTIONS:
            _warn(f"unknown section [{section}] in {OPTIONS_PATH} is ignored.")

    for section, keys in OPTIONS.items():
        table = data.get(section, {})
        if not isinstance(table, dict):
            _warn(f"{section} in {OPTIONS_PATH} is not a table; using its defaults.")
            continue

        table = _replace_deprecated(section, table)
        for key, value in table.items():
            if section == "artifacts" and key == "keywords":
                continue
            if key not in keys:
                _warn(f"unknown option {section}.{key} in {OPTIONS_PATH} is ignored.")
                continue

            default, valid, expected = keys[key]
            if valid(value):
                config[section][key] = value
            else:
                _warn(
                    f"{section}.{key} = {value!r} must be {expected}; "
                    f"using {format_option(default)}."
                )

    artifacts = data.get("artifacts", {})
    table = artifacts.get("keywords", {}) if isinstance(artifacts, dict) else {}
    if not isinstance(table, dict):
        _warn(f"artifacts.keywords in {OPTIONS_PATH} is not a table; using English.")
        table = {}

    for key, value in table.items():
        if key not in DEFAULT_KEYWORDS:
            _warn(f"unknown keyword artifacts.keywords.{key} is ignored.")
        elif _is_text(value):
            keywords[key] = value
        else:
            _warn(
                f"artifacts.keywords.{key} = {value!r} must be a non-empty string; "
                f"using {DEFAULT_KEYWORDS[key]}."
            )

    return config
