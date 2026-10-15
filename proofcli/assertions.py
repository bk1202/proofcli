"""Bounded semantic assertions against real UTF-8 output files."""

import csv
import io
import re
from pathlib import Path

from .spec import SpecError, strict_json_loads

SEMANTIC_READ_LIMIT = 1024 * 1024


def _check(expected, kind, passed, actual):
    return {
        "name": f"file:{expected['path']}:{kind}", "passed": passed,
        "expected": expected[kind], "actual": actual,
    }


def _exact(actual, expected):
    if type(expected) is dict:
        return (type(actual) is dict and actual.keys() == expected.keys()
                and all(_exact(actual[key], value) for key, value in expected.items()))
    if type(expected) is list:
        return (type(actual) is list and len(actual) == len(expected)
                and all(_exact(left, right) for left, right in zip(actual, expected)))
    if type(expected) in (int, float) and type(actual) in (int, float):
        return actual == expected
    return type(actual) is type(expected) and actual == expected


def _contains(actual, expected):
    if type(expected) is dict:
        return (type(actual) is dict and all(
            key in actual and _contains(actual[key], value) for key, value in expected.items()
        ))
    return _exact(actual, expected)


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
    for row in reader:
        if len(row) != len(headers):
            raise ValueError(f"CSV row {reader.line_num} has {len(row)} fields; expected {len(headers)}")
        rows += 1
    missing = [column for column in expected.get("columns", []) if column not in headers]
    actual = {"columns": headers, "rows": rows, "missing_columns": missing}
    return not missing and rows >= expected.get("min_rows", 0), actual


def validate_file_content(path: Path, expected: dict) -> list:
    """Return requested semantic checks; unreadable/malformed data fails closed.

    The runner first verifies containment, regular-file status and minimum size.
    This function also handles missing paths safely when used independently.
    """
    kinds = [kind for kind in ("text_regex", "json_contains", "csv") if kind in expected]
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
            elif kind == "json_contains":
                value = strict_json_loads(text)
                passed = _contains(value, expected[kind])
                actual = {"contains": passed}
            else:
                passed, actual = _csv_check(text, expected[kind])
        except (SpecError, ValueError, UnicodeError, csv.Error, re.error, OverflowError, RecursionError) as exc:
            passed, actual = False, {"error": str(exc)}
        checks.append(_check(expected, kind, passed, actual))
    return checks
