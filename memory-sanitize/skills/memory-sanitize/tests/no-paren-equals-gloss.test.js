// no-paren-equals-gloss 規則の振る舞いを textlint-tester で固定する。
//
// 起動: bash <SKILL_DIR>/scripts/test.sh  (npx 経由)
// 単体: node --test tests/no-paren-equals-gloss.test.js  (依存解決済みの場合)

const nodeTest = require('node:test');
global.describe = nodeTest.describe;
global.it = nodeTest.it;
global.before = nodeTest.before;
global.after = nodeTest.after;
global.beforeEach = nodeTest.beforeEach;
global.afterEach = nodeTest.afterEach;

const TextLintTester = require('textlint-tester').default || require('textlint-tester');
const rule = require('../scripts/rules/no-paren-equals-gloss.js');

const tester = new TextLintTester();

tester.run('no-paren-equals-gloss', rule, {
  valid: [
    // --- 普通の括弧 (等号を含まない) は許容 ---
    { text: '本文中の補足 (= ではないただの括弧書き) は通る。'.replace('(= ', '(') },
    { text: '英単語混入なら日本語化するという方針です。' },
    { text: '半角括弧そのものは禁止していない (補足は許可)。' },
    { text: '括弧内に等号を含まない (例えば: 説明) なら通る。' },

    // --- バッククォート内は Code ノードで自動除外 ---
    { text: 'リテラル `(=` を本文で言及することは許容する。' },
    { text: 'コード片の `if (= true)` を例示する。' },

    // --- 全角の `（＝` は本 rule の対象外 ---
    { text: '全角括弧の中に全角等号を入れた例 （＝ 全角形) は本 rule では検出しない。'.replace(/\)/, '）') },

    // --- 等号が括弧の直後でない場合 (空白挟みなど) は対象外 ---
    { text: '括弧の中に空白を挟んで等号を置いた ( = 例) は対象外。' },
  ],
  invalid: [
    {
      text: 'これは違反例 (= 括弧内同格挿入) を含む文章である。',
      errors: [{ message: '禁止構文: 半角括弧直後の等号 — 括弧内同格挿入は使わない' }],
    },
    {
      text: '一文に複数回出現する (= 一つ目) し、 さらにここでも (= 二つ目) 出る。',
      errors: [
        { message: '禁止構文: 半角括弧直後の等号 — 括弧内同格挿入は使わない' },
        { message: '禁止構文: 半角括弧直後の等号 — 括弧内同格挿入は使わない' },
      ],
    },
    {
      text: '日本語の途中に(=隙間なし)でも検出される。',
      errors: [{ message: '禁止構文: 半角括弧直後の等号 — 括弧内同格挿入は使わない' }],
    },
  ],
});
