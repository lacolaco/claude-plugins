---
name: retrospective
description: "Retrospective centered on auditing every rule and knowledge source in the session context. Enumerates all rules (CLAUDE.md, memory, skills, agents) and knowledge (KB pages, references), classifies each as followed/violated/effective/stale, diagnoses structural causes of failures, and implements fixes. Use after finishing a task, before creating a PR, or whenever the user says 'retrospective', 'wrap up learnings', or similar."
user-invocable: true
---

# Retrospective

Run before a commit or PR is created.

This retrospective audits every rule and knowledge source in the session context against what actually happened — not the agent's self-reported narrative of what went well or badly.

## On the limits of self-report

Same-context self-reflection is documented to fail via "degeneration of thought" (Reflexion, Multi-Agent Reflexion): the reflecting model reinforces its original bias rather than finding a new angle.

This skill mitigates that by ending the Submission with three parallel critic agents, each auditing from an independent context with a distinct adversarial perspective (coverage, classification, remediation).

Critics shift the probability away from append-only failure modes; they do not eliminate it. A low-finding verdict is not proof of thoroughness — only that the critic did not catch the main agent.

## The 6 stages

Reference vocabulary for locating where things happened during agent execution.

- **Input**: Receiving instructions, context, skills, CLAUDE.md, memory, tool descriptions, and actively collecting information.
- **Interpretation**: Reading the meaning, intent, and premises of the input.
- **Planning**: Task decomposition, ordering, tool selection, scope definition.
- **Action**: Tool invocation, file edits, command execution.
- **Inspection**: Verifying results and judging pass/fail.
- **Output**: Reporting to the user and deciding what to persist.

## Phase 1: Session facts

Brief chronological record of what happened. No interpretation.

For Input, inventory every rule and knowledge source in context — CLAUDE.md at each layer, memory entries (scan the memory directory; record which fired and which did not), skills invoked, agents used, KB pages read.

For Output, include the user's reaction (dissatisfaction or satisfaction).

## Phase 2: Context audit

Enumerate every rule and knowledge source from the Phase 1 inventory. Audit each against what actually happened. This is the core of the retrospective.

### Rules

Sources: CLAUDE.md (every loaded layer), memory (feedback entries), skill definitions, agent definitions.

For each rule:

- **Followed + effective** → the rule works. Record as a Keep.
- **Followed + ineffective** → the rule was applied but did not produce the intended outcome. The rule's content needs fixing (wrong prescription, outdated assumption).
- **Violated** → the rule existed in context but was not applied. Diagnose the structural cause: wrong layer (not loaded at the point of decision), too abstract (did not pattern-match the situation), buried or shadowed (drowned in volume), contradicted (another rule prescribed the opposite), not triggered (activation condition mismatch). A violated rule is a broken rule.
- **Not relevant** → no action, but note if loaded unnecessarily (scope too broad).

### Knowledge

Sources: KB pages, memory (user/project/reference entries), documentation consulted during the session.

For each item:

- **Used + accurate** → no action.
- **Used + stale or inaccurate** → update the source.
- **Available but not used** → was it relevant? If yes, diagnose why it was not consulted.
- **Needed but unavailable** → gap to fill.

### Gaps

Problems or missed opportunities with no covering rule or knowledge. These are candidates for new rules, knowledge, or higher-level fixes (hooks, skills).

## Phase 3: Improvement implementation

For each finding from the audit (violated rules, ineffective rules, stale knowledge, gaps), judge from Step 1 in order and stop at the first step that applies.

1. **Eliminate** — architectural change, automation that removes the work.
2. **Deterministic guardrail** — lint, typecheck, CI, hook.
3. **Skill** — multi-step recurring workflow.
4. **Agent prompt** — specific agent behavior.
5. **Rule library operation** (CLAUDE.md, skills, agents, memory) — **fix** (wrong content, wrong description, wrong trigger), **move** (wrong layer/placement), **delete** (obsolete), or **append** (new rule — last resort). For a violated rule, the structural diagnosis from Phase 2 dictates the operation. "Covered by existing rule" is never a terminal conclusion when the rule was violated.

As a retrospective outcome, do not modify the global layer (everything under `~/.claude/`). Present global candidates to the user as a separate task.

## Submission

Invoke three critics **in parallel** (each is a bundled agent under `agents/`). Pass each the same input:

- the workspace rule library entry points
- the Phase 2 audit results (per-rule and per-knowledge classifications)
- the Phase 3 improvement log
- the proposed Submission text
- the workspace writing-style source

| Agent | Perspective |
|-------|-------------|
| `critic-coverage` | Did the audit see everything? Source enumeration, gap analysis |
| `critic-classification` | Did the audit judge correctly? Keep quality, library drift, classification consistency |
| `critic-remediation` | Did the fixes match the problems? Violation diagnostics, layer placement, style |

Action findings from all three verdicts:

- `delete`, `move`, or `fix` workspace-local rules immediately
- queue plugin-PR-scoped findings as separate PRs
- report items requiring external coordination as `needs explicit follow-up`

Present the result to the user as a single readable headline plus a list of actions taken, followed by counters (rules audited, keeps, violations diagnosed, knowledge items audited, gaps found, fixed, moved, deleted, appended). If uncommitted changes remain, commit and push.
