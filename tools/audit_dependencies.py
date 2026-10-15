"""Check the locked build tools against PyPI's version-specific advisory feed."""

import json
from pathlib import Path
import re
from urllib.request import urlopen


def main():
    lock = Path(__file__).resolve().parents[1] / "requirements-build.txt"
    checked = []
    findings = []
    for line in lock.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_-]+)==([A-Za-z0-9.]+) --hash=sha256:([0-9a-f]{64})", line)
        if not match:
            raise ValueError(f"unlocked build requirement: {line}")
        name, version, digest = match.groups()
        with urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=20) as response:
            data = json.load(response)
        assert any(file["digests"]["sha256"] == digest for file in data["urls"]), "wheel hash not present in PyPI metadata"
        advisories = [v for v in data.get("vulnerabilities", []) if not v.get("withdrawn")]
        checked.append(name + "==" + version)
        if advisories:
            findings.append({"package": name, "version": version, "advisories": advisories})
    print(json.dumps({"source": "PyPI version-specific JSON advisory feed", "checked": checked, "findings": findings}, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
