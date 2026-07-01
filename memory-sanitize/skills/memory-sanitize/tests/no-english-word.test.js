// no-english-word 規則の振る舞いを textlint-tester で固定する。
//
// 起動: bash <SKILL_DIR>/scripts/test.sh  (npx 経由)
// 単体: node --test tests/no-english-word.test.js  (依存解決済みの場合)
//
// textlint-tester は global の describe/it/before/after を期待する Mocha 互換
// 設計。 node:test の同名 API を global に bind してそのまま起動する。

const nodeTest = require('node:test');
global.describe = nodeTest.describe;
global.it = nodeTest.it;
global.before = nodeTest.before;
global.after = nodeTest.after;
global.beforeEach = nodeTest.beforeEach;
global.afterEach = nodeTest.afterEach;

// ユーザー overlay (~/.config/memory-sanitize/) の影響を排除し、 スキル同梱の
// data/proper-nouns.txt + data/acronyms.txt のみが許可一覧として効くようにする。
// 作業ツリー内のパス (例: tests/__no_overlay__/) は誰かが同名ディレクトリを
// 作った瞬間にオーバーレイを誤って読み込むため、 プロセスごとに一意な空 dir を
// mkdtempSync で確保し、 そこを指す (= overlay 抑止を偶然ではなく構造的に保証)。
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
process.env.XDG_CONFIG_HOME = fs.mkdtempSync(
  path.join(os.tmpdir(), 'mem-san-test-no-overlay-')
);

const TextLintTester = require('textlint-tester').default || require('textlint-tester');
const rule = require('../scripts/rules/no-english-word.js');

const tester = new TextLintTester();

tester.run('no-english-word', rule, {
  valid: [
    // --- 純英語 Str ノードはルール対象外 ---
    { text: 'TypeScript and JavaScript are siblings.' },
    { text: 'Conventional Commits' },
    { text: 'pure english sentence without any cjk' },

    // --- 日本語のみは違反なし ---
    { text: 'これは日本語のみの文章です。' },

    // --- マスク対象 (構造的引用) ---
    { text: '[[entities/notion-sync]] を参照する。' },
    { text: 'ドキュメントは https://example.com/foo を見てください。' },
    { text: '設定は ~/.config/memory-sanitize/proper-nouns.txt に置く。' },
    { text: '相対パスは ./foo/bar や ../baz でも書ける。' },
    { text: 'リポジトリは lacolaco/dotfiles にある。' },
    { text: '設定ファイルは config.json または settings.yaml に書く。' },
    { text: 'バージョン v1.2.3 をリリースした。' },
    { text: '連絡先は dev@lacolaco.net です。' },
    { text: '詳細は L42 または L100-200 を参照。' },
    { text: 'チケットは PM-56 と LACO-2 で対応する。' },

    // --- 許可一覧 (スキル同梱) ---
    { text: 'HTML を生成する。' },
    { text: 'TypeScript と JavaScript を使う。' },
    { text: 'Conventional Commits 規約に従う。' },

    // --- バッククォート (textlint の Code ノードで自動除外) ---
    { text: '設定キーは `outputMode` を指定する。' },
    { text: 'コマンドは `git status` を叩く。' },

    // --- 数値開始のトークンは違反としない (v?\d ガード) ---
    { text: '使うのは v1 系のみ。' },
  ],
  invalid: [
    {
      text: '日本語の中にunknownな単語が混ざっている。',
      errors: [{ message: '英単語混入: "unknown"' }],
    },
    {
      text: '本文に foo および bar が混入する。',
      errors: [
        { message: '英単語混入: "foo"' },
        { message: '英単語混入: "bar"' },
      ],
    },
    {
      // phrase の構成単語が単独で出てきたら違反として扱う
      // (= "Conventional Commits" 全体は許可、 "Conventional" 単独は不許可)
      text: 'これは Conventional な書き方ではない。',
      errors: [{ message: '英単語混入: "Conventional"' }],
    },
  ],
});
