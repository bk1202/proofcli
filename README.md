# ProofCLI

Acceptance checks for commands that produce files.

A command can exit 0, print “done,” and still write the wrong result. ProofCLI runs it against a declarative JSON contract: stage known inputs in a fresh working directory, check the exit code and logs, inspect output contents, and keep a report and artifacts when requested.

Use it as a small CI acceptance gate for exporters, data transforms, generators, and agent-produced artifacts. A pass means the declared assertions passed. Choosing assertions that establish the promised result remains your responsibility.

Python 3.10+ · Windows 10/11 and macOS · Standard-library-only runtime · MIT

## Quickstart

```console
git clone https://github.com/bk1202/proofcli.git
cd proofcli
python -m pip install .
proofcli validate examples/export/good.json
proofcli run examples/export/good.json --artifacts evidence-good --report good-report.json
proofcli run examples/export/false-success.json --artifacts evidence-broken --report broken-report.json
```

The first export passes: it reads a three-row CSV fixture and writes a JSON summary plus normalized CSV. The broken export deliberately drops every record while printing success and exiting 0. Its files are valid and nonempty, so presence and size checks pass. ProofCLI returns **1** because the JSON summary and CSV row count violate the contract. The retained broken files make the failure inspectable.

Artifact directories must be new; choose a new name before repeating these commands. Report files are replaced when you explicitly reuse their paths. The spec and staged input sources are protected from report replacement.

You can also install with `python -m pip install git+https://github.com/bk1202/proofcli.git` when Git is installed. On macOS, use `python3` if that is your Python executable. `python -m proofcli` works in place of `proofcli`.

## Commands

```console
proofcli init proofcli.json
proofcli validate proofcli.json
proofcli run proofcli.json
proofcli run proofcli.json --json
proofcli run proofcli.json --artifacts evidence --report report.json
```

- `init PATH` writes a working starter spec. It refuses to replace an existing file unless you add `--force`.
- `validate SPEC` checks the spec without executing the command. It does not establish that its executable or input files are available, or that its assertions will pass.
- `run SPEC` executes the command and checks its results.
- `--json` emits one JSON report on stdout, including captured child logs.
- `--report PATH` saves the complete JSON report, whether stdout uses human or JSON format.
- `--artifacts DIR` copies declared output files into a new directory, preserving relative paths. It also keeps files whose content assertions failed, provided they are regular files inside the work directory.

The original `proofcli SPEC` form still runs a spec. `--version` and `--help` are available.

## A useful output contract

The runnable [export example](examples/export/good.json) uses this shape:

```json
{
  "version": 1,
  "name": "CSV export acceptance check",
  "argv": ["{python}", "{spec_dir}/export.py", "input.csv", "report.json"],
  "inputs": [{"source": "fixtures/input.csv", "dest": "input.csv"}],
  "timeout_seconds": 5,
  "expect": {
    "exit_code": 0,
    "stdout_regex": "Export complete",
    "files": [
      {
        "path": "report.json",
        "min_size": 1,
        "json_contains": {
          "currency": "CAD",
          "summary": {"row_count": 3, "total": "33.75"}
        }
      },
      {
        "path": "report.csv",
        "min_size": 1,
        "csv": {"columns": ["id", "customer", "amount"], "min_rows": 3}
      }
    ]
  }
}
```

The fixture is copied from beside the spec into the work directory before execution. `{spec_dir}` locates the exporter without relying on the caller's current directory. The deliberately [broken spec](examples/export/false-success.json) runs the same exporter with `--broken`.

| Field | Contract |
| --- | --- |
| `version` | Required integer `1`. |
| `name` | Optional nonempty report name. |
| `argv` | Required nonempty array of strings; no implicit shell. |
| `inputs` | Optional array of `{"source": "...", "dest": "..."}` file copies. Source is relative to the spec directory; destination is relative to the work directory. |
| `timeout_seconds` | Finite number greater than `0` and at most `86400`; default `10`. |
| `expect.exit_code` | Expected integer child exit code; default `0`. |
| `expect.stdout_regex`, `expect.stderr_regex` | Optional nonempty Python regular expressions, matched with `re.search`. |
| `expect.files[].path` | Relative path of a required regular output file. |
| `expect.files[].min_size` | Inclusive minimum size in bytes; default `0`. |
| `expect.files[].text_regex` | Python regular expression over UTF-8 file text. |
| `expect.files[].json_contains` | Expected JSON object subset, including nested objects. Extra object keys are allowed. Arrays match exactly; booleans are distinct from numbers. |
| `expect.files[].csv.columns` | Required CSV header names. Extra columns are allowed. |
| `expect.files[].csv.min_rows` | Minimum number of data rows, excluding the header. |

