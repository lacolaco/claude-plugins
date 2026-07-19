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
#   session A, defeating the per-session voice rotation.
#
# Plugin root resolution:
#   Claude Code sets CLAUDE_PLUGIN_ROOT for hook invocations but NOT for the
#   Bash tool used by skill adapters. We fall back to resolving the plugin
#   root from this file's own location (lib/ → ../..) so callers from either
#   entry point work without having to pre-export the variable.

resolve_speaker() {
  local session_id="$1"
  local data_dir="$HOME/.claude/session-tts"
  local session_dir="$data_dir/sessions/$session_id"

  [ -z "$session_id" ] && return 1
  [ ! -e "$session_dir/speaker" ] && return 1
  [ -e "$session_dir/silenced" ] && return 1

  local speaker_id
  speaker_id=$(cat "$session_dir/speaker" 2>/dev/null || echo "")
  [ -z "$speaker_id" ] && return 1

  printf '%s' "$speaker_id"
}

_voice_context_plugin_root() {
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    printf '%s' "$CLAUDE_PLUGIN_ROOT"
    return
  fi
  (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
}

speak_text() {
  local speaker_id="$1"
  local text="$2"
  local session_id="$3"
  local plugin_root
  plugin_root=$(_voice_context_plugin_root)
  printf '%s' "$text" | \
    SESSION_TTS_SPEAKER_ID="$speaker_id" \
    SESSION_TTS_SESSION_ID="$session_id" \
    uv run --directory "$plugin_root/python" \
    python "$plugin_root/scripts/say-response.py"
}
