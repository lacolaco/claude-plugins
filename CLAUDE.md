# claude-plugins

## Language

This is an English-language OSS project. All content — code, documentation, commit messages, PR descriptions, and plugin skill definitions — must be written in English. When porting content from non-English sources, translate it as part of the extraction process.

## Plugin Change Checklist

When modifying a plugin's behavior, update ALL of the following in the same commit:

- `{plugin}/scripts/*.sh` or other code files
- `{plugin}/.claude-plugin/plugin.json` (bump version, update description)
- `.claude-plugin/marketplace.json` (mirror version and description)
- `README.md`: plugin table row, overview, "How it works", "Configuration", and any other references
- Grep the repo for hardcoded values related to the change (branch names, defaults, etc.) and update every occurrence

## Hook Script Conventions

When writing a Claude Code hook script (`{plugin}/scripts/*.sh` referenced from `hooks.json`):

- Confirm the hook input schema (`cwd`, `tool_name`, `tool_input.*`, `session_id`, hook-event-specific fields) before designing the script.
- Read stdin once into a variable, then run multiple `jq` queries via `printf '%s' "$input" | jq ...`. Never let `jq` consume stdin directly when more than one field may be needed now or later.
- Resolve repo state with `git -C "$cwd"` using the `cwd` field from hook input, not the script's inherited cwd.
- Implement matching logic inside the script (branch on `tool_name`, inspect `tool_input.command`, etc.). Conditional fields like `if:` on hook entries are not honored by Claude Code.

## Treat Plugin Behavior Changes as Breaking Changes

A `protect-main-branch` (or any other plugin) hook is a published API consumed by every install. Before changing what a hook accepts, denies, or no-ops on:

- Surface the contract options (what should be allowed / denied) via `AskUserQuestion` before implementing, instead of patching the immediate symptom.
- Bump the major version when the set of allowed/denied operations changes. Document the removed behavior in the commit message under `BREAKING CHANGE:`.
