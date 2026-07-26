// no-heading-separator 規則の振る舞いを textlint-tester で固定する。
//
// 起動: bash <SKILL_DIR>/scripts/test.sh  (npx 経由)
// 単体: node --test tests/no-heading-separator.test.js  (依存解決済みの場合)
//
// 検出方針: 見出し (`Header` ノード) に区切り線 `─` (U+2500、罫線) を含めない。
// 「種別──主題」「主題──概念」のような二要素詰め込みは禁止し、単一の
// 自然な句にする。em ダッシュなどの他ダッシュ類は no-em-dash-ja 規則で
// 本文と見出しの両方を網羅するため、本規則の対象外。

const nodeTest = require('node:test');
global.describe = nodeTest.describe;
global.it = nodeTest.it;
global.before = nodeTest.before;
global.after = nodeTest.after;
global.beforeEach = nodeTest.beforeEach;
global.afterEach = nodeTest.afterEach;

const TextLintTester = require('textlint-tester').default || require('textlint-tester');
const rule = require('../scripts/rules/no-heading-separator.js');

const tester = new TextLintTester();

tester.run('no-heading-separator', rule, {
  valid: [
    // --- 単一の句の見出し ---
    { text: '# 単純な見出し\n\n本文。' },
    { text: '## 助詞でつなぐ見出し\n\n本文。' },
    { text: '### 読点で、 つなぐ見出し\n\n本文。' },
    { text: '## 「同値関係としての分類」\n\n本文。' },

    // --- 本文中に `─` が出現しても見出し以外なので対象外 ---
    { text: '## 普通の見出し\n\n本文に ─ が出ても見出し規則の対象外。' },

    // --- バッククォート内の `─` リテラル言及 (Code ノード) は対象外 ---
    { text: '## 区切り線について\n\nリテラル `─` を本文で言及することは許容する。' },
  ],
  invalid: [
    {
      text: '## 種別──主題\n\n本文。',
      errors: [{
        message: '禁止構文: 見出しに区切り線 "──" (U+2500) を含めない: 単一の自然な句にする',
      }],
    },
    {
      // 単独の `─` も検出
      text: '### 主題─概念\n\n本文。',
      errors: [{
        message: '禁止構文: 見出しに区切り線 "─" (U+2500) を含めない: 単一の自然な句にする',
      }],
    },
    {
      // 一つの見出しに複数の区切り線
      text: '## 種別──主題─補足\n\n本文。',
      errors: [
        { message: '禁止構文: 見出しに区切り線 "──" (U+2500) を含めない: 単一の自然な句にする' },
        { message: '禁止構文: 見出しに区切り線 "─" (U+2500) を含めない: 単一の自然な句にする' },
      ],
    },
  ],
});
