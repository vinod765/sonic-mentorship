#!/usr/bin/env python3
"""
Script 8 — delete_qos.py
ONLY RUN AFTER script 7 exits with code 0.

Deletes all Group A and Group B qos.json.j2 files from device/ directories.
These are now covered by the base templates in files/build_templates/.

Group C and OTHER are NOT touched — they have unique content.

Run:
    # dry run first
    python3 tools/8_delete_qos.py --repo ~/sonic-buildimage --csv audit_qos.csv --dry-run

    # delete for real (one vendor at a time recommended)
    python3 tools/8_delete_qos.py --repo ~/sonic-buildimage --csv audit_qos.csv --vendor arista

    # delete all
    python3 tools/8_delete_qos.py --repo ~/sonic-buildimage --csv audit_qos.csv
"""

import os
import csv
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--csv", default="audit_qos.csv")
    parser.add_argument("--vendor", default=None, help="Limit to one vendor")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)

    with open(args.csv) as f:
        rows = list(csv.DictReader(f))

    # only delete group A and B
    target_rows = [r for r in rows if r["group"] in ("A", "B")]

    deleted = 0
    skipped = 0

    for row in target_rows:
        vendor = row["vendor"]
        group = row["group"]

        if args.vendor and vendor != args.vendor:
            continue

        full_path = os.path.join(repo_root, row["rel_path"])

        if os.path.islink(full_path):
            skipped += 1
            continue

        if not os.path.exists(full_path):
            skipped += 1
            continue

        if args.dry_run:
            print(f"[DRY RUN] would delete (Group {group}): {row['rel_path']}")
        else:
            os.remove(full_path)
            print(f"[DELETE] Group {group}: {row['rel_path']}")
        deleted += 1

    print(f"\n--- Summary ---")
    print(f"  {'Would delete' if args.dry_run else 'Deleted'}: {deleted}")
    print(f"  Skipped (symlinks, missing, or wrong vendor): {skipped}")
    print(f"  Group C and OTHER: untouched (unique content)")

if __name__ == "__main__":
    main()
