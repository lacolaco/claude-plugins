#!/bin/bash
# SessionStart hook handler.
#
# Two responsibilities:
#   1. Assign a voice to this session (rotating through the configured slots).
#      The assignment lives at $sessions_dir/$session_id; once written it is
#      kept across re-fires (clear/compact) so the voice stays stable for the
#      lifetime of the session.
#   2. Make sure the local TTS engine is installed, running, and has the
#      required voice models loaded. Idempotent — typical re-runs do nothing.

set -e

# shellcheck source=lib/voice-context.sh
. "${CLAUDE_PLUGIN_ROOT}/scripts/lib/voice-context.sh"

session_id=$(jq -r '.session_id // empty')
if [ -z "$session_id" ]; then
  exit 0
fi

data_dir="$HOME/.claude/session-tts"
sessions_dir="$data_dir/sessions"
index_file="$data_dir/index"
session_file="$sessions_dir/$session_id"

mkdir -p "$sessions_dir"

# --- inject mid-turn narration guidance into Claude's context ---
# SessionStart hook stdout is captured by Claude Code as additional context
# (https://code.claude.com/docs/en/hooks: "Any text your hook script prints
# to stdout is added as context for Claude"). This is the only point at
# which the plugin can teach the model when to invoke /session-tts:say —
# without it the skill exists but is never called autonomously.
cat <<'EOF'
[session-tts] TTS is enabled for this session.

The /session-tts:say skill is available to speak Japanese phrases aloud as
**verbal task-progress reports during autonomous, multi-step work**. The
goal is to let the user follow your progress by ear without reading every
message.

Call /session-tts:say at these moments:
- **Task transitions**: when you finish a task and move on to the next
- **Problems**: when a task hits an unexpected obstacle, error, or blocker
- **Important findings**: when investigation surfaces a notable result
- **Direction changes**: when you revise the plan or pivot the approach

Length: keep each call under ~100 Japanese characters.

**Format**: every utterance must begin with a brief lead-in phrase (枕詞)
before the main content, so the listener has a beat to register that an
update is coming instead of being dropped into the body cold. Match the
lead-in to the moment:

- transitions: 「報告です。」「完了です。」「進捗です。」
- problems: 「問題発生です。」「エラーです。」
- findings: 「発見です。」「気づきです。」
- direction changes: 「方針転換です。」「アプローチを変えます。」

Examples (lead-in + body, adapt to the actual work):
- (transition) 「報告です。ログイン機能のテストが全て通りました。次はAPI部分の実装に入ります」
- (problem) 「問題発生です。ビルドが3つのmoduleで失敗しています。原因を調べます」
- (finding) 「発見です。キャッシュ設定が原因でレスポンスが遅くなっていました」
- (pivot) 「方針転換です。最初のREST実装は要件に合わないのでGraphQLに切り替えます」

Avoid:
- Mechanical tool announcements (e.g.「ファイルを読みます」「Bash実行します」)
- Per-tool narration; report at the milestone, not at each step
- The final response of a turn (Stop hook narrates the final assistant
  message automatically)

The skill is a no-op if TTS has been silenced via /session-tts:tts off.
EOF

# --- pick a voice for this session (only if not already assigned) -----
newly_assigned=0
if [ ! -f "$session_file" ]; then
  prev=$(cat "$index_file" 2>/dev/null || echo -1)
  case "$prev" in ''|*[!0-9-]*) prev=-1 ;; esac
  next=$(( (prev + 1) % 3 ))
  case "$next" in
    0) speaker_id=888753760  ;;  # voice slot 1
    1) speaker_id=1431611904 ;;  # voice slot 2
    2) speaker_id=345585728  ;;  # voice slot 3
    *) speaker_id=888753760  ;;
  esac
  echo "$next" > "$index_file"
  echo "$speaker_id" > "$session_file"
  newly_assigned=1
fi

# --- engine bootstrap + (optional) ready announcement ---------------------
# Both run in the background so SessionStart returns instantly. The
# announcement only fires when this is the first SessionStart for the session
# (newly_assigned=1) so /clear and /compact don't repeat it on every refire.
plugin_root="${CLAUDE_PLUGIN_ROOT}"
{
  uv run --directory "$plugin_root/python" \
    python "$plugin_root/python/setup_engine.py"
  setup_status=$?
  if [ "$newly_assigned" = "1" ] && [ "$setup_status" = "0" ]; then
    sid=$(resolve_speaker "$session_id") && speak_text "$sid" "TTSを開始します。"
  fi
} >> "$data_dir/setup.log" 2>&1 < /dev/null &
disown
