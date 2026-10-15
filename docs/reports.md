# Reports and errors

`--json` writes one JSON object on stdout. `--report PATH` uses a UTF-8 temporary file in the same directory plus atomic replacement. Write failure returns `error`/exit 2 while preserving execution evidence on stdout. Preflight errors are saved when a safe destination is known; protected/ambiguous paths are never written. Reports are unsigned.

Schema version remains `1`; consumers should tolerate added fields and check `status`:

- `passed`: all requested checks completed and passed.
- `failed`: command/assertion/deadline/output failure.
- `error`: configuration, supervision, cleanup, or I/O prevented normal verification.
- `interrupted`: handled SIGINT/SIGTERM/Windows break; verification may be incomplete.
- `valid`/`created`: schema validation/starter creation; neither executes a command.

Run reports contain `name`, resolved `argv`, child `exit_code`, `timed_out`, captured `stdout`/`stderr`, `checks`, `duration_seconds`, historical `workdir`, retained `artifacts`, and input byte fingerprints. `output_truncated` marks overflow; `output_incomplete` marks pipes that could not reach EOF after ordinary-tree cleanup.

`verification_complete` means the assertion worker returned the requested checks within its deadline. A failed file precondition skips that file's content checks and fails the run. Missing checks after interruption/deadline are **unverified**, not passes. Preflight error reports may omit run-only fields.

Checks have `name`, `passed`, `expected`, and `actual`. JSON differences identify the first mismatch with a `$`-rooted JSON Pointer, reason, and bounded previews. CSV differences identify headers/counts or the first differing record/field. A failed `verification` check means the worker could not return a bounded report within its deadline.

Exit codes are `0` success, `1` command/assertion/deadline failure, `2` spec/supervision/I/O, `130` SIGINT/Windows break, `143` SIGTERM. A negative POSIX child return code indicates a signal and is separate from ProofCLI's exit.

Reports contain arguments, paths, hashes, and logs. Keep them private when those are sensitive. SHA-256 identifies fixture bytes, not provenance or correctness beyond assertions.
