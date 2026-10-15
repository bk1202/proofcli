"""Bounded semantic assertions against real UTF-8 output files."""

import csv
import io
import re
from decimal import Decimal
from pathlib import Path

from .spec import SpecError, strict_json_loads

SEMANTIC_READ_LIMIT = 1024 * 1024


def _check(expected, kind, passed, actual):
    return {
        "name": f"file:{expected['path']}:{kind}", "passed": passed,
        "expected": expected[kind], "actual": actual,
    }


def _preview(value):
    if isinstance(value, Decimal):
        return {"number": str(value)}
    if isinstance(value, dict):
        return {"type": "object", "keys": list(value)[:10], "key_count": len(value)}
    if isinstance(value, list):
        return {"type": "array", "length": len(value)}
    if isinstance(value, str) and len(value) > 256:
        return value[:256] + "..."
    return value


def _difference(actual, expected, *, subset=False, path="$"):
    def mismatch(reason):
        return {"path": path, "reason": reason, "expected": _preview(expected), "actual": _preview(actual)}
    if type(expected) is dict and type(actual) is dict:
        for key, value in expected.items():
            pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in actual:
                return {"path": pointer, "reason": "missing field", "expected": _preview(value)}
            difference = _difference(actual[key], value, subset=subset, path=pointer)
            if difference:
                return difference
        if not subset and actual.keys() != expected.keys():
            return mismatch("unexpected fields: " + repr(sorted(actual.keys() - expected.keys())[:10]))
        return None
    if type(expected) is list and type(actual) is list:
        if len(actual) != len(expected):
            return mismatch("array length differs")
        for index, (left, right) in enumerate(zip(actual, expected)):
            difference = _difference(left, right, path=path + "/" + str(index))
            if difference:
                return difference
        return None
    numeric = (int, float, Decimal)
    if type(expected) in numeric and type(actual) in numeric:
        if Decimal(str(actual)) == Decimal(str(expected)):
            return None
    elif type(actual) is type(expected) and actual == expected:
        return None
    return mismatch("value or type differs")


def _csv_check(text, expected):
    # csv's default single-field limit is smaller than the file read budget.
    # Restore it so the callable API does not permanently change caller settings.
    previous_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(max(previous_limit, SEMANTIC_READ_LIMIT))
        return _read_csv(text, expected)
    finally:
        csv.field_size_limit(previous_limit)


def _read_csv(text, expected):
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = next(reader)
    except StopIteration:
        raise ValueError("CSV is empty; a header row is required") from None
    if not headers or any(not header.strip() for header in headers):
        raise ValueError("CSV headers must be nonempty")
    if len(set(headers)) != len(headers):
        raise ValueError("CSV headers must be unique")
    rows = 0
    difference = None
    for row in reader:
        if len(row) != len(headers):
            raise ValueError(f"CSV row {reader.line_num} has {len(row)} fields; expected {len(headers)}")
        if "rows" in expected and difference is None:
            if rows < len(expected["rows"]):
                difference = _difference(dict(zip(headers, row)), expected["rows"][rows], path="$/rows/" + str(rows))
            else:
                difference = {"path": "$/rows/" + str(rows), "reason": "unexpected record"}
        rows += 1
    missing = [column for column in expected.get("columns", []) if column not in headers]
    actual = {"columns": headers, "rows": rows, "missing_columns": missing}
    exact = not expected.get("exact_columns", False) or headers == expected["columns"]
    if not exact:
        actual["column_mismatch"] = {"expected": expected["columns"], "actual": headers}
    if "rows" in expected and rows != len(expected["rows"]) and difference is None:
        difference = {"path": "$/rows", "reason": "record count differs",
                      "expected": len(expected["rows"]), "actual": rows}
    if difference:
        actual["difference"] = difference
    return not missing and exact and not difference and rows >= expected.get("min_rows", 0), actual


def validate_file_content(path: Path, expected: dict) -> list:
    """Return requested semantic checks; unreadable/malformed data fails closed.

    The runner first verifies containment, regular-file status and minimum size.
    This function also handles missing paths safely when used independently.
    """
    kinds = [kind for kind in ("text_regex", "json_contains", "json_equals", "csv") if kind in expected]
    if not kinds:
        return []
    try:
        with Path(path).open("rb") as handle:
            data = handle.read(SEMANTIC_READ_LIMIT + 1)
        if len(data) > SEMANTIC_READ_LIMIT:
            raise ValueError(f"semantic file exceeds {SEMANTIC_READ_LIMIT} byte read limit")
        text = data.decode("utf-8-sig", errors="strict")
    except (OSError, UnicodeError, ValueError) as exc:
        return [_check(expected, kind, False, {"error": str(exc)}) for kind in kinds]
    checks = []
    for kind in kinds:
        try:
            if kind == "text_regex":
                passed = re.search(expected[kind], text) is not None
                actual = {"matched": passed}
            elif kind in ("json_contains", "json_equals"):
                value = strict_json_loads(text, precise=True)
                difference = _difference(value, expected[kind], subset=(kind == "json_contains"))
                passed = difference is None
                actual = {"contains" if kind == "json_contains" else "equals": passed}
                if difference:
                    actual["difference"] = difference
            else:
                passed, actual = _csv_check(text, expected[kind])
        except (SpecError, ValueError, UnicodeError, csv.Error, re.error, OverflowError, RecursionError) as exc:
            passed, actual = False, {"error": str(exc)}
        checks.append(_check(expected, kind, passed, actual))
    return checks
