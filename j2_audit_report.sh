#!/bin/bash

REPO="$HOME/sonic-buildimage"
OUT="$HOME/j2_audit_report_v3.txt"
TMP="/tmp/j2_audit"

mkdir -p "$TMP"
cd "$REPO" || exit 1

echo "=== SONiC Jinja2 Template Audit v3 ===" > "$OUT"
echo "Date: $(date)" >> "$OUT"
echo "" >> "$OUT"

# PRE-CHECK 1 — Submodule status
echo "--- PRE-CHECK: SUBMODULE STATUS ---" >> "$OUT"
uninit=$(git submodule status | grep "^-" | wc -l)
total_sub=$(git submodule status | wc -l)
echo "  Total submodules: $total_sub" >> "$OUT"
echo "  Uninitialized submodules: $uninit" >> "$OUT"
if [ "$uninit" -gt 0 ]; then
  echo "  WARNING: Some submodules not initialized — .j2 files inside may be missing" >> "$OUT"
  git submodule status | grep "^-" | awk '{print "    " $2}' >> "$OUT"
else
  echo "  All submodules initialized — audit covers full repo" >> "$OUT"
fi
echo "" >> "$OUT"

# PRE-CHECK 2 — .j2 DIRECTORIES (repo anomaly)

echo "--- PRE-CHECK: .j2 NAMED DIRECTORIES (repo anomaly) ---" >> "$OUT"
dir_count=$(find . -name "*.j2" -type d -not -path "./.git/*" | wc -l)
echo "  Directories with .j2 extension: $dir_count" >> "$OUT"
if [ "$dir_count" -gt 0 ]; then
  echo "  These are NOT template files — likely test fixtures or repo errors:" >> "$OUT"
  find . -name "*.j2" -type d -not -path "./.git/*" | while read d; do
    echo "    $d" >> "$OUT"
  done
fi
echo "" >> "$OUT"


# PRE-CHECK 3 — Symlinks
echo "--- PRE-CHECK: SYMLINKED .j2 FILES ---" >> "$OUT"
symlink_count=$(find . -name "*.j2" -type l -not -path "./.git/*" | wc -l)
echo "  Total .j2 symlinks found: $symlink_count" >> "$OUT"
if [ "$symlink_count" -gt 0 ]; then
  echo "  These already point to a shared source — listed below:" >> "$OUT"
  find . -name "*.j2" -type l -not -path "./.git/*" | while read link; do
    target=$(readlink "$link")
    echo "    $link -> $target" >> "$OUT"
  done
else
  echo "  No symlinks found — all .j2 files are independent copies" >> "$OUT"
fi
echo "" >> "$OUT"

# PRE-CHECK 4 — Case sensitivity
echo "--- PRE-CHECK: UPPERCASE .J2 FILES ---" >> "$OUT"
upper_count=$(find . -name "*.J2" -type f -not -path "./.git/*" | wc -l)
echo "  Uppercase .J2 files found: $upper_count" >> "$OUT"
echo "" >> "$OUT"

# SECTION 1 — ALL .j2 FILES (files only)
echo "--- ALL .j2 FILES ---" >> "$OUT"
find . -name "*.j2" -type f -not -path "./.git/*" | sort >> "$OUT"
TOTAL=$(find . -name "*.j2" -type f -not -path "./.git/*" | wc -l)
echo "" >> "$OUT"
echo "Total: $TOTAL files" >> "$OUT"
echo "" >> "$OUT"

# SECTION 2 — PATH BREAKDOWN
echo "--- PATH BREAKDOWN: platform/ vs device/ vs rest ---" >> "$OUT"
platform_count=$(find ./platform -name "*.j2" -type f -not -path "./.git/*" 2>/dev/null | wc -l)
device_count=$(find ./device -name "*.j2" -type f -not -path "./.git/*" 2>/dev/null | wc -l)
rest_count=$(find . -name "*.j2" -type f -not -path "./.git/*" -not -path "./platform/*" -not -path "./device/*" | wc -l)
echo "  platform/ : $platform_count files" >> "$OUT"
echo "  device/   : $device_count files" >> "$OUT"
echo "  rest      : $rest_count files" >> "$OUT"
echo "" >> "$OUT"

