# Changelog

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
