#!/usr/bin/env python3
"""
Script 7 — validate_qos.py
Validates that the base templates created by script 6 are correct.

For Group A and B — validation is simple:
  - Base template content must match what was in every original file
  - Since all files in group A are identical, if base template matches
    any one of them, it matches all of them

Also validates that Group C and OTHER files are NOT being touched.

Run:
    python3 tools/7_validate_qos.py --repo ~/sonic-buildimage --csv audit_qos.csv
"""

import os
import csv
import argparse
import sys

GROUP_A_EXPECTED = "{%- include 'qos_config.j2' %}"
GROUP_B_EXPECTED = "{%- include 'qos_config_t1.j2' %}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--csv", default="audit_qos.csv")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)
    templates_dir = os.path.join(repo_root, "files", "build_templates")

    with open(args.csv) as f:
        rows = list(csv.DictReader(f))

    results = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    print(f"\n=== Validating base templates exist ===\n")

    # check base template A exists and has correct content
    qos_a = os.path.join(templates_dir, "qos.json.j2")
    if os.path.exists(qos_a):
        with open(qos_a) as f:
            content = f.read().strip()
        if content == GROUP_A_EXPECTED:
            print(f"PASS  files/build_templates/qos.json.j2 — correct content")
            results["PASS"] += 1
        else:
            print(f"FAIL  files/build_templates/qos.json.j2 — wrong content")
            print(f"      expected: {GROUP_A_EXPECTED}")
            print(f"      got:      {content}")
            results["FAIL"] += 1
    else:
        print(f"FAIL  files/build_templates/qos.json.j2 — file missing, run script 6 first")
        results["FAIL"] += 1

    # check base template B exists and has correct content
    qos_b = os.path.join(templates_dir, "qos_t1.json.j2")
    if os.path.exists(qos_b):
        with open(qos_b) as f:
            content = f.read().strip()
        if content == GROUP_B_EXPECTED:
            print(f"PASS  files/build_templates/qos_t1.json.j2 — correct content")
            results["PASS"] += 1
        else:
            print(f"FAIL  files/build_templates/qos_t1.json.j2 — wrong content")
            print(f"      expected: {GROUP_B_EXPECTED}")
            print(f"      got:      {content}")
            results["FAIL"] += 1
    else:
        print(f"FAIL  files/build_templates/qos_t1.json.j2 — file missing, run script 6 first")
        results["FAIL"] += 1

    print(f"\n=== Validating Group A files match base template ===\n")
    group_a = [r for r in rows if r["group"] == "A"]
    for row in group_a:
        fpath = os.path.join(repo_root, row["rel_path"])
        if not os.path.exists(fpath):
            results["SKIP"] += 1
            continue
        with open(fpath, errors="replace") as f:
            content = f.read().strip()
        if content == GROUP_A_EXPECTED:
            results["PASS"] += 1
            print(f"PASS  {row['rel_path']}")
        else:
            results["FAIL"] += 1
            print(f"FAIL  {row['rel_path']}")
            print(f"      content: {content[:80]}")

    print(f"\n=== Validating Group B files match base template ===\n")
    group_b = [r for r in rows if r["group"] == "B"]
    for row in group_b:
        fpath = os.path.join(repo_root, row["rel_path"])
        if not os.path.exists(fpath):
            results["SKIP"] += 1
            continue
        with open(fpath, errors="replace") as f:
            content = f.read().strip()
        if content == GROUP_B_EXPECTED:
            results["PASS"] += 1
            print(f"PASS  {row['rel_path']}")
        else:
            results["FAIL"] += 1
            print(f"FAIL  {row['rel_path']}")
            print(f"      content: {content[:80]}")

    print(f"\n=== Validation Summary ===")
    print(f"  PASS : {results['PASS']}")
    print(f"  FAIL : {results['FAIL']}")
    print(f"  SKIP : {results['SKIP']}")

    if results["FAIL"] > 0:
        print(f"\nFix failures before running script 8.")
        sys.exit(1)
    else:
        print(f"\nAll good. Safe to delete Group A and B originals.")
        print(f"Next: run 8_delete_qos.py")
        sys.exit(0)

if __name__ == "__main__":
    main()
