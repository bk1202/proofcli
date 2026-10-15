# Validation evidence — 0.3.0

## 0.4.0 follow-up

The invalid-byte false positive was reproduced against 0.3.0: a command writing `FF` passed a replacement-character regex. New real-process regressions cover invalid stdout/stderr, byte recovery, correctly encoded replacement characters, split multibyte output, and interruption draining. The Action entry point is executed with passing, failing, malformed, and protected-report contracts.

Local Windows validation ran 94 tests successfully with 7 explicit platform/filesystem skips before the final Action report-error regression was added. Wheel installation and source rebuild/installation passed. The final inventory is 95 tests; final platform outcomes are recorded by the linked candidate/release workflows, not inferred from this inventory.

The demo's rendered MP4 was inspected at each scene and probed: H.264, 1920×1080, 900 frames, 30.000 seconds. Its messages and mismatch values come from an actual exporter subprocess and an actual CLI subprocess. The locked demo dependency audit returned zero advisory entries after unused scaffold lint dependencies were removed. A real download of the 0.3.0 release exercised the new PyPI transfer verifier against its exact tag commit and package checksums.

## 0.3.0 release

Local validation used Windows and CPython 3.10.6 on October 14, 2026.

- Source suite: 87 tests run successfully, 5 explicit skips (POSIX signal/detach behavior and local link-creation restrictions).
- Installed-wheel suite outside the source tree: 87 tests run successfully, 5 explicit skips, in 32.849 seconds. A subsequently added literal-punctuation filename regression also passed; its paired POSIX FIFO regression requires hosted validation.
- Wheel metadata/license/entry-point checks, fresh venv installation and real execution passed. Rebuilding the sdist into a wheel and repeating installation/execution passed. The child interpreter imported the installed package and retained its virtual environment.
- All six hash-locked build tools were checked against PyPI's version-specific advisory feed and published wheel hashes; no advisory entries were returned. This is a point-in-time feed check, not independent source/security certification. There are zero declared runtime dependencies.
- Baseline failures were actually reproduced: numeric JSON false positive, regex hang requiring an external watchdog, and delayed termination after output overflow. The audit document distinguishes observations from source-inspection findings.

The final regression inventory has 89 tests. Hosted CI runs installed-command tests on Windows/macOS with Python 3.10/3.13, two wheel/sdist installation jobs, and an advisory job. Platform-specific skips are expected; never count a skip as a pass. Refer to the candidate/release workflow results for hosted outcomes rather than extrapolating from the Windows sandbox.

The initial hosted candidate (`9aebb7e`) passed all four runtime-test jobs and the advisory job. Both distribution gates caught a checker bug comparing canonical extraction targets with noncanonical temporary roots (macOS `/var` and Windows 8.3 aliases). That check was fixed rather than disabled; packaging and release remain gated on the corrected candidate's results.

The corrected candidate (`569cbad`) passed [all seven hosted gates](https://github.com/bk1202/proofcli/actions/runs/38695358037): four runtime jobs, two distribution jobs, and the advisory check. Observed runtime summaries: Windows ran 89 tests with 3 platform/privilege skips; macOS ran 89 with 2 Windows-only skips. Later release-workflow changes are validated again before tagging; the release workflow also reruns the gates before publishing assets.

Local temporary files use a writable workspace directory because the sandbox restricts atomic renames in its OS temp area. Those restrictions are not treated as a ProofCLI guarantee or a reason to weaken atomic report writing.

See [the audit](docs/audit-0.3.md) for unresolved limits. Test results do not establish arbitrary semantic correctness, sandboxing, or universal production readiness.
