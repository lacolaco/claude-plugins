# Shared helpers for session-tts adapters. Source this file from any adapter
# script that needs to resolve the per-session voice and forward text to the
# core (say-response.py).
#
# ensure_speaker <session_id>
#   Gives the session a voice from the rotation unless it already holds one
#   of SESSION_TTS_VOICE_IDS. A speaker file holding any other id (e.g. an
#   AivisSpeech style id from session-tts <= 0.13) is replaced. Also gives
#   the session a stereo position (ensure_pan). Returns 0 when it assigned a
#   voice, 1 when the existing one was kept.
#
# ensure_pan <session_id>
#   Gives the session a random stereo position unless sessions/<sid>/pan
#   already holds a valid one: a decimal in [-1, 1] (-1 = left edge,
#   1 = right edge of PAN_RANGE in say-response.py). Invalid content is
#   replaced. Called from ensure_speaker, so the position is assigned
#   together with the voice and kept for the whole session.
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

# Rotation order: VOICEVOX Engine 0.26.2 style ids of each character's
# ノーマル style, as listed by the engine's /speakers.
SESSION_TTS_VOICE_IDS=(
  3    # ずんだもん
  2    # 四国めたん
  8    # 春日部つむぎ
  14   # 冥鳴ひまり
  108  # 東北きりたん
)

ensure_pan() {
  local pan_file="$HOME/.claude/session-tts/sessions/$1/pan"
  local current
  current=$(cat "$pan_file" 2>/dev/null || echo "")
  if [[ "$current" =~ ^-?(0(\.[0-9]+)?|1(\.0+)?)$ ]]; then
    return 0
  fi
  # Uniform over -1.000 .. 1.000 in steps of 0.001.
  local n=$(( RANDOM % 2001 - 1000 )) sign=""
  if [ "$n" -lt 0 ]; then
    sign="-"
    n=$(( -n ))
  fi
  mkdir -p "$(dirname "$pan_file")"
  printf '%s%d.%03d\n' "$sign" $(( n / 1000 )) $(( n % 1000 )) > "$pan_file"
}

ensure_speaker() {
  local session_id="$1"
  local data_dir="$HOME/.claude/session-tts"
  local session_dir="$data_dir/sessions/$session_id"
  local index_file="$data_dir/index"

  ensure_pan "$session_id"

  local current id
  current=$(cat "$session_dir/speaker" 2>/dev/null || echo "")
  for id in "${SESSION_TTS_VOICE_IDS[@]}"; do
    [ "$current" = "$id" ] && return 1
  done

  local prev next
  prev=$(cat "$index_file" 2>/dev/null || echo -1)
  case "$prev" in ''|*[!0-9]*) prev=-1 ;; esac
  next=$(( (prev + 1) % ${#SESSION_TTS_VOICE_IDS[@]} ))
  mkdir -p "$session_dir"
  echo "$next" > "$index_file"
  echo "${SESSION_TTS_VOICE_IDS[$next]}" > "$session_dir/speaker"
  return 0
}

resolve_speaker() {
  local session_id="$1"
  local data_dir="$HOME/.claude/session-tts"
  local session_dir="$data_dir/sessions/$session_id"

  [ -z "$session_id" ] && return 1
  [ ! -e "$session_dir/speaker" ] && return 1
  [ -e "$session_dir/silenced" ] && return 1

  # Sessions that started under an older plugin version may still hold a
  # voice id the current engine does not have.
  ensure_speaker "$session_id" || true

  cat "$session_dir/speaker"
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
