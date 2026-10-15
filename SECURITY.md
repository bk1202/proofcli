# Security policy

Treat commands, specs, fixtures, and execution environments as trusted. ProofCLI is an assertion runner, **not a sandbox**. Commands retain filesystem/network permissions and inherited environment. Process ownership/path checks address ordinary failures; they are not hostile-code containment.

Capture/read limits, assertion deadlines, process cleanup, and fresh directories reduce hangs, stale passes, and accidental consumption. Generated output files are not quota-controlled. SIGKILL/crashes, uninterruptible I/O, POSIX session breakaway, and concurrent path replacement cannot be universally controlled. See [the audit](docs/audit-0.3.md).

Reports are unsigned and can contain sensitive argv/paths/logs. Do not publish them blindly.

There are no runtime dependencies. Build tools are pinned with universal-wheel hashes. `tools/audit_dependencies.py` checks their versions/hashes against PyPI's advisory feed and fails on unavailable metadata or advisories. This point-in-time feed check is not a comprehensive source audit. CI pins action commits, uses read-only permissions and no persisted checkout credentials, and avoids privileged PR triggers. Only release publication gets repository write permission. No PyPI credentials/publication are configured.

Use **Security → Report a vulnerability** on GitHub when available. If private reporting is unavailable, open an issue requesting a private channel without disclosing exploit details or secrets. No private email or guaranteed response time is advertised.

This pre-1.0 project has no LTS commitment. Fixes target the latest release. Report regressions with version and a minimal, non-sensitive reproduction. No independent third-party security audit has been performed.
