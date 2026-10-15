# Validation

Validated locally on Windows with Python 3.10.6 on October 14, 2026.

- Built the 0.2.0 Python wheel and installed it into a separate virtual environment.
- Ran `PROOFCLI_TEST_INSTALLED=1 python -m unittest discover -s tests -v` with that environment's command on PATH: **64 tests run, 63 passed, 1 skipped** in 17.266 seconds. CLI invocations ran outside the source tree without a source PYTHONPATH. The skipped hard-link test cannot create hard links in the local sandbox; it runs on filesystems that support them.
- Source tests also passed. Local tests use a writable workspace temporary directory because the execution sandbox prohibits atomic renames in its OS temporary directory.
- The real export example stages a three-row CSV, produces a JSON summary and normalized CSV, and passes content checks. Its broken variant produces valid, nonempty files and exits 0, while ProofCLI returns 1 because JSON totals and CSV row counts are wrong. Failed artifacts are retained for inspection when requested.
- Tests exercise real processes and files, including descendant timeout cleanup, separate stdout/stderr, literal shell characters, Windows batch-file rejection, fresh directories, content validation, strict schemas, input staging, saved reports, and artifact preservation. No process behavior is mocked.

The Windows/macOS, Python 3.10/3.13 GitHub Actions matrix runs the installed command and real-process tests. Check the repository's Actions page for hosted platform results. Two batch-file tests apply only to Windows and are skipped on macOS.

Passing these tests establishes the documented MVP behavior. It does not establish semantic correctness of arbitrary files or make the temporary directory a security sandbox. See the README for the contract and limits.
