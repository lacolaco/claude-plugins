# Shared helpers for session-tts adapters. Source this file from any adapter
# script that needs to resolve the per-session voice and forward text to the
# core (say-response.py).
#
# resolve_speaker <session_id>
#   Prints the assigned speaker id on stdout. Returns 1 if the session has
#   no voice assigned or has been silenced via /session-tts:tts off.
#
# speak_text <speaker_id> <text> <session_id>
#   Forwards the given text to say-response.py with the speaker and
#   session id injected via env. session_id is required so the core
#   scopes its single-flight pidfile per session — without it, a new
#   utterance from session B would kill an in-progress utterance from
#   session A, defeating the per-session voice rotation. Requires
#   CLAUDE_PLUGIN_ROOT to be set (it always is when called from a hook
#   or skill).

resolve_speaker() {
  local session_id="$1"
  local data_dir="$HOME/.claude/session-tts"
  local session_file="$data_dir/sessions/$session_id"
  local silenced_file="$data_dir/silenced/$session_id"

  [ -z "$session_id" ] && return 1
  [ ! -e "$session_file" ] && return 1
  [ -e "$silenced_file" ] && return 1

  local speaker_id
  speaker_id=$(cat "$session_file" 2>/dev/null || echo "")
  [ -z "$speaker_id" ] && return 1

  printf '%s' "$speaker_id"
}

speak_text() {
  local speaker_id="$1"
  local text="$2"
  local session_id="$3"
  printf '%s' "$text" | \
    SESSION_TTS_SPEAKER_ID="$speaker_id" \
    SESSION_TTS_SESSION_ID="$session_id" \
    uv run --directory "${CLAUDE_PLUGIN_ROOT}/python" \
    python "${CLAUDE_PLUGIN_ROOT}/scripts/say-response.py"
}
