#!/bin/bash
# Guard: block git operations that can modify the protected branch.
#
# Configuration (environment variables):
#   PROTECT_MAIN_BRANCH_NAME
#     Space-separated list of protected branch names (defaults to "main").
#     Example: PROTECT_MAIN_BRANCH_NAME="main master develop"
#
#   PROTECT_MAIN_BRANCH_ALLOWED_SUBCOMMANDS
#     Space-separated list of git subcommands that should NOT be blocked even
#     when run on a protected branch. Subcommands not in the blocklist are
#     ignored. Example: PROTECT_MAIN_BRANCH_ALLOWED_SUBCOMMANDS="merge revert"

input=$(cat)
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
[ -z "$cwd" ] && cwd=$(pwd)

protected_branches="${PROTECT_MAIN_BRANCH_NAME:-main}"
branch=$(git -C "$cwd" branch --show-current 2>/dev/null)

case " $protected_branches " in
  *" $branch "*) ;;
  *) exit 0 ;;
esac

command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')

# Block subcommands that can change the branch tip locally or publish it.
# `pull` is intentionally not blocked: it is the normal way to sync the protected
# branch with its upstream. Working-tree-only operations (checkout/switch/stash)
# are also allowed.
if [[ "$command" =~ (^|[^[:alnum:]_/-])git[[:space:]]+(commit|push|merge|rebase|reset|cherry-pick|revert|am)([[:space:]]|$) ]]; then
  sub="${BASH_REMATCH[2]}"

  # Per-user allowlist: skip the deny if this subcommand is explicitly allowed.
  allowed_subcommands="${PROTECT_MAIN_BRANCH_ALLOWED_SUBCOMMANDS:-}"
  case " $allowed_subcommands " in
    *" $sub "*) exit 0 ;;
  esac

  jq -n --arg branch "$branch" --arg sub "$sub" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("Cannot run `git " + $sub + "` on " + $branch + " branch. Create a feature branch first.")
    }
  }'
fi

exit 0
