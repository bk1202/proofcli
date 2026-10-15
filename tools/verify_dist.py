"""Validate the wheel and rebuild/install the sdist in fresh environments."""

import email
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile

PROJECT = Path(__file__).resolve().parents[1]


def run(argv, cwd, env=None):
    subprocess.run(list(map(str, argv)), cwd=cwd, env=env, check=True, timeout=180)


def inspect_wheel(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        metadata = email.message_from_bytes(archive.read(next(n for n in names if n.endswith(".dist-info/METADATA"))))
        assert metadata["Name"] == "proofcli"
        assert metadata["License-Expression"] == "MIT"
        assert not metadata.get_all("Requires-Dist"), "unexpected runtime dependency"
        assert all(not n.startswith(("tests/", "tools/", "work/", ".git/")) for n in names)
        for required in ("proofcli/process.py", "proofcli/_verify.py", "proofcli/winjob.py"):
            assert required in names
        assert any(n.endswith("licenses/LICENSE") for n in names)
        return metadata["Version"]


def install_and_exercise(wheel, root):
    environment = root / "environment"
    venv.EnvBuilder(with_pip=True).create(environment)
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    cli = scripts / ("proofcli.exe" if os.name == "nt" else "proofcli")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    caller = root / "outside-source"
    caller.mkdir()
    run([python, "-m", "pip", "install", "--no-index", wheel], caller, env)
    run([cli, "--version"], caller, env)
    run([cli, "init", "contract.json"], caller, env)
    run([cli, "run", "contract.json", "--report", "result.json"], caller, env)
    assert json.loads((caller / "result.json").read_text())["status"] == "passed"
    # This failed in 0.2.0 on POSIX: resolving the Python symlink lost the venv.
    spec = {"version": 1, "argv": ["{python}", "-c",
            "import sys,proofcli; from importlib.metadata import version; "
            "assert version('proofcli') == proofcli.__version__; print(sys.prefix)"],
            "expect": {"stdout_regex": re.escape(str(environment))}}
    (caller / "venv.json").write_text(json.dumps(spec), encoding="utf-8")
    run([cli, "venv.json", "--json"], caller, env)


def main():
    dist = PROJECT / "dist"
    wheels = list(dist.glob("*.whl"))
    sources = list(dist.glob("*.tar.gz"))
    assert len(wheels) == len(sources) == 1, "dist must contain exactly one wheel and one sdist"
    version = inspect_wheel(wheels[0])
    with tempfile.TemporaryDirectory(prefix="proofcli-package-") as directory:
        root = Path(directory)
        install_and_exercise(wheels[0], root / "wheel")
        unpacked = root / "source"
        unpacked.mkdir()
        # Do not trust even our own release archive's paths or link entries.
        with tarfile.open(sources[0]) as archive:
            for member in archive:
                target = (unpacked / member.name).resolve()
                assert target.is_relative_to(unpacked) and not member.name.startswith("/"), "unsafe sdist path"
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    assert member.isfile(), "sdist contains a special file or link"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as reader, target.open("xb") as writer:
                        shutil.copyfileobj(reader, writer)
        source = next(unpacked.iterdir())
        for required in ("CHANGELOG.md", "SECURITY.md", "examples/export/fixtures/input.csv", "tools/verify_dist.py"):
            assert (source / required).is_file(), f"sdist missing {required}"
        rebuilt = root / "rebuilt"
        run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", rebuilt, source], root)
        rebuilt_wheel = next(rebuilt.glob("*.whl"))
        assert inspect_wheel(rebuilt_wheel) == version
        install_and_exercise(rebuilt_wheel, root / "sdist")
    checksums = "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
                        for p in sorted([wheels[0], sources[0]]))
    (dist / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    print("Wheel and sdist installation/real execution checks passed; SHA256SUMS written.")


if __name__ == "__main__":
    main()
