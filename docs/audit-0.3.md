# 0.3 adversarial audit

Maintainer-led review and real-process regressions against baseline `67ca72b` (0.2.0). This is not an independent third-party review, benchmark, or production certification. All implementation modules, tests, examples, packaging, manifest, and CI were inspected.

| Finding | Evidence | Response |
| --- | --- | --- |
| JSON numeric false positive | A real command wrote `{"n":1.0000000000000001}`; expectation `1.0` passed in 0.2.0. | Decimal comparisons and precision-safe specs. |
| Regex hang | `(a+)+$` on 30 `a` plus `!` required an external three-second watchdog. | Separate supervised worker/deadline. |
| Ineffective output limit | A real command wrote 2 MiB then slept; old CLI waited and retained an unbounded temporary log. | Bounded pipes and active overflow termination. |
| POSIX normal-exit orphan | Source inspection: baseline terminated groups only on timeout/exception. | Cleanup on every exit; real descendant/detached-pipe tests. |
| Lost venv interpreter | Source inspection: executable symlink resolution maps POSIX venv Python to base Python. | Preserve lexical executable path; installed-wheel/sdist child-import checks. |
| Link/normalization aliases | Source inspection: outputs followed links and filenames used casefold without NFC. | Reject aliases/links; real filesystem tests where supported. |
| Lost reports and vague failures | Write errors discarded completed evidence; semantic failures were booleans/counts. | Preserve reports/evidence; precise field/header/record diagnostics. |
| Release gaps | Floating Actions, no sdist-install gate/changelog/release flow. | Immutable pins, hashed tools, clean installs/rebuilds, advisory checks, gated assets. |

Baseline timings were single failure reproductions, not performance comparisons. Coverage also includes Unicode paths, malformed/oversized specs, device names, signals, unexpected exits, wrong data, input fingerprints, stale output, and report errors. Skips are explicit when the OS/filesystem cannot provide a feature. See `VALIDATION.md` and hosted CI for actual results; a test inventory is not proof of a pass.

## Unresolved limits

1. Commands have full user permissions; no general output-file disk, memory, CPU, or network quota.
2. Detached POSIX sessions can survive group cleanup. Pipe draining is bounded/fails closed, but detached work may survive. SIGKILL/crashes and uninterruptible native I/O can prevent cleanup. Windows uses documented Job Objects and CPython's process handle.
3. Filesystem checks/copy hashes are not atomic snapshots and do not defeat hostile external path swaps. Locale, clock, randomness, timestamps, and external-service state are not fixed by fixture bytes.
4. Command/assertion deadlines are separate; cleanup adds a bounded grace interval. Specs/semantic reads are capped at 1 MiB; internal assertion reports at 8 MiB. Python regex and Excel-style CSV semantics are retained.
5. Reports are unsigned, logs use UTF-8 replacement decoding, and only declared properties are verified. Weak fixtures or assertions can still accept bad results.
6. An independent maintainer/security review and actual adoption feedback remain outstanding. Green CI does not erase these limits.
