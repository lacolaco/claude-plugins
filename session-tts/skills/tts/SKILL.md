---
description: Toggle Claude Code TTS playback for the current session (session-tts plugin). TTS is ON by default at session start; this skill is for silencing the current session, re-enabling it after off, or checking status. Argument is one of `on`, `off`, `toggle`, or `status` (default `status`). Only this session is affected; other concurrent sessions stay as they are.
disable-model-invocation: true
---

# TTS toggle ($ARGUMENTS)

The session-tts plugin reads Claude responses aloud via `Stop`, `StopFailure`, and `Notification` hooks. A `SessionStart` hook assigns this session a voice and marks it ON automatically, so every new session speaks by default. This skill is the override path: silence the current session, re-enable after silencing, or check status.

The voice assigned to this session is decided once at SessionStart and stays the same even after `tts off`/`tts on` — only playback is gated.

The silence flag lives at `$HOME/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID`: when present, the dispatcher skips playback for this session. Other concurrent sessions stay as they are.

Run the action below with the Bash tool. Use the env var `$CLAUDE_CODE_SESSION_ID` (exported by Claude Code to subprocesses) so the flag is scoped to this session.

Argument handling (default to `status` when `$ARGUMENTS` is empty):

- `on`:
  ```
  rm -f "$HOME/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID"
  echo "Claude TTS (this session): ON"
  ```
- `off`:
  ```
  mkdir -p "$HOME/.claude/session-tts/silenced"
  touch "$HOME/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID"
  echo "Claude TTS (this session): OFF"
  ```
- `toggle`:
  ```
  flag="$HOME/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID"
  if [ -e "$flag" ]; then
    rm -f "$flag"; echo "Claude TTS (this session): ON"
  else
    mkdir -p "$(dirname "$flag")"; touch "$flag"; echo "Claude TTS (this session): OFF"
  fi
  ```
- `status`:
  ```
  if [ -e "$HOME/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID" ]; then
    echo "Claude TTS (this session): OFF"
  else
    echo "Claude TTS (this session): ON"
  fi
  ```

Execute the requested action and report the resulting line. No additional explanation is needed.
