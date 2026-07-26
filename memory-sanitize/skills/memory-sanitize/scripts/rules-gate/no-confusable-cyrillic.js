// memory-sanitize 独自 rule: キリル文字の同形文字混入を検出する
//
// 生成時に「同形文字滑り」が起きる。ラテン文字の a c e o p x y H K M T などと
// 字形が同じキリル文字 (U+0400-U+04FF) が、見た目そのままで混ざる。読んでも
// 気づけず、コマンド名や識別子に混ざれば動かない。
//
// 検出範囲:
//   - Str ノード (地の文)
//   - Code / CodeBlock ノード
//     散文だけを見る他の rule と違い、コードも対象にする。バッククォート内に
//     混ざったキリル文字は、散文に混ざったものより危険で、実行して初めて
//     気づくため。旧来この検査を担っていたシェルスクリプトは生の行を grep
//     していたので、Str だけに絞ると検出力が落ちる。
//
// 対象をキリル文字だけに絞る理由:
//   - ギリシャ文字も同形文字の供給源だが、技術文書では λ μ π Ω などが正当に
//     使われる。混ぜると誤検知になる
//   - 日本語・英語の技術文書にキリル文字が正当に現れることは事実上ない
//
// 経緯:
//   - 2026-07-19 に作者のグローバル規範へキリル文字が混入した実績がある。
//     当時は claude-settings の scripts/check-norms.sh が perl で検査して
//     いたが、同じ規則をリポジトリごとに書くのをやめてここへ移した

const CYRILLIC_RE = /\p{Script=Cyrillic}+/gu;

module.exports = function (context) {
  const { Syntax, RuleError, report, locator, getSource } = context;

  function scan(node) {
    const raw = getSource(node);
    CYRILLIC_RE.lastIndex = 0;
    let m;
    while ((m = CYRILLIC_RE.exec(raw)) !== null) {
      const chars = [...m[0]]
        .map((c) => `U+${c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')}`)
        .join(' ');
      report(
        node,
        new RuleError(
          `異スクリプト文字の混入: "${m[0]}" (${chars}) はキリル文字。ラテン文字と字形が同じため見た目では気づけない`,
          { padding: locator.range([m.index, m.index + m[0].length]) }
        )
      );
    }
  }

  return {
    [Syntax.Str](node) {
      scan(node);
    },
    [Syntax.Code](node) {
      scan(node);
    },
    [Syntax.CodeBlock](node) {
      scan(node);
    },
  };
};
