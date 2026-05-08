---
description: Toggle Claude Code TTS playback for the current session (kokoro-tts plugin). Voice is ON by default at session start; this skill is for silencing the current session, re-enabling it after off, or checking status. Argument is one of `on`, `off`, `toggle`, or `status` (default `status`). Only this session is affected; other concurrent sessions stay as they are.
disable-model-invocation: true
---

# Voice toggle ($ARGUMENTS)

The kokoro-tts plugin reads Claude responses aloud via `Stop`, `StopFailure`, and `Notification` hooks. A `SessionStart` hook creates the per-session flag automatically, so every new session speaks by default. This skill is the override path: silence the current session, re-enable after silencing, or check status.

Playback is scoped to the current session via a flag file at `$HOME/.claude/kokoro-tts/sessions/$CLAUDE_CODE_SESSION_ID`. The dispatch script reads `session_id` from the hook input JSON and only invokes the TTS engine when the matching flag file exists, so concurrent sessions that turned voice off stay silent.

Run the action below with the Bash tool. Use the env var `$CLAUDE_CODE_SESSION_ID` (exported by Claude Code to subprocesses) so the flag is scoped to this session.

Argument handling (default to `status` when `$ARGUMENTS` is empty):

- `on`:
  ```
  mkdir -p "$HOME/.claude/kokoro-tts/sessions"
  touch "$HOME/.claude/kokoro-tts/sessions/$CLAUDE_CODE_SESSION_ID"
  echo "Claude voice (this session): ON"
  ```
- `off`:
  ```
  rm -f "$HOME/.claude/kokoro-tts/sessions/$CLAUDE_CODE_SESSION_ID"
  echo "Claude voice (this session): OFF"
  ```
- `toggle`:
  ```
  flag="$HOME/.claude/kokoro-tts/sessions/$CLAUDE_CODE_SESSION_ID"
  if [ -e "$flag" ]; then
    rm -f "$flag"; echo "Claude voice (this session): OFF"
  else
    mkdir -p "$(dirname "$flag")"; touch "$flag"; echo "Claude voice (this session): ON"
  fi
  ```
- `status`:
  ```
  if [ -e "$HOME/.claude/kokoro-tts/sessions/$CLAUDE_CODE_SESSION_ID" ]; then
    echo "Claude voice (this session): ON"
  else
    echo "Claude voice (this session): OFF"
  fi
  ```

Execute the requested action and report the resulting line. No additional explanation is needed.
