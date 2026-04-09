---
name: handover
description: "Create or update a structured handover document at the end of a Claude Code session to ensure task continuity across sessions. Use this skill whenever the user mentions 'handover', 'hand over', 'wrap up', 'end session', 'done for today', 'pass it on', 'save progress', or any phrase suggesting they want to end the current session and preserve context for the next one."
user-invocable: true
---

Create or update a handover document for the next Claude session.

The document path is specified via $ARGUMENTS. If not provided, use `<workspaceRootDir>/task.local.md`.

## Steps

### Phase 1: Gather Information

Before writing, build an accurate picture of the current state:

1. If an existing handover document exists, read it and identify gaps with the current state
2. Run `git status` and `git log` to confirm the actual state of work
3. Check TaskList for outstanding tasks (skip if task tools are unavailable)
4. Recall approaches attempted and failed during this session

### Phase 2: Write the Document

Based on gathered information, write the handover document following the template below. Even if an existing document exists, **rewrite it entirely from the template** to ensure accuracy. Use the previous document as a reference, but reflect the current session's state.

**Strictly distinguish hypotheses from facts.** If something was judged as "probably X" during this session, do not write it as a fact. The next session will act on it without verification. State the confidence level for hypotheses and cite evidence for facts.

Ask the user if anything is unclear. Do not fill gaps with guesses.

### Phase 3: Self-Review

After writing, verify the document:

- Can the next session resume work from this document alone?
- Are facts and hypotheses clearly separated?
- Are next actions specific? ("Investigate the behavior of function X in file Y" rather than just "investigate")

## Template

Follow this Markdown template. The comments in each section are guidelines — do not include them in the output.

```markdown
# Handover Document

Written at: YYYY-MM-DD

## Goals
<!-- List overall task goals as a checklist. Mark completed and pending items -->
- [x] Completed goal
- [ ] Pending goal

## Current State
<!-- Briefly describe the current state of work. What's working and what isn't -->

## Tasks
<!-- List outstanding tasks in priority order. Note dependencies if any -->

## Facts
<!-- Verified facts. Cite evidence (code locations, logs, documentation URLs, etc.) -->

## Hypotheses
<!-- Unverified hypotheses. State confidence level (high/medium/low) and how to verify -->

## Failure Log
<!-- Approaches that were tried and failed. Record what was tried and why it failed. Critical for preventing the next session from repeating the same mistakes -->

## Issues
<!-- Unresolved concerns or blockers -->

## Plans
<!-- Strategy and direction going forward -->

## Notes
<!-- Any other information the next session should know -->
```
