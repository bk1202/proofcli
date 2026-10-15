# Release procedure

1. Inspect confirmed defects, compatibility changes, and unresolved limits. Update both package version declarations, changelog, and docs; do not infer readiness from test count.
2. Install the hash-locked build tools, build wheel/sdist, run `tools/verify_dist.py`, then run the real-process suite against the installed wheel. `tools/audit_dependencies.py` checks build versions/hashes against PyPI's advisory feed; no runtime dependencies are declared.
3. Only after local validation, publish the candidate branch and obtain green Windows/macOS tests, both distribution-install jobs, and the advisory job. Inspect skips/failures. Merge the same reviewed candidate into main; retain CI links as evidence.
4. Create and push an annotated `v<package-version>` tag targeting the validated commit. A pre-1.0 release is not a production/security certification.
5. The tag triggers `release.yml`. The read-only reusable validation matrix must pass again before the publish job gets scoped `contents: write`. It checks tag/version agreement, builds with pinned tools, verifies fresh wheel/sdist installs, extracts accurate notes from the versioned changelog, and creates the GitHub release with both distributions plus `SHA256SUMS`. No PyPI publication occurs.
6. Confirm the release workflow and actual downloadable assets/checksums before announcing completion. Release creation deliberately does not overwrite an existing release; failed/partial releases require maintainer inspection rather than silently replacing published bytes.

Actions are pinned to immutable official commits; checkout credentials are not persisted. There are no privileged PR triggers or user text interpolated into shell source. Release tags enter shell commands through quoted environment variables. Only the publish job receives write permissions; no long-lived publishing token is stored.

Build-tool locks contain universal wheels and all dependencies needed by supported Python versions. When updating them, review upstream projects/versions, download from PyPI, regenerate hashes, audit advisories, and rerun every platform/package gate. This locks tooling; bit-for-bit reproducible archives across all hosts are not claimed.