echo "  platform/ breakdown by vendor:" >> "$OUT"
find ./platform -name "*.j2" -type f -not -path "./.git/*" 2>/dev/null \
  | awk -F'/' '{print $3}' | sort | uniq -c | sort -rn \
  | awk '{print "    " $1 " " $2}' >> "$OUT"
echo "" >> "$OUT"

echo "  device/ breakdown by vendor:" >> "$OUT"
find ./device -name "*.j2" -type f -not -path "./.git/*" 2>/dev/null \
  | awk -F'/' '{print $3}' | sort | uniq -c | sort -rn \
  | awk '{print "    " $1 " " $2}' >> "$OUT"
echo "" >> "$OUT"

# SECTION 3 — FILENAMES WITH MULTIPLE COPIES
echo "--- FILENAMES WITH MULTIPLE COPIES ---" >> "$OUT"
find . -name "*.j2" -type f -not -path "./.git/*" \
  | awk -F'/' '{print $NF}' \
  | sort | uniq -c | sort -rn \
  | awk '$1 > 1' >> "$OUT"
echo "" >> "$OUT"

# SECTION 4 — EXACT DUPLICATES
find . -name "*.j2" -type f -not -path "./.git/*" \
  -exec md5sum {} \; > "$TMP/hashes_exact.txt"

echo "--- EXACT DUPLICATES (byte-perfect identical content) ---" >> "$OUT"
sort "$TMP/hashes_exact.txt" | awk '{print $1}' | uniq -d | while read h; do
  echo "" >> "$OUT"
  echo "  HASH: $h" >> "$OUT"
  grep "^$h" "$TMP/hashes_exact.txt" | awk '{print "    " $2}' >> "$OUT"
done
echo "" >> "$OUT"

# SECTION 5 — NEAR DUPLICATES (normalized)
echo "--- NEAR-DUPLICATES (differ only by whitespace/blank lines) ---" >> "$OUT"
> "$TMP/hashes_normalized.txt"
find . -name "*.j2" -type f -not -path "./.git/*" | while read fpath; do
  normhash=$(sed 's/[[:space:]]*$//' "$fpath" | grep -v '^$' | md5sum | awk '{print $1}')
  echo "$normhash $fpath" >> "$TMP/hashes_normalized.txt"
done

sort "$TMP/hashes_normalized.txt" | awk '{print $1}' | uniq -d | while read h; do
  files=$(grep "^$h " "$TMP/hashes_normalized.txt" | awk '{print $2}')
  exact_hashes=$(echo "$files" | while read f; do grep " $f$" "$TMP/hashes_exact.txt" | awk '{print $1}'; done | sort -u)
  exact_count=$(echo "$exact_hashes" | wc -l)
  if [ "$exact_count" -gt 1 ]; then
    echo "" >> "$OUT"
    echo "  NORM_HASH: $h" >> "$OUT"
    grep "^$h " "$TMP/hashes_normalized.txt" | awk '{print "    " $2}' >> "$OUT"
    echo "    ^ identical except whitespace/blank lines" >> "$OUT"
  fi
done
echo "" >> "$OUT"

# SECTION 6 — MODIFIED VARIANTS
echo "--- MODIFIED VARIANTS (same filename, different content) ---" >> "$OUT"
find . -name "*.j2" -type f -not -path "./.git/*" \
  | awk -F'/' '{print $NF}' \
  | sort | uniq -d | while read fname; do
    echo "" >> "$OUT"
    echo "  FILE: $fname" >> "$OUT"
    grep -E "/$fname$" "$TMP/hashes_exact.txt" | while read hash path; do
      echo "    [$hash] $path" >> "$OUT"
    done
done
echo "" >> "$OUT"

# SECTION 7 — DIFF SUMMARY TOP 5
echo "--- DIFF SUMMARY: TOP 5 MOST COPIED MODIFIED FILES ---" >> "$OUT"
TOP5=$(find . -name "*.j2" -type f -not -path "./.git/*" \
  | awk -F'/' '{print $NF}' \
  | sort | uniq -c | sort -rn \
  | awk '$1 > 1 {print $2}' \
  | head -5)

