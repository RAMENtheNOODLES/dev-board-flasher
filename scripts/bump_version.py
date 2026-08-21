"""Bumps the version in pyproject.toml based on new commit messages.

Reads commit messages (subject+body per commit, records separated by
\\x1e) from stdin, decides a bump level from their conventional-commit
prefixes, and rewrites the `version = "..."` line in pyproject.toml.
Used by .github/workflows/version-bump.yml on every push to `develop`.

The version keeps a `-devN` prerelease suffix while on develop: a
matching commit bumps major/minor/patch and resets devN to 0, otherwise
devN is simply incremented (or set to 0 if the current version has none).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

VERSION_LINE_RE = re.compile(r'^(version = ")([^"]+)(")$', re.MULTILINE)
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-dev(\d+))?$")

BREAKING_RE = re.compile(r"^\w+(\([^)]*\))?!:", re.MULTILINE)
BREAKING_FOOTER_RE = re.compile(r"^BREAKING CHANGE:", re.MULTILINE)
FEAT_RE = re.compile(r"^feat(\([^)]*\))?:", re.MULTILINE)
FIX_RE = re.compile(r"^(fix|hotfix)(\([^)]*\))?:", re.MULTILINE)


def bump_level(commit_messages: str) -> str | None:
    if BREAKING_RE.search(commit_messages) or BREAKING_FOOTER_RE.search(commit_messages):
        return "major"
    if FEAT_RE.search(commit_messages):
        return "minor"
    if FIX_RE.search(commit_messages):
        return "patch"
    return None


def next_version(current: str, level: str | None) -> str:
    match = VERSION_RE.match(current)
    if not match:
        raise ValueError(f"Version {current!r} doesn't match X.Y.Z or X.Y.Z-devN")
    major, minor, patch, dev = match.groups()
    major, minor, patch = int(major), int(minor), int(patch)
    dev = int(dev) if dev is not None else None

    if level == "major":
        return f"{major + 1}.0.0-dev0"
    if level == "minor":
        return f"{major}.{minor + 1}.0-dev0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}-dev0"
    return f"{major}.{minor}.{patch}-dev{0 if dev is None else dev + 1}"


def main() -> None:
    commit_messages = sys.stdin.read()
    level = bump_level(commit_messages)

    content = PYPROJECT.read_text(encoding="utf-8")
    match = VERSION_LINE_RE.search(content)
    if not match:
        raise SystemExit(f"Couldn't find a version line in {PYPROJECT}")

    current = match.group(2)
    new_version = next_version(current, level)

    content = VERSION_LINE_RE.sub(rf"\g<1>{new_version}\g<3>", content, count=1)
    PYPROJECT.write_text(content, encoding="utf-8")

    print(new_version)


if __name__ == "__main__":
    main()
