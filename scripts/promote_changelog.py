"""Promotes the [Unreleased] section of CHANGELOG.md on release to main.

Renames the `## [Unreleased]` heading to a dated `## [X.Y.Z] - YYYY-MM-DD`
heading (using the version currently in pyproject.toml), opens a fresh
empty `## [Unreleased]` above it, and updates the compare-link reference
block at the bottom of the file to match. If [Unreleased] has no content
to promote, the file is left untouched. Used by
.github/workflows/promote-changelog.yml on every push to `main`.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"

PYPROJECT_VERSION_RE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
UNRELEASED_HEADING_RE = re.compile(r"^## \[Unreleased\][ \t]*\n", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^## \[", re.MULTILINE)
UNRELEASED_LINK_RE = re.compile(
    r"^\[Unreleased\]: (?P<base>https://\S+/compare/)v(?P<prev>\S+?)\.\.\.HEAD$",
    re.MULTILINE,
)


def read_current_version() -> str:
    match = PYPROJECT_VERSION_RE.search(PYPROJECT.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"Couldn't find a version line in {PYPROJECT}")
    return match.group(1)


def promote(content: str, new_version: str, date: str) -> str | None:
    heading = UNRELEASED_HEADING_RE.search(content)
    if not heading:
        raise SystemExit(f"Couldn't find an [Unreleased] heading in {CHANGELOG}")

    next_heading = NEXT_HEADING_RE.search(content, heading.end())
    body_end = next_heading.start() if next_heading else len(content)
    body = content[heading.end():body_end]
    if not body.strip():
        return None

    content = (
        content[:heading.start()]
        + f"## [Unreleased]\n\n## [{new_version}] - {date}\n"
        + body
        + content[body_end:]
    )

    link = UNRELEASED_LINK_RE.search(content)
    if not link:
        raise SystemExit(f"Couldn't find the [Unreleased] compare link in {CHANGELOG}")
    base, prev = link.group("base"), link.group("prev")
    new_links = (
        f"[Unreleased]: {base}v{new_version}...HEAD\n"
        f"[{new_version}]: {base}v{prev}...v{new_version}"
    )
    content = content[:link.start()] + new_links + content[link.end():]

    return content


def main() -> None:
    new_version = read_current_version()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    content = CHANGELOG.read_text(encoding="utf-8")
    promoted = promote(content, new_version, date)

    if promoted is None:
        print("NO_CHANGE")
        return

    CHANGELOG.write_text(promoted, encoding="utf-8")
    print(f"CHANGED:{new_version}")


if __name__ == "__main__":
    main()
