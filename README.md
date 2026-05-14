# claude-plugins

Claude Code plugins by lacolaco.

## Plugins

| Plugin | Description |
|--------|-------------|
| [protect-main-branch](./protect-main-branch) | Prevent git operations that would modify the main branch (configurable) |
| [session-handover](./session-handover) | Session handover/takeover for task continuity between sessions |
| [retrospective](./retrospective) | Structured 6-stage retrospective for tasks, PRs, and incidents |
| [session-tts](./session-tts) | Read Claude Code responses aloud locally with a different Japanese voice per session. Instructs Claude to deliver mid-turn progress narration via a synchronous Bash call into the say adapter. Permission prompts include the workspace name. ON by default; engine and voices are managed automatically (Apple Silicon) |

## protect-main-branch

Blocks git subcommands that would modify the protected branch (defaults to `main`) when checked out in Claude Code.

### How it works

- On any branch other than the protected branch: no-op (all operations allowed)
- On the protected branch: Bash commands invoking the following git subcommands are denied — `commit`, `push`, `merge`, `rebase`, `reset`, `cherry-pick`, `revert`, `am`. All other operations (Write, Edit, `git pull`, `git status`, `git switch`, etc.) pass through unchanged.

`git pull` is intentionally allowed so the protected branch can be synced with its upstream. To introduce changes to the protected branch, do the work on a feature branch and merge it via a PR.

When blocked, the hook returns:

```
Cannot run `git <subcommand>` on <branch> branch. Create a feature branch first.
```

### Configuration

The protected branch name defaults to `main`. To protect a different branch or multiple branches, set the `PROTECT_MAIN_BRANCH_NAME` environment variable (space-separated list) in your Claude Code `settings.json`:

```json
{
  "env": {
    "PROTECT_MAIN_BRANCH_NAME": "main master develop"
  }
}
```

This can be set at user scope (`~/.claude/settings.json`), project scope (`.claude/settings.json`), or local (`.claude/settings.local.json`).

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install protect-main-branch@lacolaco-plugins
```

### Prerequisites

- `jq` must be installed

## session-handover

Provides two paired skills for managing task continuity between Claude Code sessions:

- **`/handover`** - Creates or updates a structured handover document (`task.local.md`) at session end, capturing goals, current state, tasks, facts, hypotheses, issues, and next actions
- **`/takeover`** - Resumes work from a handover document at session start, with a rigorous 3-phase process: read, externalize tasks, then verify and execute

### How it works

When ending a session, invoke `/handover` to generate a structured Markdown document that captures the current state of work. When starting a new session, invoke `/takeover` to read that document and resume work with full context.

The takeover skill enforces a disciplined approach: it reads the handover document, externalizes all tasks using Claude Code's task tools, and only then begins verification and execution. It treats all claims from the previous session as hypotheses until verified.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install session-handover@lacolaco-plugins
```

## retrospective

Provides the `/retrospective` skill: a structured 6-stage framework (input → interpretation → planning → action → inspection → output) for reviewing a completed task, PR, or incident.

### How it works

The skill walks through five phases:

1. **Fact recording** — log what happened at each of the 6 stages, without mixing in interpretation
2. **Bottom-up Problem surfacing** — trace Problems from downstream stages (Output, Inspection) up to upstream (Interpretation, Input) to find the true cause
3. **Keep extraction** — capture reusable success patterns
4. **Top-down Try rollout** — apply fixes from upstream down; do not plug the same hole twice
5. **Improvement implementation flow** — for each Try, judge in order: (1) eliminate, (2) deterministic guardrail, (3) skill, (4) agent prompt, (5) workspace `CLAUDE.md` as the last resort

