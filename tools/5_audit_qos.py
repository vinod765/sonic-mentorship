#!/usr/bin/env python3
"""
Script 5 — audit_qos.py
Finds all qos.json.j2 files in sonic-buildimage device/ directories,
classifies each into a group based on content pattern, outputs CSV.

Groups:
  A — single line: {%- include 'qos_config.j2' %}       (72 copies, base template candidate)
  B — single line: {%- include 'qos_config_t1.j2' %}    (9 copies, base template candidate)
  C — has WRED macro + include qos_config.j2             (17 copies, symlink dedup only)
  OTHER — full standalone inline config                  (rest)

Run:
    python3 tools/5_audit_qos.py --repo ~/sonic-buildimage --out audit_qos.csv
"""

import os
import re
import csv
import argparse
from collections import Counter

GROUP_A = "{%- include 'qos_config.j2' %}"
GROUP_B = "{%- include 'qos_config_t1.j2' %}"
GROUP_C_MARKER = "generate_wred_profiles"

def classify(filepath):
    try:
        with open(filepath, "r", errors="replace") as f:
            content = f.read().strip()
        if content == GROUP_A:
            return "A"
        if content == GROUP_B:
            return "B"
        if GROUP_C_MARKER in content and "qos_config.j2" in content:
            return "C"
        return "OTHER"
    except Exception as e:
        return f"ERROR:{e}"

def find_qos_files(repo_root):
    results = []
    for dirpath, _, filenames in os.walk(repo_root):
        for fname in filenames:
            if fname != "qos.json.j2":
                continue
            full_path = os.path.join(dirpath, fname)
            if os.path.islink(full_path):
                continue
            rel = os.path.relpath(full_path, repo_root)
            if not rel.startswith("device"):
                continue
            results.append(full_path)
    return sorted(results)

def parse_path(filepath, repo_root):
    rel = os.path.relpath(filepath, repo_root)
    parts = rel.replace("\\", "/").split("/")
    vendor     = parts[1] if len(parts) > 1 else "unknown"
    hw_platform = parts[2] if len(parts) > 2 else ""
    profile    = parts[3] if len(parts) > 3 else ""
    return vendor, hw_platform, profile, rel

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", default="audit_qos.csv")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)
    print(f"Scanning: {repo_root}")

    files = find_qos_files(repo_root)
    print(f"Found {len(files)} non-symlink qos.json.j2 files in device/\n")

    rows = []
    group_counts = Counter()

    for fpath in files:
        group = classify(fpath)
        vendor, hw, profile, rel = parse_path(fpath, repo_root)
        group_counts[group] += 1
        rows.append({
            "rel_path": rel,
            "vendor": vendor,
            "hw_platform": hw,
            "profile": profile,
            "group": group,
        })

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["rel_path", "vendor", "hw_platform", "profile", "group"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Output written to: {args.out}\n")
    print("--- Group distribution ---")
    print(f"  Group A  ({GROUP_A[:35]}...): {group_counts['A']} files  ← base template candidate")
    print(f"  Group B  ({GROUP_B[:35]}...): {group_counts['B']} files  ← base template candidate")
    print(f"  Group C  (WRED macro + include):               {group_counts['C']} files  ← symlink dedup only")
    print(f"  OTHER    (full standalone inline config):       {group_counts['OTHER']} files  ← symlink dedup only")
    print(f"  ERRORS:                                         {sum(v for k,v in group_counts.items() if k.startswith('ERROR'))} files")

    print(f"\n--- per-vendor breakdown ---")
    vendor_groups = {}
    for row in rows:
        v = row["vendor"]
        g = row["group"]
        if v not in vendor_groups:
            vendor_groups[v] = Counter()
        vendor_groups[v][g] += 1
    for vendor in sorted(vendor_groups):
        print(f"  {vendor}:")
        for g, count in sorted(vendor_groups[vendor].items()):
            print(f"    Group {g}: {count}")

if __name__ == "__main__":
    main()
