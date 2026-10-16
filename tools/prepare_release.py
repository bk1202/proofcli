"""Prepare accurate notes only for the package's exact version tag."""

import os
from pathlib import Path
import re
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 build environments use the locked fallback.
    import tomli as tomllib


def main():
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    tag = os.environ["RELEASE_TAG"]
    if tag != "v" + version or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError("release tag must exactly match the package version")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    section = changelog.split("\n## " + version + " — ", 1)[1].split("\n## ", 1)[0]
    notes = "## Changes\n\n" + section.split("\n", 1)[1].strip() + "\n\n"
    repo = os.environ.get("GITHUB_REPOSITORY", "bk1202/proofcli")
    run = os.environ.get("GITHUB_RUN_ID")
    if run:
        notes += f"Validation workflow: [runtime, Action, distribution and advisory checks](https://github.com/{repo}/actions/runs/{run}).\n\n"
    notes += f"[Screenshot of a failing check and a passing run](https://github.com/{repo}/releases/download/{tag}/proofcli-screenshot.png). Requires Python 3.10+. Assets contain a universal Python wheel, source distribution, that screenshot, and SHA256SUMS. PyPI publication runs separately after this release; check its workflow before assuming index availability. Commands run with your user permissions, and a pass covers only the declared assertions. See SECURITY.md and docs/audit-0.3.md for remaining limits.\n"
    Path("dist/RELEASE_NOTES.md").write_text(notes, encoding="utf-8")


if __name__ == "__main__":
    main()
