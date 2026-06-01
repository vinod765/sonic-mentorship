# J2 Template Reuse Design — sonic-buildimage
## Overview

The idea is to separate shared template logic from per-device data. Instead of every device having its own copy of a template, there will be one base template per config type and each device will have a small `override.json` with only what's unique to it.

```
Base Template (.j2)  +  Device Override JSON  →  Final Config File
   [shared logic]         [device-specific]         [rendered output]
```

---

## Directory Structure

```
sonic-buildimage/
│
├── device/
│   ├── mellanox/
│   │   ├── vendor_defaults.json              ← Mellanox-wide defaults
│   │   ├── x86_64-mlnx_msn2700-r0/
│   │   │   └── override.json                 ← only what's unique to this device
│   │   └── x86_64-mlnx_msn3800-r0/
│   │       └── override.json
│   │
│   ├── arista/
│   │   ├── vendor_defaults.json
│   │   └── x86_64-arista_7050cx3_32s/
│   │       └── override.json
│   └── ...
│
└── templates/
    ├── base_defaults.json                     ← repo-wide fallback values
    └── base/
        ├── buffers.json.j2
        ├── buffers_defaults_t0.j2
        ├── buffers_defaults_t1.j2
        ├── buffers_defaults_t2.j2
        ├── buffers_defaults_def_lossy.j2
        ├── buffers_dynamic.json.j2
        ├── buffer_ports.j2
        └── buffer_ports_t0.j2
```

Device directories no longer contain `.j2` files — only `override.json`.

---

## Three-Level Override Hierarchy

Context is built by merging three JSON layers, last one wins:

```
Level 1 — templates/base_defaults.json             (repo-wide fallbacks)
           +
Level 2 — device/<vendor>/vendor_defaults.json     (vendor-wide values)
           +
Level 3 — device/<vendor>/<profile>/override.json  (device-specific)
           ↓
       deep_merge(L1, L2, L3)
           ↓
       render base template with merged context
           ↓
       final config file
```

If a device is identical to vendor defaults, `override.json` can be empty or skipped.

---

## JSON Examples

**`templates/base_defaults.json`**
```json
{
  "default_topo": "t0",
  "buffer_mode": "static",
  "ingress_lossless_pool_size": "4194304",
  "egress_lossless_pool_size": "16777152",
  "port_count": 32,
  "port_range_start": 0
}
```

**`device/mellanox/vendor_defaults.json`**
```json
{
  "default_topo": "t1",
  "buffer_mode": "dynamic",
  "ingress_lossless_pool_size": "20971328"
}
```

**`device/mellanox/x86_64-mlnx_msn2700-r0/override.json`**
```json
{
  "port_count": 32,
  "ingress_lossless_pool_size": "20971328"
}
```

---

## Template — Before and After

**Before:**
```jinja2
{%- set default_topo = 't0' %}
```

**After:**
```jinja2
{%- set default_topo = device.default_topo | default('t0') %}
{%- set buffer_mode = device.buffer_mode | default('static') %}
```

The `| default()` filter means if nothing is passed, the template still renders fine.

---

## Render Script

```python
# tools/render_template.py
import json
import os
from jinja2 import Environment, FileSystemLoader

def deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def build_context(vendor: str, device_profile: str) -> dict:
    repo_root = os.path.dirname(os.path.dirname(__file__))

    with open(os.path.join(repo_root, "templates", "base_defaults.json")) as f:
        context = json.load(f)

    vendor_path = os.path.join(repo_root, "device", vendor, "vendor_defaults.json")
    if os.path.exists(vendor_path):
        with open(vendor_path) as f:
            context = deep_merge(context, json.load(f))

    device_path = os.path.join(repo_root, "device", vendor, device_profile, "override.json")
    if os.path.exists(device_path):
        with open(device_path) as f:
            context = deep_merge(context, json.load(f))

    return {"device": context}

def render(template_name: str, vendor: str, device_profile: str) -> str:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    env = Environment(
        loader=FileSystemLoader(os.path.join(repo_root, "templates", "base")),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template(template_name)
    context = build_context(vendor, device_profile)
    return template.render(**context)
```

Plugs into the existing `sonic-cfggen` pipeline — doesn't replace anything, just feeds the right context in.

---

## Migration Phases

| Filename | Copies | What Changes | Phase |
|---|---|---|---|
| `buffers.json.j2` | 215 | `default_topo` — single variable | 1 |
| `buffers_defaults_t0.j2` | 159 | Pool sizes, port count range | 2 |
| `buffers_defaults_t1.j2` | 183 | Pool sizes, port count range | 2 |
| `buffers_defaults_t2.j2` | 24 | Pool sizes, port count range | 2 |
| `buffers_defaults_def_lossy.j2` | 21 | Buffer values | 2 |
| `buffers_dynamic.json.j2` | 20 | Dynamic buffer parameters | 2 |
| `buffer_ports.j2` | 37 | Port range and count | 2 |
| `buffer_ports_t0.j2` | 20 | Port range and count | 2 |
| `qos.json.j2` | 201 | Structure varies per vendor | 3 |
| `qos_defaults_t1.j2` | 16 | QoS values | 3 |
| `qos_defaults_def_lossy.j2` | 21 | QoS values | 3 |
| Remaining 39 variant filenames | small counts | Varies | 4 |

**Phase 1 — `buffers.json.j2`**
- One base template, `default_topo` moves to per-device `override.json`
- Sets up the full infrastructure — `templates/base/`, `base_defaults.json`, render script, JSON hierarchy
- Validate by diffing render output against the current file for each device
- ~214 files removed

**Phase 2 — `buffers_defaults` and `buffer_ports` variants**
- Base templates for each, pool sizes and port counts go into override JSONs
- `override.json` files from Phase 1 already exist — just adding more keys
- No new infrastructure needed
- ~480 additional files removed

**Phase 3 — `qos.json.j2` and `qos_defaults` variants**
- Some are plain static JSON, others are full Jinja templates with loops and DSCP/TC mapping
- Will do a per-vendor analysis after Phase 2 is merged before starting this phase
- ~238 files

**Phase 4 — Remaining 39 variant filenames**
- Long tail cleanup, same pattern as previous phases
