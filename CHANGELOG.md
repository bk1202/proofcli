# Changelog

## Unreleased

### Changed

- Human-readable output now leads with failing checks: each shows the differing JSON/CSV path, the reason, and the expected and actual values on separate lines as JSON. Passing checks collapse into a count. Child stdout/stderr and the temporary directory are still printed, as before, on passing and failing runs.
- Errors raised before a command runs (usage errors, missing spec, existing artifact directory, existing `init` target) print the error itself instead of `ERROR: command` and `Exit: None; elapsed: 0.000s`.
- The timeout check reads `finished in 0.071s (limit 10s)` or `timed out: exceeded the 1s limit` instead of `expected 10; actual False`.

No report schema changes: `--json` and `--report` output is identical.

## 0.4.1 — 2026-10-15

### Fixed

- Latch handled interrupts while supervising a process instead of raising between a pipe read and saving its bytes. A macOS CI run exposed this timing-sensitive output-loss case after the 0.4.0 drain fix.
- Preserve bounded pipe draining when an interrupt arrives after process-tree cleanup has started. The real child-to-parent signal regression now repeats 20 times per POSIX test run.

No contract or report schema changes. Custom caller-installed signal handlers and ignored/default signals remain unchanged; ProofCLI defers only its own interruption handlers and Python's standard Ctrl+C handler during supervision.

## 0.4.0 — 2026-10-15

### Fixed

- Reject invalid UTF-8 in captured logs instead of letting replacement characters satisfy regex assertions. Reports retain the offending captured bytes as base64 and identify the first decoding error.
- Drain pending pipe data after handled interruption, within the existing capture and drain limits.
- Include truncation, incomplete-pipe, and encoding diagnostics in the output-capture check.

### Added

- A composite GitHub Action with Python setup, reports, exit-code propagation, and a job summary. No package installation is needed by consumers.
- A 30-second demo built from actual exporter and CLI results, plus an intentionally failing workflow that contrasts an exit-code-only step with output verification.
- PyPI Trusted Publishing after successful GitHub release validation, using the same checksum-verified distribution files.
- Linux runtime and cross-platform Action integration checks.

### Compatibility

Invalid UTF-8 output now fails verification, including contracts with file-only checks. Decoded log fields remain available for inspection; `output_bytes_base64` preserves the captured prefix for invalid streams. Binary logs are not supported as passing text output. Existing UTF-8 contracts and spec version 1 remain supported.

## 0.3.0 — 2026-10-15

### Fixed

- Stop output overflow with bounded pipes instead of unbounded temporary logs.
- Bound regex/content verification using a supervised assertion worker/deadline.
- Clean ordinary POSIX descendants on normal completion; bound draining of pipes held by detached children.
- Handle SIGTERM/Windows break; preserve interruption reports and execution evidence on report-write errors.
- Compare output decimals precisely and reject precision-losing spec numbers.
- Preserve venv interpreter paths instead of dereferencing Python symlinks.
- Reject output links/reparse points, staged-input hard-link aliases, normalization/device aliases, overlapping destinations, lone surrogates, and oversized/nonregular specs.
- Escape terminal controls in human diagnostics.

### Added

- Exact JSON (`json_equals`), exact CSV headers/ordered records, and precise mismatch locations/values.
- Fixture fingerprints, `verification_complete`, and a separate assertion deadline.
- Real regressions for lying summaries, missing records, wrong values, and unexpected columns.
- Wheel/sdist install/rebuild gates, hashed build tools, immutable Actions pins, advisories/checksums, and gated release assets.

### Compatibility

Spec version 1 and legacy invocation remain. Subset/count defaults are unchanged. Output overflow now stops execution, ordinary background POSIX children do not survive completion, and ambiguous/link-based contracts or precision-losing spec decimals are rejected. This is a pre-1.0 hardening release, not independent security certification or universal production readiness.

## 0.2.0 — 2026-10-14

- Input staging, JSON/CSV/text checks, authoring/validation commands, reports/artifacts, and public Windows/macOS CI.

## 0.1.0 — 2026-10-14

- Initial local argv/exit/log/file-size prototype, temporary directories, reports, tests, and MIT license.
