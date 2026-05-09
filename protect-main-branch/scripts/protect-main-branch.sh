#!/bin/bash
# Guard: block Write/Edit/push on protected branches
# The protected branch names can be configured via the PROTECT_MAIN_BRANCH_NAME
# environment variable as a space-separated list (defaults to "main").
# Example: PROTECT_MAIN_BRANCH_NAME="main master develop"

protected_branches="${PROTECT_MAIN_BRANCH_NAME:-main}"
branch=$(git branch --show-current 2>/dev/null)

case " $protected_branches " in
  *" $branch "*) ;;
  *) exit 0 ;;
esac

input=$(cat)
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')

case "$tool_name" in
  Write|Edit)
    file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
    [ -z "$file_path" ] && exit 0
    repo_dir=$(git rev-parse --show-toplevel 2>/dev/null)
    case "$file_path" in
      "$repo_dir"/*) ;;
      *) exit 0 ;;
    esac
    # Allow editing gitignored files
    if git check-ignore -q "$file_path" 2>/dev/null; then
      exit 0
    fi
    ;;
  Bash)
    command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')
    # Only block git push commands; allow everything else (incl. ops outside the repo)
    case "$command" in
      *"git push"*) ;;
      *) exit 0 ;;
    esac
    ;;
  *)
    exit 0
    ;;
esac

jq -n --arg branch "$branch" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("Cannot edit/push on " + $branch + " branch. Create a feature branch first.")
  }
}'
