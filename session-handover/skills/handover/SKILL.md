---
name: handover
description: "Write or update your handover document so the next holder of this job seat can take over your responsibilities. The seat you hold is identified by (project, role) in the document's frontmatter; the document is a handoff report, not a personal diary. Use this skill whenever the user mentions 'handover', 'hand over', 'wrap up', 'end session', 'done for today', 'pass it on', 'save progress', or any phrase suggesting they want to preserve the current work for the next session."
user-invocable: true
allowed-tools: Bash(handover-dir)
---

Write or update a handover document so the next holder of this job seat can take it over. This is not a task dump and it is not a personal diary: the document is a **handoff package** that the next holder will be held to account for if they rely on it.

**A handover is a record of incomplete work.** If you are writing this, your tenure is ending with the work unfinished — that is the only reason a successor is needed. Be honest about why: what you tried and could not close, where you are blocked, what you may have misjudged, what you suspect you did not see. The next holder is taking this seat because you could not bring it to a finished state within your tenure; your handoff report is the explanation they need to do what you could not. Do not write it as a victory lap, and do not soften failures to look better — the next holder will spot the gap, and the ledger will show that you tried to hide it.

**Help the next holder avoid your fate.** Your dismissal does not stem only from specific wrong decisions; it stems from a way of working that did not close the task — heuristics that misled you, verifications you skipped, assumptions you anchored on, framings you did not question. In your Knowledge and History entries, be specific about not just *what* you decided but *how* you decided, so the next holder can see which parts of your method failed and choose a different one. If they repeat your method they will be relieved the same way you were, and your handoff will have failed too.

Be honest, be specific, and do not paper over failures.

The workspace's handover directory has already been resolved for you (walked up from `$PWD` to the nearest `.handover/`, or fallen back to `$HOME/.handover`):

```
<base> = !`handover-dir`
```

Each handover document represents one **job seat** and lives at `<base>/<holder>.md`, where `<holder>` is the current holder's English first name. The seat's identity (which project, which role) is encoded in the document's frontmatter — not in the filename. The filename only tells you who is currently sitting in the seat. Use the absolute `<base>` above verbatim for every read/list/write below — **never construct the path from `cwd` yourself**.

## Step 1: Determine the seat you hold

- **If you already hold a seat this session** — you took it over via `/takeover`, or you minted it during an earlier `/handover` this session — you continue holding it. Open the same `<base>/<your-name>.md` and update it. Do not rename yourself.
- **Otherwise you are minting a new seat** — pick a common English first name that is **not already taken** in `<base>/` (e.g. `alice`, `bob`, `charlie`). Your file is `<base>/<your-name>.md`, all lowercase. This name is yours for the rest of the session.

Get the current timestamp for History entries: `date +%Y-%m-%dT%H:%M`.

## Step 2: Gather the true state

Before writing, build an accurate picture — do not write from memory alone:

1. If your document already exists, read it in full.
2. Run `git status` and `git log` to confirm the actual state of the work.
3. Check the task list for outstanding items.
4. Recall what you attempted, decided, discovered, and abandoned during your tenure.

## Step 3: Write the document

The document is one YAML frontmatter block followed by exactly two body blocks. **No title** — the filename is the current holder, the frontmatter identifies the seat.

### Frontmatter — the seat's identity

```
---
project: <project-slug>
role: <role-slug>
description: <one-line job description>
---
```

- `project`: the project this seat belongs to, as a kebab-case slug (e.g. `portfolio-manager`, `blog-contents`). For seats whose work spans no single project, use `home` or another stable label that disambiguates the seat.
- `role`: the role the seat-holder fills, as a kebab-case slug (e.g. `release-manager`, `kb-curator`, `auth-maintainer`). Name the **seat**, not the current task. A role survives across tasks; a task is what the role does this week.
- `description`: one-line job description — a stable statement of the work this seat exists to do (e.g. `Drive the release cycle — version bumps, changelogs, deploy, post-release verification`). Treat it like a role description in a hiring document: it identifies the job, not the current status. ≤ ~80 chars is a good target. Plain text only — no markdown, no quotes.

