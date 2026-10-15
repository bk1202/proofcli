# Specification version 1

UTF-8 JSON with optional BOM; maximum 1 MiB. Unknown fields, duplicate keys, nonfinite numbers, invalid Unicode, and malformed regexes are errors before execution. Specification decimals that cannot round-trip through Python's float representation are rejected instead of rounded; encode precision-sensitive amounts as strings. Output decimals are compared precisely.

| Field | Meaning |
| --- | --- |
| `version` | Required integer `1`. |
| `name` | Optional nonempty label. |
| `argv` | Nonempty string array, no NULs; executable is absolute or on PATH. |
| `timeout_seconds` | Command deadline `(0, 86400]`, default `10`. |
| `verification_timeout_seconds` | Separate assertion deadline `(0, 60]`, default `5`. |
| `inputs` | Optional `{source, dest}` regular file copies. |
| `expect` | Required assertion object. |

Sources resolve inside the spec directory. Destinations/outputs use forward-slash relative paths without traversal, absolute/drive paths, controls, lone surrogates, Windows device aliases, or trailing dots/spaces. Names are compared case-insensitively after Unicode NFC normalization. Duplicate/overlapping destinations and input/output aliases are rejected. This portable policy is stricter than any one filesystem.

Fixtures are streamed to independent copies before execution; reports record copied bytes/SHA-256. A detected identity/size/mtime change during copying is an error, not an atomic snapshot guarantee against hostile writers. Permissions/timestamps are not replayed. Environment, locale, clock, random seeds, and external services remain the command author's responsibility.

## Assertions

`expect.exit_code` defaults to `0`. At least one log regex or file assertion must also be supplied. `stdout_regex`/`stderr_regex` use Python `re.search` without implicit flags. Logs are UTF-8 decoded with invalid bytes replaced; checks apply to that representation, not encoding validity.

Each `expect.files` entry requires `path` and supports:

| Property | Semantics |
| --- | --- |
| `min_size` | Inclusive nonnegative bytes; default `0` allows empty files. |
| `text_regex` | Nonempty Python regex over strict UTF-8-sig file text. |
| `json_contains` | Expected object subset, recursively for objects; arrays are exact/ordered, including keys within array objects. |
| `json_equals` | Any JSON value; exact keys, arrays/order, and scalar types/values. Numeric `1`/`1.0` compare equal; booleans do not equal numbers. |
| `csv` | Rules below. |

Semantic reads are capped at 1 MiB per file. Invalid JSON/UTF-8, duplicate keys, malformed CSV, or read/deadline limits fail closed. Size/existence checks support larger files. Output symlinks/reparse points and staged-input hard-link aliases are rejected. Path checks are not transactional protection against hostile external races.

CSV uses Python's Excel-style `csv.reader(..., strict=True)`, not a universal CSV-dialect validator. Headers are required; empty/duplicate names and ragged rows fail. Whitespace/text are not normalized; values are strings.

| CSV property | Semantics |
| --- | --- |
| `columns` | Nonempty unique required headers. Extras/different order remain allowed by default for compatibility. |
| `exact_columns` | Boolean requiring `columns`; true requires the exact ordered headers. |
| `min_rows` | Nonnegative minimum data records, excluding the header. |
| `rows` | Exact ordered record objects with string values; no missing/extra records, keys, or differing values. With `columns`, records require exactly those keys. |

A CSV object requires at least one rule. Use exact rows/columns for fixture acceptance; a minimum count cannot detect replaced or duplicated records.

## Compatibility

0.3 retains spec version 1 and legacy invocation. Existing subset/count semantics are unchanged. Intentional tightening: overflow terminates commands; ordinary POSIX children are cleaned on normal exit; link/device/normalization aliases and precision-losing spec decimals are rejected. See the changelog before upgrading workflows that relied on those behaviors.
