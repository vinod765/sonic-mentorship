# sonic-mentorship/tools — Migration Tooling

These scripts handle the full Phase 1 migration of `buffers.json.j2`
from 215 hardcoded per-device copies to a single base template + JSON override hierarchy.

---

## Prerequisites

```bash
pip install jinja2
```

Your sonic-buildimage clone must exist locally. Scripts run against it — they don't touch this repo.

---

## Step-by-step

### Step 1 — Audit all buffers.json.j2 files

```bash
cd vinod765/sonic-mentorship

python3 tools/1_audit_buffers.py \
    --repo /path/to/sonic-buildimage \
    --out audit_buffers.csv
```

Produces `audit_buffers.csv` with columns:
`rel_path, vendor, hw_platform, profile, default_topo`

Check the per-vendor breakdown in the output. Confirm `t1` is the global majority.

---

### Step 2 — Generate override JSONs

```bash
# dry run first — see what would be created
python3 tools/2_generate_overrides.py \
    --repo /path/to/sonic-buildimage \
    --csv audit_buffers.csv \
    --dry-run

# if it looks right, run for real
python3 tools/2_generate_overrides.py \
    --repo /path/to/sonic-buildimage \
    --csv audit_buffers.csv
```

This creates:
- `device/<vendor>/vendor_defaults.json` for each vendor (only if majority != base default)
- `device/<vendor>/<hw>/override.json` for each device that differs from its vendor majority

---

### Step 3 — Validate render output

Before this step, make sure these files exist in sonic-buildimage:
- `files/build_templates/base_defaults.json`
- `files/build_templates/buffers.json.j2`  (your modified base template)
- `files/build_scripts/render_template.py`

```bash
# validate one vendor first
python3 tools/3_validate_render.py \
    --repo /path/to/sonic-buildimage \
    --csv audit_buffers.csv \
    --vendor mellanox

# if that passes, validate all
python3 tools/3_validate_render.py \
    --repo /path/to/sonic-buildimage \
    --csv audit_buffers.csv
```

Every device should show PASS. Fix any DIFFs before proceeding.

---

### Step 4 — Delete original files

Only run this after Step 3 exits with code 0.

```bash
# dry run first
python3 tools/4_delete_originals.py \
    --repo /path/to/sonic-buildimage \
    --csv audit_buffers.csv \
    --vendor mellanox \
    --dry-run

# delete for real (one vendor at a time for first PR)
python3 tools/4_delete_originals.py \
    --repo /path/to/sonic-buildimage \
    --csv audit_buffers.csv \
    --vendor mellanox
```

---

## PR Strategy

Don't do all 215 files in one PR. Sequence:

1. First PR — Mellanox only (clean, well-understood, t1 majority, ~30-40 files)
   - Adds base template, render script, base_defaults.json
   - Adds mellanox/vendor_defaults.json
   - Adds mellanox device override.json files
   - Deletes mellanox buffers.json.j2 copies

2. Second PR — next vendor (Broadcom or Cisco)
   - override.json files only for that vendor
   - deletion of their copies

3. Repeat per vendor until all 215 are gone.

Each PR is small, reviewable, and doesn't break other vendors.

---

## Notes

- Symlinks (449 of them) are NOT touched by these scripts. Handle separately in Phase 2.
- Arista uses non-standard topos (lt2, ft2) — their override.json files will be created
  correctly by script 2, but flag this to Antony since it's a deviation from the pattern.
- DYNAMIC entries (devices already using dynamic default pattern, e.g. some Marvell) are
  skipped — they don't need migration.
