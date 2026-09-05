# claude-plugins

Claude Code plugins by lacolaco.

## Plugins

| Plugin | Description |
|--------|-------------|
| [protect-main-branch](./protect-main-branch) | Prevent git operations that would modify the main branch (configurable) |
| [session-handover](./session-handover) | Job-succession handover/takeover: each document is a job seat identified by (project, role); the successor renames it to their own name, audits the inherited handoff report, reads every referenced artifact via mandatory read tasks, and continues under fresh accountability |
| [retrospective](./retrospective) | GIGO-grounded retrospective — trace problems to their upstream origin, fix at the stage where the cause lives |
| [session-tts](./session-tts) | Read Claude Code responses aloud locally with a different Japanese voice per session. Instructs Claude to deliver mid-turn progress narration via a synchronous Bash call into the say adapter. Permission prompts include the workspace name. ON by default; controllable via `SESSION_TTS_ENABLED` env var; playback volume is adjustable via `/session-tts:volume`. Engine and voices are managed automatically (Apple Silicon) |
| [tech-writing](./tech-writing) | Japanese technical writing norms for books, articles, and documentation |
| [memory-sanitize](./memory-sanitize) | Reproducible Japanese prose quality checker using textlint-ja + custom rules. Detection only, no auto-fix. Requires Node.js |

## protect-main-branch

Blocks git subcommands that would modify the protected branch (defaults to `main`) when checked out in Claude Code.

### How it works

- On any branch other than the protected branch: no-op (all operations allowed)
- On the protected branch: Bash commands invoking the following git subcommands are denied — `commit`, `push`, `merge`, `rebase`, `reset`, `cherry-pick`, `revert`, `am`. All other operations (Write, Edit, `git pull`, `git status`, `git switch`, etc.) pass through unchanged.
- Individual subcommands can be exempted from the block via `PROTECT_MAIN_BRANCH_ALLOWED_SUBCOMMANDS` (see Configuration).
- The whole hook can be turned off for the current scope via `PROTECT_MAIN_BRANCH_DISABLE=1` (see Configuration). Useful for solo-author repos with linear-history-on-main policies where the protection is the wrong default.

`git pull` is intentionally allowed so the protected branch can be synced with its upstream. To introduce changes to the protected branch, do the work on a feature branch and merge it via a PR.

When blocked, the hook returns:

```
Cannot run `git <subcommand>` on <branch> branch. Create a feature branch first.
```

### Configuration

Three environment variables can be set in your Claude Code `settings.json` (at user scope `~/.claude/settings.json`, project scope `.claude/settings.json`, or local `.claude/settings.local.json`). Settings are loaded at session start, so a new session must be opened for changes to take effect.

#### `PROTECT_MAIN_BRANCH_DISABLE` — turn the hook off entirely

When set to `"1"`, the hook exits 0 unconditionally and allows every git operation on every branch, including the protected one. The other two variables are not consulted. Defaults to unset (hook active).

```json
{
  "env": {
    "PROTECT_MAIN_BRANCH_DISABLE": "1"
  }
}
```

Place this in `.claude/settings.local.json` of a specific repository to opt that repository out of protection while keeping the hook active everywhere else. Any value other than `"1"` (including `"0"`, `"true"`, empty string) keeps the hook active — the check is strictly `= "1"` so the kill switch can only be tripped intentionally.

#### `PROTECT_MAIN_BRANCH_NAME` — protected branch names

Space-separated list of branch names to protect. Defaults to `main`.

```json
{
  "env": {
    "PROTECT_MAIN_BRANCH_NAME": "main master develop"
  }
}
```

#### `PROTECT_MAIN_BRANCH_ALLOWED_SUBCOMMANDS` — per-user allowlist

Space-separated list of git subcommands that should be exempted from the block even when run on a protected branch. Subcommands not in the default blocklist (e.g. `pull`, `fetch`) are unaffected by this setting since they are never blocked.

