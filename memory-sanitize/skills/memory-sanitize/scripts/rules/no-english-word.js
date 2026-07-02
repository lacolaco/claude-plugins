// memory-sanitize 独自 rule: 日本語文中の英単語混入を検出する
//
// 検出範囲: 日本語文字 (ひらがな・カタカナ・漢字) を含む textlint Str ノードに
//          出現する連続英字 (2 文字以上)。 純英語の Str ノード (= 日本語文字を
//          1 文字も含まないテキスト) はルールの目的 (混在検出) の対象外として
//          スキップする。
// 除外:
//   - 純英語テキスト (= 見出し中のスラッグ単独行・英文引用・コード片等)
//   - 許可一覧 (data/proper-nouns.json・data/acronyms.json と XDG 上の overlay)
//   - URL・ファイル経路・バージョン記法・拡張子付きファイル名・[[wikilink]]・環境変数名 (regex で mask)
//   - バッククォート内コード・コードブロック (textlint の Code/CodeBlock ノードで自動除外)

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// 許可一覧の読み込み元 (= スキル同梱の default と、 ユーザー固有の overlay を merge)
//   1. スキル同梱 default: <SKILL_DIR>/data/{proper-nouns,acronyms}.json
//      (= 普遍的に固有名詞・略語として確立した語のみ)
//   2. ユーザー固有 overlay: $XDG_CONFIG_HOME/memory-sanitize/{proper-nouns,acronyms}.json
//      または ~/.config/memory-sanitize/{proper-nouns,acronyms}.json
//      (= ユーザーのワークスペース・プロジェクト・人物・組織等の workspace 固有識別子)
//
// データファイルは JSON (`{"groups": {"<label>": ["Foo", "Bar"]}}` 形式)。
// 旧 .txt (1 行 1 語、 # でコメント) 形式も読み込めるよう互換維持。
// 許可エントリは単語 ("SQLite") でも phrase ("Conventional Commits") でもよい。
// phrase の場合は phrase 全体が text に出現したときのみマッチ、 構成単語が単独で
// 出現しても許可されない (= 「Conventional」 単独で書かれたら違反として検出)。

const SKILL_DATA_DIR = path.join(__dirname, '..', '..', 'data');
const XDG_CONFIG_HOME = process.env.XDG_CONFIG_HOME || path.join(os.homedir(), '.config');
const USER_CONFIG_DIR = path.join(XDG_CONFIG_HOME, 'memory-sanitize');

function readJsonAllowlist(filepath) {
  if (!fs.existsSync(filepath)) return [];
  const data = JSON.parse(fs.readFileSync(filepath, 'utf8'));
  // 想定: { "groups": { "<label>": ["Foo", "Bar"] } }
  // また: { "entries": ["Foo", "Bar"] }、 または素のフラット配列 ["Foo", "Bar"] にも対応
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.entries)) return data.entries;
  if (data.groups && typeof data.groups === 'object') {
    return Object.values(data.groups).flat();
  }
  return [];
}

function readLegacyTxtAllowlist(filepath) {
  if (!fs.existsSync(filepath)) return [];
  return fs
    .readFileSync(filepath, 'utf8')
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#'));
}

