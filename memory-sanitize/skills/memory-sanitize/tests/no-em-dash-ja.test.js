// no-em-dash-ja 規則の振る舞いを textlint-tester で固定する。
//
// 起動: bash <SKILL_DIR>/scripts/test.sh  (npx 経由)
// 単体: node --test tests/no-em-dash-ja.test.js  (依存解決済みの場合)
//
// 検出方針: 日本語の地の文・見出しで em dash `—` (U+2014)、horizontal bar `―`
// (U+2015)、2倍ダッシュ `——` を使うのを禁ずる。en dash `–` (U+2013) は
// 範囲表記として許容、純英語テキスト内の英語複合語 (Curry–Howard など) は
// 対象外。コードブロック・バッククォート内は textlint 標準で自動除外。

const nodeTest = require('node:test');
global.describe = nodeTest.describe;
global.it = nodeTest.it;
global.before = nodeTest.before;
global.after = nodeTest.after;
global.beforeEach = nodeTest.beforeEach;
global.afterEach = nodeTest.afterEach;

const TextLintTester = require('textlint-tester').default || require('textlint-tester');
const rule = require('../scripts/rules/no-em-dash-ja.js');

const tester = new TextLintTester();

tester.run('no-em-dash-ja', rule, {
  valid: [
    // --- 日本語のみで em dash を含まない ---
    { text: 'これは普通の日本語文章です。' },
    { text: '読点で区切る、 句点で区切る。 これだけで十分。' },

    // --- en dash は範囲表記として許容 ---
    { text: '範囲を 2020–2025 のように en dash で書く。' },

    // --- 純英語テキスト内の em dash や英語複合語は対象外 ---
    { text: 'See the Curry–Howard correspondence.' },
    { text: 'This is an English sentence — with em dash — and continues.' },

    // --- バッククォート内 (Code ノード) は除外 ---
    { text: 'リテラル `—` を本文で言及することは許容する。' },
    { text: '記号 `―` をコード片として扱う。' },

    // --- ハイフン (短) は対象外 ---
    { text: '通常のハイフン - を含む文。' },
  ],
  invalid: [
    {
      // em dash (U+2014)
      text: '日本語の地の文に — を入れるのは禁止する。',
      errors: [{ message: '禁止構文: ダッシュ "—" (U+2014) を日本語の地の文・見出しで使わない' }],
    },
    {
      // horizontal bar (U+2015)
      text: '日本語の文章に ― を混入する。',
      errors: [{ message: '禁止構文: ダッシュ "―" (U+2015) を日本語の地の文・見出しで使わない' }],
    },
    {
      // 2倍ダッシュ (U+2014 を 2 つ並べた)
      text: '同格挿入を A——挿入——B のように書かない。',
      errors: [
        { message: '禁止構文: 2倍ダッシュ "——" を日本語の地の文・見出しで使わない' },
        { message: '禁止構文: 2倍ダッシュ "——" を日本語の地の文・見出しで使わない' },
      ],
    },
    {
      // 一文に em dash と horizontal bar の両方が混入
      text: 'これは — と ― を混在させた悪い例。',
      errors: [
        { message: '禁止構文: ダッシュ "—" (U+2014) を日本語の地の文・見出しで使わない' },
        { message: '禁止構文: ダッシュ "―" (U+2015) を日本語の地の文・見出しで使わない' },
      ],
    },
  ],
});
