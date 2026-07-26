#!/usr/bin/env bash
# CI gate for the mechanically decidable rules in memory-sanitize.
#
# This script does NOT implement any rule. It invokes the rules that live in
# memory-sanitize/skills/memory-sanitize/scripts/rules-gate/, which is the
# single implementation. An earlier version of this file reimplemented the
# spacing check as a perl regex, which meant the same rule existed in three
# places and drifted immediately.
#
# Why only rules-gate/ and not scripts/rules/: the gate rules can be driven to
# zero without editorial judgement (delete a space, replace a character). The
# rules in scripts/rules/ cannot — no-english-word needs allow-list decisions
# or translation, no-em-dash-ja needs sentences rewritten. Running the full set
# here yields 146 findings on this repo, most of them English prose that is
# correct as written, so it could never be a pass/fail gate. Those rules stay
# agent-invoked through the skill.
#
# The text plugin is what lets textlint read .sh/.js/.py at all; without it
# textlint only handles Markdown and plain text. Rules cannot be selectively
# disabled through the config when --rulesdir is used (--rulesdir enables
# everything in the directory regardless), which is exactly why the split into
# two directories exists.
#
# Excluded paths:
#   - everything under session-tts/. Its tests and implementation comments
#     treat a Japanese full stop followed by a space as the subject under test,
#     asserting on it as expected output; normalizing them would change what
#     the tests assert.
#   - any tests/ directory. Rule test fixtures must contain the very pattern
#     the rule detects.
#
# These comments deliberately describe the forbidden sequences instead of
# quoting them. Under the text plugin a shell script is plain text, so there is
# no code node to exempt a quoted example, and any file that spells the pattern
# out reports itself.
set -euo pipefail
cd "$(dirname "$0")/.."

RULES_GATE="memory-sanitize/skills/memory-sanitize/scripts/rules-gate"
CONFIG="scripts/textlintrc.gate.json"

# mapfile is bash 4+; macOS ships bash 3.2, so build the array by splitting.
targets=($(git ls-files '*.md' '*.sh' '*.js' '*.py' \
  | grep -v '^session-tts/' | grep -v '/tests/'))

# A tracked file missing from the working tree must fail loudly rather than
# being skipped with a warning.
for f in "${targets[@]}"; do
  if [ ! -r "$f" ]; then
    echo "NG: tracked target is not readable (deleted?): $f" >&2
    exit 1
  fi
done

npx --yes \
  -p textlint@^15 \
  -p @textlint/textlint-plugin-text \
  textlint \
    --rulesdir "$RULES_GATE" \
    -c "$CONFIG" \
    "${targets[@]}"

echo "OK: gate rules clean (${#targets[@]} files)"
