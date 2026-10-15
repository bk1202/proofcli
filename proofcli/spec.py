"""Small, strict JSON contract. Validation never executes a command."""

import json
import math
import re
import stat
import unicodedata
from decimal import Decimal
from pathlib import Path, PureWindowsPath


class SpecError(ValueError):
    pass


SPEC_READ_LIMIT = 1024 * 1024


def canonical_path(value):
    return unicodedata.normalize("NFC", value).casefold()


def _keys(value, allowed, location):
    if not isinstance(value, dict):
        raise SpecError(f"{location} must be an object")
    unknown = value.keys() - allowed
    if unknown:
        raise SpecError(f"{location}: unknown field(s): {', '.join(sorted(unknown))}")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SpecError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise SpecError(f"invalid JSON number: {value}")


def _float(value):
    number = float(value)
    if not math.isfinite(number):
        raise SpecError(f"invalid JSON number: {value}")
    if Decimal(str(number)) != Decimal(value):
        raise SpecError(f"JSON number loses precision: {value}; encode exact decimals as strings")
    return number


def _precise_float(value):
    if not math.isfinite(float(value)):
        raise SpecError(f"invalid JSON number: {value}")
    return Decimal(value)


def strict_json_loads(data, *, precise=False):
    """Parse JSON without duplicate keys or nonfinite numbers."""
    value = json.loads(data, object_pairs_hook=_pairs, parse_constant=_constant,
                       parse_float=_precise_float if precise else _float)
    def unicode_strings(item):
        if isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeError as exc:
                raise SpecError("JSON strings must not contain lone Unicode surrogates") from exc
        elif isinstance(item, dict):
            for key, child in item.items():
                unicode_strings(key)
                unicode_strings(child)
        elif isinstance(item, list):
            for child in item:
                unicode_strings(child)
    unicode_strings(value)
    return value


def _output_path(value):
    if not isinstance(value, str) or not value:
        raise SpecError("file path must be a nonempty relative path")
    parts = value.split("/")
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved.update(f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10))
    reserved.update(f"{prefix}{i}" for prefix in ("COM", "LPT") for i in "¹²³")
    if (
        PureWindowsPath(value).drive
        or value.startswith("/")
        or any(c in value for c in '\\<>:"|?*')
        or any(unicodedata.category(c) in ("Cc", "Cs") for c in value)
        or any(p in ("", ".", "..") or p.endswith((" ", ".")) for p in parts)
        or any(p.split(".")[0].rstrip(" ").upper() in reserved for p in parts)
    ):
        raise SpecError(f"file path must be portable, relative, and contain no traversal: {value!r}")
    return value


validate_relative_path = _output_path


def _regex(value, location):
    if not isinstance(value, str) or not value:
        raise SpecError(f"{location} must be a nonempty regex string")
    try:
        re.compile(value)
    except (re.error, OverflowError, RecursionError) as exc:
        raise SpecError(f"{location}: invalid regex: {exc}") from exc


