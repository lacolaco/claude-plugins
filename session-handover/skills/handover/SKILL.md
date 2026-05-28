---
name: handover
description: "Write or update your handover document so a successor agent can reincarnate as you — inheriting your memory, understanding, and experience, not just a task list. Use this skill whenever the user mentions 'handover', 'hand over', 'wrap up', 'end session', 'done for today', 'pass it on', 'save progress', or any phrase suggesting they want to preserve the current work for the next session."
user-invocable: true
---

Write or update a handover document so a successor can continue your work. This is not a task dump: the successor **reincarnates as you**, inheriting your memory, understanding, and experience. Write for that successor.

Each handover document belongs to one **identity** and lives at `.claude/handover/<identity>.md`. Multiple identities coexist in the same workspace because agents work in parallel — your document is yours alone.

## Step 1: Determine your identity

- **If you already have an identity this session** — you took it over via `/takeover`, or you self-named during an earlier handover this session — update that same file. Do not rename yourself.
- **Otherwise you are a new subject** — self-name. List `.claude/handover/` and choose a common English first name that is **not already taken** (e.g. `alice`, `bob`, `charlie`). Your file is `.claude/handover/<name>.md`, all lowercase. This name is now yours for the rest of the session.

Get the current timestamp for History entries: `date +%Y-%m-%dT%H:%M`.

## Step 2: Gather the true state

Before writing, build an accurate picture — do not write from memory alone:

1. If your document already exists, read it in full.
2. Run `git status` and `git log` to confirm the actual state of the work.
3. Check the task list for outstanding items.
4. Recall what you attempted, decided, discovered, and abandoned this session.

## Step 3: Write the document

The document has exactly two blocks. **No frontmatter, no title** — the filename is the identity.

### `## Knowledge` — stock information

Your distilled, present-tense understanding. **Rewrite this block entirely every handover** so it stays lean and current. Supersede stale understanding rather than appending caveats.

- `### Goals & Non-Goals` — what this work must achieve, and what is explicitly out of scope.
- `### Current State` — where you are now, the active focus, the immediate next step, and any blocker stopping progress.
- `### Mental Model` — how the system/problem actually works and **why** the current approach was chosen. The core of what a successor needs to think like you.
- `### Facts` — verified truths only. Cite evidence: a code path, a log, a doc URL, or a History timestamp it was distilled from.
- `### Hypotheses` — unverified beliefs. State confidence (high/medium/low) and how to verify each.
- `### References` — index of external artifacts (commits, PRs, issues, plans, code paths) by path/URL.

### `## History` — flow information

The raw, chronological record of what happened. **Append only — never rewrite or delete existing entries. Newest at the bottom.**

One entry per milestone, format:

```
- YYYY-MM-DDThh:mm [type] What happened. → Outcome.
```

Types (use exactly these):

- `attempt` — you tried something. Always pair with its outcome.
- `finding` — a fact about the system surfaced.
- `decision` — you chose a direction. State why.
- `failure` — an approach that did not work. State why, and append ` lesson: <what to avoid/do instead>`.
- `pivot` — you changed plan or strategy. Append ` lesson: ...` if there is one.
- `handover` — you were told to hand over. This entry closes the generation and marks the reincarnation boundary.

Reference artifacts with a trailing `[ref: <path/PR/commit>]`; never paste their contents.

Add entries for everything significant that happened this session, then **close with a `[handover]` entry**.

## Rules

- **Reference, never duplicate.** If information already lives in a commit, PR, issue, plan, or code, link to it — do not copy it into the document. Only information that exists nowhere else (your hypotheses, failures, rationale, mental model) belongs inline.
- **Redact secrets.** Never write API keys, passwords, tokens, or PII into the document.
- **Separate facts from hypotheses.** A guess written as a fact will be acted on without verification. State confidence for anything unproven.
- Ask the user if anything is unclear. Do not fill gaps with guesses.

## Step 4: Self-review

- Could a successor resume from this document alone and think the way you do?
- Is the Knowledge block lean — no duplication of artifacts, no stale understanding?
- Is every Facts claim evidenced, and every Hypotheses entry marked with confidence?
- Did you append History without touching past entries, and close with `[handover]`?
