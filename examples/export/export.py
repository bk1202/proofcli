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
    report = {
        "currency": "CAD",
        "summary": {"row_count": len(normalized), "total": format(total, ".2f")},
        "rows": normalized,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    csv_path = args.report.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "customer", "amount"])
        writer.writeheader()
        writer.writerows(normalized)
    print("Export complete: %s and %s" % (args.report.name, csv_path.name))


if __name__ == "__main__":
    main()
