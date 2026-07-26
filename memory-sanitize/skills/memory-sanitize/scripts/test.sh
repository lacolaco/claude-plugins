#!/usr/bin/env bash
# memory-sanitize: 規則の自動テスト起動スクリプト
# textlint-tester + node:test (node --test) で tests/*.test.js を実行する。
#
# 使い方:
#   bash test.sh
#
# 設計:
#   - スキル配下に node_modules を持たない (check.sh と同じ非永続原則)
#   - 一時 dir に package.json を生成して npm install、NODE_PATH 経由で
#     require 解決。終了時に一時 dir を削除。
#   - 2 回目以降は npm のキャッシュ (~/.npm/_cacache/) が効くため高速。

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

shopt -s nullglob
TEST_FILES=("$SKILL_DIR"/tests/*.test.js)
shopt -u nullglob

if [[ ${#TEST_FILES[@]} -eq 0 ]]; then
  echo "ERROR: テストファイルが見つかりません ($SKILL_DIR/tests/*.test.js)" >&2
  exit 2
fi

echo "===================="
echo "Test target (${#TEST_FILES[@]} files):"
for f in "${TEST_FILES[@]}"; do
  echo "  $f"
done
echo "===================="

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/memory-sanitize-test.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

cat > "$TMP_DIR/package.json" <<'JSON'
{
  "name": "memory-sanitize-test-deps",
  "private": true,
  "dependencies": {
    "textlint-tester": "^15"
  }
}
JSON

(cd "$TMP_DIR" && npm install --silent --no-fund --no-audit --no-progress) >/dev/null

NODE_PATH="$TMP_DIR/node_modules" node --test "${TEST_FILES[@]}"
