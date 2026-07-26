// no-confusable-cyrillic 規則の振る舞いを textlint-tester で固定する。
//
// 起動: bash <SKILL_DIR>/scripts/test.sh (npx 経由)
// 単体: node --test tests/no-confusable-cyrillic.test.js (依存解決済みの場合)
//
// 検出方針: 生成時の同形文字滑りで混ざるキリル文字 (U+0400-U+04FF) を検出する。
// 他の rule と違いバッククォート内コードとコードブロックも対象にする。コードに
// 混ざったキリル文字は実行して初めて気づくため、散文より危険である。
// ギリシャ文字は技術文書で正当に使われるので対象にしない。

const nodeTest = require('node:test');
global.describe = nodeTest.describe;
global.it = nodeTest.it;
global.before = nodeTest.before;
global.after = nodeTest.after;
global.beforeEach = nodeTest.beforeEach;
global.afterEach = nodeTest.afterEach;

const TextLintTester = require('textlint-tester').default || require('textlint-tester');
const rule = require('../scripts/rules-gate/no-confusable-cyrillic.js');

const tester = new TextLintTester();

tester.run('no-confusable-cyrillic', rule, {
  valid: [
    // --- 純粋な日本語 ---
    { text: '着手前に前提を明示せよ。' },

    // --- ラテン文字は当然許容 ---
    { text: 'PR 作成時に scripts/check.sh を実行する。' },
    { text: 'コマンドは `git status` を使う。' },

    // --- ギリシャ文字は技術文書で正当に使われるので対象外 ---
    { text: '時間計算量は O(n) で、係数を λ とする。' },
    { text: '単位は μs で測る。' },
  ],
  invalid: [
    {
      // 地の文に混ざったキリル文字 а (U+0430)
      text: 'キリルの а が混ざっている。',
      errors: [{
        message: '異スクリプト文字の混入: "а" (U+0430) はキリル文字。ラテン文字と字形が同じため見た目では気づけない',
      }],
    },
    {
      // バッククォート内コードも対象にする。実行して初めて気づくため
      text: 'コマンド `gіt status` を実行する。',
      errors: [{
        message: '異スクリプト文字の混入: "і" (U+0456) はキリル文字。ラテン文字と字形が同じため見た目では気づけない',
      }],
    },
    {
      // コードブロックも対象
      text: '```\nсd /tmp\n```',
      errors: [{
        message: '異スクリプト文字の混入: "с" (U+0441) はキリル文字。ラテン文字と字形が同じため見た目では気づけない',
      }],
    },
    {
      // 連続したキリル文字は 1 件としてまとめて報告する
      text: 'これは абв という並び。',
      errors: [{
        message: '異スクリプト文字の混入: "абв" (U+0430 U+0431 U+0432) はキリル文字。ラテン文字と字形が同じため見た目では気づけない',
      }],
    },
  ],
});
