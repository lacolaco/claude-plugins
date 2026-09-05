---
name: kb-ingest
description: |
  Edited a project's manifest, lockfile, or config? Added or deleted a whole project? Then its `.knowledge/` wiki page is now stale — use this skill to ingest (regenerate the page) or deingest (remove it). Assume the user won't mention the wiki or KB; trigger from the file touched or the action alone.

  Fire when:
  - a project's stack/dependency/build/deploy/structure-defining file changes — package.json, any lockfile (pnpm-lock, uv.lock, gleam.lock), pyproject.toml, gleam.toml, tsup.config, angular.json, wrangler.toml, Dockerfile/Cloud Run, pnpm-workspace.yaml, new workspace packages — or its CLAUDE.md;
  - a project is cloned, forked, or placed under a KB anchor (`~/works/`, `~/.claude/`), or a project directory is removed from one;
  - **AI-generated intermediate-artifact files appear, change, or are discovered** anywhere under a KB-covered repo — design docs (`docs/designs/*.md`), review records (`docs/reviews/*.md`), plans (`docs/plans/*.md`), acceptance-test records, retrospectives, conversation logs — **regardless of git tracking state** (commit-tracked, staged, or untracked all qualify). Even encountering one via `ls`/`git status`/file read while doing unrelated work fires this skill: check whether the file is mirrored into `~/.knowledge/raw/<project>/<category>/` and copy it over if not.
  - the user says "ingest", "add to KB", "register in .knowledge", or "wiki-ize".

  Do NOT fire for ordinary feature/bugfix edits to source code, nor for changes to the KB's own schema or lint rules.
---
# kb-ingest (ingest / deingest)

The KB lives at `~/.knowledge/`. The storage schema (raw/wiki layout, OKF v0.1 conformance, page conventions, status notation, symlink spec) is in `~/.knowledge/CLAUDE.md` — read it before starting.

The `wiki/` layer is an **OKF v0.1 bundle** — every page you write or update must satisfy §9.1 (parseable YAML frontmatter + non-empty `type`).

## Ingest

1. Read the schema (`~/.knowledge/CLAUDE.md`).
2. **Collect intermediate-artifact files into `~/.knowledge/raw/`**: scan `~/works/<project>/docs/{designs,reviews,plans}/` and any other location holding AI-generated middle artifacts (acceptance-test records, retrospectives, conversation logs). Copy each into `~/.knowledge/raw/<project>/<category>/<name>.md` if not already mirrored. Tracking state is irrelevant — commit-tracked files are mirrored too. Never delete the source as a shortcut and never skip the copy because "it's already committed in the repo".
3. Read the target **at manifest depth only** (no full-source reads). Create/update `~/.knowledge/wiki/projects/<name>.md` → update `wiki/entities/` and `wiki/topics/` for cross-cutting elements and add cross-links → register in `wiki/index.md` (entry format below) → append to `wiki/log.md` under the matching `## YYYY-MM-DD` H2 heading (or add a new heading newest-on-top). Cite the source raw path for every claim (`raw/<project>/...` for mirrored artifacts; anchor path — `works/<path>` or `~/.claude/<path>` — for source code, manifests, README, CLAUDE.md); mark unverified items as `(guess)`.
4. **Write OKF frontmatter at the top of every wiki page** (see schema for controlled `type` vocabulary):

   ```yaml
   ---
   type: Project Wiki        # or Entity Wiki / Topic Wiki
   title: <human-readable name>
   description: <one sentence>          # required; the index entry is copied from this
   tags: [<keyword>, ...]               # recommended
   timestamp: <ISO 8601 UTC>            # this ingest's clock
   source_paths:                        # optional
     - works/<project>/<file or dir>
   source_commit: <git SHA>             # optional but recommended
   ---
   ```
5. **Index entries are copied from `description`, not written fresh.** Each `wiki/index.md` line is `- [Title](relative/path.md): <the page's description verbatim>`, grouped under the `## projects/` / `## entities/` / `## topics/` headings. OKF §8 says entries SHOULD carry the linked concept's `description`, and that field is one sentence — so an index line is one sentence too. Writing a separate, longer summary in the index is what makes the catalog grow past its purpose: it exists for progressive disclosure, to let a reader see what is available before opening pages. If a page's `description` is missing or is more than one sentence, fix the page first, then copy.