def _json_value(value):
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError as exc:
            raise SpecError("strings must contain valid Unicode, without lone surrogates") from exc
        return
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _json_value(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for key, item in value.items():
            _json_value(key)
            _json_value(item)
        return
    raise SpecError("json_contains must contain only JSON values and finite numbers")


def validate_spec(spec):
    try:
        _json_value(spec)
    except RecursionError as exc:
        raise SpecError("spec is nested too deeply") from exc
    _keys(spec, {"version", "name", "argv", "timeout_seconds", "verification_timeout_seconds", "expect", "inputs"}, "spec")
    if type(spec.get("version")) is not int or spec["version"] != 1:
        raise SpecError("version must be 1")
    name = spec.get("name", "command")
    if not isinstance(name, str) or not name.strip():
        raise SpecError("name must be a nonempty string")
    argv = spec.get("argv")
    if (
        not isinstance(argv, list) or not argv
        or any(not isinstance(arg, str) or "\x00" in arg for arg in argv)
        or not argv[0].strip()
    ):
        raise SpecError("argv must be a nonempty array of strings, with a nonempty executable and no NULs")
    timeout = spec.get("timeout_seconds", 10)
    if type(timeout) not in (int, float) or not 0 < timeout <= 86400 or not math.isfinite(timeout):
        raise SpecError("timeout_seconds must be a finite number greater than 0 and at most 86400")
    verification_timeout = spec.get("verification_timeout_seconds", 5)
    if type(verification_timeout) not in (int, float) or not 0 < verification_timeout <= 60:
        raise SpecError("verification_timeout_seconds must be greater than 0 and at most 60")
    expect = spec.get("expect")
    _keys(expect, {"exit_code", "stdout_regex", "stderr_regex", "files"}, "expect")
    exit_code = expect.get("exit_code", 0)
    if type(exit_code) is not int:
        raise SpecError("expect.exit_code must be an integer")
    for stream in ("stdout_regex", "stderr_regex"):
        if stream in expect:
            _regex(expect[stream], f"expect.{stream}")
    files = expect.get("files", [])
    if not isinstance(files, list):
        raise SpecError("expect.files must be an array")
    seen = set()
    for file in files:
        _keys(file, {"path", "min_size", "text_regex", "json_contains", "json_equals", "csv"}, "expect.files entry")
        _output_path(file.get("path"))
        key = canonical_path(file["path"])
        if key in seen:
            raise SpecError(f"duplicate file expectation: {file['path']}")
        seen.add(key)
        if any(other != key and (other.startswith(key + "/") or key.startswith(other + "/")) for other in seen):
            raise SpecError("expected file paths cannot contain one another")
        minimum = file.get("min_size", 0)
        if type(minimum) is not int or minimum < 0:
            raise SpecError("min_size must be a nonnegative integer (bytes)")
        if "text_regex" in file:
            _regex(file["text_regex"], "expect.files[].text_regex")
        if "json_contains" in file:
            if not isinstance(file["json_contains"], dict):
                raise SpecError("expect.files[].json_contains must be an object")
            try:
                _json_value(file["json_contains"])
            except RecursionError as exc:
                raise SpecError("json_contains is nested too deeply") from exc
        if "json_equals" in file:
            _json_value(file["json_equals"])
        if "csv" in file:
            table = file["csv"]
            _keys(table, {"columns", "min_rows", "exact_columns", "rows"}, "expect.files[].csv")
            if not table:
                raise SpecError("expect.files[].csv requires columns or min_rows")
            if "columns" in table:
                columns = table["columns"]
                if (not isinstance(columns, list) or not columns
                        or any(not isinstance(column, str) or not column.strip() for column in columns)
                        or len(set(columns)) != len(columns)):
                    raise SpecError("csv.columns must be a nonempty array of unique nonempty strings")
            if "min_rows" in table and (type(table["min_rows"]) is not int or table["min_rows"] < 0):
                raise SpecError("csv.min_rows must be a nonnegative integer")
            if "exact_columns" in table:
                if type(table["exact_columns"]) is not bool or "columns" not in table:
                    raise SpecError("csv.exact_columns must be boolean and requires csv.columns")
            if "rows" in table:
                if not isinstance(table["rows"], list) or any(
                    not isinstance(row, dict) or not row or
                    any(not isinstance(value, str) for value in row.values()) for row in table["rows"]
                ):
                    raise SpecError("csv.rows must be an array of nonempty objects with string field values")
                if "columns" in table and any(set(row) != set(table["columns"]) for row in table["rows"]):
                    raise SpecError("every csv.rows record must have exactly the csv.columns keys")
    inputs = spec.get("inputs", [])
    if not isinstance(inputs, list):
        raise SpecError("inputs must be an array")
    destinations = set()
    normalized_inputs = []
    for item in inputs:
        _keys(item, {"source", "dest"}, "inputs entry")
        source = validate_relative_path(item.get("source"))
        dest = validate_relative_path(item.get("dest"))
        key = canonical_path(dest)
        if key in destinations:
            raise SpecError(f"duplicate input destination: {dest}")
        if key in seen:
            raise SpecError(f"input destination cannot also be an expected output: {dest}")
        destinations.add(key)
        if any(other != key and (other.startswith(key + "/") or key.startswith(other + "/")) for other in destinations):
            raise SpecError("input destinations cannot contain one another")
        normalized_inputs.append({"source": source, "dest": dest})
    if not files and not any(key in expect for key in ("stdout_regex", "stderr_regex")):
        raise SpecError("expect requires at least one stdout/stderr regex or output file check beyond exit code")
    return {
        "version": 1, "name": name, "argv": list(argv), "timeout_seconds": timeout,
        "verification_timeout_seconds": verification_timeout,
        "expect": {**expect, "exit_code": exit_code, "files": files},
        "inputs": normalized_inputs,
    }


def load_spec(path):
    try:
        # utf-8-sig accepts JSON saved with a Windows UTF-8 BOM.
        if not stat.S_ISREG(Path(path).stat().st_mode):
            raise SpecError("spec must be a regular file")
        with Path(path).open("rb") as handle:
            raw = handle.read(SPEC_READ_LIMIT + 1)
        if len(raw) > SPEC_READ_LIMIT:
            raise SpecError(f"spec exceeds {SPEC_READ_LIMIT} byte limit")
        data = raw.decode("utf-8-sig")
        return validate_spec(strict_json_loads(data))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise SpecError(f"cannot read spec: {exc}") from exc
