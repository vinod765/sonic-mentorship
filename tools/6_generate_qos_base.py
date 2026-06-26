#!/usr/bin/env python3
"""
Script 6 — generate_qos_base.py
Reads audit_qos.csv, creates base templates in files/build_templates/ for
Group A and Group B qos.json.j2 files.

Group A — 72 copies of: {%- include 'qos_config.j2' %}
  → files/build_templates/qos.json.j2

Group B — 9 copies of: {%- include 'qos_config_t1.j2' %}
  → files/build_templates/qos_t1.json.j2

No override hierarchy needed here — unlike buffers.json.j2 which had a
per-device variable (default_topo), these qos files have NO variables at all.
They're pure includes. One base template per group, that's it.

Group C and OTHER are not touched — handled separately via symlink dedup.

Run:
    python3 tools/6_generate_qos_base.py --repo ~/sonic-buildimage --csv audit_qos.csv --dry-run
    python3 tools/6_generate_qos_base.py --repo ~/sonic-buildimage --csv audit_qos.csv
"""

import os
import csv
import argparse

GROUP_A_CONTENT = "{%- include 'qos_config.j2' %}\n"
GROUP_B_CONTENT = "{%- include 'qos_config_t1.j2' %}\n"

def write_file(path, content, dry_run):
    if dry_run:
        print(f"  [DRY RUN] would write: {path}")
        print(f"    content: {content.strip()}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path) as f:
            if f.read() == content:
                print(f"  [SKIP] already correct: {path}")
                return
    with open(path, "w") as f:
        f.write(content)
    print(f"  [WRITE] {path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--csv", default="audit_qos.csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)
    templates_dir = os.path.join(repo_root, "files", "build_templates")

    with open(args.csv) as f:
        rows = list(csv.DictReader(f))

    group_a = [r for r in rows if r["group"] == "A"]
    group_b = [r for r in rows if r["group"] == "B"]
    group_c = [r for r in rows if r["group"] == "C"]
    group_other = [r for r in rows if r["group"] == "OTHER"]

    print(f"\n=== Creating base templates ===\n")

    # Group A base template
    qos_a_path = os.path.join(templates_dir, "qos.json.j2")
    write_file(qos_a_path, GROUP_A_CONTENT, args.dry_run)
    print(f"    → covers {len(group_a)} Group A files\n")

    # Group B base template
    qos_b_path = os.path.join(templates_dir, "qos_t1.json.j2")
    write_file(qos_b_path, GROUP_B_CONTENT, args.dry_run)
    print(f"    → covers {len(group_b)} Group B files\n")

    print(f"=== Summary ===")
    print(f"  Base templates created: 2")
    print(f"  Group A files (safe to delete): {len(group_a)}")
    print(f"  Group B files (safe to delete): {len(group_b)}")
    print(f"  Group C files (NOT touched — symlink dedup needed): {len(group_c)}")
    print(f"  OTHER files  (NOT touched — symlink dedup needed): {len(group_other)}")
    print(f"\nNext: run 7_validate_qos.py to confirm base templates are correct")

if __name__ == "__main__":
    main()
