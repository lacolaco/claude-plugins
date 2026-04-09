---
name: takeover
description: "Resume work from a previous session's handover document. Reads the document and follows a structured process to restart work safely. Use this skill whenever the user mentions 'takeover', 'take over', 'resume', 'continue', 'pick up where we left off', 'read task.local.md', or any phrase suggesting they want to continue work from a previous session."
user-invocable: true
---

Read the handover document from the previous session and resume work.

The document path is specified via $ARGUMENTS. If not provided, use `<workspaceRootDir>/task.local.md`.

## Steps

Execute the following 3 phases in order. Do not read or write code, or run `git` operations until Phase 1-2 are complete. Acting on an incomplete understanding risks wasting time on stale assumptions and introducing bugs.

### Phase 1: Read and Understand

1. Read the handover document in full
2. Process each section with the following lens:
   - **Goals**: Understand the overall scope. Confirm with the user later whether pending goals are still valid
   - **Current State**: Note the state as described. Verify against reality in Phase 3
   - **Tasks**: These will be externalized in Phase 2
   - **Facts**: Stated as verified, but these are the previous session's judgments. **Treat everything as a hypothesis until you verify it yourself, even if marked as "confirmed" or "verified"**
   - **Hypotheses**: Unverified assumptions. Follow the stated verification methods if provided
   - **Failure Log**: Record of failed approaches. Treat these as constraints to avoid repeating the same mistakes
   - **Issues**: Unresolved concerns. Decide in Phase 2 whether to convert them to tasks or treat as blockers
   - **Plans**: The previous session's intended strategy. Use as reference, but it is not binding
   - **Notes**: Acknowledge as supplementary context

### Phase 2: Externalize Tasks

3. Create all outstanding tasks from the Tasks, Issues, and pending Goals sections using TaskCreate
4. Set dependencies between tasks using TaskUpdate

As the context window progresses, details from the handover document read early on will be compressed or lost. Externalizing to task tools preserves visibility over the full scope of work.

If task tools are unavailable, output the task list as a checklist in the conversation.

### Phase 3: Verify and Execute

5. Work through the task list
6. Before starting each task, verify the facts it depends on. Do not take the handover document's claims at face value — cross-check against code, logs, and test results
7. If the handover document and reality diverge, update the handover document

Ask the user if anything is unclear. Do not fill gaps with guesses.
