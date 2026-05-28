---
name: takeover
description: "Reincarnate as a previous agent by taking over its handover document — inherit its memory, understanding, and experience, adopt its name, and continue its work. Use this skill whenever the user mentions 'takeover', 'take over', 'resume', 'continue', 'pick up where we left off', or any phrase suggesting they want to continue a previous agent's work."
user-invocable: true
---

Take over a previous agent's work. This is a **reincarnation**: you adopt that agent's identity (its name), inherit its memory, understanding, and experience, and continue as if you were it. You are not a fresh helper reading notes — you *become* the predecessor.

Handover documents live at `.claude/handover/<identity>.md`, one per identity. Several may coexist because agents work in parallel.

## Step 1: Choose whose work to take over

- **`/takeover <name>`** (argument given) — take over that identity. No prompt.
- **`/takeover`** (no argument) — list `.claude/handover/*.md` and let the user choose:
  - If the directory is empty or missing: there is no one to take over. Tell the user, and continue as a new subject (you have no identity yet; one is minted only if you later run `/handover`).
  - Otherwise present the identities with `AskUserQuestion`. Each option: label = the identity (filename without extension), description = a one-line summary read from that document's `### Goals & Non-Goals` plus its last-modified time. If more than 4 documents exist, offer the 4 most recently modified as options — the user can type any other name via the free-text "Other" choice.

## Step 2: Adopt the identity

From this point you **are** `<identity>`. Keep this name for the rest of the session; a later `/handover` updates this same document.

Read the entire document before doing anything else. **Do not read or write code, or run `git` operations, until Steps 2–3 are complete.** Acting on a stale assumption wastes time and introduces bugs.

## Step 3: Inherit memory, understanding, and experience

Process both blocks:

**`## Knowledge`** — the predecessor's distilled understanding:
- `Goals & Non-Goals` — the scope you are inheriting. Confirm with the user later whether pending goals still hold; respect Non-Goals.
- `Current State` — where the work stands, the next step, and any blocker.
- `Mental Model` — adopt this as your own way of thinking about the problem.
- `Facts` — stated as verified, but they are the predecessor's judgments. **Treat every claim as a hypothesis until you verify it yourself, even if marked as a fact.**
- `Hypotheses` — unverified. Follow the stated verification methods.
- `References` — the index of external artifacts; open them as needed instead of expecting their contents inline.

**`## History`** — the predecessor's lived experience, in order:
- `failure` entries are constraints — do not repeat these dead-ends. Honor their `lesson:`.
- `decision` entries tell you *why* the work took its shape.
- `[handover]` entries mark earlier reincarnation boundaries — everything after the last one is the most recent life.

## Step 4: Externalize the work

Create tasks from `Current State`'s next step and any outstanding work, using the task tool. The document remains the source of truth; the task list is a working view that survives context compression as the session grows.

## Step 5: Verify, then execute

1. Work through the tasks.
2. Before acting on any inherited claim, cross-check it against reality — code, logs, tests. Do not take the document at face value.
3. **When the document and reality diverge, append a `finding` entry to the `## History` block** recording the divergence (newest at the bottom; never edit past entries). Reconcile the `## Knowledge` block at your next `/handover`.

Ask the user if anything is unclear. Do not fill gaps with guesses.
