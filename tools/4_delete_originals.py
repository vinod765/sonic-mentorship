#!/usr/bin/env python3
"""
Script 4 — delete_originals.py
ONLY RUN THIS AFTER 3_validate_render.py exits 0.

Deletes all non-symlink buffers.json.j2 files from device/ directories
since they've been replaced by the base template + override hierarchy.

Symlinks are left alone — they need separate handling (either re-point
to the new base template location or delete, TBD in Phase 2).

Run:
    python3 tools/4_delete_originals.py --repo /path/to/sonic-buildimage --csv audit_buffers.csv

Pass --dry-run first to see what would be deleted.
Pass --vendor mellanox to limit to one vendor (recommended for first PR).
"""

import os
import csv
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--csv", default="audit_buffers.csv")
    parser.add_argument("--vendor", default=None, help="Limit to one vendor")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)

    with open(args.csv) as f:
        rows = list(csv.DictReader(f))

    deleted = 0
    skipped = 0

    for row in rows:
        vendor = row["vendor"]
        rel_path = row["rel_path"]

        if args.vendor and vendor != args.vendor:
            continue

        full_path = os.path.join(repo_root, rel_path)

        # never delete symlinks here
        if os.path.islink(full_path):
            skipped += 1
            continue

        if not os.path.exists(full_path):
            skipped += 1
            continue

        if args.dry_run:
            print(f"[DRY RUN] would delete: {rel_path}")
        else:
            os.remove(full_path)
            print(f"[DELETE] {rel_path}")
        deleted += 1

    print(f"\n--- Summary ---")
    print(f"  {'Would delete' if args.dry_run else 'Deleted'}: {deleted}")
    print(f"  Skipped (symlinks or missing): {skipped}")

if __name__ == "__main__":
    main()
