"""Validate semantic contracts against real files; no mocked command behavior."""

import json
from pathlib import Path
import tempfile
import unittest

from proofcli.assertions import SEMANTIC_READ_LIMIT, validate_file_content
from proofcli.spec import SpecError, strict_json_loads, validate_relative_path, validate_spec


class FileContentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="proofcli-content-test-")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name, "result")

    def check(self, content, kind, value):
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.path.write_bytes(content)
        checks = validate_file_content(self.path, {"path": "result", kind: value})
        self.assertEqual(len(checks), 1)
        check = checks[0]
        self.assertEqual(check["name"], "file:result:" + kind)
        self.assertEqual(check["expected"], value)
        self.assertIn("actual", check)
        return check

    def test_text_regex_matches_utf8_with_bom(self):
        self.assertTrue(self.check(b"\xef\xbb\xbfverified\r\n", "text_regex", r"^verified\r?\n$")["passed"])
        self.assertTrue(self.check("caf\u00e9", "text_regex", "caf\u00e9")["passed"])
        self.assertFalse(self.check("almost", "text_regex", "verified")["passed"])

    def test_json_object_subset_is_recursive(self):
        actual = {"report": {"ok": True, "rows": 4, "extra": "allowed"}, "other": 1}
        self.assertTrue(self.check(json.dumps(actual), "json_contains", {"report": {"ok": True}})["passed"])
        self.assertFalse(self.check(json.dumps(actual), "json_contains", {"report": {"rows": 5}})["passed"])
        self.assertFalse(self.check("[]", "json_contains", {})["passed"])

    def test_json_arrays_are_exact_and_boolean_is_not_number(self):
        for actual, expected, passes in (
            ('{"items":[1,2]}', {"items": [1, 2]}, True),
            ('{"items":[1,2,3]}', {"items": [1, 2]}, False),
            ('{"items":[2,1]}', {"items": [1, 2]}, False),
            ('{"items":[{"id":1,"extra":2}]}', {"items": [{"id": 1}]}, False),
            ('{"ok":1}', {"ok": True}, False),
            ('{"ok":true}', {"ok": 1}, False),
            ('{"items":[true]}', {"items": [1]}, False),
            ('{"count":1.0}', {"count": 1}, True),
        ):
            with self.subTest(actual=actual, expected=expected):
                self.assertEqual(self.check(actual, "json_contains", expected)["passed"], passes)

    def test_json_bom_is_accepted_and_invalid_json_fails_closed(self):
        self.assertTrue(self.check(b'\xef\xbb\xbf{"ok":true}', "json_contains", {"ok": True})["passed"])
        for content in (
            "not JSON", '{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}',
            '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e10000}',
            '{"x":"\\ud800"}', '{"\\ud800":1}',
        ):
            with self.subTest(content=content):
                check = self.check(content, "json_contains", {})
                self.assertFalse(check["passed"])
                self.assertIn("error", check["actual"])

    def test_csv_required_columns_and_data_rows(self):
        check = self.check("id,name,extra\r\n1,Ada,x\r\n2,Bob,y\r\n", "csv", {
            "columns": ["name", "id"], "min_rows": 2,
        })
        self.assertTrue(check["passed"])
        self.assertEqual(check["actual"]["rows"], 2)
        self.assertFalse(self.check("id,name\n1,Ada\n", "csv", {"columns": ["missing"]})["passed"])
        self.assertFalse(self.check("id,name\n1,Ada\n", "csv", {"min_rows": 2})["passed"])
        self.assertTrue(self.check("id,name\n", "csv", {"min_rows": 0})["passed"])

    def test_csv_quoting_bom_and_embedded_newline_are_valid(self):
        text = '\ufeffid,note\r\n1,"hello,\r\nworld"\r\n'
        check = self.check(text, "csv", {"columns": ["id", "note"], "min_rows": 1})
        self.assertTrue(check["passed"])
        self.assertEqual(check["actual"]["rows"], 1)

    def test_csv_large_field_within_file_read_limit_is_valid(self):
        check = self.check("note\n" + "x" * 200000 + "\n", "csv", {"columns": ["note"], "min_rows": 1})
        self.assertTrue(check["passed"])

    def test_csv_duplicate_empty_headers_ragged_and_malformed_rows_fail(self):
        for content in (
            "", "id,id\n1,2\n", ",name\n1,Ada\n", "id,name\n1\n",
            "id,name\n1,Ada,extra\n", 'id,name\n1,"unterminated\n',
        ):
            with self.subTest(content=content):
                check = self.check(content, "csv", {"min_rows": 0})
                self.assertFalse(check["passed"])
                self.assertIn("error", check["actual"])

    def test_missing_directory_invalid_utf8_and_large_files_fail_all_requested_checks(self):
        expected = {"path": "result", "text_regex": "x", "json_contains": {}, "csv": {"min_rows": 0}}
        for content in (None, b"\xff", b"x" * (SEMANTIC_READ_LIMIT + 1)):
            with self.subTest(content_length=None if content is None else len(content)):
                if content is not None:
                    self.path.write_bytes(content)
                checks = validate_file_content(self.path, expected)
                self.assertEqual(len(checks), 3)
                self.assertTrue(all(not check["passed"] and "error" in check["actual"] for check in checks))
        self.path.unlink()
        self.path.mkdir()
        self.assertTrue(all(not check["passed"] for check in validate_file_content(self.path, expected)))

    def test_exact_read_limit_is_accepted_and_no_assertions_needs_no_file(self):
        self.assertTrue(self.check(b"x" * SEMANTIC_READ_LIMIT, "text_regex", "^x+$")["passed"])
        self.assertEqual(validate_file_content(self.path.parent / "missing", {"path": "missing"}), [])