Specs are UTF-8 JSON; a UTF-8 BOM is accepted. Unknown fields, duplicate JSON keys, invalid types, and nonfinite numbers are rejected. At least one log regex or output-file assertion is required in addition to the exit code.

Paths in `inputs` and `expect.files` use forward slashes and must be portable relative paths without traversal. Input sources must resolve to regular files inside the spec directory, including through symlinks. Input destinations cannot also be expected output paths. Duplicate destinations and output paths are rejected, ignoring case.

Regexes have no implicit flags. Use inline flags such as `(?m)` when needed, and escape backslashes in JSON. For print output across Windows and macOS, `"done\\r?\\n"` accepts CRLF and LF. CSV checks reject duplicate headers and ragged rows. JSON checks reject malformed JSON, duplicate keys, and nonfinite numbers.

## Execution and evidence

Every run starts with a fresh temporary work directory. Only declared inputs are staged there. The command receives no interactive stdin. It inherits the environment.

Use an absolute executable or a name on `PATH`. The exact first token `{python}` selects ProofCLI's Python interpreter. `{spec_dir}` and `{work_dir}` in arguments expand to their absolute directories. There is no variable expansion, globbing, or pipe/redirection interpretation. Windows `.bat` and `.cmd` executables are rejected because Windows can route them through a shell.

By default the work directory and generated files are deleted after verification. Its path in the report is historical. Use `--artifacts` to retain declared outputs and `--report` to save the result. Human output lists each check; JSON output keeps child stdout and stderr inside report fields.

Captured logs in a report are capped at **1 MiB per stream**, decoded as UTF-8 with invalid bytes replaced. Exceeding the cap fails the run. Logs are collected in temporary files until the process ends, so the cap does not limit disk usage or stop the command early. Content checks (`text_regex`, `json_contains`, `csv`) accept files up to **1 MiB**; larger files fail those checks. Existence and size checks can inspect larger files.

| ProofCLI exit code | Meaning |
| --- | --- |
| `0` | All run checks passed, or validation/spec creation succeeded. |
| `1` | An assertion failed, the process could not start, or it timed out. |
| `2` | Invalid spec, usage, or I/O error. |
| `130` | Interrupted. |

The child's exit code is separate from ProofCLI's exit code. A spec can intentionally expect a nonzero child exit.

## Boundaries

**Run trusted commands and trusted specs.** A clean working directory is not an operating-system sandbox. Commands retain your user's permissions and can access files outside the work directory and the network. There are no CPU, memory, or disk quotas.

Commands must finish their work before exiting. On Windows 10/11, ProofCLI assigns a suspended process to a Job Object before its code runs; job setup failure prevents execution. The job terminates descendants on timeout/interruption and remaining descendants when it closes. On macOS, a new process session allows group termination on timeout/interruption; detached processes may escape. A timeout does not undo external side effects.

These checks establish specific properties, not universal correctness. A declared row count can still be fabricated; a media file can have the right size but the wrong duration. Use representative fixtures and assertions tied to the real promise. Format-aware media validation, YAML, command suites, and plugins are outside this release.

## Motivation and provenance

CLI-Anything reports describe path operations [announcing success while producing empty geometry (#406)](https://github.com/HKUDS/CLI-Anything/issues/406) and an [accepted audio duration differing from the rendered duration (#407)](https://github.com/HKUDS/CLI-Anything/issues/407). These reports motivated result assertions; they are not claims about every version of that project. Basic file-size checks would not reliably catch either semantic failure.

ProofCLI is independently implemented. No CLI-Anything code was copied.

## Development

```console
python -m pip install -e .
python -m unittest discover -s tests -v
```

Tests launch real subprocesses and inspect real files, including the export regression above. GitHub Actions installs the package and sets `PROOFCLI_TEST_INSTALLED=1` to exercise the installed command outside the source tree. The matrix covers Windows and macOS with Python 3.10 and 3.13. Check actual workflow results for platform verification; a committed workflow alone is not a completed run.

See [practical use cases](docs/use-cases.md), [contributing](CONTRIBUTING.md), and the [MIT license](LICENSE).
