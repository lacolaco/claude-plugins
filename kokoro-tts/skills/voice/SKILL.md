---
description: Toggle Claude Code TTS playback for the current session (kokoro-tts plugin). Argument is one of `on`, `off`, `toggle`, or `status` (default `status`). Only this session is affected; other concurrent sessions stay as they are.
disable-model-invocation: true
---

# Voice toggle ($ARGUMENTS)

The kokoro-tts plugin reads Claude responses aloud via `Stop`, `StopFailure`, and `Notification` hooks. Each hook fires for the session that produced the response, but Claude Code's hook commands run as plain subprocesses — without per-session scoping, every concurrent session would speak at once.

This skill scopes playback to the current session by managing a flag file at `$HOME/.claude/kokoro-tts/sessions/$CLAUDE_CODE_SESSION_ID`. The dispatch script in the hook reads `session_id` from the hook input JSON and only invokes the TTS engine when the matching flag file exists.

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
