#!/usr/bin/env python3
"""
Script 1 — audit_buffers.py
Finds all buffers.json.j2 files in sonic-buildimage,
extracts default_topo value, skips symlinks.
Outputs: audit_buffers.csv

Run from your sonic-buildimage clone root:
    python3 tools/1_audit_buffers.py --repo /path/to/sonic-buildimage
"""

import os
import re
import csv
import argparse

TEMPLATE_NAME = "buffers.json.j2"
# matches: {%- set default_topo = 't1' %} or {% set default_topo = "t1" %}
TOPO_PATTERN = re.compile(
    r"""\{%-?\s*set\s+default_topo\s*=\s*['"]([^'"]+)['"]\s*-?%\}"""
)

def find_buffers_j2(repo_root):
    results = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        # skip submodule dirs that aren't initialized (no files inside)
        for fname in filenames:
            if fname != TEMPLATE_NAME:
                continue
            full_path = os.path.join(dirpath, fname)
            # skip symlinks — they already point to a shared source
            if os.path.islink(full_path):
                continue
            results.append(full_path)
    return results

def extract_topo(filepath):
    try:
        with open(filepath, "r", errors="replace") as f:
            content = f.read()
        match = TOPO_PATTERN.search(content)
        if match:
            return match.group(1)
        # some files use a dynamic default pattern already
        if "default_topo" in content:
            return "DYNAMIC"
        return "NOT_FOUND"
    except Exception as e:
        return f"ERROR:{e}"

def parse_vendor_device(filepath, repo_root):
    # filepath like: /repo/device/mellanox/x86_64-mlnx_msn2700-r0/profile/buffers.json.j2
    rel = os.path.relpath(filepath, repo_root)
    parts = rel.split(os.sep)
    # parts[0] = 'device', parts[1] = vendor, parts[2] = hw_platform, parts[3...] = profile/file
    if len(parts) >= 4 and parts[0] == "device":
        vendor = parts[1]
        hw_platform = parts[2]
        profile = parts[3] if len(parts) > 4 else ""
    else:
        vendor = "unknown"
        hw_platform = "unknown"
        profile = ""
    return vendor, hw_platform, profile

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to sonic-buildimage clone")
    parser.add_argument("--out", default="audit_buffers.csv")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)
    print(f"Scanning: {repo_root}")

    files = find_buffers_j2(repo_root)
    print(f"Found {len(files)} non-symlink buffers.json.j2 files")

    rows = []
    topo_counts = {}

    for fpath in sorted(files):
        topo = extract_topo(fpath)
        vendor, hw_platform, profile = parse_vendor_device(fpath, repo_root)
        rel = os.path.relpath(fpath, repo_root)
        rows.append({
            "rel_path": rel,
            "vendor": vendor,
            "hw_platform": hw_platform,
            "profile": profile,
            "default_topo": topo,
        })
        topo_counts[topo] = topo_counts.get(topo, 0) + 1

    # write csv
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["rel_path", "vendor", "hw_platform", "profile", "default_topo"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nOutput written to: {args.out}")
    print(f"\n--- default_topo distribution ---")
    for topo, count in sorted(topo_counts.items(), key=lambda x: -x[1]):
        print(f"  {topo:<20} {count} files")

    print(f"\n--- per-vendor breakdown ---")
    vendor_topo = {}
    for row in rows:
        v = row["vendor"]
        t = row["default_topo"]
        if v not in vendor_topo:
            vendor_topo[v] = {}
        vendor_topo[v][t] = vendor_topo[v].get(t, 0) + 1

    for vendor in sorted(vendor_topo):
        print(f"  {vendor}:")
        for topo, count in sorted(vendor_topo[vendor].items(), key=lambda x: -x[1]):
            print(f"    {topo:<20} {count}")

if __name__ == "__main__":
    main()
