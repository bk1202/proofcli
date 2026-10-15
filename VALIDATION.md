# Validation evidence — 0.3.0

Local validation used Windows and CPython 3.10.6 on October 14, 2026.

- Source suite: 87 tests run successfully, 5 explicit skips (POSIX signal/detach behavior and local link-creation restrictions).
- Installed-wheel suite outside the source tree: 87 tests run successfully, 5 explicit skips, in 32.849 seconds. A subsequently added literal-punctuation filename regression also passed; its paired POSIX FIFO regression requires hosted validation.
- Wheel metadata/license/entry-point checks, fresh venv installation and real execution passed. Rebuilding the sdist into a wheel and repeating installation/execution passed. The child interpreter imported the installed package and retained its virtual environment.
- All six hash-locked build tools were checked against PyPI's version-specific advisory feed and published wheel hashes; no advisory entries were returned. This is a point-in-time feed check, not independent source/security certification. There are zero declared runtime dependencies.
- Baseline failures were actually reproduced: numeric JSON false positive, regex hang requiring an external watchdog, and delayed termination after output overflow. The audit document distinguishes observations from source-inspection findings.

The final regression inventory has 89 tests. Hosted CI runs installed-command tests on Windows/macOS with Python 3.10/3.13, two wheel/sdist installation jobs, and an advisory job. Platform-specific skips are expected; never count a skip as a pass. Refer to the candidate/release workflow results for hosted outcomes rather than extrapolating from the Windows sandbox.

Local temporary files use a writable workspace directory because the sandbox restricts atomic renames in its OS temp area. Those restrictions are not treated as a ProofCLI guarantee or a reason to weaken atomic report writing.

See [the audit](docs/audit-0.3.md) for unresolved limits. Test results do not establish arbitrary semantic correctness, sandboxing, or universal production readiness.
