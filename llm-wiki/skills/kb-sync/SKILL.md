---
name: kb-sync
description: |
  Sync stale pages in the knowledge base at `~/.knowledge/` (LLM Wiki). Re-ingests wiki pages that drifted from their sources to resolve drift.
  Use for "refresh the KB", "update a stale page", or "sync".
---
# kb-sync (re-ingest stale pages)

1. Identify target projects from the `陳腐化の疑い` section of the `kb-lint` skill's `kb-lint.sh` (§3 staleness suspects).
2. Re-ingest each target with `kb-ingest`'s Ingest procedure, refreshing the page's OKF `timestamp` field, `source_commit`, and `source_paths` (overwriting the existing page). The whole frontmatter must keep satisfying OKF §9.1 (non-empty `type`).
3. Update the index if it changed, and append a one-liner sync entry to `~/.knowledge/wiki/log.md` under the matching `## YYYY-MM-DD` H2 heading (or add a new heading newest-on-top).