All retrospective outcomes are written to workspace-local locations only — the skill does not modify the global `~/.claude/` layer.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install retrospective@lacolaco-plugins
```

## session-tts

Reads Claude Code's responses aloud on your local machine. Each Claude Code session is automatically assigned one of three different Japanese voices in a fixed rotation, so when several sessions are running you can tell them apart by voice. Synthesis happens locally; no external API is called during playback.

### How it works

The plugin subscribes to six hook events:

- **`SessionStart`** — assigns this session a voice from the 3-slot rotation (the assignment is stored at `~/.claude/session-tts/sessions/$session_id` and stays stable across `clear`/`compact` re-fires). It also kicks off a background engine bootstrap that is idempotent: typical re-runs do nothing.
- **`SessionEnd`** — fires when this session terminates (`/clear`, `/compact`, logout, etc.). SIGTERMs any in-flight playback for this session via the per-session pidfile so audio doesn't outlive the session that started it. Voice assignment and the silence flag are intentionally left in place so the same session_id keeps its voice across `/clear`.
- **`Stop`** — fires when Claude finishes a normal response; speaks `last_assistant_message`
- **`StopFailure`** — fires when the turn ends due to an API error; speaks `last_assistant_message`
- **`Notification`** with the `permission_prompt` matcher only — a tool needs approval → speaks 「<workspace>で承認待ちです」, where `<workspace>` is the basename of `cwd` from the hook input (e.g. 「claude-pluginsで承認待ちです」). Falls back to 「承認待ちです。」 if `cwd` is missing. (Other Notification subtypes including `idle_prompt` are intentionally not subscribed.)
- **Reminder hooks** (do not speak, only inject context):
  - **`PostToolUse:TodoWrite`** — task transition: nudge to narrate completion → next task
  - **`PreToolUse:Monitor`** — about to watch a long-running background task: nudge to narrate what/why
  - **`PreToolUse:Agent`** — about to dispatch a sub-agent: nudge to narrate the delegated work + plan
  - **`UserPromptSubmit`** — new turn boundary: nudge to narrate at milestones if this becomes multi-step
  All four dispatch through `scripts/remind-say.sh <trigger>` and return `hookSpecificOutput.additionalContext` (or, for UserPromptSubmit, stdout) reminding Claude to call `say.sh` via Bash synchronously (no `run_in_background`). The model still owns wording and 枕詞. No-op when the session has no voice or has been silenced. High-frequency tools (Write/Edit/Bash) are deliberately not matched to avoid context spam.

On the first session ever, the SessionStart hook downloads the local TTS engine binary into `~/.claude/session-tts/engine/` and installs the three voice models. From then on it just probes the engine's health endpoint (sub-100 ms) and exits.

### Architecture

The plugin is structured around a single **core**, `scripts/say-response.py`, that takes plain UTF-8 text on stdin and a per-session voice via `SESSION_TTS_SPEAKER_ID` env. It:

- **Preempts** any in-progress playback from the same session — every entry point (Stop hook, Notification hook, mid-turn say.sh) shares one per-session pidfile, and a new utterance SIGTERMs the recorded process group before claiming the file. The latest report always wins, so users never wait through stale audio to hear what's current. Concurrent sessions still have independent pidfiles and never silence each other.
- Strips Markdown (code blocks, tables, URLs, parentheses, etc.)
- Normalizes inline `.` (e.g. `say.sh`, `src/foo.tsx`, `0.7.3`, `127.0.0.1`) to a space so the engine doesn't treat the period as a sentence boundary and insert a long pause inside a filename, path, or version number. Sentence-ending `.` (followed by whitespace or end of text) is left alone.
- Splits text on **paragraph boundaries first**, then sentence/clause boundaries inside each paragraph. The first chunk is intentionally small (≤ 60 chars) so the first audible word arrives quickly even on long responses; later chunks are larger (≤ 250 chars) for natural cadence. Markdown headings (`## title`) are *not* emitted as their own paragraph — the heading text is folded into the next paragraph with a `。` separator, so a single-word heading does not become a 2-character chunk bracketed by audible silence (`prePhonemeLength` pad + `afplay` device-open overhead per chunk).
- Synthesizes chunks via the local engine's HTTP API over a keep-alive `httpx.Client` and pushes each WAV onto a playback queue so audio starts as soon as the first chunk is ready (synthesis and playback run in parallel)
- A player thread drains the queue, plays each WAV with macOS `afplay` in order, and deletes the temp files

Around the core are thin **adapters**, one per input source. Each adapter is responsible for whatever its own input contract dictates (hook payload schemas, notification fields, skill arguments) and ends with a plain-text call into the core via `scripts/lib/voice-context.sh`:

| Adapter | Input source | Text / Output |
|---------|--------------|------|
| `scripts/dispatch.sh` | Stop / StopFailure hook payload (stdin JSON) | `last_assistant_message` (spoken) |
| `scripts/notify-permission.sh` | Notification:permission_prompt payload | `<workspace>で承認待ちです。` (spoken) |
| `skills/say/say.sh` | Bash tool argv (called by Claude synchronously for mid-turn narration) | the argument verbatim (spoken) |
| `scripts/remind-say.sh <trigger>` | hook stdin (one of: TodoWrite, Monitor, Agent, UserPromptSubmit) | JSON `additionalContext` reminder (todo/monitor/agent) or plain stdout (prompt). Not spoken. |

