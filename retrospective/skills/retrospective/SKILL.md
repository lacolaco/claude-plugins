---
name: retrospective
description: "Retrospective based on a 6-stage process (input → interpretation → planning → action → inspection → output). Surfaces problems bottom-up from outputs and applies fixes top-down from upstream. Holes plugged upstream are not plugged again downstream. Use this skill after finishing a task, before creating a PR, or whenever the user says 'retrospective', 'wrap up learnings', 'identify improvements', or similar."
user-invocable: true
---

# Retrospective

Run this skill before a commit or PR is created.

An agent's task execution proceeds through 6 stages:

**Input → Interpretation → Planning → Action → Inspection → Output**

A retrospective lifts **Problems bottom-up** from downstream to upstream, and applies **Tries top-down** from upstream to downstream. **A hole plugged upstream is not plugged again downstream.** Layered defenses are added only when upstream countermeasures are low-confidence.

## On the limits of self-report

This skill is run by the same agent that produced the session being retrospected. Same-context self-reflection is documented to fail via "degeneration of thought" (Reflexion, Multi-Agent Reflexion): the reflecting model reinforces its original bias rather than finding a new angle.

The skill therefore bundles fresh-context critic agents at every step where the main agent's bias would otherwise control the outcome:

- Phase 2 Opportunity surfacing: `opportunity-finder` (refutes "no opportunities")
- Phase 3 Keep extraction: `keep-extractor` (refutes case-specific or industry-baseline Keeps)
- Phase 5 Step 5.5 search log: `search-log-critic` (refutes "no existing rule covers this")
- Submission curator audit: `curator` (refutes "library is healthy")

Even with these critics, this skill cannot fully break the agent's self-report — the agent still chooses what to pass to each critic, and counters in the Submission are agent-reported. The critics shift the probability away from append-only failure modes; they do not eliminate it. Acknowledge this limit when reviewing the Submission: a low-bloat report is not proof the retrospective was thorough, only that no critic caught the agent.

All four critics are configured with `model: sonnet`, following Anthropic's published Claude Code guidance that Sonnet is the recommended tier for "most engineering" work. Critic tasks are adversarial reasoning — refuting search logs, stress-testing Keeps, auditing library drift — not parallelized high-volume execution. Haiku is appropriate for the latter; sub-agents doing logical refutation work need at least Sonnet's reasoning tier.

## The 6 stages

- **Input**: Receiving instructions, context, skills, CLAUDE.md, tool descriptions, and actively collecting information via Read/Grep/Glob/WebFetch, etc.
- **Interpretation**: Reading the meaning, intent, and premises of the input
- **Planning**: Task decomposition, ordering, tool selection, scope definition
- **Action**: Tool invocation, file edits, command execution
- **Inspection**: Verifying results and judging pass/fail
- **Output**: Reporting to the user and deciding what to persist

## Phase 1: Fact recording

Record the facts that occurred at each of the 6 stages, in chronological order. Do not mix in interpretation or evaluation.

- **Input**: Instructions received / information collected and its primacy
- **Interpretation**: Intent read / premises assumed
- **Planning**: Steps broken down / tools selected / scope fixed
- **Action**: Operations executed / side effects that occurred / places redone
- **Inspection**: Verifications performed / acceptance criteria adopted
- **Output**: Content reported / whether it was persisted / user reaction (dissatisfaction, satisfaction)

## Phase 2: Bottom-up surfacing — Problems and Opportunities (Output → Input)

From downstream to upstream, surface two kinds of findings at each stage.

**Problems** (failures and defects that actually occurred):

1. What Problem occurred at this stage?
2. Could this stage have detected or corrected the downstream Problem?
3. Is the true cause here, or further upstream?

**Opportunities** (no failure occurred, but a better outcome was possible):

4. What worked at this stage but could have been better (faster, more precise, less costly)?
5. What new tool, pattern, skill, or workflow could have been adopted at this stage?
6. What did the ideal outcome look like at this stage, and what gap remained between the actual result and that ideal?

Surfacing Opportunities is non-optional. A retrospective that only finds Problems is a defensive workflow, not a self-improvement one. The absence of failure does not mean the absence of room to improve.

### Phase 2 verification — opportunity-finder agent (mandatory)

After surfacing Opportunities, **before proceeding to Phase 3**, invoke the bundled `opportunity-finder` agent via the Agent tool (`agents/opportunity-finder.md`). Pass it your surfaced Opportunities list (which may be empty) and a brief description of the session. The agent runs in a fresh context with a default-to-find posture and returns either `no additional opportunities found` or `additional opportunities: <list>`.

Merge any additional Opportunities the agent surfaces into the Phase 2 result before moving on. Do not silently discard them — that defeats the purpose of the gate.

