#!/usr/bin/env python3
import os
import csv
import json
import argparse
from collections import Counter

BASE_DEFAULT_TOPO = "t0"

def majority(values):
    if not values:
        return None
    c = Counter(values)
    return c.most_common(1)[0][0]

def load_csv(csv_path):
    with open(csv_path) as f:
        return list(csv.DictReader(f))

def write_json(path, data, dry_run):
    if dry_run:
        print(f"  [DRY RUN] would write: {path}")
        print(f"    {json.dumps(data)}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f)
        if existing == data:
            print(f"  [SKIP] already correct: {path}")
            return
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"  [WRITE] {path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--csv", default="audit_buffers.csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)
    rows = load_csv(args.csv)

    skip_topos = {"NOT_FOUND", "DYNAMIC"}

    # group by vendor to find majority per vendor
    vendor_rows = {}
    for row in rows:
        v = row["vendor"]
        if v == "unknown" or row["default_topo"] in skip_topos:
            continue
        vendor_rows.setdefault(v, []).append(row)

    print(f"\n=== Generating vendor_defaults.json files ===\n")

    vendor_majority = {}
    for vendor, vrows in sorted(vendor_rows.items()):
        topos = [r["default_topo"] for r in vrows]
        maj = majority(topos)
        vendor_majority[vendor] = maj

        if maj != BASE_DEFAULT_TOPO:
            vendor_path = os.path.join(repo_root, "device", vendor, "vendor_defaults.json")
            write_json(vendor_path, {"default_topo": maj}, args.dry_run)
            print(f"    vendor={vendor} majority={maj} ({topos.count(maj)}/{len(topos)})")
        else:
            print(f"    vendor={vendor} majority={maj} — same as base, skipping vendor_defaults.json")

    print(f"\n=== Generating profile-level override.json files ===\n")

    override_count = 0
    skipped_count = 0
    seen = set()

    for row in rows:
        vendor = row["vendor"]
        hw_platform = row["hw_platform"]
        profile = row["profile"]
        topo = row["default_topo"]

        if vendor == "unknown" or topo in skip_topos:
            continue

        # skip if no profile (file sits directly in hw_platform dir)
        if not profile:
            continue

        vendor_maj = vendor_majority.get(vendor, BASE_DEFAULT_TOPO)

        # only write override if this profile differs from vendor majority
        if topo == vendor_maj:
            skipped_count += 1
            continue

        profile_dir = os.path.join(repo_root, "device", vendor, hw_platform, profile)
        override_path = os.path.join(profile_dir, "override.json")

        # deduplicate — same path might appear multiple times in CSV
        if override_path in seen:
            continue
        seen.add(override_path)

        write_json(override_path, {"default_topo": topo}, args.dry_run)
        override_count += 1

    print(f"\n--- Summary ---")
    print(f"  override.json files written: {override_count}")
    print(f"  profiles matching vendor majority (no override needed): {skipped_count}")

if __name__ == "__main__":
    main()
