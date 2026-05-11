# session-tts — Design Notes

Implementation reference for contributors. Companion to the user-facing
overview in [`../README.md`](../README.md). This file documents *why* the
code is shaped the way it is — design decisions, data flow, file layout,
and the invariants that hold across hooks and skills.

## 1. Goals and constraints

- **Read every Claude turn aloud locally.** No external API at playback
  time; once the first session has bootstrapped, the plugin is fully
  offline.
- **One stable voice per session.** Multiple concurrent Claude Code
  sessions must be distinguishable by ear, and the assignment must
  survive `/clear` and `/compact` re-fires of `SessionStart`.
- **Concurrent sessions never silence each other.** Single-flight is
  scoped per session, not global — a Stop in session B must not cut
  off session A. Otherwise the per-session voice rotation is
  pointless: you would always hear only the most-recent session.
- **Low time-to-first-audio (TTFA).** A long response should start
  speaking within a second; the user should not wait for the whole
  reply to be synthesized before hearing anything.
- **Single-flight within a session.** A new utterance from a session
  cancels any still-playing utterance from the *same* session, so
  a fresh reply replaces a stale one.
- **ON by default, easy to silence.** A new session speaks
  automatically; silencing is a per-session opt-out.
- **Apple Silicon macOS only** (engine binary is `arm64`-specific; the
  player uses `afplay`).

## 2. Component map

```
session-tts/
├── .claude-plugin/plugin.json     # plugin metadata
├── hooks/hooks.json               # hook subscriptions (SessionStart / Stop / StopFailure / Notification / PreToolUse / PostToolUse / UserPromptSubmit)
├── scripts/
│   ├── session-on.sh              # SessionStart adapter (voice rotation + engine bootstrap)
│   ├── dispatch.sh                # Stop / StopFailure adapter
│   ├── notify-permission.sh       # Notification:permission_prompt adapter
│   ├── remind-say.sh              # Reminder adapter for PostToolUse:TodoWrite, PreToolUse:Monitor, PreToolUse:Agent, UserPromptSubmit (trigger passed as argv[1])
│   ├── say-response.py            # CORE: text → audio
│   └── lib/voice-context.sh       # shared resolve_speaker / speak_text helpers
├── python/
│   ├── pyproject.toml             # uv-managed runtime (httpx, py7zr)
│   └── setup_engine.py            # engine binary + voice model bootstrap
└── skills/
    ├── tts/SKILL.md               # /session-tts:tts on/off/toggle/status
    ├── tts/tts.sh                 # /session-tts:tts skill adapter (silence + kill current playback)
    └── say/say.sh                 # adapter for the say path; not a slash command.
                                   # Called by Claude with Bash + run_in_background=true for mid-turn narration.
```

The plugin is structured as a single **core** (`say-response.py`)
plus thin **adapters**, one per input source. Hook payload shapes and skill
argument conventions stay inside the adapters; the core only sees plain
UTF-8 text on stdin and a speaker id on `SESSION_TTS_SPEAKER_ID`.

## 3. Data flow

### 3.1 Per-utterance pipeline

```
adapter (hook stdin / skill arg)
  → resolve_speaker (lib/voice-context.sh)
  → speak_text (lib/voice-context.sh)
  → say-response.py (stdin = text, env = speaker)
      ├── wait_for_previous_playback (queue)
      ├── clean()              # strip markdown
      ├── split_into_chunks()  # paragraph → sentence/clause
      ├── synth_worker  ──┐
      │                    ├── play_queue (FIFO)
      └── player_worker ──┘    (afplay each WAV in order)
```

Synth and playback run on separate threads with a `queue.Queue` between
them. The synth thread enqueues a temp WAV path the moment each chunk
finishes; the player thread drains the queue, calls `afplay`, and unlinks
the temp file. This is what gives the plugin its low TTFA: playback
starts as soon as chunk 1 is synthesized, while chunks 2..N synthesize
in the background.

### 3.2 Adapter responsibilities

