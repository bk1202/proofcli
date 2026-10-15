"""Private assertion worker: a pathological regex cannot hang the supervisor."""

import json
from pathlib import Path
import re
import sys

from .assertions import validate_file_content


def evaluate(payload):
    from .runner import _check, _file_check
    checks = []
    spec = payload["spec"]
    root = Path(payload["root"])
    for stream in ("stdout", "stderr"):
        key = stream + "_regex"
        if key in spec["expect"]:
            matched = re.search(spec["expect"][key], payload[stream]) is not None
            checks.append(_check(key, matched, spec["expect"][key], {"matched": matched}))
    for expected in spec["expect"]["files"]:
        check = _file_check(root, expected, payload["input_identities"])
        checks.append(check)
        if check["passed"]:
            checks.extend(validate_file_content(root.joinpath(*expected["path"].split("/")), expected))
    return checks


def main():
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    checks = evaluate(payload)
    Path(sys.argv[2]).write_text(json.dumps(checks, ensure_ascii=True, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    main()
