# claude-plugins

Claude Code plugins by lacolaco.

## Plugins

| Plugin | Description |
|--------|-------------|
| [protect-main-branch](./protect-main-branch) | Prevent direct edits and pushes to the main branch (configurable) |
| [session-handover](./session-handover) | Session handover/takeover for task continuity between sessions |
| [retrospective](./retrospective) | Structured 6-stage retrospective for tasks, PRs, and incidents |
| [kokoro-tts](./kokoro-tts) | Read Claude Code responses aloud locally using Kokoro TTS via mlx-audio (Apple Silicon, Japanese voice) |

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

## kokoro-tts

Reads Claude Code's responses aloud on your machine using [Kokoro TTS](https://huggingface.co/hexgrad/Kokoro-82M) via [mlx-audio](https://github.com/ml-explore/mlx-audio). Inference runs locally; no external API calls during playback. Playback is scoped to the session that opted in, so concurrent Claude Code sessions do not speak over each other.

### How it works

The plugin registers three hook events:

- **`Stop`** — fires when Claude finishes a normal response
- **`StopFailure`** — fires when the turn ends due to an API error
- **`Notification`** — fires for notifications such as approval prompts (reads the `message` field)

Each hook calls `scripts/dispatch.sh`, which:

1. Reads the hook input JSON from stdin and extracts `session_id`
2. Skips silently unless `~/.claude/kokoro-tts/sessions/<session_id>` exists (per-session flag)
3. Forwards the JSON to `scripts/say-response.py`, which:
   - Strips Markdown (code blocks, tables, URLs, parentheses, etc.)
   - Replaces common technical terms with katakana via a built-in dictionary; falls back to `alkana` for the rest
   - Synthesizes audio with Kokoro (`jf_alpha`, the highest-rated Japanese voice)
   - Plays the WAV with macOS `afplay` and deletes the temp file

The Python runtime is isolated under `python/` and managed by `uv`; the hook calls `uv run --directory ${CLAUDE_PLUGIN_ROOT}/python`.

### Toggle voice playback

Use the `/kokoro-tts:voice` skill from any Claude Code session:

```
/kokoro-tts:voice on      # enable for THIS session
/kokoro-tts:voice off     # disable for THIS session
/kokoro-tts:voice toggle  # flip
/kokoro-tts:voice status  # show current state (default)
```

The skill writes to `~/.claude/kokoro-tts/sessions/$CLAUDE_CODE_SESSION_ID`, so each session is independent. Other concurrent sessions are unaffected.

### Customize the voice

Edit constants at the top of `kokoro-tts/scripts/say-response.py`:

| Constant | Default | Notes |
|---|---|---|
| `MODEL_ID` | `mlx-community/Kokoro-82M-bf16` | HuggingFace model id |
| `VOICE` | `jf_alpha` | Japanese voice (also available: `jf_gongitsune`, `jf_tebukuro`, `jf_nezumi`, `jm_kumo`) |
| `SPEED` | `1.2` | Playback speed |
| `MAX_TEXT_LENGTH` | `600` | Truncate long responses |

Add domain terms to the `CUSTOM` dictionary for better katakana pronunciation.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install kokoro-tts@lacolaco-plugins
```

After installing, run `/kokoro-tts:voice on` in any session you want to hear aloud.

### Prerequisites

- macOS on Apple Silicon (M1+)
- [`uv`](https://docs.astral.sh/uv/) on `PATH` (the plugin uses `uv run --directory`)
- `jq` on `PATH` (used by the dispatcher to read `session_id` from hook input)
- First run downloads the Kokoro model (~355 MB) from HuggingFace

## License

MIT