6. **Do not duplicate ground truth.** Versions, package manager, presence of CLAUDE.md, etc. come from `package.json` / lockfile / filesystem at query time. The wiki holds only knowledge that cannot be re-derived from the primary source (purpose, cross-cutting relations, pitfalls, contradictions). Verify package manager **from the actual lockfile** — do not trust external tables.
7. Large monorepos / framework forks such as `angular` get a pointer page only.
8. **Mandatory post-write sanitize (textlint).** After every wiki write/update (project page, entity/topic page, `index.md`, `log.md`), run the `memory-sanitize` skill's `check.sh` on `<changed wiki .md files>` and reach 0 violations before moving to step 9. The check surfaces candidates — judge each: if a real violation, restructure the prose; if a false positive (heading-then-list `:` etc.), leave as-is and note why. **Do not pass `~/.knowledge/raw/*` or the allowlist `*.json` files to check.sh** — they are not prose. Restrict the argument list to the `.md` files this ingest touched.
9. **Mandatory post-write tech-writing review.** After step 8 reaches 0 violations, perform the `tech-writing` skill review on every wiki `.md` page this ingest touched. Read the skill's normative sections in full and inspect each touched page for violations the mechanical lint cannot detect — paragraph structure, argumentative rigor, redundancy, performative phrasing, LLM-style filler. Fix violations or, for justified exceptions, leave a one-line reason. If the review modifies prose, re-run step 8's `check.sh` to confirm textlint still passes.
10. **Mandatory post-write OKF check.** Run `the `kb-lint` skill's `kb-lint.sh`` and confirm the §0 conformance row reports `frontmatter 欠落 0 / type 欠落 0 / 予約構造違反 0`. Any non-zero count blocks declaring the ingest complete — fix the offending page (add `type:` or restore the reserved file's required structure) and re-run. Declaring the ingest complete requires steps 8, 9, and 10 to have passed.

`~/.knowledge/` is plain-dir (no git) — edit files directly, no commit needed.

## Batch ingest

For a full sweep of all repos, fan out **1 project = 1 subagent** in parallel (`Agent` tool / `subagent_type: general-purpose`). Each subagent: reads the schema, ingests its assigned repo at manifest depth, writes `wiki/projects/<name>.md`, cites raw paths, returns a 3-5 line summary only (not the page body).

**Known race:** parallel runs race on writes to `index.md` / `log.md`. Subagents must use idempotent appends (read-verify-insert or retry). After the batch, verify with kb-lint and:

```
grep -c '^- \[' ~/.knowledge/wiki/index.md
ls -1 ~/.knowledge/wiki/projects ~/.knowledge/wiki/entities ~/.knowledge/wiki/topics | grep -c '\.md$'
```

The two counts must match (catches duplicates / drops).

After the batch, also run the mandatory post-write sanitize from step 8, the tech-writing review from step 9, and the OKF check from step 10 on every wiki `.md` page the batch touched (or `~/.knowledge/wiki/**/*.md` if the touched set is hard to enumerate). Reach 0 violations on all three before declaring the batch complete.

## Deingest

Triggered immediately after a project is fully removed from its anchor (e.g. `~/works/<project>/` deleted).

1. Delete `~/.knowledge/wiki/projects/<name>.md`.
2. Remove the registration line from `wiki/index.md`.
3. Scan for references in other pages with `grep -rn '<name>' ~/.knowledge/wiki/`, and clean each hit in `entities/` / `topics/` / `projects/*.md` (drop the mention, or excise while preserving surrounding context).
4. If a related entity / topic was **only used by the now-deleted project**, delete that page too. If one consumer of many was lost, just drop the row in the consumer list.
5. Append the deletion event to `wiki/log.md`.
6. Remove proper-noun mentions in the schema (`~/.knowledge/CLAUDE.md`) or other skills' ingest examples to prevent drift.
7. **Mandatory post-write sanitize + tech-writing review + OKF check** (same as the ingest path's steps 8-10): run the `memory-sanitize` skill's `check.sh` on every `.md` file this deingest touched (`index.md`, `log.md`, any consumer page edited in step 3), perform the `tech-writing` skill review on the same set, and run `the `kb-lint` skill's `kb-lint.sh``. Reach 0 violations on all three before declaring the deingest complete.
