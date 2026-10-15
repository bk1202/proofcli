"""Fetch verified distribution bytes from a successful, commit-matched GitHub release."""

import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "proofcli-release-validation"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024:
        raise ValueError("release response exceeds size limit")
    return data


def main():
    tag = os.environ["RELEASE_TAG"]
    commit = os.environ["RELEASE_COMMIT"]
    repo = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("expected a stable version tag and exact commit")
    api = f"https://api.github.com/repos/{repo}"
    ref = json.loads(fetch(api + "/git/ref/tags/" + tag))["object"]
    if ref["type"] == "tag":
        ref = json.loads(fetch(api + "/git/tags/" + ref["sha"]))["object"]
    if ref["type"] != "commit" or ref["sha"] != commit:
        raise ValueError("release tag does not point to the validated commit")
    release = json.loads(fetch(api + "/releases/tags/" + tag))
    if release["draft"] or release["prerelease"]:
        raise ValueError("expected a published stable release")
    version = tag[1:]
    names = {f"proofcli-{version}-py3-none-any.whl", f"proofcli-{version}.tar.gz"}
    assets = {a["name"]: a for a in release["assets"]}
    files = {}
    for name in names | {"SHA256SUMS"}:
        asset = assets[name]
        url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
        if asset["browser_download_url"] != url:
            raise ValueError("unexpected release asset URL")
        data = fetch(url)
        if len(data) != asset["size"]:
            raise ValueError("release asset size mismatch")
        digest = hashlib.sha256(data).hexdigest()
        if asset.get("digest") and asset["digest"] != "sha256:" + digest:
            raise ValueError("GitHub asset digest mismatch")
        files[name] = data
    sums = {}
    for line in files.pop("SHA256SUMS").decode("utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if name in sums or not re.fullmatch("[0-9a-f]{64}", digest):
            raise ValueError("invalid checksum manifest")
        sums[name] = digest
    for name in names:
        if hashlib.sha256(files[name]).hexdigest() != sums[name]:
            raise ValueError("distribution checksum mismatch")
    destination = Path("packages")
    destination.mkdir(exist_ok=False)
    for name, data in files.items():
        (destination / name).write_bytes(data)
    print(f"Verified {tag} distributions against commit {commit} and SHA256SUMS")


if __name__ == "__main__":
    main()