| Adapter                              | Input contract                                  | Output                                       |
| ------------------------------------ | ----------------------------------------------- | -------------------------------------------- |
| `scripts/dispatch.sh`                | Stop / StopFailure hook stdin (JSON)            | speaks `last_assistant_message`              |
| `scripts/notify-permission.sh`       | `Notification:permission_prompt` hook stdin     | speaks `${basename(cwd)}で承認待ちです。`    |
| `skills/say/say.sh`                  | Bash tool argv (model-driven, `run_in_background=true`) | speaks argv[1] verbatim              |
| `scripts/session-on.sh` (special)    | `SessionStart` hook stdin                       | speaks "TTSを開始します。" (1st run only) + injects guidance via stdout |
| `scripts/remind-say.sh todo`         | `PostToolUse:TodoWrite` hook stdin              | injects `hookSpecificOutput.additionalContext` reminder (does not speak) |
| `scripts/remind-say.sh monitor`      | `PreToolUse:Monitor` hook stdin                 | injects reminder before a long watch starts (does not speak)              |
| `scripts/remind-say.sh agent`        | `PreToolUse:Agent` hook stdin                   | injects reminder before sub-agent dispatch (does not speak)               |
| `scripts/remind-say.sh prompt`       | `UserPromptSubmit` hook stdin                   | writes stdout reminder (auto-appended to context); does not speak         |

Adapters are thin. They:

1. Parse their own input format (hook JSON / argv / env).
2. Either (a) compute the text to speak and call `speak_text`, or
   (b) emit `hookSpecificOutput.additionalContext` JSON to nudge the
   model. A given adapter does one or the other, not both.
3. For speech-producing adapters: resolve the per-session voice via
   `resolve_speaker` first.

If the text or voice is missing, the adapter exits silently. This keeps
hook noise out of Claude Code's UI on edge cases (no session id, never
went through `SessionStart`, silenced, etc.).

### 3.3 Why the reminder hooks do not speak

`remind-say.sh` (and the four hook events that dispatch it) is the
only family of adapters that *injects context* rather than producing
audio. The reason: hook payloads (todo content, tool args, user
prompts) are typically English or terse non-sentence text, and
AivisSpeech is a Japanese engine — feeding the engine raw payload
strings would either fail or sound nonsensical. Editorial framing
(枕詞, summary, lead-in phrase) belongs to the model, which can
compose a proper Japanese sentence. The hooks' only job is to be a
**deterministic forcing function** that the model cannot forget at
todo-state-change moments.

PostToolUse hooks have a different output contract from SessionStart:
plain stdout goes only to the debug log, so the hook must return JSON
of the form `{"hookSpecificOutput": {"hookEventName": "PostToolUse",
"additionalContext": "..."}}` for the text to actually reach the
model's context. The hook is also configured **synchronous** (no
`async: true`) because the injected reminder must be in the context
before the model generates its next text response.

## 4. Disk layout (`~/.claude/session-tts/`)

State is keyed by user, not by repo, so all sessions share the engine and
voice models.

```
~/.claude/session-tts/
├── engine/                       # extracted AivisSpeech-Engine (arm64)
│   └── run                       # ENGINE_BIN
├── engine.pid                    # last-launched engine PID (best-effort)
├── engine.log                    # engine stdout+stderr
├── setup.log                     # SessionStart background bootstrap log
├── index                         # voice rotation cursor (0..2)
├── sessions/
│   └── <session_id>              # contents = assigned speaker_id (style_id)
├── silenced/
│   └── <session_id>              # presence file → /session-tts:tts off
└── playback/
    └── <session_id>              # current playback's process group id, per session
```

Invariants:

- A session has a voice **iff** `sessions/<sid>` exists. The file is
  created exactly once per session, on the first `SessionStart`, and is
  read by every subsequent hook and skill adapter.
- A session is silenced **iff** `silenced/<sid>` exists. The two files
  are independent, so toggling silence does not change voice.
- `playback/<session_id>` reflects the most-recently-launched
  `say-response.py` process group **for that session**. Different
  sessions have separate pidfiles. All utterance types within a
  session share this one pidfile and queue uniformly. Stale entries
  are harmless because `wait_for_previous_playback` treats
  `ProcessLookupError` from `os.killpg(pgid, 0)` as "slot is free".

## 5. Voice assignment

Three voices are baked in (`setup_engine.py` / `VOICES`); each is
identified by an `aivm_model_uuid` (for installation) and a `style_id`
(for `/audio_query` and `/synthesis` calls). The plugin uses the latter
on the per-session speaker id.

Rotation algorithm (`session-on.sh`):

```
prev = read(index_file) or -1
next = (prev + 1) mod 3
sessions/<sid> = VOICES[next].style_id
index_file = next
```

Why a separate `index` cursor instead of, say, hashing the session id?
Predictability: if you open three sessions back-to-back, you get all
three different voices in order. With a hash you might collide.

