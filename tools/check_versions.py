"""Fail when the package version and documented install/Action pins disagree.

Checks pyproject.toml, proofcli.__version__, `pip install proofcli==X.Y.Z` pins,
`bk1202/proofcli@vX.Y.Z` Action references, and `releases/tag/vX.Y.Z` links in
README.md and docs/*.md. Historical asset links (`releases/download/...`) and
CHANGELOG entries are intentionally not checked. Zero dependencies.
"""

import ast
from pathlib import Path
import re
import sys

PATTERNS = {
    "pip pin": re.compile(r"\bproofcli==([0-9][0-9A-Za-z.+-]*)"),
    "Action pin": re.compile(r"\bbk1202/proofcli@v([0-9]+\.[0-9]+\.[0-9]+[0-9A-Za-z.+-]*)"),
    "release link": re.compile(r"/proofcli/releases/tag/v([0-9]+\.[0-9]+\.[0-9]+[0-9A-Za-z.+-]*)"),
}


def _pyproject_version(root):
    section = None
    for line in (root / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped
        elif section == "[project]":
            match = re.fullmatch(r'version\s*=\s*"([^"]+)"', stripped)
            if match:
                return match.group(1)
    raise ValueError("pyproject.toml has no [project] version")


def _module_version(root):
    tree = ast.parse((root / "proofcli" / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "__version__" for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("proofcli/__init__.py has no __version__")


def check(root):
    """Return a list of human-readable mismatch descriptions (empty when consistent)."""
    root = Path(root)
    version = _pyproject_version(root)
    problems = []
    module = _module_version(root)
    if module != version:
        problems.append(f"proofcli/__init__.py: __version__ {module!r} != pyproject {version!r}")
    documents = [root / "README.md", *sorted((root / "docs").glob("*.md"))]
    found = 0
    for document in documents:
        if not document.is_file():
            continue
        for number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            for kind, pattern in PATTERNS.items():
                for match in pattern.finditer(line):
                    found += 1
                    if match.group(1) != version:
                        problems.append(f"{document.relative_to(root).as_posix()}:{number}: "
                                        f"{kind} {match.group(1)} != pyproject {version}")
    if not found:
        problems.append("no documented pip/Action/release pins found; check the patterns")
    return problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[1]
    problems = check(root)
    if problems:
        print("Version references disagree:", file=sys.stderr)
        for problem in problems:
            print("  " + problem, file=sys.stderr)
        return 1
    print(f"Version {_pyproject_version(root)} is consistent across package and docs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
