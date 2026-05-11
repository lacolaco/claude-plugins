---
description: Toggle Claude Code TTS playback for the current session (session-tts plugin). TTS is ON by default at session start; this skill is for silencing the current session, re-enabling it after off, or checking status. Argument is one of `on`, `off`, `toggle`, or `status` (default `status`). Only this session is affected; other concurrent sessions stay as they are.
disable-model-invocation: true
---

# TTS toggle ($ARGUMENTS)

The session-tts plugin reads Claude responses aloud via `Stop`, `StopFailure`, and `Notification` hooks. A `SessionStart` hook assigns this session a voice and marks it ON automatically, so every new session speaks by default. This skill is the override path: silence the current session, re-enable after silencing, or check status.

The voice assigned to this session is decided once at SessionStart and stays the same even after `tts off`/`tts on` — only playback is gated.

The silence flag lives at `$HOME/.claude/session-tts/silenced/$CLAUDE_CODE_SESSION_ID`: when present, the dispatcher skips playback for this session. Other concurrent sessions stay as they are. Switching to `off` (directly or via `toggle`) additionally terminates any utterance that is still playing for this session, so the silence takes effect immediately rather than draining the current chunk queue.

Run the action below with the Bash tool. Default to `status` when `$ARGUMENTS` is empty.

```
bash "${CLAUDE_PLUGIN_ROOT}/skills/tts/tts.sh" "$ARGUMENTS"
```

Execute the requested action and report the resulting line. No additional explanation is needed.
