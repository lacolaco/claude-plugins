---
description: Adjust the session-tts playback volume globally (afplay --volume coefficient). The default is 0.8 to keep TTS quieter than other audio (notifications, music). Argument is a decimal in [0.0, 1.0] to set the volume, `status` (default) to show the current value, or `reset` to restore the default. The setting is shared across all sessions and persists across sessions and restarts.
disable-model-invocation: true
---

# TTS volume ($ARGUMENTS)

The session-tts plugin pipes every chunk through `afplay --volume <coefficient>` so TTS does not dominate over other audio (notifications, music) when the system volume is up. macOS has no native way to make `afplay` follow the system "alert volume"; this skill is the override path.

The chosen value lives at `$HOME/.claude/session-tts/volume` and is read by `say-response.py` for every chunk it plays. The setting is per-user, not per-session — adjusting it affects every active and future session. A value outside `[0.0, 1.0]` is rejected; an empty file or missing file falls back to the built-in default (`0.8`).

Run the action below with the Bash tool. Default to `status` when `$ARGUMENTS` is empty.

```
bash "${CLAUDE_PLUGIN_ROOT}/skills/volume/volume.sh" "$ARGUMENTS"
```

Execute the requested action and report the resulting line. No additional explanation is needed.
