// no-space-after-ja-punctuation 規則の振る舞いを textlint-tester で固定する。
//
// 起動: bash <SKILL_DIR>/scripts/test.sh (npx 経由)
// 単体: node --test tests/no-space-after-ja-punctuation.test.js (依存解決済みの場合)
//
// 検出方針: 英文の「ピリオドの後は 1 スペース」を日本語に持ち込んだ空白のうち、
// 句読点直後だけを見る。全角語どうしの間は公開 rule
// ja-no-space-between-full-width、閉じ括弧の直後は公開 rule
// ja-no-space-around-parentheses が担うため本規則の対象外とする。

const nodeTest = require('node:test');
global.describe = nodeTest.describe;
global.it = nodeTest.it;
global.before = nodeTest.before;
global.after = nodeTest.after;
global.beforeEach = nodeTest.beforeEach;
global.afterEach = nodeTest.afterEach;

const TextLintTester = require('textlint-tester').default || require('textlint-tester');
const rule = require('../scripts/rules-gate/no-space-after-ja-punctuation.js');

const tester = new TextLintTester();

tester.run('no-space-after-ja-punctuation', rule, {
  valid: [
    // --- 空白のない日本語 ---
    { text: '着手前に前提を明示せよ。複数の解釈があるなら示せ。' },
    { text: '隣接コードとそのスタイルは、依頼と無関係な改善をせず保て。' },

    // --- 日本語と ASCII の間の空白は正しい組版 ---
    { text: '削除してよいのは不要になった import と関数のみ。' },
    { text: 'PR 作成成功時だけでなく、CI 失敗で停止した時も通知する。' },

    // --- 半角の閉じ括弧は対象外。英語テンプレートの [] を拾わないため ---
    { text: '**Issue**: [Description] の形式で書く。' },
    { text: '関数 fn(x) を呼ぶ。' },

    // --- 行末の句点 ---
    { text: '検証が通るまでループせよ。' },

    // --- 他 rule の担当範囲は本規則では検出しない ---
    { text: '手順は エージェントスキルに書け。' },

    // --- バッククォート内コードは Code ノードなので対象外 ---
    { text: 'リテラル `A。 B` を本文で言及することは許容する。' },

    // --- 英文のみの段落 ---
    { text: 'This is English prose. It keeps normal spacing.' },
  ],
  invalid: [
    {
      // 全角の閉じ括弧の直後。公開 rule では埋まらない範囲
      text: '「結論から」 は結論だけではない。',
      errors: [{ message: '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる' }],
    },
    {
      // 全角の丸括弧の閉じも対象。半角 ) は対象外なので全角で書く
      text: '前提（省略可） を示せ。',
      errors: [{ message: '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる' }],
    },
    {
      // 句点直後の空白
      text: '前提を明示せよ。 複数の解釈があるなら示せ。',
      errors: [{
        message: '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる',
      }],
    },
    {
      // 読点直後の空白
      text: '隣接コードは、 依頼と無関係な改善をせず保て。',
      errors: [{
        message: '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる',
      }],
    },
    {
      // 後続が ASCII でも検出する。公開 rule では埋まらない範囲
      text: 'グルーピングしない。 Agent View の制約に合わせた。',
      errors: [{
        message: '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる',
      }],
    },
    {
      // 1 文に複数箇所
      text: '前提を示せ。 解釈を示せ、 そして進めよ。',
      errors: [
        { message: '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる' },
        { message: '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる' },
      ],
    },
    {
      // 連続した空白もまとめて 1 件として報告する
      text: '前提を示せ。   複数の解釈がある。',
      errors: [{
        message: '原則として、全角の約物の直後に半角スペースを入れません: 英文の書式を日本語に持ち込んでいる',
      }],
    },
  ],
});
