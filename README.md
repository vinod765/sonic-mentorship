# SONiC Jinja2 Template Audit Script

## Approach

The audit is broken into pre-checks and analysis sections.

**Pre-checks** handle repo-level anomalies before any analysis begins — uninitialized submodules that could cause files to be silently missing, `.j2` named directories (which are not templates), symlinks that already point to a shared source, and case variants like `.J2`.

**Duplicate detection** is done in two passes. First, an MD5 hash of every `.j2` file is computed for exact byte-level comparison. Second, a normalized hash is computed by stripping trailing whitespace and blank lines, which catches files that are functionally identical but differ only in formatting.

**Modified variant detection** groups files by filename across the repo. If the same filename appears in multiple vendor paths with different hashes, it means the template has been copied and independently modified — these are the files most worth consolidating.

**Diff summaries** are generated for the top 5 most-copied filenames, showing exactly what changed between vendor copies using unified diffs, making it easier to understand how much the templates have diverged.

The final summary aggregates all findings into a single count table for a quick overview.
