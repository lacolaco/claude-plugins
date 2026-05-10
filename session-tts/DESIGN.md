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
├── hooks/hooks.json               # hook subscriptions (SessionStart / Stop / StopFailure / Notification)
├── scripts/
│   ├── session-on.sh              # SessionStart adapter (voice rotation + engine bootstrap)
│   ├── dispatch.sh                # Stop / StopFailure adapter
│   ├── notify-permission.sh       # Notification:permission_prompt adapter
│   ├── remind-say-on-todo.sh      # PostToolUse:TodoWrite adapter (context-injection only)
│   ├── say-skill.sh               # /session-tts:say skill adapter
│   ├── say-response.py            # CORE: text → audio
│   └── lib/voice-context.sh       # shared resolve_speaker / speak_text helpers
├── python/
│   ├── pyproject.toml             # uv-managed runtime (httpx, py7zr)
│   └── setup_engine.py            # engine binary + voice model bootstrap
└── skills/
    ├── tts/SKILL.md               # /session-tts:tts on/off/toggle/status
    └── say/SKILL.md               # /session-tts:say <japanese>
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
      ├── kill_previous_playback (single-flight)
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
| `scripts/say-skill.sh`               | `/session-tts:say` skill argv                   | speaks argv[1] verbatim                      |
| `scripts/session-on.sh` (special)    | `SessionStart` hook stdin                       | speaks "TTSを開始します。" (1st run only) + injects guidance via stdout |
| `scripts/remind-say-on-todo.sh`      | `PostToolUse:TodoWrite` hook stdin              | injects `hookSpecificOutput.additionalContext` reminder (does not speak) |

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

### 3.3 Why the TodoWrite hook does not speak

`remind-say-on-todo.sh` is the only adapter that *injects context*
rather than producing audio. The reason: todo content is typically
English (e.g. "Implement X", "Fix Y") or terse non-sentence text,
and AivisSpeech is a Japanese engine — feeding the engine raw todo
strings would either fail or sound nonsensical. Editorial framing
(枕詞, summary, lead-in phrase) belongs to the model, which can
compose a proper Japanese sentence. The hook's only job is to be a
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
  sessions have separate pidfiles, so they cannot kill each other.
  Stale entries are harmless because `kill_previous_playback`
  ignores `ProcessLookupError`.

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

A new utterance must replace, not overlap with, an **in-progress
utterance from the same session**. Different sessions never preempt
each other — that would defeat the per-session voice rotation by
making only the most-recent session audible.

Implementation uses POSIX process groups and a per-session pidfile:

1. The core reads `SESSION_TTS_SESSION_ID` from env and constructs
   `PIDFILE = ~/.claude/session-tts/playback/<session_id>`.
2. `kill_previous_playback()` reads `PIDFILE` (if any) and sends
   `SIGTERM` to the **whole process group** with `os.killpg`. That
   kills the previous Python process *and* its `afplay` child in
   one go; without `killpg`, the child `afplay` would survive a
   single-PID kill on the parent. Because `PIDFILE` is per session,
   only same-session processes can be the target.
3. `register_self()` calls `os.setpgrp()` (becoming a new
   process-group leader) and writes its PID to `PIDFILE`.
4. On clean exit, `clear_self()` removes its own pidfile entry.

If `SESSION_TTS_SESSION_ID` is missing (defensive — should not happen
in practice because every adapter passes it), single-flight degrades
to "no preemption at all" rather than "global preemption". Better to
leak a stale playback than to silence other sessions.

Stale pidfile entries are harmless because both `os.killpg` errors
(`ProcessLookupError`, `PermissionError`) are swallowed.

## 9. Hook subscriptions

`hooks/hooks.json` subscribes five events. Audio-producing hooks are
`async: true` so they never block the turn flow; the context-injection
hook is synchronous so its output reaches the model before the next
response.

| Event                                      | Adapter                       | async | Notes                                                                        |
| ------------------------------------------ | ----------------------------- | ----- | ---------------------------------------------------------------------------- |
| `SessionStart`                             | `session-on.sh`               | yes   | voice rotation, engine bootstrap, instruction injection via stdout            |
| `Stop`                                     | `dispatch.sh`                 | yes   | normal turn end; speaks `last_assistant_message`                              |
| `StopFailure`                              | `dispatch.sh`                 | yes   | turn ended due to API error; speaks `last_assistant_message`                  |
| `Notification` matcher `permission_prompt` | `notify-permission.sh`        | yes   | tool needs approval; speaks workspace-aware Japanese phrase                   |
| `PostToolUse` matcher `TodoWrite`          | `remind-say-on-todo.sh`       | no    | does not speak; injects `additionalContext` reminding the model to call `/say` |

Other `Notification` subtypes (`idle_prompt` etc.) are intentionally
**not** subscribed — narrating idle prompts is annoying and adds no
value over the existing visual prompt.

The `TodoWrite` hook is **the only synchronous hook** in the plugin.
That is intentional: its output is consumed by the model's next
generation step, so it must complete first. Latency is negligible
(one `jq -n` invocation).

## 10. How `/session-tts:say` gets invoked

The skill is model-invocable, but the model needs to be reminded to
call it. Two layers of reinforcement:

### 10.1 SessionStart instruction injection (broad guidance)

`session-on.sh` prints a short instruction block to stdout. Per
`https://code.claude.com/docs/en/hooks`, stdout from `SessionStart`,
`UserPromptSubmit`, and `UserPromptExpansion` "is added as context
that Claude can see and act on" — `SessionStart` is the natural place
to teach the model when to invoke the skill.

The injected text:

- declares that TTS is enabled,
- lists the four moments to call the skill (transition / problem /
  finding / pivot),
- requires every utterance to begin with a brief lead-in phrase (枕詞)
  so the listener has a beat to register that an update is coming, and
- explicitly forbids per-tool narration and use for the final turn
  message (Stop already covers that).

The same constraints are duplicated in `skills/say/SKILL.md` so they
appear in both the auto-injected guidance and the skill's own
description.

### 10.2 PostToolUse:TodoWrite reminder (deterministic forcing function)

The `SessionStart` injection is broad guidance and decays in attention
as the conversation grows. The `TodoWrite` hook is the **point-in-time
forcing function** that fires *exactly* at one of the four moments
("task transition") and re-surfaces the rule into the model's context
right when it matters. This is the mechanism that closes the gap
between "the model understands the rule in the abstract" and "the
model actually invokes the skill at runtime."

Why `TodoWrite` specifically:

- `TodoWrite` is the canonical signal of a transition. The tool's
  semantics — marking items `in_progress`/`completed` — *are* the
  transition. No heuristic needed.
- It fires at most once per state change, so reminders do not
  spam the context.
- It is the only tool whose firing maps 1:1 to a milestone-level
  event. `Write` / `Edit` / `Bash` fire too often to be reasonable
  triggers.

The hook does not detect *which* todos changed (PostToolUse only sees
post-state, not the diff). It assumes "if `TodoWrite` was called,
something transitioned" — true by construction, since `TodoWrite`
without a state change is useless.

## 11. Skills

### 11.1 `/session-tts:tts <on|off|toggle|status>`

Pure shell: toggles the presence of
`~/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID`. The skill is
declared `disable-model-invocation: true` so the model never calls it
on its own — it is purely user-driven.

### 11.2 `/session-tts:say <japanese>`

Model-invocable. Wraps `scripts/say-skill.sh "$1"`, which goes through
the same `resolve_speaker` → `speak_text` path as the hooks. If the
session is silenced, `resolve_speaker` returns failure and the skill
exits without speaking.

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
