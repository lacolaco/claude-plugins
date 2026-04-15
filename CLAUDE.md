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
