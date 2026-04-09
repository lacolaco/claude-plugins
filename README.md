# claude-plugins

Claude Code plugins by lacolaco.

## Plugins

| Plugin | Description |
|--------|-------------|
| [protect-main-branch](./protect-main-branch) | Prevent direct edits and pushes to the main branch |
| [session-handover](./session-handover) | Session handover/takeover for task continuity between sessions |

## protect-main-branch

Blocks Write, Edit, and `git push` operations when on the main branch in Claude Code.

### How it works

- On any branch other than `main`: no-op (all operations allowed)
- On `main` branch:
  - **Write/Edit**: Blocks editing tracked (non-gitignored) files within the repository
  - **Bash**: Blocks `git push` commands
  - Editing gitignored files is always allowed
  - Editing files outside the repository is always allowed

When blocked, the hook returns:

```
Cannot edit/push on main branch. Create a feature branch first.
```

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install protect-main-branch@lacolaco-plugins
```

### Prerequisites

- `jq` must be installed

## session-handover

Provides two paired skills for managing task continuity between Claude Code sessions:

- **`/handover`** - Creates or updates a structured handover document (`task.local.md`) at session end, capturing goals, current state, tasks, facts, hypotheses, issues, and next actions
- **`/takeover`** - Resumes work from a handover document at session start, with a rigorous 3-phase process: read, externalize tasks, then verify and execute

### How it works

When ending a session, invoke `/handover` to generate a structured Markdown document that captures the current state of work. When starting a new session, invoke `/takeover` to read that document and resume work with full context.

The takeover skill enforces a disciplined approach: it reads the handover document, externalizes all tasks using Claude Code's task tools, and only then begins verification and execution. It treats all claims from the previous session as hypotheses until verified.

### Installation

```
/plugin marketplace add lacolaco/claude-plugins
/plugin install session-handover@lacolaco-plugins
```

## License

MIT
