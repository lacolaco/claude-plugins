#!/bin/bash
# /session-tts:tts skill entry point.
# Usage: tts.sh on|off|toggle|status
#
# When silencing the session (off / toggle-to-off), also kills any utterance
# that is still playing for this session. Without this, calling `tts off`
# while a long response is being read aloud would leave audio playing until
# the current chunk queue drains — surprising and frustrating.
#
# When activating a session that was started with SESSION_TTS_ENABLED=0,
# performs late activation: removes silenced, ensures the engine is running,
# and outputs the narration context so the model learns how to use TTS.

set -e

action="${1:-status}"
session_id="${CLAUDE_CODE_SESSION_ID:-}"

if [ -z "$session_id" ]; then
  echo "session-tts:tts: CLAUDE_CODE_SESSION_ID is not set" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
plugin_root="$(cd "$script_dir/../.." && pwd)"

data_dir="$HOME/.claude/session-tts"
session_dir="$data_dir/sessions/$session_id"
silenced_file="$session_dir/silenced"
pidfile="$session_dir/playback"

# shellcheck source=../../scripts/lib/voice-context.sh
. "$plugin_root/scripts/lib/voice-context.sh"

kill_current_playback() {
  [ -f "$pidfile" ] || return 0
  local pgid
  pgid=$(cat "$pidfile" 2>/dev/null || echo "")
  if [ -n "$pgid" ]; then
    kill -TERM -- "-$pgid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
}

emit_narration_context() {
  cat <<EOF
[session-tts] TTS is enabled for this session.

You can deliver **verbal task-progress reports during autonomous, multi-step
work** so the user can follow your progress by ear without reading every
message.

**Invoke via the Bash tool** (synchronous — do NOT pass \`run_in_background\`):

\`\`\`
Bash(
  command: bash "$plugin_root/skills/say/say.sh" "<lead-in + body, one short Japanese phrase>",
  description: "TTS report"
)
\`\`\`

The call blocks until synthesis and playback finish. Keep each phrase short
(under ~100 Japanese characters) so the turn doesn't stall, and only narrate
at real milestones — see the list below.

Call this at these moments:
- **Task transitions**: when you finish a task and move on to the next
- **Problems**: when a task hits an unexpected obstacle, error, or blocker
- **Important findings**: when investigation surfaces a notable result
- **Direction changes**: when you revise the plan or pivot the approach

Length: keep each prompt under ~100 Japanese characters.

**Format**: every phrase must begin with a brief lead-in (枕詞) before
the body, so the listener has a beat to register that an update is
coming instead of being dropped into content cold. Match the lead-in
to the moment:

- transitions: 「報告です。」「完了です。」「進捗です。」
- problems: 「問題発生です。」「エラーです。」
- findings: 「発見です。」「気づきです。」
- direction changes: 「方針転換です。」「アプローチを変えます。」

say.sh itself is a no-op if TTS has been silenced via /session-tts:tts off,
so it's safe to call it without checking silence status.
EOF
}

silence_on() {
  mkdir -p "$session_dir"
  touch "$silenced_file"
  kill_current_playback
  echo "Claude TTS (this session): OFF"
}

silence_off() {
  local was_silenced=0
  [ -e "$silenced_file" ] && was_silenced=1
  rm -f "$silenced_file"

  if [ "$was_silenced" = "1" ]; then
    emit_narration_context
    # Ensure engine is running (background, non-blocking)
    {
      uv run --directory "$plugin_root/python" \
        python "$plugin_root/python/setup_engine.py"
      if [ $? -eq 0 ]; then
        sid=$(resolve_speaker "$session_id") && speak_text "$sid" "TTSを開始します。" "$session_id"
      fi
    } >> "$data_dir/setup.log" 2>&1 < /dev/null &
    disown
  else
    echo "Claude TTS (this session): ON"
  fi
}

case "$action" in
  on)
    silence_off
    ;;
  off)
    silence_on
    ;;
  toggle)
    if [ -e "$silenced_file" ]; then
      silence_off
    else
      silence_on
    fi
    ;;
  status)
    if [ -e "$silenced_file" ]; then
      echo "Claude TTS (this session): OFF"
    else
      echo "Claude TTS (this session): ON"
    fi
    ;;
  *)
    echo "usage: tts.sh on|off|toggle|status" >&2
    exit 1
    ;;
esac
