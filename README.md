# claude-plugins

Claude Code plugins by lacolaco.

## Plugins

| Plugin | Description |
|--------|-------------|
| [protect-main-branch](./protect-main-branch) | Prevent direct edits and pushes to the main branch |

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

## License

MIT
