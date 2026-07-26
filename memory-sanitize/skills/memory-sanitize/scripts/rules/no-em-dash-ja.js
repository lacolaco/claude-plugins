// memory-sanitize 独自 rule: 日本語の地の文・見出しでダッシュ類を禁止する
//
// 検出パターン (textlint の Str ノード本文):
//   - em dash `—` (U+2014)
//   - horizontal bar `―` (U+2015)
//   - 2倍ダッシュ `——` (em dash 2 連)
//
// 除外:
//   - en dash `–` (U+2013) は範囲表記として許容
//   - 純英語の Str ノード (日本語文字を含まない) は対象外
//     例: "Curry–Howard correspondence" や、英語の地の文中の em dash
//   - バッククォート内コード・コードブロック (textlint の Code/CodeBlock ノードで自動除外)

// 日本語文字 (ひらがな・カタカナ・漢字) を含むかを判定するパターン。
// 純英語の文 (例: 英語複合語 Curry–Howard、英文中の em dash) を救うために
// 「日本語文字を 1 文字でも含む Str ノード」のみを検査対象とする。
const HAS_JA_RE = /[぀-ゟ゠-ヿ一-鿿]/;

// 2倍ダッシュ (em dash 2 連) と単発の em dash / horizontal bar を走査する。
// 2倍ダッシュを先に検出して位置を記録し、単発走査では記録済み位置をスキップする。
const DOUBLE_RE = /——/g;
const SINGLE_RE = /[—―]/g;

module.exports = function (context) {
  const { Syntax, RuleError, report, locator, getSource } = context;
  return {
    [Syntax.Str](node) {
      const raw = getSource(node);

      if (!HAS_JA_RE.test(raw)) {
        return;
      }

      const consumed = new Set();

      DOUBLE_RE.lastIndex = 0;
      let m;
      while ((m = DOUBLE_RE.exec(raw)) !== null) {
        for (let i = m.index; i < m.index + 2; i++) consumed.add(i);
        report(
          node,
          new RuleError('禁止構文: 2倍ダッシュ "——" を日本語の地の文・見出しで使わない', {
            padding: locator.range([m.index, m.index + 2]),
          })
        );
      }

      SINGLE_RE.lastIndex = 0;
      while ((m = SINGLE_RE.exec(raw)) !== null) {
        if (consumed.has(m.index)) continue;
        const ch = m[0];
        const label = ch === '—' ? '"—" (U+2014)' : '"―" (U+2015)';
        report(
          node,
          new RuleError(`禁止構文: ダッシュ ${label} を日本語の地の文・見出しで使わない`, {
            padding: locator.range([m.index, m.index + 1]),
          })
        );
      }
    },
  };
};
