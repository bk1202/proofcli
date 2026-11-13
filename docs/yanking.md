# Yanking a bad release and shipping a fix

Use this when a version already on PyPI is broken or unsafe. PyPI never lets a version number be uploaded twice or replaced, so the fix is always a new version.

Yanking keeps the files on PyPI but tells installers to skip that version unless it is the only release that matches an exact pin (`==` or `===`, for example `proofcli==X.Y.Z`). It does not delete the files, and it can be undone. PyPI yanks a whole release, not one file inside it.

Yank sparingly. PyPI's own guidance is to yank when a release is broken or uninstallable, when it breaks its own compatibility promise, or when it contains a security problem. Deleting a release is not part of this procedure.

## 1. Yank the bad version on PyPI

1. Sign in to PyPI with an account that can manage `proofcli`, and open `https://pypi.org/manage/project/proofcli/releases/`.
2. Next to the bad version, open Options and choose Yank.
3. Confirm in the dialog. A reason is optional and is shown on the release page and to installers. Give one.
4. From a clean environment, `pip install proofcli` should select the newest release that is not yanked. `pip install proofcli==X.Y.Z` still installs the yanked version.

## 2. Cut a fixed release

1. Fix the problem on a branch and add a regression test that fails without the fix.
2. Bump both package version declarations from [the release procedure](releasing.md): `version` under `[project]` in `pyproject.toml`, and `__version__` in `proofcli/__init__.py`. Add a changelog entry that names the yanked version and what was wrong.
3. Update version pins in `README.md` and `docs/` (`proofcli==`, `bk1202/proofcli@v`, and `/proofcli/releases/tag/v` links). `tools/check_versions.py` checks those. It also checks release tags in `.github/workflows/demo-video.yml` and `bk1202/proofcli@v` pins in the demo source. It does not check `CHANGELOG.md`.
4. Follow [the release procedure](releasing.md) from step 2. The new version must be higher than the yanked one (for example `0.4.4` after yanking `0.4.3`).
5. Pushing the annotated `v<version>` tag runs `release.yml` (Release assets). When that run succeeds, `pypi.yml` starts from the default branch. It does not start after a failed release. The upload is the `publish` job. That job uses the `pypi` environment, which requires approval from bk1202 before the files go to PyPI. Open the waiting run and approve it.
6. Do the post-publish checks in [the release procedure](releasing.md) step 7, including a fresh `pip install proofcli==<new version>`.

## 3. Tidy the GitHub side

- Leave the old tag in place. Do not move or reuse it.
- Edit the old GitHub Release notes to say the version was yanked, why, and which version replaces it.
- If the GitHub Action (`bk1202/proofcli@v...`) was affected, say which tag users should move to.

## 4. If the upload itself failed halfway

Do not retry blindly. Check whether the version now exists on PyPI. If it does and the files are fine, nothing more is needed. If it exists and is bad, yank it and release a new version as above. If it does not exist, rerun the failed `publish` job in `pypi.yml`. That job uploads the distributions the `distributions` job already checked. It does not build them again.