Order (reverse):

1. **Output**: Excess or missing in the report / missing persistence / specifics of user dissatisfaction
2. **Inspection**: Verification skipped / wrong acceptance criteria / inappropriate verification method
3. **Action**: Tool misuse / wrong arguments / missed side effects / environment misrecognition
4. **Planning**: Wrong decomposition granularity / wrong order / scope drift
5. **Interpretation**: Misreading of intent / swapping of premises / overlooked contradictions
6. **Input**: Insufficient information / contaminated information / insufficient collection / primary source not consulted

### Are existing rules themselves inducing the Problem?

If a description in CLAUDE.md or a skill invites a literal interpretation that causes runaway behavior, the rule itself has a defect in wording or granularity. Do not stop at blaming only your own interpretation.

### Input errors are an independent factor alongside insufficiency

"Insufficient information" and "contaminated information" are different. Countermeasures differ too. Identify the source of contamination (outdated skill, stale CLAUDE.md, tool description divergent from implementation, secondary source treated as primary, hallucinated memory, distorted previous-session summary).

## Phase 3: Extracting Keeps

At each stage, extract the success patterns worth keeping.

- Which stage had what working?
- Can it be abstracted into a reusable form?

Quality bar:

- Not specific to this case; applicable to similar situations
- Not "verified X" but at the level of "did not place a premise without verification"

### Phase 3 verification — keep-extractor agent (mandatory)

After listing Keeps, **before proceeding to Phase 4**, invoke the bundled `keep-extractor` agent via the Agent tool (`agents/keep-extractor.md`). Pass it your Keeps list and a brief description of the session. The agent runs in a fresh context with a default-to-revise posture and returns either `keeps confirmed` or `keeps need revision: <list>`.

For each Keep flagged `needs revision`, revise (raise the abstraction, strip session-specific nouns, add context bounds) or drop it. Do not keep flagged Keeps unchanged — the gate exists to catch session facts and industry baselines that drift into Keeps under the main agent's bias.

## Phase 4: Top-down Try rollout (Input → Output)

For both the true causes (from Problems) and the Opportunities identified in Phase 2, establish Tries from upstream downward. **A hole plugged upstream is not plugged again downstream.**

Before establishing a Try at each stage, ask:

- If the true cause was already cut off upstream, no countermeasure is needed at this stage
- For Opportunities, ask whether an upstream adoption (e.g. a new tool earlier in the pipeline, a new skill that re-shapes Planning) is sufficient before adding stage-local Tries
- Layered defense is applied only when the upstream countermeasure is low-confidence

Tries from Problems address recurrence (defensive). Tries from Opportunities adopt new tools, patterns, or workflows (progressive). Both kinds of Tries flow through the same Phase 5 implementation ladder.

Order (forward):

1. **Input**: Define information source priority / discipline active collection / fix stale skills, CLAUDE.md, tool descriptions
2. **Interpretation**: Add confirmation conditions / surface premises / discipline contradiction detection
3. **Planning**: Templatize plans / discipline decomposition granularity / define scope
4. **Action**: Tool selection criteria / turn operation patterns into skills / enumerate side effects in advance
5. **Inspection**: Document inspection items / define acceptance criteria
6. **Output**: Report format / discipline persistence decisions

### Continuously recurring work patterns

Among the Problems from Phase 2, ones that satisfy all of the following are skill candidates:

- Consist of multiple steps
- Will recur in the future
- Not already covered by an existing skill, or can be handled by extending one

Bad example: "Procedure for the specific files edited this time" (too local)
Good example: "Post-merge workflow after a PR is merged (delete branch → retrospective → update handover)"

### Quality bar for principles

Bad example: "Verify Gemini API `oneOf` support in advance"
Good example: "Do not use secondary information as a basis for causal reasoning. Back it up with an actual check or a primary source."

## Phase 5: Improvement implementation flow

Process each Try from Phase 4 via the following flow. **Always judge from Step 1 in order.** At each step ask "can this means address it?" — if yes, apply it and end the flow. If no, proceed to the next step. Do not skip ahead.

### Step 1: Can it be eliminated?

Ask whether the rule or work itself can be prevented from arising: architectural change, automation that removes the step, design that structurally prevents the problem.

- Yes → apply and end the flow
- No → proceed to Step 2. Record why you judged it impossible

### Step 2: Can a deterministic guardrail enforce it?

Ask whether a machine can enforce or detect it: lint, typecheck, CI, pre-commit hooks, `settings.json` hooks, etc.

- Yes → apply and end the flow
- No → proceed to Step 3. Record why you judged it impossible

### Step 3: Can it become a skill?

