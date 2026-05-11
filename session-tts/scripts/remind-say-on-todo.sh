#!/bin/bash
# PostToolUse:TodoWrite hook adapter.
#
# Does NOT speak. Returns hookSpecificOutput.additionalContext so Claude
# Code injects a reminder into the model's context, nudging it to dispatch
# the session-tts-speaker agent (which in turn calls the say skill) with a
# properly composed Japanese narration before its next text response.
#
# Why a reminder rather than auto-narration: todo content is typically
# English (or terse non-sentence text), and AivisSpeech is a Japanese
# engine. Editorial framing (枕詞, summary, lead-in) belongs to the
# model; the hook's job is just to be a deterministic forcing function
# so the model does not forget at transition moments.
#
# No-op when the session has no voice assigned or has been silenced via
# /session-tts:tts off — TTS is disabled so the nudge would only add
# noise to the model's context.

set -e

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')

data_dir="$HOME/.claude/session-tts"
[ -z "$session_id" ] && exit 0
[ ! -e "$data_dir/sessions/$session_id" ] && exit 0
[ -e "$data_dir/silenced/$session_id" ] && exit 0

# PostToolUse stdout is NOT auto-injected as context (unlike SessionStart).
# We must return JSON with hookSpecificOutput.additionalContext.
jq -n '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: "[session-tts] Todo state changed. Before your next text response, dispatch the `session-tts-speaker` agent via `Agent({subagent_type: \"session-tts-speaker\", prompt: \"<phrase>\", run_in_background: true})` to narrate this transition. Open with a lead-in phrase (報告です / 着手します / 完了です など) and keep it under ~100 Japanese characters. Example prompt: 「報告です。<前のタスク>が完了しました。次は<次のタスク>に入ります」. Always use run_in_background=true so it does not block your next work. Skip if you just dispatched the agent in the immediately preceding step."
  }
}'
