"""Export a small CSV dataset to a JSON summary and normalized CSV.

The --broken switch deliberately demonstrates a false-success regression:
the command exits zero and writes valid, nonempty files with incorrect contents.
"""

import argparse
import csv
from decimal import Decimal
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--broken", action="store_true")
    parser.add_argument("--fault", choices=("missing-record", "wrong-value", "extra-column"))
    args = parser.parse_args()

    with args.source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    normalized = [
        {
            "id": row["id"],
            "customer": row["customer"],
            "amount": format(Decimal(row["amount"]), ".2f"),
        }
        for row in rows
    ]
    if args.broken:
        # Simulate a regression that drops records while still reporting success.
        normalized = []

    total = sum((Decimal(row["amount"]) for row in normalized), Decimal("0"))
    original_count = len(normalized)
    if args.fault == "missing-record":
        normalized = normalized[:-1]
    elif args.fault == "wrong-value":
        normalized[1]["amount"] = "999.00"
    report = {
        "currency": "CAD",
        "summary": {"row_count": original_count, "total": format(total, ".2f")},
        "rows": normalized,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    csv_path = args.report.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["id", "customer", "amount"] + (["internal_debug"] if args.fault == "extra-column" else [])
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([dict(row, internal_debug="unexpected") for row in normalized]
                         if args.fault == "extra-column" else normalized)
    print("Export complete: %s and %s" % (args.report.name, csv_path.name))


if __name__ == "__main__":
    main()