The shared helper `scripts/lib/voice-context.sh` resolves the per-session speaker (or returns failure if the session has no voice or has been silenced) and forwards text to the core. Hook payload schemas never leak into the core.

The Python runtime is isolated under `python/` and managed by `uv`; adapters call `uv run --directory ${CLAUDE_PLUGIN_ROOT}/python`.

### Mid-turn narration

In addition to the hook-triggered narration of full responses, Claude is instructed to deliver **verbal task-progress reports during autonomous, multi-step work** so the user can follow progress by ear without reading every message.

The model invokes `skills/say/say.sh` through the **Bash tool, synchronously** — `run_in_background` is intentionally not passed:

```
Bash(
  command: bash "${CLAUDE_PLUGIN_ROOT}/skills/say/say.sh" "<lead-in + body, ≤100 Japanese chars>",
  description: "TTS report"
)
```

The call blocks for the duration of synthesis + playback. The 100-character cap and milestone-only discipline keep that block short enough not to disrupt the turn.

`skills/say/say.sh` is the same implementation used by the Stop / Notification hook adapters; it goes through `voice-context.sh::resolve_speaker` → `speak_text` and is automatically a no-op if the session has been silenced via `/session-tts:tts off`.

Suggested calling moments:

- **Task transitions** — finishing one task and moving on to the next
- **Problems** — an unexpected obstacle, error, or blocker
- **Important findings** — investigation surfaces a notable result
- **Direction changes** — revising the plan or pivoting the approach

Constraints: under ~100 Japanese characters per call, one phrase per invocation, reported at milestones rather than at each tool call, and always opened with a brief lead-in phrase (枕詞) like 「報告です。」「問題発生です。」「発見です。」「方針転換です。」 so the listener can orient before the body. Not used for the final turn message (Stop already handles that).

The plugin nudges Claude toward making this call via two mechanisms:

1. A `SessionStart` instruction injected through the hook's stdout (declares the calling moments, lead-in rule, and the exact synchronous Bash call shape).
2. Four reminder hooks, all dispatched through `scripts/remind-say.sh <trigger>`, that re-surface the narration rule at point-in-time milestones — `PostToolUse:TodoWrite` (task transition), `PreToolUse:Monitor` (long watch starting), `PreToolUse:Agent` (sub-agent dispatch), `UserPromptSubmit` (new turn boundary). Each injects a short reminder via `hookSpecificOutput.additionalContext` (or stdout for UserPromptSubmit) and does not produce audio — the model owns wording and 枕詞 because hook payloads are typically English/terse and the engine is Japanese. Each reminder ends with `Skip if you just narrated in the immediately preceding step.` so the model self-throttles when several triggers fire close together.

Actual frequency is still up to model judgment. `say.sh` itself is a no-op if TTS has been silenced via `/session-tts:tts off`, so accidental calls during silenced sessions don't produce audio.

### Toggle voice playback: `/session-tts:tts`

Voice is ON by default in every new session. Use the `/session-tts:tts` skill to override:

```
/session-tts:tts off     # silence THIS session
/session-tts:tts on      # re-enable
/session-tts:tts toggle  # flip
/session-tts:tts status  # show current state (default)
```

The skill toggles `~/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID` and is independent of the voice assignment, so silencing then re-enabling preserves the same voice. Switching to `off` additionally kills any utterance still playing for this session (via the per-session playback pidfile), so the silence takes effect immediately rather than draining the remaining chunk queue. Other concurrent sessions are unaffected. The same flag is honored by `say.sh` (used by both the mid-turn narration call described above and the Stop / Notification hook adapters), so silenced sessions stay silent across every entry point.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install session-tts@lacolaco-plugins
```

After installing, every new session speaks by default with a rotating voice. Use `/session-tts:tts off` to silence a particular session.

### Prerequisites

- macOS on Apple Silicon (M1+)
- [`uv`](https://docs.astral.sh/uv/) on `PATH`
- `jq` on `PATH`
- Internet access on the **first** SessionStart only — to fetch the engine binary (~200 MB) and the three voice models (~50 MB total). Subsequent sessions run fully offline.

### Voices and licensing

The bundled voices are licensed under [ACML 1.0](https://aivm-specs.aivis-project.com/license/acml/) and downloaded from [AivisHub](https://hub.aivis-project.com/) on first use. ACML 1.0 permits personal use with credit; check the per-voice terms on AivisHub before any other use (commercial use, redistribution, derivative works, etc).

## License

MIT