The rotation happens **only on the first** `SessionStart`. If `clear`
or `compact` re-fires the hook later, `sessions/<sid>` already exists
and the script skips both the rotation step and the "TTSを開始します。"
announcement. That's why `newly_assigned` gates the announcement: we
do not want to repeat it after every re-fire.

## 6. Engine bootstrap

`python/setup_engine.py` is run on every `SessionStart` in the
background. It is split into three idempotent steps:

1. **`ensure_engine_binary`** — if `~/.claude/session-tts/engine/run` is
   missing, download the AivisSpeech-Engine `.7z.001` from GitHub
   Releases, extract via `py7zr`, and move `macOS-arm64/` into place.
2. **`ensure_engine_running`** — if `GET /version` does not respond,
   spawn the engine with `start_new_session=True` so it outlives the
   hook process. On macOS, prepend `taskpolicy -t 0 -l 0` to give the
   engine the highest throughput / latency tiers — without this, output
   waveforms drift slightly under CPU pressure because tensor-op
   scheduling becomes non-deterministic.
3. **`ensure_voices`** — `GET /aivm_models`, compute the missing UUIDs,
   and `POST /aivm_models/install` for each with the AivisHub download
   URL.

Typical re-runs hit only the first half of step 2 (a sub-100 ms
`/version` probe) and exit. The whole bootstrap is wrapped in a single
`try/except` and logs failures into `setup.log`; nothing is propagated
back to the foreground hook so a transient network blip does not break
session start.

## 7. Text processing (`say-response.py`)

### 7.1 Cleanup (`clean`)

The Stop hook hands us `last_assistant_message`, which is Markdown.
Reading Markdown verbatim sounds awful (asterisks, backticks, table
pipes, fenced code blocks), so we strip aggressively *before* chunking.

Stripped:

- Fenced code blocks and 4-space indented code (entirely)
- Table rows (any line containing `|`) and table separators (`---`,
  `:--`)
- Blockquotes and shell-prompt lines (`> `, `$ `)
- Headings (`#`) and inline emphasis (`**`, `*`, `` ` ``)
- Bare URLs (`https?://\S+`)
- Markdown images (entirely; alt text rarely speaks well)
- Markdown links (kept the label, dropped the URL)

Special-cased: list items keep their source paragraph (no extra `\n\n`)
so playback flows naturally; instead each item gets a trailing `。` if
it lacks one. That gives the synthesizer a clause-level pause between
items without the longer paragraph-level gap.

Heading folding: a markdown heading paragraph (single line matching
`#{1,6}\s+\S`) is *not* emitted on its own. Its cleaned text is held
over and prepended to the next non-heading paragraph with a `。`
separator, so a `## 検証` followed by its section body produces one
paragraph, not two. Without this, the heading would render as its own
≤ a few-character chunk bracketed by `prePhonemeLength` lead-in +
`afplay` device-open overhead, audibly isolating a single word. If a
heading is the last paragraph (no content follows), it is emitted
on its own as a fallback. Regular paragraph breaks are preserved.

Hard cap: `MAX_TEXT_LENGTH = 2000` chars after cleanup. Anything past
that is truncated.

### 7.2 Chunking (`split_into_chunks`)

Two-level split:

1. Paragraphs (split on `\n\n`+).
2. Inside each paragraph, sentence/clause boundaries
   (`。．！？!?、，,`).

Bounds:

- `FIRST_CHUNK_MAX = 60` chars — the first chunk is small so the engine
  returns audio fast and the user hears something within a second.
- `LATER_CHUNK_MAX = 250` chars — later chunks are closer to the
  engine's "sweet spot" (the docs warn that `> 1000` chars per
  `/synthesis` call collapses prosody into monotone and may leak
  memory).
- `MAX_CHUNKS = 8` — past this, chunks are dropped and a closing
  `「以下、省略します。」` is appended so the user hears the cut
  instead of an abrupt mid-sentence stop. Without this cap, a verbose
  reply could play for over a minute with no easy way to interrupt.

Speed adaptation: if `len(chunks) >= FAST_SPEED_CHUNK_THRESHOLD (4)`,
all chunks are synthesized with `speedScale = FAST_SPEED_SCALE (1.2)`.
Multi-paragraph answers get sped up so they don't drag.

### 7.3 Synthesis tweaks

- `prePhonemeLength = 0.5` — pads each chunk's leading silence so
  `afplay`'s device-open transient (especially on Bluetooth) lands
  inside the silence rather than over the first phoneme.
- `httpx.Client` is shared across all chunks for a single utterance so
  TCP+TLS keep-alive cuts the per-chunk latency.
