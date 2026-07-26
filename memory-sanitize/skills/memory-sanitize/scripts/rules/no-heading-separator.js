// memory-sanitize 独自 rule: 見出しに区切り線 `─` (U+2500) を含めない
//
// 検出パターン (textlint の Header ノード本文):
//   - 罫線文字 `─` (U+2500、box drawings light horizontal)
//   - 連続した `──` (二要素を「種別──主題」のように詰め込む様式)
//
// 除外:
//   - 本文中 (= Header 以外) の `─` 出現は本規則の対象外
//     (= 表罫線・装飾線等は別の文脈で議論する)
//   - バッククォート内コード・コードブロック (textlint の Code/CodeBlock ノードで自動除外)
//
// 補足:
//   - em ダッシュ等の他ダッシュ類は no-em-dash-ja 規則が本文と見出しの両方を
//     網羅するため、本規則の検出対象は U+2500 系のみとする
//   - tech-writing 規範 20 行目を機械化したもの。見出しは単一の自然な句にする

const SEPARATOR_RE = /─+/g;

module.exports = function (context) {
  const { Syntax, RuleError, report, locator, getSource } = context;
  return {
    [Syntax.Header](node) {
      const raw = getSource(node);
      SEPARATOR_RE.lastIndex = 0;
      let m;
      while ((m = SEPARATOR_RE.exec(raw)) !== null) {
        const matched = m[0];
        report(
          node,
          new RuleError(
            `禁止構文: 見出しに区切り線 "${matched}" (U+2500) を含めない: 単一の自然な句にする`,
            { padding: locator.range([m.index, m.index + matched.length]) }
          )
        );
      }
    },
  };
};
