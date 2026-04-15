#!/bin/bash
# Guard: block Write/Edit/push on the protected branch
# The protected branch name can be configured via the PROTECT_MAIN_BRANCH_NAME
# environment variable (defaults to "main").

protected_branch="${PROTECT_MAIN_BRANCH_NAME:-main}"
branch=$(git branch --show-current 2>/dev/null)
if [ "$branch" != "$protected_branch" ]; then
  exit 0
fi

# For Write/Edit: only block tracked (non-ignored) files within the repo
file_path=$(jq -r '.tool_input.file_path // empty')
if [ -n "$file_path" ]; then
  repo_dir=$(git rev-parse --show-toplevel 2>/dev/null)
  case "$file_path" in
    "$repo_dir"/*) ;;
    *) exit 0 ;;
  esac
  # Allow editing gitignored files
  if git check-ignore -q "$file_path" 2>/dev/null; then
    exit 0
  fi
fi

jq -n --arg branch "$protected_branch" '{"decision":"block","reason":("Cannot edit/push on " + $branch + " branch. Create a feature branch first.")}'
