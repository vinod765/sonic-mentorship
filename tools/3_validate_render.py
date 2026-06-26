import os
import csv
import json
import difflib
import argparse
import sys

def get_render_fn(repo_root):
    scripts_dir = os.path.join(repo_root, "files", "build_scripts")
    sys.path.insert(0, scripts_dir)
    from render_template import render, build_context
    return render, build_context

def load_original(filepath):
    with open(filepath, "r", errors="replace") as f:
        return f.read()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--csv", default="audit_buffers.csv")
    parser.add_argument("--vendor", default=None)
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)

    try:
        render, build_context = get_render_fn(repo_root)
    except ImportError as e:
        print(f"ERROR: Could not import render_template.py — {e}")
        sys.exit(1)

    with open(args.csv) as f:
        rows = list(csv.DictReader(f))

    results = {"PASS": 0, "DIFF": 0, "SKIP": 0, "ERROR": 0}

    for row in rows:
        vendor     = row["vendor"]
        hw_platform = row["hw_platform"]
        profile    = row["profile"]
        topo       = row["default_topo"]
        rel_path   = row["rel_path"]

        if args.vendor and vendor != args.vendor:
            continue

        if topo in ("NOT_FOUND", "DYNAMIC", "unknown"):
            results["SKIP"] += 1
            continue

        original_path = os.path.join(repo_root, rel_path)
        if not os.path.exists(original_path) or os.path.islink(original_path):
            results["SKIP"] += 1
            continue

        try:
            original = load_original(original_path)
            rendered = render("buffers.json.j2", vendor, hw_platform, profile)

            if original.strip() == rendered.strip():
                results["PASS"] += 1
                print(f"PASS  {rel_path}")
            else:
                results["DIFF"] += 1
                print(f"DIFF  {rel_path}")
                diff = difflib.unified_diff(
                    original.splitlines(keepends=True),
                    rendered.splitlines(keepends=True),
                    fromfile="original",
                    tofile="rendered",
                    n=3
                )
                print("".join(list(diff)[:40]))
                if args.fail_fast:
                    print("\n--fail-fast set, stopping.")
                    break

        except Exception as e:
            results["ERROR"] += 1
            print(f"ERROR {rel_path} — {e}")
            if args.fail_fast:
                break

    print(f"\n=== Validation Summary ===")
    print(f"  PASS  : {results['PASS']}")
    print(f"  DIFF  : {results['DIFF']}")
    print(f"  SKIP  : {results['SKIP']}")
    print(f"  ERROR : {results['ERROR']}")

    if results["DIFF"] > 0 or results["ERROR"] > 0:
        sys.exit(1)
    else:
        print("\nAll good. Safe to proceed with deletion.")
        sys.exit(0)
