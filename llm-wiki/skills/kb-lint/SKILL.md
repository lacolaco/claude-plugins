---
name: kb-lint
description: |
  Lint the knowledge base at `~/.knowledge/` (LLM Wiki). Deterministic checks are delegated to a script; contradictions, broken links, and staleness are reported as proposals only (no auto-fix).
  Use for KB health checks, contradiction detection, right after a batch ingest, or before relying on the KB as evidence.
---
# kb-lint (KB health check)

Mechanical checks are delegated to a script (do not count things in-context).

1. Run the `kb-lint` skill's `kb-lint.sh`. It enumerates:
   - **§0 OKF v0.1 conformance** — non-reserved pages missing frontmatter or non-empty `type`; reserved files (`index.md` / `log.md`) violating §6 / §7 structure. Any non-zero count is a hard violation of the spec.
   - **§1-3 KB hygiene** — unregistered pages / broken or missing links / staleness suspects (via `source_commit` first, mtime fallback).
2. Walk the schema's source-authority items: each project's prose (README / CLAUDE.md) ⇄ code / lockfile / config contradictions, mismatches against `wiki/projects/`, and dead citations. Detection only — resolution happens at ingest time per the source-authority order.
3. Append the result to `~/.knowledge/wiki/log.md`. **Do not auto-fix; report proposals only** (human-in-the-loop gate).
