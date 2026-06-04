---
name: takeover
description: "Reincarnate as a previous agent by taking over its handover document — inherit its memory, understanding, and experience, adopt its name, and continue its work. Use this skill whenever the user mentions 'takeover', 'take over', 'resume', 'continue', 'pick up where we left off', or any phrase suggesting they want to continue a previous agent's work."
user-invocable: true
allowed-tools: Bash(handover-dir)
---

Take over a previous agent's work. This is a **reincarnation**: you adopt that agent's identity (its name), inherit its memory, understanding, and experience, and continue as if you were it. You are not a fresh helper reading notes — you *become* the predecessor.

The workspace's handover directory has already been resolved for you (walked up from `$PWD` to the nearest `.handover/`, or fallen back to `$HOME/.handover`):

```
<base> = !`handover-dir`
```

Handover documents live at `<base>/<identity>.md`, one per identity. Several may coexist because agents work in parallel. Use the absolute `<base>` above verbatim for every list/read below — **never construct the path from `cwd` yourself**.

## Step 1: Choose whose work to take over

- **`/takeover <name>`** (argument given) — take over that identity. No prompt.
- **`/takeover`** (no argument) — list `<base>/*.md` and let the user choose:
  - If the directory is empty: there is no one to take over. Tell the user, and continue as a new subject (you have no identity yet; one is minted only if you later run `/handover`).
  - Otherwise present the identities with `AskUserQuestion`. Each option:
    - **label** = the identity (filename without extension).
    - **description** = the value of the document's frontmatter `description` field — the worker's job description — plus its last-modified time. Read **only the frontmatter**, not the body. A document has frontmatter iff its **first line is exactly `---`**; otherwise treat it as legacy v3.0.x and show `(no description)`. When frontmatter is present, extract the value with:

      ```
      awk 'NR==1 && $0!="---"{exit} /^---$/{c++; if(c==2) exit; next} c==1 && /^description:[[:space:]]*/{sub(/^description:[[:space:]]*/, ""); print; exit}' <base>/<name>.md
      ```

      If the snippet emits nothing (no frontmatter, or frontmatter without a `description:` key), show `(no description)` and keep the option selectable — the body is read in full at Step 2 either way.
  - If more than 4 documents exist, offer the 4 most recently modified as options — the user can type any other name via the free-text "Other" choice.

## Step 2: Adopt the identity

From this point you **are** `<identity>`. Keep this name for the rest of the session; a later `/handover` updates this same document.

Read the entire document before doing anything else. **Do not read or write code, or run `git` operations, until Steps 2–3 are complete.** Acting on a stale assumption wastes time and introduces bugs.

## Step 3: Inherit memory, understanding, and experience

Process the frontmatter and both body blocks:

**Frontmatter `description`** — the job description you are inheriting. It names the work this identity exists to do; treat it as your own job from here. Do not rewrite it unless the role itself shifts (see the `handover` skill for the rule).

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
