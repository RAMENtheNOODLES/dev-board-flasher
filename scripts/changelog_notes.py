"""Extracts one version's release notes body from CHANGELOG.md.

Used by .github/workflows/release.yml's "Create GitHub release" step to
populate the GitHub release notes from the corresponding
`## [X.Y.Z] - YYYY-MM-DD` section (its Added/Changed/Fixed/etc.
subsections), rather than GitHub's auto-generated PR list.
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"

NEXT_HEADING_RE = re.compile(r"^## \[", re.MULTILINE)


def extract(content: str, version: str) -> str:
    heading_re = re.compile(
        rf"^## \[{re.escape(version)}\][ \t]*(?:- .*)?$\n", re.MULTILINE
    )
    heading = heading_re.search(content)
    if not heading:
        raise SystemExit(f"No '## [{version}]' section found in {CHANGELOG}")

    next_heading = NEXT_HEADING_RE.search(content, heading.end())
    body_end = next_heading.start() if next_heading else len(content)
    return content[heading.end():body_end].strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Version to extract, e.g. 1.3.0")
    parser.add_argument("output", type=Path, help="File to write the extracted notes to")
    args = parser.parse_args()

    content = CHANGELOG.read_text(encoding="utf-8")
    # Written directly to a file (rather than printed to stdout) so the
    # notes survive intact regardless of the calling shell's console
    # encoding.
    args.output.write_text(extract(content, args.version) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
