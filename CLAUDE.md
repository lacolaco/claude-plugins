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

## Plugin Testing

"Tests pass" is a strict statement. It means **the production path was executed**, not that syntax checks succeeded.

- **Production path** for plugin behavior: invoke `claude --plugin-dir <plugin-source>` (see `claude --help`). Both `claude -p` non-interactive and interactive sessions count. Hooks and adapter scripts run exactly as they will for installed users.
- **Sanity checks** (NOT tests): `jq -e .` on JSON, `bash -n` on shell scripts, `python -c "ast.parse(...)"`, piping simulated stdin into a script. These prove syntax and shape. They do not prove behavior. Never declare "tests pass" based on these alone.
- Before declaring a fix verified, define what production-path execution proves the fix. For concurrency / cross-session bugs: spawn at least 2 concurrent `claude --plugin-dir` subprocesses with distinct prompts and verify both exit codes plus the observable side effect (e.g. per-session pidfile coexistence, no SIGTERM = exit 143).
- Never hot-patch `~/.claude/plugins/cache/<plugin>/<version>/` to test a change. The cache is a deployment artifact, not a development surface — `--plugin-dir` is the canonical mechanism.

## Design Documentation

When summarizing code in `DESIGN.md` / `README.md` / equivalent:

- Separate observed from inferred. Code reading reveals **what the code does**, not **why**. Words like "intentional", "by design", "to ensure X" are inferences and require evidence beyond code reading (commit message, original design doc, author confirmation). If the evidence is absent, write "the code currently does X" — make no intent claim.
- Before submitting, scan internal consistency: each goal/constraint in the document's opening section must be enforced by the behaviors described later. List each goal, find the section that secures it. Contradictions (e.g. "concurrent sessions distinguishable by ear" vs "global single-flight cancels other sessions") indicate either a doc bug or a code bug — surface it, do not paper it over with prose.

## Treat Plugin Behavior Changes as Breaking Changes

A `protect-main-branch` (or any other plugin) hook is a published API consumed by every install. Before changing what a hook accepts, denies, or no-ops on:

- Surface the contract options (what should be allowed / denied) via `AskUserQuestion` before implementing, instead of patching the immediate symptom.
- Bump the major version when the set of allowed/denied operations changes. Document the removed behavior in the commit message under `BREAKING CHANGE:`.