for fname in $TOP5; do
  echo "" >> "$OUT"
  echo "  ════════════════════════════════" >> "$OUT"
  echo "  FILE: $fname" >> "$OUT"
  echo "  ════════════════════════════════" >> "$OUT"
  mapfile -t paths < <(grep -E "/$fname$" "$TMP/hashes_exact.txt" | awk '{print $2}')
  total_copies=${#paths[@]}
  unique_versions=$(grep -E "/$fname$" "$TMP/hashes_exact.txt" | awk '{print $1}' | sort -u | wc -l)
  echo "  Total copies: $total_copies | Distinct versions: $unique_versions" >> "$OUT"
  echo "" >> "$OUT"
  [ "$total_copies" -lt 2 ] && continue
  base="${paths[0]}"
  echo "  Base file: $base" >> "$OUT"
  echo "" >> "$OUT"
  seen_hashes=$(grep " $base$" "$TMP/hashes_exact.txt" | awk '{print $1}')
  compared=0
  for other in "${paths[@]:1}"; do
    other_hash=$(grep " $other$" "$TMP/hashes_exact.txt" | awk '{print $1}')
    echo "$seen_hashes" | grep -q "$other_hash" && continue
    seen_hashes="$seen_hashes $other_hash"
    echo "  vs: $other" >> "$OUT"
    diff --unified=1 "$base" "$other" 2>/dev/null | head -40 | sed 's/^/    /' >> "$OUT"
    echo "" >> "$OUT"
    compared=$((compared + 1))
    [ "$compared" -ge 3 ] && break
  done
done

# FINAL SUMMARY
echo "--- FINAL SUMMARY ---" >> "$OUT"

TOTAL=$(find . -name "*.j2" -type f -not -path "./.git/*" | wc -l)
SYMLINKS=$(find . -name "*.j2" -type l -not -path "./.git/*" | wc -l)
J2_DIRS=$(find . -name "*.j2" -type d -not -path "./.git/*" | wc -l)
MULTI=$(find . -name "*.j2" -type f -not -path "./.git/*" \
  | awk -F'/' '{print $NF}' | sort | uniq -d | wc -l)
EXACT_GROUPS=$(sort "$TMP/hashes_exact.txt" | awk '{print $1}' | uniq -d | wc -l)
EXACT_FILES=$(sort "$TMP/hashes_exact.txt" | awk '{print $1}' | uniq -d | while read h; do
  grep "^$h" "$TMP/hashes_exact.txt" | wc -l
done | awk '{s+=$1} END {print s}')
NEAR_GROUPS=$(sort "$TMP/hashes_normalized.txt" | awk '{print $1}' | uniq -d | while read h; do
  files=$(grep "^$h " "$TMP/hashes_normalized.txt" | awk '{print $2}')
  exact_hashes=$(echo "$files" | while read f; do
    grep " $f$" "$TMP/hashes_exact.txt" | awk '{print $1}'
  done | sort -u | wc -l)
  [ "$exact_hashes" -gt 1 ] && echo "$h"
done | wc -l)
MOD_VARIANTS=$(find . -name "*.j2" -type f -not -path "./.git/*" \
  | awk -F'/' '{print $NF}' | sort | uniq -d | while read fname; do
    unique=$(grep -E "/$fname$" "$TMP/hashes_exact.txt" | awk '{print $1}' | sort -u | wc -l)
    [ "$unique" -gt 1 ] && echo "$fname"
done | wc -l)

echo "" >> "$OUT"
echo "  Total .j2 files (actual files only)          : $TOTAL" >> "$OUT"
echo "  Total .j2 symlinks                            : $SYMLINKS" >> "$OUT"
echo "  Total .j2 entries (files + symlinks)          : $((TOTAL + SYMLINKS))" >> "$OUT"
echo "  .j2 named directories (anomaly)               : $J2_DIRS" >> "$OUT"
echo "  Filenames appearing in multiple locations     : $MULTI" >> "$OUT"
echo "  Exact duplicate groups (byte-perfect)         : $EXACT_GROUPS" >> "$OUT"
echo "  Total files involved in exact duplication     : $EXACT_FILES" >> "$OUT"
echo "  Near-duplicate groups (whitespace diff only)  : $NEAR_GROUPS" >> "$OUT"
echo "  Modified variant filenames (same name, diff content) : $MOD_VARIANTS" >> "$OUT"
echo "" >> "$OUT"

echo "=== END OF REPORT ===" >> "$OUT"
echo "Done. Report at $OUT"