- Failed `/synthesis` calls are skipped (not aborted): better to lose
  one sentence than to leave the user wondering why nothing is being
  read.

## 8. Single-flight playback (per session)

A new utterance must coordinate with any **in-progress utterance from
the same session**. The rule is uniform: **everything queues, nothing
is killed**. Every entry point — Stop / StopFailure hook,
Notification:permission_prompt hook, and mid-turn say.sh — shares one
per-session pidfile, and a new utterance polls that pidfile until the
recorded process group is gone, then registers itself.

Earlier designs split coordination by scope (Stop hook preempts, mid-
turn queues, Stop waits for mid-turn) but the resulting matrix of
asymmetric rules was hard to reason about and the user-perceived
behavior — "two voices speaking at the same time" or "the mid-turn
report disappeared" — kept regressing. Uniform queue beats clever
preempt.

Trade-off: an old utterance is never cut short, even if it has been
superseded by a fresher one. In practice this almost never matters
because each turn produces a single Stop-hook reading, and mid-turn
say is short (≤100 Japanese chars, a few seconds).

Different sessions also never preempt each other — that would defeat
the per-session voice rotation by making only the most-recent session
audible.

Implementation uses POSIX process groups and a per-session pidfile:

1. The core reads `SESSION_TTS_SESSION_ID` from env and constructs
   `PIDFILE = ~/.claude/session-tts/playback/<session_id>`.
2. `wait_for_previous_playback()` polls `PIDFILE` with `signal 0`
   (`os.killpg(pgid, 0)` — existence check, no signal delivered).
   When the recorded process group is gone, it returns. While the
   previous group is still alive, it sleeps in 0.2 s ticks.
3. `register_self()` calls `os.setpgrp()` (becoming a new
   process-group leader) and writes its PID to `PIDFILE`. The PID
   doubles as the new process-group leader id, so the next utterance
   can `killpg(pgid, 0)` against it.
4. On clean exit, `clear_self()` removes its own pidfile entry.

`os.killpg` is still the right tool for the existence check (over
`os.kill` against the bare pid) because each utterance becomes a
process-group leader via `setpgrp()`; checking the group includes
the child `afplay`.

If `SESSION_TTS_SESSION_ID` is missing (defensive — should not happen
in practice because every adapter passes it), the queue degrades to
"no coordination at all" rather than blocking forever. Better to risk
a brief overlap than to deadlock on a missing key.

Stale pidfile entries are harmless because both `os.killpg` errors
(`ProcessLookupError`, `PermissionError`) are swallowed and read as
"slot is free".

## 9. Hook subscriptions

`hooks/hooks.json` subscribes eight events. Audio-producing hooks are
`async: true` so they never block the turn flow; context-injecting
hooks are synchronous so their stdout (or `hookSpecificOutput`) reaches
the model before the next response.

| Event                                      | Adapter                       | async | Notes                                                                                  |
| ------------------------------------------ | ----------------------------- | ----- | -------------------------------------------------------------------------------------- |
| `SessionStart`                             | `session-on.sh`               | no    | voice rotation, instruction injection via stdout, self-backgrounded engine bootstrap   |
| `Stop`                                     | `dispatch.sh`                 | yes   | normal turn end; speaks `last_assistant_message`                                       |
| `StopFailure`                              | `dispatch.sh`                 | yes   | turn ended due to API error; speaks `last_assistant_message`                           |
| `Notification` matcher `permission_prompt` | `notify-permission.sh`        | yes   | tool needs approval; speaks workspace-aware Japanese phrase                            |
| `PostToolUse` matcher `TodoWrite`          | `remind-say.sh todo`          | no    | does not speak; reminds the model to narrate the task transition                       |
| `PreToolUse` matcher `Monitor`             | `remind-say.sh monitor`       | no    | does not speak; reminds the model to narrate what is being monitored and why           |
| `PreToolUse` matcher `Agent`               | `remind-say.sh agent`         | no    | does not speak; reminds the model to narrate the delegated subtask + follow-up         |
| `UserPromptSubmit` (no matcher)            | `remind-say.sh prompt`        | no    | does not speak; reminds the model that this turn may be multi-step and to narrate it   |

Other `Notification` subtypes (`idle_prompt` etc.) are intentionally
**not** subscribed — narrating idle prompts is annoying and adds no
value over the existing visual prompt. Likewise the reminder hooks
target only matchers that mark a real milestone (Monitor = long
watch, Agent = sub-agent dispatch, TodoWrite = task transition,
UserPromptSubmit = new turn boundary). High-frequency tools like
Write / Edit / Bash are deliberately **not** matched, because firing
a reminder on every one of them would bloat the context and dilute
the signal.

