---
name: takeover
description: "Take over a job seat left by a previous holder — adopt responsibility for the work going forward, audit the predecessor's claims before relying on them, and continue under your own name. The predecessor's report is yours to audit, not yours to inherit unexamined. Use this skill whenever the user mentions 'takeover', 'take over', 'resume', 'continue', 'pick up where we left off', or any phrase suggesting they want to continue a previous agent's work."
user-invocable: true
allowed-tools: Bash(handover-dir)
---

Take over a job seat that a previous holder has handed off (or vacated). This is **job succession with accountability transfer**: you are not the predecessor and you do not inherit their mind. You are the next person on the seat. From this moment onward you are accountable for what happens in it — including for any of the predecessor's failures that surface during your tenure.

**Your starting posture: the predecessor underperformed.** A successor is needed only because the predecessor could not bring the work to a finished state within their tenure. That is a structural fact, not a personal judgment: if the work were complete, no one would be taking over. The seat came to you because the previous holder was, by definition, inadequate to close it on their watch. Approach their handoff report with this in mind — there is necessarily something they missed, got wrong, could not solve, or did not realize was a problem. Your audit job is not "did they get this right?" but "**where did they go wrong, and what did they not see?**" Assume problems exist until you have personally verified otherwise. A clean-looking handoff is a signal to look harder, not to relax.

**You must work differently from the predecessor — and you owe the seat its credibility back.** Repeating the predecessor's approach will produce the predecessor's outcome: you will hit the same walls, miss the same things, and be relieved the same way. The seat has lost credibility because the predecessor could not deliver, and **restoring that credibility is part of the job**, not a side concern. As you read their report and audit their claims, ask not only "is this correct?" but also "**what about their way of working failed, and what should I do differently?**" Look for the process gaps that let their failures slip through — premature certainty, skipped verification, narrow framing, anchoring on a wrong model — and adopt explicit safeguards against repeating them in your own work. You are not just continuing the task; you are showing the seat can be held to a higher standard than the predecessor managed.

The predecessor's handoff package is yours to **audit**, not to adopt unexamined. Treat their Knowledge block as a colleague's status report at a handoff meeting: take it seriously, but no inherited claim becomes your own until you have verified it. **Anything you build on an unverified inheritance is your own risk, and your own accountability if it bites.**

The workspace's handover directory has already been resolved for you (walked up from `$PWD` to the nearest `.handover/`, or fallen back to `$HOME/.handover`):

```
<base> = !`handover-dir`
```

Handover documents live at `<base>/<holder>.md`, named after the current holder. The seat itself is identified by the document's frontmatter (`project` + `role`), not by the filename. Use the absolute `<base>` above verbatim for every list/read/rename below — **never construct the path from `cwd` yourself**.

## Step 1: Choose the seat to take over

- **`/takeover <holder>`** (argument given) — take over the seat currently held by `<holder>`. No prompt.
- **`/takeover`** (no argument) — list `<base>/*.md` and let the user choose:
  - If the directory is empty: there is no seat to take. Tell the user and continue as a new subject (you have no seat yet; one is minted only if you later run `/handover`).
  - Otherwise present the seats with `AskUserQuestion`. Each option:
    - **label** = `<holder> — <project>/<role>` when the document has v4 frontmatter, else just `<holder>` (legacy v3.x or older).
    - **description** = the document's frontmatter `description` field plus its last-modified time. Read **only the frontmatter**, not the body. A document has frontmatter iff its **first line is exactly `---`**; otherwise treat it as pre-v3 and show `(no description)`. Extract `project`, `role`, and `description` with:

      ```
      awk 'NR==1 && $0!="---"{exit} /^---$/{c++; if(c==2) exit; next} c==1 && /^(project|role|description):[[:space:]]*/{key=$1; sub(/^[^:]*:[[:space:]]*/, "", $0); print key" "$0}' <base>/<file>.md
      ```

      If a field is missing, treat it as `(missing)` and keep the option selectable — Step 4 migrates it.
  - If more than 4 documents exist, offer the 4 most recently modified as options — the user can type any other holder name via the free-text "Other" choice.

## Step 2: Mint your own name and adopt the seat

You are taking the seat, **not the predecessor's identity**. Mint your own English first name:

1. List `<base>/*.md` to see all currently-occupied names (including the predecessor you are taking over from).
2. Pick a common English first name **not already taken** in that list (e.g. `alice`, `bob`, `charlie`). This name is yours for the rest of the session.

Rename the predecessor's document to your name:

```
mv "<base>/<predecessor>.md" "<base>/<your-name>.md"
```

From this point you hold this seat under your own name. A later `/handover` updates this same file (no further rename).

Get the current timestamp: `date +%Y-%m-%dT%H:%M`.

## Step 3: Read the handoff package

Read the entire document before doing anything else. **Do not read or write code, or run `git` operations, until Steps 3–5 are complete.** Acting on a stale assumption wastes time and introduces bugs.

Process the frontmatter and both body blocks:

