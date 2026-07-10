---
name: retrospective
description: "Retrospective grounded in the garbage-in-garbage-out principle: traces problems from Output back to their upstream origin across six stages, then fixes at the stage where the cause lives — knowledge deficiencies get knowledge fixes, not downstream rule patches. Implements fixes in the current session. Use after finishing a task, before creating a PR, or whenever the user says 'retrospective', 'wrap up learnings', or similar."
user-invocable: true
---

# Retrospective

Run before a commit or PR is created.

## Core principle: fix where it broke

This retrospective is grounded in garbage-in-garbage-out: if the input was wrong, no amount of downstream rules can reliably compensate. Each problem is traced to the upstream stage where it originated, and the fix is applied there — not patched over downstream.

An Input-stage deficiency (missing, stale, or wrong knowledge) is fixed by knowledge operations — not by appending a rule that says "remember to check X."

## On the limits of self-report

Same-context self-reflection fails via "degeneration of thought" (Reflexion, Multi-Agent Reflexion). This skill mitigates that with three parallel critic agents at Submission, each auditing from a fresh context.

## The 6 stages

- **Input**: Knowledge, rules, tools, and instructions received or collected.
- **Interpretation**: Reading meaning, intent, and premises.
- **Planning**: Decomposition, ordering, tool selection, scope.
- **Action**: Tool invocation, edits, commands.
- **Inspection**: Verifying results, judging pass/fail.
- **Output**: Reporting, persistence decisions.

## Phase 1: Session facts

Brief chronological record. No interpretation.

Inventory every rule and knowledge source in context — CLAUDE.md at each layer, memory entries (which fired, which did not), skills invoked, agents used, KB pages read. Include the user's reaction in Output.

## Phase 2: Bottom-up tracing

Walk from Output back to Input. At each stage:

- **Problems** — what went wrong? Is the true cause here, or further upstream?
- **Opportunities** — no failure, but a better outcome was reachable.

**Root cause test**: "If this cause were eliminated at this stage, would all downstream symptoms disappear?" If yes, this is the true cause. If no, trace further upstream.

Record the originating stage for each cause. This attribution drives Phase 4.

## Phase 3: Keeps

At each stage, name a success pattern worth keeping. Quality bar: applicable to future sessions, phrased as a principle, not a session-specific verified fact.

## Phase 4: Stage-matched remediation

For each true cause and opportunity from Phase 2, **design and implement** a fix at the stage where the cause lives. A downstream patch for an upstream cause is not a valid fix.

### Input — the context was wrong or missing

Knowledge, memory, or tool access was deficient. No downstream rule compensates for bad input.

- **Knowledge**: invoke `kb-ingest` to create missing pages, revise stale pages, or reorganize. If a wiki page was consulted but inaccurate, update it now. If needed knowledge was absent, ingest it now.
- **Memory**: add or revise memories (user/project/reference/feedback).
- **Tools**: configure MCP servers, hooks, or access.

### Interpretation — the context was present but misread

- **Fix** ambiguous rules (wrong content, unclear trigger, too abstract to pattern-match).
- **Move** rules to the correct layer (invisible at the point of decision = wrong layer).
- **Delete** obsolete or contradictory rules.

### Planning — understood correctly, planned poorly

- **Skill**: codify as a recurring workflow.
- **Agent**: define specialized behavior.

### Action — plan correct, execution failed

- **Eliminate**: automate the manual step.
- **Guardrail**: hook, lint, CI, typecheck.

### Inspection — verification missed the defect

- Strengthen verification steps or test coverage.

### Output — correct but poorly delivered

- Fix reporting, persistence, or communication rules.

### Implementation mandate

**Implement each fix in this session.** Do not propose — execute.

- Knowledge operations: invoke the relevant `kb-*` skill now.
- Rule operations: edit the file directly.
- Guardrails: create or modify the configuration.
- Global layer (`~/.claude/`): present to the user as a separate task. The retrospective does not modify the global layer.

Only actions requiring external coordination (user auth, cross-repo, upstream dependency) may be deferred as `needs explicit follow-up`.

## Submission

Invoke three critics **in parallel** (bundled under `agents/`):

| Agent | Perspective |
|-------|-------------|
| `critic-coverage` | Exhaustiveness — source enumeration, stage coverage, missed problems |
| `critic-classification` | Correctness — keep quality, stage attribution, library drift |
| `critic-remediation` | Remediation soundness — stage alignment, implementation verification, style |

Action the verdict's findings in this session. Present the result as a headline plus actions taken, with counters (problems traced, opportunities surfaced, knowledge operations, rule fixes, keeps, items deferred).

If uncommitted changes remain, commit and push.