class SemanticSpecTests(unittest.TestCase):
    def spec(self, file=None, **extras):
        return {"version": 1, "argv": ["{python}", "-c", "pass"],
                "expect": {"files": [file or {"path": "result"}]}, **extras}

    def test_semantic_fields_and_inputs_normalize(self):
        value = self.spec({"path": "result", "text_regex": "ok", "json_contains": {"ok": True},
                           "csv": {"columns": ["id"], "min_rows": 1}},
                          inputs=[{"source": "fixtures/input.csv", "dest": "data/input.csv"}])
        normalized = validate_spec(value)
        self.assertEqual(normalized["inputs"], value["inputs"])
        self.assertEqual(validate_spec(self.spec())["inputs"], [])
        self.assertEqual(validate_relative_path("data/input.csv"), "data/input.csv")

    def test_invalid_semantic_fields_are_rejected(self):
        for field, invalid in (
            ("text_regex", ""), ("text_regex", "["), ("text_regex", True),
            ("json_contains", []), ("json_contains", None),
            ("json_contains", {"bad": float("nan")}),
            ("json_contains", {"bad": float("inf")}),
            ("json_contains", {"bad": {1: "integer key"}}),
            ("json_contains", {"bad": ("tuple",)}),
            ("csv", {}), ("csv", []), ("csv", {"unknown": 1}),
            ("csv", {"columns": []}), ("csv", {"columns": "id"}),
            ("csv", {"columns": [""]}), ("csv", {"columns": [" "]}),
            ("csv", {"columns": ["id", "id"]}), ("csv", {"columns": [1]}),
            ("csv", {"min_rows": -1}), ("csv", {"min_rows": True}),
            ("csv", {"min_rows": 1.5}),
            ("csv", {"columns": ["id"], "exact_columns": "yes"}),
            ("csv", {"exact_columns": True}), ("csv", {"rows": [{}]}),
            ("csv", {"rows": [{"id": 1}]}),
            ("csv", {"columns": ["id"], "rows": [{"other": "1"}]}),
        ):
            with self.subTest(field=field, invalid=invalid):
                with self.assertRaises(SpecError):
                    validate_spec(self.spec({"path": "result", field: invalid}))

    def test_input_shapes_paths_duplicates_and_output_overlap_are_rejected(self):
        for inputs in (
            None, {}, ["input"], [{}], [{"source": "in"}], [{"dest": "in"}],
            [{"source": "in", "dest": "out", "unknown": True}],
            [{"source": "../in", "dest": "out"}],
            [{"source": "in", "dest": "../out"}],
            [{"source": "in", "dest": "C:/out"}],
            [{"source": "in", "dest": "a\\b"}],
            [{"source": "in", "dest": "same"}, {"source": "other", "dest": "SAME"}],
            [{"source": "in", "dest": "RESULT"}],
        ):
            with self.subTest(inputs=inputs):
                with self.assertRaises(SpecError):
                    validate_spec(self.spec(inputs=inputs))

    def test_strict_json_rejects_invalid_numbers_and_duplicate_keys(self):
        for data in ('{"x":NaN}', '{"x":1e10000}', '{"x":1,"x":2}'):
            with self.subTest(data=data):
                with self.assertRaises(SpecError):
                    strict_json_loads(data)


if __name__ == "__main__":
    unittest.main()