```json
{
  "env": {
    "PROTECT_MAIN_BRANCH_ALLOWED_SUBCOMMANDS": "merge revert"
  }
}
```

The allowlist accepts any subcommand, including `commit` and `push` — the plugin trusts your configuration. Use this when your workflow legitimately requires running a normally-blocked subcommand on the protected branch (for example, merging a feature branch back into `main` locally).

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install protect-main-branch@lacolaco-plugins
```

### Prerequisites

- `jq` must be installed

## session-handover

Carries work across Claude Code sessions as **job succession**, not as a reincarnated identity. The document is a handoff report and an accountability ledger; the successor audits the predecessor's claims before relying on them, and continues under their own name.

- **`/handover`** — write or update your handover document so the next holder of this seat can take it over
- **`/takeover`** — take over a job seat: rename the document to your own name, audit the prior holder's report, read every referenced artifact before doing any work, and continue under fresh accountability

### Conceptual frame: succession, not reincarnation

This plugin previously (v3.x) modeled handover as **reincarnation**: a successor adopted the predecessor's identity and "inherited their mind". In practice that frame collapsed the self/other boundary that critical verification depends on — successors treated the predecessor's Knowledge as their own past judgments and stopped questioning them.

v4 reframes the relationship as **job succession with accountability transfer**:

- The successor is **not** the predecessor. They take the seat under their own name.
- The Knowledge block is the prior holder's handoff report — useful, but to be **audited**, not inherited. Until the successor has verified a claim, anything they build on it is on their own account.
- If a predecessor's failure surfaces during the successor's tenure — even one that predates them — it is now the successor's to address. The ledger records who made the original call; the recovery work belongs to the current holder. This is standard business succession discipline.
- **The successor's starting posture is that the predecessor underperformed.** A successor is needed only because the predecessor could not bring the work to a finished state within their tenure — that is a structural fact, not a personal judgment. The audit is not a courtesy; it is the successor's job to find what the predecessor missed, got wrong, or could not solve. A clean-looking handoff is a signal to look harder, not to relax.
- **The successor must work differently from the predecessor and recover the seat's credibility.** Repeating the predecessor's approach produces the predecessor's outcome — the successor will hit the same walls and be relieved the same way. The seat has lost trust because the predecessor could not deliver; restoring that trust is part of the successor's job, not a side concern. The successor identifies what about the predecessor's *method* failed (premature certainty, skipped verification, narrow framing, anchoring on a wrong model) and adopts explicit safeguards against repeating it.

### Job seats and storage

Each handover document represents one **job seat** — identified by `project` and `role` in its YAML frontmatter — and lives at `<base>/<holder>.md` where `<holder>` is the current holder's lowercase English first name. Multiple seats coexist in `<base>/` when several agents work in parallel; each seat is one file owned by its current holder.

- A new subject minting a seat picks an English first name not already taken in `<base>/`, and writes the seat's (`project`, `role`, `description`) frontmatter for the first time.
- A successor taking over an existing seat picks their **own** name (also not already taken) and **renames the predecessor's file** (`<predecessor>.md` → `<successor>.md`). The frontmatter — the seat's identity — is preserved byte-for-byte across the rename.

`<base>` is resolved **deterministically** the moment either skill fires by the `handover-dir` command (shipped in the plugin's `bin/`, which Claude Code adds to the Bash tool's `PATH` while the plugin is enabled):

1. Walk up from `$PWD`. At each ancestor:
   1. If `.handover/` exists, return its absolute path.
   2. Else if a legacy v2.x `.claude/handover/` exists, lift it to `.handover/` at the same level (atomic rename), drop the now-empty `.claude/` if no siblings remain, then return the new path.
2. If no ancestor has either, fall back to `$HOME/.handover` (created if missing).

The agent never constructs `<base>` from `cwd` itself — it runs `handover-dir` and uses its stdout verbatim. This guarantees that a session started from a subdirectory of a workspace lands in the workspace's `.handover/`, not in the subdirectory. The resolution runs only when `/handover` or `/takeover` is invoked — sessions that never use either skill incur no overhead.

These documents are **local-only working artifacts** — add `.handover/` to your `.gitignore` (or your global gitignore) so they are not committed.

### Document schema

YAML frontmatter (three stable fields) followed by two body blocks. The filename names the current holder; the frontmatter names the seat.

- **Frontmatter** (preserved byte-for-byte across handovers and takeovers, unless the role itself shifts):
  - `project` — kebab-case slug naming the project this seat belongs to (e.g. `portfolio-manager`).
  - `role` — kebab-case slug naming the role this seat fills (e.g. `release-manager`, `kb-curator`). Names the **seat**, not the current task.
  - `description` — one-line job description, ≤ ~80 chars (e.g. `Drive the release cycle — version bumps, changelogs, deploy, post-release verification`). Treat it like a role description in a hiring document.
- **`## Knowledge`** (the holder's handoff report, present-tense) — `Goals & Non-Goals`, `Current State`, `Mental Model`, `Facts` (with evidence), `Hypotheses` (with confidence), `References`. **Rewritten by the holder at each `/handover`** so it stays lean and current.
- **`## History`** (the seat's accountability ledger, append-only) — `YYYY-MM-DDThh:mm [type] ...` entries, newest at the bottom. Types: `attempt`, `finding`, `decision`, `failure` (with `lesson:`), `pivot`, `takeover` (written automatically by `/takeover` when the file is renamed), `handover` (closes a tenure).

Artifacts (commits, PRs, issues, code) are **referenced, never duplicated**; only information that exists nowhere else (hypotheses, failures, rationale, mental model) is written inline. Secrets are redacted.

### How it works

**`/handover`** — if you already hold a seat this session (from a takeover, or from minting one earlier), you update your `<your-name>.md`; otherwise you mint a new seat by picking a fresh holder name and writing the full (`project`, `role`, `description`) frontmatter for the first time. The skill rewrites the `## Knowledge` block, appends what happened to `## History`, and closes your tenure with a `[handover]` entry.

**`/takeover <holder>`** takes over the seat currently held by `<holder>` directly; **`/takeover`** with no argument lists the documents in `<base>/` and lets you choose one (labelled by `<holder> — <project>/<role>` with the frontmatter `description` and last-modified time, body not read until selection). On selection:

1. The successor mints their **own** name (not the predecessor's), picking a first name not already taken.
2. The file is renamed `<predecessor>.md` → `<successor>.md`.
3. A `[takeover]` entry is appended to `## History` noting the predecessor and whether the seat was closed properly (`[handover]` last) or forcibly taken.
4. The successor reads the full handoff package and treats every Knowledge claim as a hypothesis until they verify it against reality. Divergences are recorded as `finding` entries in `## History`; the `## Knowledge` block is reconciled at the successor's next `/handover`, when their audited understanding replaces the predecessor's report under their own name.
5. Every `References` entry and every `[ref: ...]` in `## History` becomes a **mandatory read task** — one task per unique artifact, bundles decomposed mechanically, no relevance judgment allowed. The successor drains all read tasks before any work starts, recording a short digest per artifact; unreachable artifacts are recorded as `finding` entries, never silently skipped. (The takeover skill's Steps 6–7 are the canonical definition.)

**Forced takeover**: if the predecessor did not close their tenure with `[handover]` (their session ended without `/handover`, or they vacated abruptly), takeover is still allowed. The `[takeover]` entry records the irregular transition.

Outstanding work is externalized to the task tool so it survives context compression, and task status is kept current (`in_progress` on start, `completed` only when done) so the task list is always a truthful progress report.

### Upgrading from v3.x

v3.x documents used a `description`-only frontmatter and modeled takeover as identity inheritance (the successor adopted the predecessor's name; no rename). v4 changes both: frontmatter gains `project` and `role`, and the file is renamed to the successor's own name at takeover.

On first `/takeover` of a v3.x document, the skill detects the missing `project` and/or `role` fields, proposes values (`project` inferred from the git repo root basename when applicable; `role` inferred as a kebab-case slug from the existing `description`), and asks the user to confirm before writing the migrated frontmatter. The body (`## Knowledge`, `## History`) is not touched. The migration runs at most once per seat.

### Upgrading from v2.x

v2.x stored documents at `.claude/handover/<name>.md`. v3 and v4 use `.handover/<name>.md`. **The migration runs automatically on first invocation of `/handover` or `/takeover` after upgrade** — `handover-dir` lifts the legacy directory in place. No manual `mv` is required.

To pin handovers to a particular workspace root, create `.handover/` there once (`mkdir <root>/.handover`); from then on every session under that root resolves to it.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install session-handover@lacolaco-plugins
```

## retrospective

Provides the `/retrospective` skill: traces problems from Output back to their upstream origin across six stages, then fixes at the stage where the cause lives — grounded in the garbage-in-garbage-out principle.

### How it works

The skill walks through four phases:

1. **Session facts** — brief chronological record; inventory every rule and knowledge source in context
2. **Bottom-up tracing** — walk from Output back to Input, surface problems and opportunities at each stage, trace each to its originating stage via root cause test
3. **Remediation design** — **design** (not implement) fixes at the stage where the cause lives:
   - **Input** causes (missing/stale knowledge) → knowledge operations (ingest, revise, reorganize), project docs, tool config
   - **Interpretation** causes (rules misread) → fix/move/delete rules
   - **Planning** causes → codify as skill or agent
   - **Action** causes → automate or add guardrails
   - **Inspection** causes → strengthen verification
   - **Output** causes → fix reporting or persistence
4. **Implementation** — executes only after critic audit and disposition. No fix is implemented before critics run.

The retrospective does not write to memory — memory is managed by other workflows. Global-layer changes are prepared as actionable prompts for a global-layer-managing agent.

At Submission (between Phase 4 and 5), three critic agents run in parallel from independent contexts:

| Agent | Perspective |
|-------|-------------|
| `critic-coverage` | Exhaustiveness — source enumeration, stage coverage, missed problems |
| `critic-classification` | Correctness — stage attribution, library drift |
| `critic-remediation` | Remediation soundness — stage alignment, implementation verification, style |

Every critic finding requires an explicit disposition: **actioned** (with evidence) or **contested** (with a specific counter-argument). Silent dismissal of findings is structurally blocked.

All workspace-local outcomes are written directly. The skill does not modify the global `~/.claude/` layer but prepares global changes as agent-executable prompts.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install retrospective@lacolaco-plugins
```

## session-tts

Reads Claude Code's responses aloud on your local machine. Each Claude Code session is automatically assigned one of three different Japanese voices in a fixed rotation, so when several sessions are running you can tell them apart by voice. Synthesis happens locally; no external API is called during playback.

### How it works

The plugin subscribes to six hook events:

- **`SessionStart`** — assigns this session a voice from the 3-slot rotation (the assignment is stored at `~/.claude/session-tts/sessions/$session_id/speaker` and stays stable across `clear`/`compact` re-fires). When `SESSION_TTS_ENABLED=0`, the voice is still assigned but the session starts silenced (no context injection, no engine bootstrap, no announcement). It also kicks off a background engine bootstrap that is idempotent: typical re-runs do nothing.
- **`SessionEnd`** — fires when this session terminates (`/clear`, `/compact`, logout, etc.). SIGTERMs any in-flight playback for this session via the per-session pidfile (`sessions/$session_id/playback`) so audio doesn't outlive the session that started it. The session directory and its contents are intentionally left in place so the same session_id keeps its voice across `/clear`.
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
- Trims token-leading `!` (e.g. GitLab `MR !107`, `!42`) before synthesis. The `!` there is a reference sigil, not an exclamation, and the engine would otherwise pause between it and the number. Mid- or end-of-word `!` (`Done!`, `Wow! Great`) keeps its exclamation prosody.
- Collapses runs of decorative dashes from `―—–─━` (2+ in a row, e.g. ` Insight ―――`, `━━━ section ━━━`) to a single space so the engine doesn't read the separators aloud or pause on them. A lone `—` / `–` is left alone so it can still function as prose punctuation.
- Splits text on **paragraph boundaries first**, then sentence boundaries (`。．！？!?` and ASCII `.`) inside each paragraph. Commas (`、，,`) are deliberately **not** split points — every chunk adds `prePhonemeLength` lead-in silence plus an `afplay` device-open transient, so splitting at commas would turn the engine's natural micro-pause into a much longer unnatural gap. The first chunk is intentionally small (≤ 60 chars) so the first audible word arrives quickly even on long responses; later chunks are larger (≤ 250 chars) for natural cadence. Markdown headings (`## title`) are *not* emitted as their own paragraph — the heading text is folded into the next paragraph with a `。` separator, so a single-word heading does not become a 2-character chunk bracketed by audible silence.
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

The skill toggles `~/.claude/session-tts/sessions/$CLAUDE_CODE_SESSION_ID/silenced` and is independent of the voice assignment, so silencing then re-enabling preserves the same voice. Switching to `off` additionally kills any utterance still playing for this session (via the per-session playback pidfile), so the silence takes effect immediately rather than draining the remaining chunk queue. Other concurrent sessions are unaffected. The same flag is honored by `say.sh` (used by both the mid-turn narration call described above and the Stop / Notification hook adapters), so silenced sessions stay silent across every entry point.

When `tts on` is called on a session that was silenced at start (via `SESSION_TTS_ENABLED=0`), the skill performs **late activation**: removes the silenced flag, ensures the engine is running, outputs the narration context, and announces "TTSを開始します。" — enabling full TTS mid-session without requiring a restart.

### Adjust playback volume: `/session-tts:volume`

Every chunk is played through `afplay --volume <coefficient>`. The default coefficient is `0.8`, which keeps TTS quieter than other audio (notifications, music) when system volume is up — macOS has no native way to make `afplay` follow the system "alert volume", so this is the simplest substitute. Use the `/session-tts:volume` skill to override:

```
/session-tts:volume 0.5      # set the coefficient to 0.5
/session-tts:volume status   # show the current value (default)
/session-tts:volume reset    # restore the built-in default (0.8)
```

The chosen value is persisted to `~/.claude/session-tts/volume` and read by `say-response.py` for every chunk it plays. The setting is **per-user**, not per-session — adjusting it affects every active and future session, including ones already running (the next chunk picks up the new value). Values outside `[0.0, 1.0]` are rejected and the previous setting (or the built-in default) stays in effect.

### Configuration

All configuration is done via environment variables in Claude Code's `settings.json` (`env` field). Project-level settings override global, so you can set a global default and selectively override per-project. Settings take effect at session start.

```jsonc
// ~/.claude/settings.json (global default)
{
  "env": {
    "SESSION_TTS_ENABLED": "1",
    "SESSION_TTS_VOLUME": "0.8"
  }
}

// <project>/.claude/settings.json (per-project override)
{
  "env": {
    "SESSION_TTS_ENABLED": "0"
  }
}
```

#### Environment variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `SESSION_TTS_ENABLED` | `1`/`true`/`yes` or `0`/`false`/`no` | `1` | Controls whether TTS activates on session start. When disabled, the voice is still assigned but the session starts silenced. `/session-tts:tts on` performs late activation. |
| `SESSION_TTS_VOLUME` | Decimal in `[0.0, 1.0]` | `0.8` | Default `afplay --volume` coefficient. Used when the volume file does not exist. `/session-tts:volume` writes to the file and takes priority. |
| `SESSION_TTS_ENGINE_URL` | URL | `http://127.0.0.1:10101` | TTS engine HTTP endpoint. For advanced use only (custom engine port or remote engine). |

#### Priority chain

Each configurable aspect has a clear override hierarchy (highest priority first):

- **Activation**: runtime `/session-tts:tts off|on` > `SESSION_TTS_ENABLED` env var > default ON
- **Volume**: volume file (`/session-tts:volume`) > `SESSION_TTS_VOLUME` env var > hardcoded `0.8`
- **Engine URL**: `SESSION_TTS_ENGINE_URL` env var > hardcoded `http://127.0.0.1:10101`

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install session-tts@lacolaco-plugins
```

After installing, every new session speaks by default with a rotating voice. Use `/session-tts:tts off` to silence a particular session, or set `SESSION_TTS_ENABLED=0` to start silenced by default.

### Prerequisites

- macOS on Apple Silicon (M1+)
- [`uv`](https://docs.astral.sh/uv/) on `PATH`
- `jq` on `PATH`
- Internet access on the **first** SessionStart only — to fetch the engine binary (~200 MB) and the three voice models (~50 MB total). Subsequent sessions run fully offline.

### Voices and licensing

The bundled voices are licensed under [ACML 1.0](https://aivm-specs.aivis-project.com/license/acml/) and downloaded from [AivisHub](https://hub.aivis-project.com/) on first use. ACML 1.0 permits personal use with credit; check the per-voice terms on AivisHub before any other use (commercial use, redistribution, derivative works, etc).

## tech-writing

Japanese technical writing norms for books, articles, and documentation. Provides the `/tech-writing` skill containing normative rules for formatting, paragraph structure, argumentative rigor, reader cognitive load management, perspective and narration, restraint in rhetoric, LLM-style filler prohibition, and redundancy elimination.

The rules are ported from [a gist by k16shikano](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d) and are kept faithful to it. The one rule this copy does not carry is 「一文ごとに改行する」, removed in 2.1.2, the first release after 1.0.0, because it split paragraphs into one-line fragments wherever a single newline renders as a line break. One other divergence predates that: the last bullet of 読み手の負荷の管理 completes a sentence the gist leaves truncated.

### Known limitations

- Proofreading a manuscript that is already stored one sentence per line usually reflows it into paragraphs, which is the point of the change, but not every run does: over one such document, two of three runs reflowed it and one left the layout alone. Say which layout you want if the run has to be repeatable.
- The skill's Japanese description lists `引用ブロック` and `コラム記法` under 整形, but the section's nine rules cover neither blockquotes nor a column notation; the only `コラム` rule says what a column heading may contain. Both claims come from the source gist and are left in place rather than edited here. The English description in the manifests is this repo's own wording, so it lists only what the rules actually cover.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install tech-writing@lacolaco-plugins
```

## memory-sanitize

Reproducible Japanese prose quality checker for persistent layers (memory, CLAUDE.md, skill definitions, style guides). Combines textlint-ja rules with custom rules to enforce writing discipline. Detection only — no auto-fix.

### How it works

The `/memory-sanitize` skill runs a two-stage check: first a mechanical textlint pass via `check.sh` (standard textlint-ja rules + six custom rules: `no-english-word`, `no-paren-equals-gloss`, `no-em-dash-ja`, `no-heading-separator`, `no-space-after-ja-punctuation`, `no-confusable-cyrillic`. The last two live in `scripts/rules-gate/` because they can be driven to zero without editorial judgement, and CI enforces just those via `scripts/check-gate.sh`), then an agent-driven prose quality review referencing the `tech-writing` skill.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install memory-sanitize@lacolaco-plugins
```

### Prerequisites

- Node.js (packages fetched via `npx` on first run)

## License

MIT
