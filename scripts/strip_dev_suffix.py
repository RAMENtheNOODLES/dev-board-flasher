"""Strips the -devN prerelease suffix from pyproject.toml's version.

Runs on push to `main`: a version merged in from `develop` still carries
its `-devN` suffix (e.g. `1.2.0-dev3`), so this cleans it to a plain
release version (`1.2.0`) before the release is tagged. No-ops if the
version already has no `-devN` suffix. Used by
.github/workflows/finalize-release.yml.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

VERSION_LINE_RE = re.compile(r'^(version = ")([^"]+)(")$', re.MULTILINE)
DEV_SUFFIX_RE = re.compile(r"-dev\d+$")


def main() -> None:
    content = PYPROJECT.read_text(encoding="utf-8")
    match = VERSION_LINE_RE.search(content)
    if not match:
        raise SystemExit(f"Couldn't find a version line in {PYPROJECT}")

    current = match.group(2)
    new_version = DEV_SUFFIX_RE.sub("", current)

    if new_version == current:
        print("NO_CHANGE")
        return

    content = VERSION_LINE_RE.sub(rf"\g<1>{new_version}\g<3>", content, count=1)
    PYPROJECT.write_text(content, encoding="utf-8")
    print(f"CHANGED:{new_version}")


if __name__ == "__main__":
    main()