If it is a continuously recurring work pattern, separate it into a `SKILL.md` as a procedure. If an existing skill covers it, extend that one.

Placement layer:

- Workspace-specific work pattern → workspace `<workspace>/.claude/skills/<name>/SKILL.md`

Judgment:

- Target is a work pattern → must be handled here (no exceptions). End the flow
- Target is a principle that cannot be expressed as a skill → proceed to Step 4

### Step 4: Can it be expressed in an agent prompt?

Ask whether it can be defined as the behavior of a specific agent.

Placement layer:

- Workspace-specific agent behavior → workspace `<workspace>/.claude/agents/<name>.md`

Judgment:

- Yes → apply and end the flow
- No → proceed to Step 5. Record why you judged it impossible

### Step 5: Operate on an existing rule (preferred over adding new)

If a rule that addresses the same Problem or Opportunity already exists, take exactly one of three actions on it:

- **delete** — the rule is no longer needed (the underlying condition is gone, or the rule was wrong in the first place)
- **move** — the rule belongs in a different file or section (placement is the defect)
- **fix** — the rule's content is wrong; change what it actually requires (the rule failed to capture what should be required, or its scope is misaligned with reality)

"Re-wording" the rule (changing the rhetorical surface without changing what it actually requires) is explicitly out of scope here. If a rule fails to fire despite being "right," the issue is delete (unneeded), move (wrong placement), or fix (wrong content). It is never a wording issue. Treating it as a wording issue routes the agent away from the structural problem and into low-cost rhetorical edits that don't change behavior.

Search existing CLAUDE.md / skills / agents for a rule that covers the same Problem or Opportunity. If found, apply delete, move, or fix. Merge similar items rather than stacking them; do not let the file bloat.

**Before proceeding to Step 6, produce a Step 5 search log as literal evidence.** The log must contain:

- The existing rules you reviewed (file path + brief excerpt that identifies the rule)
- For each reviewed rule, which of delete / move / fix was attempted and why it failed (e.g. "subject mismatch — this rule addresses CI premise verification, the new finding is about pre-design industry-precedent verification, integrating would conflate two axes")

A search log with zero rules reviewed is not a valid "no existing rule covers" judgment. At minimum, justify why the relevant section of CLAUDE.md / skills / agents was empty of candidates.

### Step 5.5: Adversarial verification of the search log (mandatory)

After producing the Step 5 search log, **before** proceeding to Step 6, invoke the bundled `search-log-critic` agent via the Agent tool to adversarially verify the log. This agent ships with the `retrospective` plugin (`agents/search-log-critic.md`) so it is always available wherever the skill is installed.

Pass the agent both the candidate Problem or Opportunity and the Step 5 search log. The agent runs in a fresh context that does not share the main agent's bias toward "no existing rule covers this," and is prompted to refute the log.

The agent returns exactly one verdict:

- `confirmed exhaustive` → proceed to Step 6 with both the search log and the verdict attached
- `plausible miss found: <rule file path> — <reason>` → return to Step 5, expand the search to include the surfaced rule, apply delete, move, or fix on it as appropriate, and re-run Step 5.5 with the expanded log

Why this is structural rather than self-checked: single-agent self-reflection on its own search log is documented to fail via "degeneration of thought" — the reflecting model reinforces its own original bias rather than finding a genuinely new angle. The `search-log-critic` agent runs in a fresh subagent context with an adversarial role and a default-to-refute posture, which is what breaks the loop.

### Step 6: Append a new rule to workspace CLAUDE.md (last resort)

Only when Steps 1–5 are all judged "checked but not applicable" with literal evidence. For Step 5 specifically, the evidence must include **both** the search log (existing rules reviewed + per-rule reject reason) **and** the Step 5.5 adversarial verdict of `confirmed exhaustive` from a fresh subagent. **Step 6 entry without both pieces of evidence is invalid: return to Step 5 and produce them first.**

The target is concrete work, problem-solving, workflows, or domain knowledge specific to that workspace.

**Why CLAUDE.md is the worst option: it is not modular and has no separation of concerns.** Steps 1–4 each carry a module boundary (design unit, guardrail unit, skill unit, agent unit). CLAUDE.md piles all responsibilities into a single file, causing bloat, context pollution, and responsibility mixing.

The new rule must satisfy all of the following:

- **One principle per line.** Examples minimized
- **Positive framing.** Write what to do, not what not to do (e.g. "Verify against primary source" instead of "Do not assume from secondary source")
- **WHY embedded in one sentence.** Include the motivation alongside the rule itself; do not rely on the establishment link to carry the why
- **No coined terms.** Use the vocabulary of the actual fix, not the retrospective's narrative literal text. Coined labels (made up to describe the failure) become brittle hardcoded logic and lose meaning when revisited later
- **Establishment link at the end.** Append a link to the retrospective record that established this rule

