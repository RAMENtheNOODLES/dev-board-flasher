"""Regenerates the [tool.pyside6-project] files list in pyproject.toml.

pyside6-project (Qt Creator's project file) has no built-in way to
auto-discover source files, so this script fills that gap: it globs the
project's actual .py/.ui/.qrc sources and rewrites the files list to match.
Run via `make project-files`.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

SECTION_RE = re.compile(
    r"\[tool\.pyside6[.-]project\]\s*\nfiles = \[[^\]]*\]\n?"
)


def collect_files() -> list[str]:
    files: list[Path] = []

    files.extend(
        p for p in (ROOT / "src").rglob("*.py")
        # skip generated modules produced by `make ui`/`make rcc`
        if not (p.parent == ROOT / "src" and (p.name.startswith("ui_") or p.name.endswith("_rc.py")))
    )
    files.extend((ROOT / "ui").glob("*.ui"))
    files.extend((ROOT / "assets").glob("*.qrc"))

    return sorted(p.relative_to(ROOT).as_posix() for p in files)


def main() -> None:
    files = collect_files()
    items = "\n".join(f'    "{f}",' for f in files)
    new_section = f"[tool.pyside6-project]\nfiles = [\n{items}\n]\n"

    content = PYPROJECT.read_text(encoding="utf-8")
    if SECTION_RE.search(content):
        content = SECTION_RE.sub(new_section, content)
    else:
        content = content.rstrip("\n") + "\n\n" + new_section

    PYPROJECT.write_text(content, encoding="utf-8")
    print(f"[project-files] Wrote {len(files)} entries to {PYPROJECT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
