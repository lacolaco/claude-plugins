#!/usr/bin/env bash
# memory-sanitize: 検査の入口スクリプト
# textlint 既存規則 + 独自規則 (scripts/rules/ 配下) を 1 系統で起動
# npx で textlint と関連プラグインを都度取得実行 (= 永続インストール不要)
#
# 使い方:
#   bash check.sh <target-file> [<target-file> ...]
#
# 検査対象は引数で必ず指定。既定経路は持たない (= スキルの可搬性)。
# 対象判定はエージェントが SKILL.md の手順に従って行う。

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -eq 0 ]]; then
  cat >&2 <<'EOF'
ERROR: 検査対象ファイルが指定されていません

使い方:
  bash check.sh <target-file> [<target-file> ...]

スキルは既定経路を持ちません。検査対象はエージェントが自分の実行環境から判断し、
明示的に引数で渡してください (SKILL.md の「検査対象の決定はエージェントの責務」節参照)。
EOF
  exit 2
fi

TARGETS=("$@")

echo "===================="
echo "Targets (${#TARGETS[@]} files):"
for t in "${TARGETS[@]}"; do
  echo "  $t"
done
echo "===================="

# textlint 既存 rule + 独自 rule (scripts/rules/) を 1 回の実行で適用
# - 既存 rule: writing-style と整合する文体・品質規則を `--rule` で個別に有効化
# - 独自 rule: `--rulesdir` で scripts/rules/ を読み込ませる
# - `--no-textlintrc` でユーザー環境の .textlintrc を遮断し再現性を確保
npx --yes \
  -p textlint@^15 \
  -p textlint-rule-no-mix-dearu-desumasu \
  -p textlint-rule-ja-no-mixed-period \
  -p textlint-rule-ja-no-redundant-expression \
  -p textlint-rule-ja-no-successive-word \
  -p textlint-rule-ja-no-abusage \
  -p textlint-rule-no-doubled-conjunctive-particle-ga \
  -p textlint-rule-no-doubled-joshi \
  -p textlint-rule-no-doubled-conjunction \
  -p textlint-rule-no-double-negative-ja \
  -p textlint-rule-no-dropping-the-ra \
  -p textlint-rule-no-hankaku-kana \
  -p textlint-rule-no-mixed-zenkaku-and-hankaku-alphabet \
  -p textlint-rule-ja-no-space-between-full-width \
  textlint \
    --rule no-mix-dearu-desumasu \
    --rule ja-no-mixed-period \
    --rule ja-no-redundant-expression \
    --rule ja-no-successive-word \
    --rule ja-no-abusage \
    --rule no-doubled-conjunctive-particle-ga \
    --rule no-doubled-joshi \
    --rule no-doubled-conjunction \
    --rule no-double-negative-ja \
    --rule no-dropping-the-ra \
    --rule no-hankaku-kana \
    --rule no-mixed-zenkaku-and-hankaku-alphabet \
    --rule ja-no-space-between-full-width \
    --rulesdir "$SKILL_DIR/scripts/rules" \
    --rulesdir "$SKILL_DIR/scripts/rules-gate" \
    --no-textlintrc \
    "${TARGETS[@]}"