If these constraints cannot all be satisfied, return to Step 5 and force-revise an existing rule instead.

#### Handling the global layer

**As a retrospective outcome, do not modify the global layer (everything under `~/.claude/`: CLAUDE.md, skills, agents, settings.json, etc.).** Additions, deletions, and modifications are all forbidden.

Extraction to the global layer is **overreach**. Even if a Phase 4 target is judged to have universal applicability, the retrospective does not write to the global layer. Present it to the user as a "candidate for promotion to global" and execute it as an independent task only after receiving explicit instruction. It is outside the retrospective's scope.

All retrospective outcomes are written to workspace-local locations only. Placements are workspace CLAUDE.md, skills, or agents.

### Step 7: Retroactively apply new rules to session artifacts

Once Steps 1–6 produce a new rule / skill / guardrail, retroactively check the artifacts already produced in this session (issues, MR descriptions, comments, docs, code, commit messages) against the new rule.

- Establishment and application are separate steps. Creation alone does not improve recent outputs
- When you detect a violation of the new rule, update the original artifact (GitLab / GitHub / file)
- When you confirm no violations, include "confirmed" in the retrospective submission

If artifacts that violate a rule you just established remain as is, the retrospective's outcome is empty.

## Submission

Before presenting the results, invoke the bundled `curator` agent via the Agent tool (`agents/curator.md`). Pass it the workspace's rule library entry points (CLAUDE.md, wiki/discipline directory, plugin skills and agents) and the most recent retrospective Fact files. The curator returns a structured audit report.

Then present the submission to the user as a single readable story, not as a dump of internal phase numbers and single-letter counters. Internal labels like "Phase 1 Fact recording" or "Phase 5 Step 6" should stay internal — they are the agent's scaffolding, not user-facing structure.

Use the following layout, in the workspace's natural language:

### 1. Headline (1–2 sentences)

What this retrospective changed, and what is queued for next time. The reader should grasp the outcome from the headline alone.

### 2. Health checks (only if triggered, near the top)

Surface these in plain language only when the condition is met:

- "Step 5 was likely skipped" — when one or more rules were appended this session but no rule was deleted, moved, or fixed. Confirm the Step 5.5 verdict actually came back as `confirmed exhaustive`.
- "Stuck in defensive mode" — when no Opportunities were surfaced this session and the same was true across several recent retrospectives. The workflow has degraded into Problem-only recurrence prevention.

Omit the section entirely if nothing is triggered.

### 3. What we changed

For each delete, move, fix, or append actually applied this session, one line each. No nesting, no separate sections per operation type — let the reader scan them together:

- `delete <rule path>` — one-phrase reason
- `move <rule path> to <new location>` — one-phrase reason
- `fix <rule path>` — one-phrase summary of the content change
- `append <rule path>` — one-phrase summary of the new rule

If nothing was applied this session, say so in one sentence ("No rule changes applied this session — the surfaced items routed to upstream Steps 1–4 instead, see <reference>").

### 4. Queued for next time

The top 3–5 highest-priority findings from the curator audit, each as one line. Less urgent findings remain in the full curator audit (link or appendix). Empty section is fine — say "No queued items from the curator this session."

### 5. Counters (footer)

A small footer with the raw counts, for trend tracking across retrospectives. Put it last so it does not dominate the report:

- surfaced: <N> problems, <M> opportunities
- applied: <D> delete, <V> move, <F> fix, <A> append

### Example shape of the final report

```
The OAuth refactor surfaced one slow-path bug and one verification-skipped opportunity. Fixed the existing "verify against primary source" rule to cover OAuth state callbacks; one obsolete rule queued for next time.

Stuck in defensive mode — last three retrospectives surfaced zero opportunities. Widen the Phase 2 opportunity scan next session.

What we changed:
- fix discipline/work-protocols.md "premise verification" — extended to cover OAuth state callbacks alongside CI premise
- delete discipline/agent-discipline.md "use literal error string for tests" — superseded by spec/error_matchers
- append discipline/session-discipline.md "rotate OAuth client secrets per environment" — closes a long-running confusion

Queued for next time (from the curator):
- discipline/session-discipline.md "shadow branch autonomy" overlaps fixture-project-edits-autonomous memory — merge candidate
- skills/aratame-validation example block references deleted fixture path — fix candidate

surfaced: 3 problems, 1 opportunity
applied: 1 delete, 0 move, 1 fix, 1 append
```

The example shows the layout, not a target — real retrospectives have varied content. The point is the order (headline, health, changes, queued, counters) and the plain-language tone, not the specific items.

After application, if there are uncommitted changes, autonomously commit and push.