function loadAllowlist(basename) {
  // 各経路で .json 優先 → .txt フォールバック (ユーザー overlay の段階的移行のため)
  const sources = [SKILL_DATA_DIR, USER_CONFIG_DIR];
  const collected = [];
  for (const dir of sources) {
    const jsonPath = path.join(dir, `${basename}.json`);
    if (fs.existsSync(jsonPath)) {
      collected.push(...readJsonAllowlist(jsonPath));
      continue;
    }
    const txtPath = path.join(dir, `${basename}.txt`);
    if (fs.existsSync(txtPath)) {
      collected.push(...readLegacyTxtAllowlist(txtPath));
    }
  }
  return collected;
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// 全エントリを長さ降順 (= phrase が単語より先にマッチする) で集約。
// 関心別ファイル:
//   - proper-nouns.json: 固有名詞 (製品名・サービス名・組織名・ライブラリ名等)
//   - acronyms.json:     業界横断の頭字語 (HTML/API/GCP/DOM 等)
// 言語/シェル/ファイル名慣習の予約語 (Dockerfile `COPY`・SQL `JOIN`・HTTP メソッド
// 等) は本来「コード識別子としての引用」 = バッククォート引用が正規。 検出された
// 都度バッククォート化するのが規律で、 「念のため」 で許可一覧に詰め込まない。
const ALLOWLIST_ENTRIES = [
  ...loadAllowlist('proper-nouns'),
  ...loadAllowlist('acronyms'),
].sort((a, b) => b.length - a.length);

// allowlist phrase を単語境界付きでマスクする regex を構築
const ALLOWLIST_REGEX = ALLOWLIST_ENTRIES.length
  ? new RegExp(`\\b(?:${ALLOWLIST_ENTRIES.map(escapeRegex).join('|')})\\b`, 'g')
  : null;

module.exports = function (context) {
  const { Syntax, RuleError, report, locator, getSource } = context;
  return {
    [Syntax.Str](node) {
      const raw = getSource(node);

      // 0. 検出範囲は「日本語と英語が混在した Str ノード」 のみ。
      //    日本語文字 (ひらがな・カタカナ・漢字・全角句読点を含む CJK 範囲) を
      //    1 文字も含まないテキストは「英単語混入」 の対象外 (= 純英語の見出し・
      //    引用・コード片等)。 これにより許可一覧の肥大化や構文除外の場当たり
      //    対応に頼らず、 ルール本来の目的 (= 日本語文中の英単語混入検出)
      //    だけを評価する。
      if (!/[぀-ゟ゠-ヿ一-鿿]/.test(raw)) {
        return;
      }

      let masked = raw;

      // 1. 構文的に非 prose 領域 (= 構造的引用) を空白化する。
      //    順序は「短い anchor を持つ高速判定 → URL/path → 拡張子 → version → email」 の安価順。
      masked = masked.replace(/\[\[[^\]]+\]\]/g, (m) => ' '.repeat(m.length));            // wikilink
      masked = masked.replace(/https?:\/\/[^\s)）]+/g, (m) => ' '.repeat(m.length));      // URL
      masked = masked.replace(/~\/[A-Za-z0-9_.\-\/]+/g, (m) => ' '.repeat(m.length));     // ホームパス
      masked = masked.replace(/\.[\.\/][A-Za-z0-9_.\-\/]+/g, (m) => ' '.repeat(m.length)); // 相対パス ./ ../
      masked = masked.replace(/[A-Za-z0-9_\-]+\/[A-Za-z0-9_.\-\/]+/g, (m) => ' '.repeat(m.length)); // slug 形パス (org/repo, dir/file)
      masked = masked.replace(
        /[A-Za-z0-9_\-*]+\.(md|json|yml|yaml|sh|mjs|js|ts|tsx|jsx|html|css|scss|rb|py|go|toml|ini|env|lock|patch|txt|csv|tsv|xml|svg|png|jpg|jpeg|gif|pdf|zip|tar|gz)\b/g,
        (m) => ' '.repeat(m.length)
      ); // 拡張子付きファイル名
      masked = masked.replace(/[@\^~]?\d+\.\d+\.\d+[\w\-.]*/g, (m) => ' '.repeat(m.length)); // バージョン
      masked = masked.replace(/[a-zA-Z0-9_\-]+@[\w\-.\d]+/g, (m) => ' '.repeat(m.length));   // メールアドレス
      masked = masked.replace(/\bL\d+(-\d+)?\b/g, (m) => ' '.repeat(m.length));              // 行番号参照 (Lxxx / Lxxx-yyy)
      masked = masked.replace(/\b[A-Z][A-Z0-9]*-\d+\b/g, (m) => ' '.repeat(m.length));        // Linear/GitHub issue ID (LACO-2 / PM-56 / NGJ-11)

      // 2. 許可エントリ (= phrase 含む) を出現位置でマスク
      //    全大文字略語 (HTML/HTTP/API 等) はここに登録すべき。
      //    旧版は `\b[A-Z][A-Z0-9_]{2,}\b` で 3 文字以上の全大文字略語を機械的に
      //    素通させていたが、 これは未登録略語まで無検証で許可する裏口になっていた。
      //    現状は acronyms.txt への明示的登録を唯一の窓口として、 検出規律を担保する。
      if (ALLOWLIST_REGEX) {
        masked = masked.replace(ALLOWLIST_REGEX, (m) => ' '.repeat(m.length));
      }

      // 3. 残った英字列を違反として検出
      const re = /[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9]|[A-Za-z]{2,}/g;
      let m;
      while ((m = re.exec(masked)) !== null) {
        const word = m[0];
        if (/^v?\d/.test(word)) continue;
        report(
          node,
          new RuleError(`英単語混入: "${word}"`, {
            padding: locator.range([m.index, m.index + word.length]),
          })
        );
      }
    },
  };
};
