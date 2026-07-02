---
name: kb-query
description: |
  Use this skill whenever the user is trying to recall, verify, enumerate, or reconcile facts about their own collection of projects — especially "which of my projects do X" questions. X can be a library, package, framework, version, service, cloud platform, deploy target, architectural pattern, or "what even is this project." Trigger on memory-checking and inventory intent: enumerating consumers/users of something, confirming a remembered list ("…だっけ", "…で正しい？", "…以外もあったよな", "…の気がする"), mapping relationships or dependency chains between projects, or sorting projects by which tech/version they use. Trigger even when phrased casually, even when one specific project or package is named, and even though the user never mentions a KB, wiki, or `.knowledge/`. The skill answers from the knowledge base at `~/.knowledge/` with citations.

  Do NOT trigger for: writing/debugging code inside a single named project, learning a technology in general, or adding/removing/maintaining KB pages.
---
# kb-query (querying the KB)

The KB lives at `~/.knowledge/` and the `wiki/` layer is an OKF v0.1 bundle. Page conventions, OKF type vocabulary, and citation style are in `~/.knowledge/CLAUDE.md`.

1. Search the wiki first (`~/.knowledge/wiki/index.md` → relevant page) and answer from it. **Do not re-read raw sources.**
2. Cite the page(s) you referenced. When relevant, the `type` field in a page's frontmatter (`Project Wiki` / `Entity Wiki` / `Topic Wiki`) hints at how the page should be read.
3. If the wiki is missing a valuable answer (comparison, analysis, cross-cutting connection), create a new page (via `kb-ingest` so the OKF frontmatter is written correctly) and update the index / log (compounding).
