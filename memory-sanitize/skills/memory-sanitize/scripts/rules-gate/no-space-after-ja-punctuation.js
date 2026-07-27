// memory-sanitize 独自 rule: 全角の約物の直後に半角スペースを入れない
//
// 検出パターン (textlint の Str ノード本文):
//   - 読点 U+3001 または句点 U+3002 の直後の半角スペース (後続が全角でも
//     ASCII でも検出する)
//   - 全角の閉じ括弧 `」』）〉》】〕｝］”’〟` の直後の半角スペース
//
// 除外:
//   - バッククォート内コード・コードブロック (textlint の Code/CodeBlock
//     ノードで自動除外)
//   - 全角スペース U+3000 は別の論点なので扱わない
//
// この規則の範囲を句読点だけに絞っている理由:
//   - 全角語どうしの間のスペースは公開 rule ja-no-space-between-full-width が
//     担う。あちらはカタカナどうしを複合語として除外する言語的判断を含み、
//     自前で書き直すと劣化する
//   - かっこ類を見る公開 rule ja-no-space-around-parentheses は採用しない。
//     オプションを一切持たず、英語テンプレートの半角 [] を括弧として拾うため
//     日英混在ファイルで誤検知が避けられない (作者の環境で 15 件中 10 件)。
//     そのぶんの穴をここで埋める。対象を全角の閉じ括弧に限れば半角 [] を
//     拾わないので、あちらの誤検知は原理的に起こらない
//   - 結果、公開 rule で埋まらないのは句読点直後だけ。rule 群には
//     ja-space-after-exclamation と ja-space-after-question はあるが、
//     句読点版が無い。ここがその穴を埋める
//
// 補足:
//   - 英文の「ピリオドの後は 1 スペース」を日本語に持ち込んだ書式である。
//     一度混ざると以後の書き手が隣接様式として模倣し増殖する。2026-07-26 に
//     このプラグイン自身の SKILL.md から 188 箇所、作者のグローバル規範から
//     149 箇所が検出され、そのうち 132 箇所が句読点直後だった

// 全角の閉じ括弧。開き括弧の前は Markdown のリスト記号や引用記号と紛れるので
// 見ない (素朴な照合では `- 「` を 13 件中 11 件の割合で誤検知した)。
const AFTER_PUNCT_RE = /[。、」』）〉》】〕｝］”’〟] +/g;

module.exports = function (context) {
  const { Syntax, RuleError, report, locator, getSource } = context;
  return {
    [Syntax.Str](node) {
      const raw = getSource(node);
      AFTER_PUNCT_RE.lastIndex = 0;
      let m;
      while ((m = AFTER_PUNCT_RE.exec(raw)) !== null) {
        report(
          node,
          new RuleError(
            '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる',
            { padding: locator.range([m.index, m.index + m[0].length]) }
          )
        );
      }
    },
  };
};
