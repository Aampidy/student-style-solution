#!/usr/bin/env python3
"""Merge GitHub traffic API payloads into CSV history files.

GitHub only exposes the last 14 days of views and clones. Running this on a
schedule turns that rolling window into an append-only history keyed by date.
"""

import argparse
import csv
import json
import os

DATASETS = {
    "views": {
        "file": "views.csv",
        "fields": ("date", "views", "unique_visitors"),
        "payload_key": "views",
        "count_key": "views",
        "unique_key": "unique_visitors",
    },
    "clones": {
        "file": "clones.csv",
        "fields": ("date", "clones", "unique_cloners"),
        "payload_key": "clones",
        "count_key": "clones",
        "unique_key": "unique_cloners",
    },
}


def read_rows(path):
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as handle:
        return {row["date"]: row for row in csv.DictReader(handle)}


def write_rows(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for date in sorted(rows):
            writer.writerow(rows[date])


def merge(dataset, payload, out_dir):
    path = os.path.join(out_dir, DATASETS[dataset]["file"])
    fields = DATASETS[dataset]["fields"]
    rows = read_rows(path)
    for item in payload.get(DATASETS[dataset]["payload_key"], []):
        date = item["timestamp"][:10]
        rows[date] = {
            "date": date,
            fields[1]: int(item["count"]),
            fields[2]: int(item["uniques"]),
        }
    write_rows(path, fields, rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", required=True, help="JSON from /traffic/views")
    parser.add_argument("--clones", required=True, help="JSON from /traffic/clones")
    parser.add_argument("--out", required=True, help="directory holding the CSV files")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    for dataset, source in (("views", args.views), ("clones", args.clones)):
        with open(source, encoding="utf-8") as handle:
            payload = json.load(handle)
        total = merge(dataset, payload, args.out)
        print(f"{dataset}: {total} days recorded")


if __name__ == "__main__":
    main()
