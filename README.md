# claude-plugins

Claude Code plugins by lacolaco.

## Plugins

| Plugin | Description |
|--------|-------------|
| [protect-main-branch](./protect-main-branch) | Prevent direct edits and pushes to the main branch (configurable) |
| [session-handover](./session-handover) | Session handover/takeover for task continuity between sessions |
| [retrospective](./retrospective) | Structured 6-stage retrospective for tasks, PRs, and incidents |
| [session-tts](./session-tts) | Read Claude Code responses aloud locally with a different Japanese voice per session. ON by default; engine and voices are managed automatically (Apple Silicon) |

## protect-main-branch

Blocks Write, Edit, and `git push` operations when on the protected branch (defaults to `main`) in Claude Code.

### How it works

- On any branch other than the protected branch: no-op (all operations allowed)
- On the protected branch:
  - **Write/Edit**: Blocks editing tracked (non-gitignored) files within the repository
  - **Bash**: Blocks `git push` commands
  - Editing gitignored files is always allowed
  - Editing files outside the repository is always allowed

When blocked, the hook returns:

```
Cannot edit/push on <branch> branch. Create a feature branch first.
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

The plugin subscribes to four hook events:

- **`SessionStart`** — assigns this session a voice from the 3-slot rotation (the assignment is stored at `~/.claude/session-tts/sessions/$session_id` and stays stable across `clear`/`compact` re-fires). It also kicks off a background engine bootstrap that is idempotent: typical re-runs do nothing.
- **`Stop`** — fires when Claude finishes a normal response; speaks `last_assistant_message`
- **`StopFailure`** — fires when the turn ends due to an API error; speaks `last_assistant_message`
- **`Notification`** with the `permission_prompt` matcher only — a tool needs approval → speaks 「承認待ちです。」 (Other Notification subtypes including `idle_prompt` are intentionally not subscribed.)

On the first session ever, the SessionStart hook downloads the local TTS engine binary into `~/.claude/session-tts/engine/` and installs the three voice models. From then on it just probes the engine's health endpoint (sub-100 ms) and exits.

The dispatcher:

1. Reads the hook input JSON from stdin and extracts `session_id`
2. Skips silently if the session has no voice assigned, or if `~/.claude/session-tts/silenced/<session_id>` exists (the user turned voice off for this session)
3. Optionally overrides `last_assistant_message` with a fixed phrase (used by Notification matchers)
4. Forwards the JSON to `scripts/say-response.py` along with the per-session speaker id, which:
   - Terminates any in-progress playback from a previous hook so a fresh response replaces (not overlaps with) the older one (single-flight via process-group `killpg`)
   - Strips Markdown (code blocks, tables, URLs, parentheses, etc.)
   - Splits the text on **paragraph boundaries first**, then sentence/clause boundaries inside each paragraph. The first chunk is intentionally small (≤ 40 chars) so the first audible word arrives quickly even on long responses; later chunks are larger (≤ 100 chars) for natural cadence.
   - Synthesizes chunks via the local engine's HTTP API over a keep-alive `httpx.Client` and pushes each WAV onto a playback queue so audio starts as soon as the first chunk is ready (synthesis and playback run in parallel)
   - A player thread drains the queue, plays each WAV with macOS `afplay` in order, and deletes the temp files

The Python runtime is isolated under `python/` and managed by `uv`; the hook calls `uv run --directory ${CLAUDE_PLUGIN_ROOT}/python`.

### Toggle voice playback

Voice is ON by default in every new session. Use the `/session-tts:tts` skill to override:

```
/session-tts:tts off     # silence THIS session
/session-tts:tts on      # re-enable
/session-tts:tts toggle  # flip
/session-tts:tts status  # show current state (default)
```

The skill toggles `~/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID` and is independent of the voice assignment, so silencing then re-enabling preserves the same voice. Other concurrent sessions are unaffected.

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
