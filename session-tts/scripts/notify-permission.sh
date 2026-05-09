#!/bin/bash
# Notification:permission_prompt handler.
#
# Reads the hook input JSON from stdin, derives the workspace name from
# `cwd` (basename), composes a workspace-aware Japanese line, and forwards
# everything to dispatch.sh so the existing speaker-id lookup, silence
# check, and TTS pipeline are reused unchanged.

set -e

input=$(cat)
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')

if [ -n "$cwd" ]; then
  workspace=$(basename "$cwd")
  message="${workspace}で承認待ちです。"
else
  message="承認待ちです。"
fi

printf '%s' "$input" | "${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.sh" "$message"
