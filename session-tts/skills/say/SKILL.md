---
description: Speak a Japanese phrase aloud in the current session's voice as a verbal task-progress report during autonomous, multi-step work. Use at task transitions (finishing one and starting the next), when hitting a problem, on an important finding, or when changing direction. Goes through the same audio engine as the Stop-hook narration. No-op when TTS is silenced for this session.
---

# session-tts:say

Run the following Bash command with a Japanese phrase as the argument.

```
bash "${CLAUDE_PLUGIN_ROOT}/skills/say/say.sh" "<text>"
```

Constraints:

- Keep `<text>` under ~100 Japanese characters.
- One phrase per invocation; do not batch multiple sentences.
- Report at task milestones (transition / problem / finding / pivot), not at
  every tool call.
- **Always begin with a brief lead-in phrase (枕詞)** that signals the kind
  of update before the body — e.g. 「報告です。」「問題発生です。」「発見です。」
  「方針転換です。」 — so the listener has time to orient before the content
  starts.
- Do not use this for the final response of a turn — the Stop hook reads the
  final assistant message automatically.