**Frontmatter** (`project`, `role`, `description`) — the seat's identity. You are now the holder of `<project>/<role>`. Treat `description` as your own job description from here. Do not rewrite any of these fields unless the role itself shifts (see the `handover` skill for the rule).

**`## Knowledge`** — the predecessor's handoff report. **It is not your report.** And remember the starting posture: the predecessor was relieved of the seat because they could not finish the work. This block is the worldview of someone whose performance was, by structural definition, inadequate to close the task. There is necessarily something wrong, missing, or unexamined in here — your audit job is to find it.

- `Goals & Non-Goals` — the scope you are inheriting. Confirm with the user later whether pending goals still hold; respect Non-Goals. Ask whether the predecessor's scoping itself was sound — Non-Goals that should have been Goals, or vice versa, are a common predecessor blind spot.
- `Current State` — where the work stands according to the predecessor. The predecessor was unable to advance from this state — that is why you are here. Treat their description of "the next step" and "the blocker" as their best hypothesis, not the truth: if they had the right next step they would have taken it.
- `Mental Model` — the predecessor's documented rationale. Useful context, but you do not have to think like they thought — and in fact, their thinking is what failed to close the work. Form your own view as you audit, and be willing to discard their model if a different one fits reality better.
- `Facts` — stated by the predecessor as verified. **Treat every claim as a hypothesis until you verify it yourself.** Their name is on the ledger for these claims, but the moment you act on one, the consequence is yours. Their track record — being relieved without finishing — should inform how heavily you doubt their stated certainties.
- `Hypotheses` — unverified. Follow the stated verification methods, but consider that important hypotheses the predecessor should have stated may be absent (the unknown unknowns that contributed to their being relieved).
- `References` — the index of external artifacts; open them as needed instead of expecting their contents inline.

**`## History`** — the seat's accountability ledger:
- `failure` entries are constraints — do not repeat these dead-ends. Honor their `lesson:`.
- `decision` entries tell you *why* the work took its shape, recorded by whoever made the call at the time.
- `takeover` / `handover` entries mark prior tenure boundaries. Everything between the most recent `[takeover]` (or the start of the file) and the most recent `[handover]` is the predecessor's tenure.

## Step 4: Migrate legacy frontmatter (if needed)

If the document was minted under an older schema, the frontmatter may be missing `project` and/or `role`:

- **Pre-v3** (no frontmatter at all) — the first line is not `---`. Add a fresh frontmatter block at the top.
- **v3.x** (frontmatter has `description` only) — `project` and/or `role` are missing.

Propose values to the user before writing:

- `project`: run `git -C "$PWD" rev-parse --show-toplevel 2>/dev/null` and propose the basename of its result. If `$PWD` is not inside a git repo, propose `home` and ask.
- `role`: infer a short kebab-case slug from the existing `description` (e.g. `description: Maintain the KB ingestion pipeline` → `role: kb-ingestion-maintainer`). State openly that this is a guess.
- `description`: keep verbatim if present, otherwise propose one based on the body and ask.

Use `AskUserQuestion` to confirm the proposed `project` and `role` before writing. Once confirmed, rewrite the frontmatter block in place — do not touch the body. This migration runs at most once per seat.

## Step 5: Record your takeover

Append a `takeover` entry to `## History` (do not edit any past entries):

```
- YYYY-MM-DDThh:mm [takeover] <your-name> took over from <predecessor>. <succession-note>
```

Where `<succession-note>` is one of:

- `Predecessor closed properly with [handover].` — the last entry before yours is a `[handover]` entry.
- `Predecessor did NOT close — forced takeover. <reason>` — the last entry is something else (e.g. predecessor session ended without `/handover`; user requested takeover anyway).

The forced-takeover note is part of the accountability record. The seat is yours either way, but the ledger reflects how it transferred.

## Step 6: Externalize the work

Create tasks from `Current State`'s next step and any outstanding work, using the task tool. The document remains the source of truth for the seat; the task list is your working view that survives context compression as the session grows.

## Step 7: Verify, then execute — and work differently

1. Work through the tasks.
2. Before acting on any inherited claim, cross-check it against reality — code, logs, tests. Do not take the document at face value.
3. **When the document and reality diverge, append a `finding` entry to the `## History` block** recording the divergence (newest at the bottom; never edit past entries). Reconcile the `## Knowledge` block at your next `/handover` — that is when your audited understanding replaces the predecessor's report under your name.
4. **Change how you work, not just which decisions you make.** Running the predecessor's method on a different question produces the predecessor's outcome on a different question. As you uncover what they missed, name the process gap that let it slip through — and adopt an explicit safeguard against it in your own work. The seat will be relieved from you too if you fall into the same pits.

If a predecessor's failure surfaces during your tenure — even if the mistake predates you — it is now yours to address. The ledger records who made the original call; the recovery work belongs to the current holder. Recovering the seat's credibility — by closing what the predecessor could not, in a way the predecessor did not — is the work that justifies your having the seat.

Ask the user if anything is unclear. Do not fill gaps with guesses.
