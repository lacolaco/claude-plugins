#!/bin/bash
# Notification:permission_prompt hook adapter.
#
# Composes a workspace-aware Japanese phrase from the hook payload and
# forwards it to the core (say-response.py). System notification payloads
# are freeform English text, so we generate the spoken line locally rather
# than trying to read the payload aloud.

set -e

# shellcheck source=lib/voice-context.sh
. "${CLAUDE_PLUGIN_ROOT}/scripts/lib/voice-context.sh"

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')

if [ -n "$cwd" ]; then
  workspace=$(basename "$cwd")
  text="${workspace}で承認待ちです。"
else
  text="承認待ちです。"
fi

speaker_id=$(resolve_speaker "$session_id") || exit 0
speak_text "$speaker_id" "$text" "$session_id"
