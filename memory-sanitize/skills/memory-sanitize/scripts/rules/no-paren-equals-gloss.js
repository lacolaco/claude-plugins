// memory-sanitize 独自 rule: 括弧内同格挿入の `(` + `=` 構文を完全禁止する
//
// 検出パターン: textlint の Str ノード本文中の半角開き括弧 `(` 直後に等号 `=` が
// 続く連鎖。 「X (= Y)」 のような括弧内同格挿入で、 本文の論述リズムを断ち切る
// 注釈様式を本ワークスペースの永続層では使わない方針。
//
// 検出範囲:
//   - textlint の Str ノードに出現する `(=` リテラル
//
// 除外:
//   - バッククォート内コード・コードブロック (textlint の Code/CodeBlock ノードで自動除外)
//   - 半角括弧以外の様式 (全角 `（＝` 等) は本 rule の対象外
//     (= 必要なら別 rule として追加する。 現状の運用焦点は半角形)

const PAREN_EQ_RE = /\(=/g;

module.exports = function (context) {
  const { Syntax, RuleError, report, locator, getSource } = context;
  return {
    [Syntax.Str](node) {
      const raw = getSource(node);
      PAREN_EQ_RE.lastIndex = 0;
      let m;
      while ((m = PAREN_EQ_RE.exec(raw)) !== null) {
        report(
          node,
          new RuleError('禁止構文: 半角括弧直後の等号 — 括弧内同格挿入は使わない', {
            padding: locator.range([m.index, m.index + 2]),
          })
        );
      }
    },
  };
};