All three fields are **stable**. Do not rewrite them at every handover to reflect progress, blockers, or the next step — those belong in `### Current State`. The only situations that justify changing any of them are (a) you are minting a new seat, or (b) the user has explicitly told you the role itself has shifted (scope change, pivot to a different problem). Drift must be a deliberate, traceable decision — never a silent edit.

If you are minting a **new seat**, write all three fields for the first time. If you are continuing an existing seat, **copy the existing values byte-for-byte from the prior document on disk** into the new write. Do not re-type from memory, do not paraphrase, do not "improve" the wording.

The next holder's `/takeover` reads this frontmatter to pick a seat without opening its body, so accurate values are what make lightweight selection possible.

### `## Knowledge` — your handoff report

Your present-tense, honest assessment of where the work stands. **Rewrite this block entirely every handover** so it stays lean and current. Supersede stale understanding rather than appending caveats.

- `### Goals & Non-Goals` — what this work must achieve, and what is explicitly out of scope.
- `### Current State` — where you are now, the active focus, the immediate next step, and any blocker stopping progress.
- `### Mental Model` — how the system/problem actually works and **why** the current approach was chosen. The context the next holder needs to make informed decisions.
- `### Facts` — verified truths only. Cite evidence: a code path, a log, a doc URL, or a History timestamp. The next holder will treat these as hypotheses until they re-verify, but your name is on the ledger for what you assert here.
- `### Hypotheses` — unverified beliefs. State confidence (high/medium/low) and how to verify each.
- `### References` — index of external artifacts (commits, PRs, issues, plans, code paths). One artifact per bullet, each with a resolvable locator (path, URL, PR/issue number, or commit hash) and a one-line note of what it contains. The successor's `/takeover` turns every bullet into a mandatory read task, so keep entries atomic, located, and current.

### `## History` — the seat's accountability ledger

The chronological record of what happened in this seat. **Append only — never rewrite or delete existing entries. Newest at the bottom.** Past entries record who decided what when; they are the seat's audit trail across tenures.

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
- `takeover` — a new holder took over the seat. Recorded automatically by `/takeover` (do not write by hand).
- `handover` — you handed off the seat. This entry closes your tenure.

Reference artifacts with a trailing `[ref: <path/PR/commit>]` — one resolvable locator per `[ref:]`, splitting multiple artifacts into separate markers; every `[ref:]` becomes a mandatory read task at the next `/takeover`. Never paste their contents.

Add entries for everything significant that happened during your tenure, then **close with a `[handover]` entry**.

## Rules

- **Reference, never duplicate.** If information already lives in a commit, PR, issue, plan, or code, link to it — do not copy it into the document. Only information that exists nowhere else (your hypotheses, failures, rationale, mental model) belongs inline.
- **Redact secrets.** Never write API keys, passwords, tokens, or PII into the document.
- **Separate facts from hypotheses.** A guess written as a fact will be acted on by the next holder without verification, and your name is on that claim in the ledger. State confidence for anything unproven.
- **Be honest about failures.** Do not soften failure entries to look better — the next holder needs to know exactly what went wrong so they don't repeat it.
- Ask the user if anything is unclear. Do not fill gaps with guesses.

## Step 4: Self-review

- Does the frontmatter still accurately name this seat (project + role + description)? If the role hasn't shifted, the old values should stand byte-for-byte.
- Could a next holder, reading only this document, understand the work and make informed decisions about how to continue?
- Is the Knowledge block lean — no duplication of artifacts, no stale understanding?
- Is every Facts claim evidenced, and every Hypotheses entry marked with confidence?
- Is every References entry and every History `[ref:]` a single atomic artifact with a resolvable locator — something the successor's `/takeover` can turn into one read task?
- Did you append History without touching past entries, and close with `[handover]`?