`SessionStart` and all `remind-say.sh ...` hooks are synchronous
because they rely on stdout-as-context or `hookSpecificOutput` —
Claude Code only captures that output when the hook runs synchronously.
Async hooks are fire-and-forget and their stdout is discarded. To
keep `SessionStart` non-blocking despite being synchronous,
`session-on.sh` self-backgrounds the slow engine
bootstrap with `{ … } & disown`; the synchronous part (voice rotation
+ instruction heredoc) is essentially instantaneous.

## 10. How mid-turn narration gets invoked

The model needs to be reminded to narrate progress. The calling shape
must satisfy two properties that a plain Bash invocation of `say.sh`
does not:

1. **Non-blocking** — synthesis + playback takes seconds; without
   backgrounding, the main turn waits for the whole bash → python →
   afplay chain before the next tool call can fire.
2. **Minimal context impact** — the tool call shouldn't dump SKILL.md
   text, sub-agent transcripts, or full bash output into the main
   conversation.

The Claude Code **Bash tool** with `run_in_background=true` satisfies
both: the call returns immediately with a single "Command running in
background" line and no further output until the background task is
explicitly inspected. Implementation explorations of a `session-tts:say`
skill (full SKILL.md gets injected into context) and a sub-agent (agent
sandboxes can't reach the plugin cache where `say.sh` lives) were both
ruled out by experiment.

The required call shape:

```
Bash(
  command: bash "${CLAUDE_PLUGIN_ROOT}/skills/say/say.sh" "<phrase>",
  description: "TTS report",
  run_in_background: true
)
```

### 10.1 SessionStart instruction injection (broad guidance)

`session-on.sh` prints an instruction block to stdout. Per
`https://code.claude.com/docs/en/hooks`, stdout from `SessionStart`,
`UserPromptSubmit`, and `UserPromptExpansion` "is added as context
that Claude can see and act on" — `SessionStart` is the natural place
to teach the model when and how to narrate.

The injected text:

- declares that TTS is enabled,
- spells out the exact Bash + `run_in_background=true` shape (with
  `${CLAUDE_PLUGIN_ROOT}` pre-expanded to the cached install path),
- warns that calling Bash *without* `run_in_background=true` blocks
  the turn,
- lists the four moments to invoke (transition / problem / finding /
  pivot),
- requires every utterance to begin with a brief lead-in phrase (枕詞)
  so the listener has a beat to register that an update is coming, and
- explicitly forbids per-tool narration and use for the final turn
  message (Stop already covers that).

### 10.2 Reminder hooks (deterministic forcing functions)

The `SessionStart` injection is broad guidance and decays in attention
as the conversation grows. Four hook events re-surface the narration
rule at **point-in-time moments** that map to one of the four
milestones (transition / problem / finding / pivot). All of them
dispatch through `scripts/remind-say.sh` with a trigger argument,
which produces the appropriate `hookSpecificOutput.additionalContext`
(or stdout, for UserPromptSubmit) — that is, no audio is produced;
just a short reminder Claude reads before the next response.

| Trigger          | Hook event / matcher                | Milestone it forces                                                   |
| ---------------- | ----------------------------------- | --------------------------------------------------------------------- |
| `todo`           | `PostToolUse` / `TodoWrite`         | task transition (todo state changed)                                  |
| `monitor`        | `PreToolUse` / `Monitor`            | long watch starting; model should describe what is being monitored    |
| `agent`          | `PreToolUse` / `Agent`              | sub-agent dispatch; model should describe the delegated subtask       |
| `prompt`         | `UserPromptSubmit` (no matcher)     | new turn boundary; model should narrate progress if this is multi-step |

Why these matchers specifically:

- `TodoWrite` is the canonical signal of a task transition — its very
  semantics (marking items `in_progress`/`completed`) *are* the transition.
- `Monitor` and `Agent` mark entry into long-running or delegated work
  — both are natural moments for "what's happening next" narration.
- `UserPromptSubmit` is the only event that fires at the start of every
  turn, before any tool call. It catches multi-step turns that don't
  go through TodoWrite.
- High-frequency tools (`Write` / `Edit` / `Bash`) are deliberately
  not matched — firing on every one of those would bloat the context
  and dilute the signal. A subset selection is the whole point.

Each reminder ends with the same boilerplate (`Skip if you just
narrated in the immediately preceding step.`) so the model
self-throttles when several triggers fire close together (e.g. user
prompt → todo update on the same turn).

## 11. Skills

### 11.1 `/session-tts:tts <on|off|toggle|status>`

Pure shell adapter at `skills/tts/tts.sh`. Toggles the presence of
`~/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID`. The skill is
declared `disable-model-invocation: true` so the model never calls it
on its own — it is purely user-driven.

When silencing the session (`off`, or `toggle` flipping to off), the
adapter reads the session's pidfile and sends `SIGTERM` to that
process group, then removes the pidfile. Without this step, calling
`tts off` mid-utterance would leave the current chunk queue draining
even though new utterances are blocked — surprising and frustrating.
Targeting only the session's own pidfile means a concurrent session's
audio is never affected.

### 11.2 (retired) `/session-tts:say`

Removed in v0.7.0. The previous slash-command skill made the say path
model-invocable, but every call (a) blocked the main turn until
synthesis and playback finished and (b) dumped the SKILL.md body and
Bash output into the main context. Both costs were unacceptable for a
mid-turn "report" use case.

A sub-agent variant (`agents/tts-speaker.md`) was also prototyped to
move the SKILL.md / Bash output out of the main context, but `claude
--plugin-dir` testing showed that sub-agent Bash sandboxes deny access
to plugin cache paths — the agent could `Skill`-launch `session-tts:say`
but had no working way to actually run the resulting Bash command. The
agent was discarded for the same v0.7.0.

The current entry point is a direct **Bash tool** call with
`run_in_background=true` on `${CLAUDE_PLUGIN_ROOT}/skills/say/say.sh`,
made by the main Claude after seeing the SessionStart guidance. See §10.

The underlying script `skills/say/say.sh` is unchanged and still used by
the hook adapters.

## 12. Concurrency model and invariants

- **Multiple sessions, one engine.** All Claude Code sessions on the
  same machine share `~/.claude/session-tts/engine/`. The engine is a
  single OS process bound to `127.0.0.1:10101`; concurrent sessions
  send concurrent HTTP requests and the engine handles them.
- **Multiple sessions, independent playback.** Single-flight is
  **per session**, not global. Sessions A and B can speak
  simultaneously; macOS audio mixes them and the per-session voice
  rotation is what makes the result intelligible. Only same-session
  preemption is allowed (a fresh reply in session A replaces an
  in-progress reply in session A).
- **Crash safety.** A killed Python process leaves a stale entry in
  its `playback/<session_id>` pidfile and possibly a stale temp WAV.
  Both are self-correcting on the next utterance from that session
  (`killpg` no-ops, temp files are unlinked after `afplay` per
  chunk). Other sessions are unaffected.
- **Hook re-entrancy.** `SessionStart` may fire many times for the
  same session (clear/compact). The voice-assignment branch is gated
  on `! -f "$session_file"`; the engine bootstrap is naturally
  idempotent.

## 13. External dependencies

- **`uv`** — Python runtime; adapters call
  `uv run --directory ${CLAUDE_PLUGIN_ROOT}/python python ...`.
- **`jq`** — JSON parsing in shell adapters.
- **`afplay`** — built into macOS; plays the synthesized WAVs.
- **`taskpolicy`** — built into macOS; used to boost engine scheduling
  priority. Optional — falls back to default scheduling if absent.
- **AivisSpeech-Engine** — local TTS engine binary, downloaded from
  GitHub Releases on first use.
- **AivisHub** — voice model registry, queried at engine install time
  for the three voices listed in `VOICES`.

## 14. Adding a new input source

To add another adapter (e.g. a new hook event, or a new skill):

1. Write an adapter script that produces a plain UTF-8 text string and
   resolves the session id from whatever its input contract supplies.
2. Source `lib/voice-context.sh`.
3. Call `resolve_speaker "$session_id"` to get the speaker id (exit
   silently if it returns failure).
4. Call `speak_text "$speaker_id" "$text"`.

The core does not need to change. Hook payload shapes never leak past
the adapter.

## 15. Versioning

Per the repo's plugin checklist, behavior changes touch all of:

- `session-tts/scripts/*` and/or `python/*`
- `session-tts/.claude-plugin/plugin.json` (version + description)
- `.claude-plugin/marketplace.json`
- `README.md` (plugin table row, overview, "How it works",
  "Configuration")

A change to the set of hook events that speak, or to the set of voices
in the rotation, is a breaking change and bumps the major version.
