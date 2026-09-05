#!/usr/bin/env bash
# LLM Wiki の決定的 lint（読み取り専用・報告のみ）。
# 機械的な検査をスクリプトに委譲し、LLM が in-context で数えないための前例踏襲。
# 修正はしない。提案は skill/人間が判断する（human-in-the-loop ゲート）。
set -euo pipefail

KB="${KB_DIR:-$HOME/.knowledge}"
WIKI="$KB/wiki"
INDEX="$WIKI/index.md"

echo "# KB lint report ($(date +%F))"
echo "wiki: $WIKI"
echo

# 0. OKF §9.1 conformance（frontmatter 必須 + 非空 type） ---------------------
# OKF v0.1 SPEC §9.1: 非予約 .md は YAML frontmatter を持ち、`type:` が非空。
# 予約ファイル (index.md / log.md) は §6 / §7 の構造に従う（frontmatter 不要）。
echo "## 0. OKF §9.1 conformance（非予約ページの frontmatter + type 必須）"
n_no_fm=0; n_no_type=0
while IFS= read -r p; do
  rel="${p#"$WIKI"/}"
  # frontmatter は 1 行目が `---` で開始しないと無効
  if ! head -1 "$p" | grep -q '^---$'; then
    echo "- frontmatter 欠落: $rel"
    n_no_fm=$((n_no_fm+1))
    continue
  fi
  # frontmatter ブロックを抽出（先頭の --- から次の --- まで）
  fm_block=$(awk 'NR==1 && /^---$/ {in_fm=1; next} in_fm && /^---$/ {exit} in_fm {print}' "$p")
  if [ -z "$fm_block" ]; then
    echo "- frontmatter ブロック空: $rel"
    n_no_fm=$((n_no_fm+1))
    continue
  fi
  # type 行抽出: `type:` のあと空白を許して値が空でないこと
  type_val=$(printf '%s\n' "$fm_block" | grep -m1 -E '^type:' | sed -E 's/^type:[[:space:]]*//' | sed -E 's/^"//;s/"$//' | sed -E "s/^'//;s/'$//")
  if [ -z "$type_val" ]; then
    echo "- type 欠落 / 空: $rel"
    n_no_type=$((n_no_type+1))
  fi
done < <(find "$WIKI" -type f -name '*.md' ! -name index.md ! -name log.md | sort)
# 予約ファイル構造の軽量チェック
n_reserved_warn=0
if [ -f "$INDEX" ] && head -1 "$INDEX" | grep -q '^---$'; then
  echo "- 予約 §6 違反: index.md に frontmatter が混入"
  n_reserved_warn=$((n_reserved_warn+1))
fi
LOG="$WIKI/log.md"
if [ -f "$LOG" ] && head -1 "$LOG" | grep -q '^---$'; then
  echo "- 予約 §7 違反: log.md に frontmatter が混入"
  n_reserved_warn=$((n_reserved_warn+1))
fi
if [ -f "$LOG" ] && ! grep -qE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' "$LOG"; then
  echo "- 予約 §7 違反: log.md に ISO 8601 日付見出し (## YYYY-MM-DD) が無い"
  n_reserved_warn=$((n_reserved_warn+1))
fi
echo "- frontmatter 欠落 $n_no_fm / type 欠落 $n_no_type / 予約構造違反 $n_reserved_warn"
echo

# 1. index 整合性（登録漏れ = orphan 候補） --------------------------------
echo "## 1. index 未登録ページ（orphan 候補）"
n_files=0; n_missing=0
while IFS= read -r p; do
  n_files=$((n_files+1))
  rel="${p#"$WIKI"/}"
  if ! grep -qF "($rel)" "$INDEX"; then
    echo "- 未登録: $rel"
    n_missing=$((n_missing+1))
  fi
done < <(find "$WIKI" -type f -name '*.md' ! -name index.md ! -name log.md | sort)
n_index=$(grep -cE '^- \[' "$INDEX" || true)
echo "- ページ $n_files / index 項目 $n_index / 未登録 $n_missing"
echo

# 1b. index エントリと description の整合（OKF §8） ------------------------
# OKF §8: index のエントリは、リンク先の frontmatter description を載せる。
# description は §4.1 で "A single sentence"。よって index 行も一文である。
# 文字列の加工は bash のリテラル置換で行う。sed のブラケット式と \t は BSD と
# GNU で挙動が違い、マルチバイトの扱いもロケールに依存するため使わない。
echo "## 1b. index エントリ（OKF §8: description の転記）"
n_no_desc=0; n_multi=0; n_mismatch=0; n_badfmt=0; n_noline=0
while IFS= read -r p; do
  rel="${p#"$WIKI"/}"
  raw="$(awk '
    /^---$/ { n++; next }
    n==1 && /^description:/ { sub(/^description:[[:space:]]*/, ""); print; exit }
    n>=2 { exit }
  ' "$p")"
  # 末尾の空白を落とす。
  while [ "${raw% }" != "$raw" ] || [ "${raw%	}" != "$raw" ]; do
    raw="${raw% }"; raw="${raw%	}"
  done
  # 引用符で囲まれていれば中身が値。囲まれていなければ " #" 以降がコメント。
  case "$raw" in
    '"'*'"') desc="${raw#\"}"; desc="${desc%\"}" ;;
    "'"*"'") desc="${raw#\'}"; desc="${desc%\'}" ;;
    '"'*|"'"*)
      # 引用符で始まるが終わっていない = 末尾にコメントが付いている。
      body="${raw%%\"*}"; desc="${raw#\"}"; desc="${desc%%\"*}" ;;
    *)
      desc="$raw"
      case "$desc" in
        *" #"*) desc="${desc%% #*}" ;;
        *"	#"*) desc="${desc%%	#*}" ;;
      esac
      while [ "${desc% }" != "$desc" ] || [ "${desc%	}" != "$desc" ]; do
        desc="${desc% }"; desc="${desc%	}"
      done ;;
  esac
  case "$desc" in
    "")
      echo "- description 欠落: $rel"; n_no_desc=$((n_no_desc+1)); continue ;;
    "|"*|">"*)
      echo "- description がブロックスカラー（索引へ転記できない）: $rel"
      n_no_desc=$((n_no_desc+1)); continue ;;
  esac
  # 一文か。引用の句点（。」）と英語の略語を先に潰してから区切りを数える。
  body="$desc"
  # かぎ括弧の中は引用。リテラル一致で丸ごと外す（ロケールに依存しない）。
  while :; do
    case "$body" in
      *「*」*)
        pre="${body%%「*}"; rest="${body#*「}"; post="${rest#*」}"
        body="$pre$post" ;;
      *) break ;;
    esac
  done
  for abbr in "e.g." "i.e." "cf." "vs." "etc." "No." "Inc." "Ltd."; do
    body="${body//"$abbr"/}"
  done
  body="${body%。}"; body="${body%.}"
  if printf '%s' "$body" | grep -qE '。|\. +[A-Za-z]'; then
    echo "- description が複数文: $rel"; n_multi=$((n_multi+1))
  fi
  # index 行を、行頭のリンクだけで引く。区切りは問わずに拾い、形を別に見る。
  esc="$(printf '%s' "$rel" | sed 's/[.[\*^$/]/\\&/g')"
  line="$(grep -E "^- \[[^]]*\]\($esc\)" "$INDEX" || true)"
  if [ -z "$line" ]; then
    echo "- index に行頭のエントリが無い: $rel"; n_noline=$((n_noline+1)); continue
  fi
  case "$line" in
    *"): "*)
      entry="${line#*): }"
      if [ "$entry" != "$desc" ]; then
        echo "- index が description と不一致: $rel"; n_mismatch=$((n_mismatch+1))
      fi ;;
    *)
      echo "- index の区切りが \"): \" でない: $rel"; n_badfmt=$((n_badfmt+1)) ;;
  esac
done < <(find "$WIKI" -type f -name '*.md' ! -name index.md ! -name log.md | sort)
echo "- description 欠落 $n_no_desc / 複数文 $n_multi / index 不一致 $n_mismatch / index 書式違反 $n_badfmt / index 行なし $n_noline"
echo

# 2. リンク切れ・未作成ページ ----------------------------------------------
echo "## 2. リンク切れ（相対 .md リンク先が無い = リンク切れ or 未作成 ingest 候補）"
n_dead=0
while IFS= read -r f; do
  dir="$(dirname "$f")"
  while IFS= read -r tgt; do
    [ -z "$tgt" ] && continue
    case "$tgt" in http*|/*) continue;; esac
    base="${tgt%%#*}"
    if [ ! -f "$dir/$base" ]; then
      echo "- ${f#"$WIKI"/} → $tgt"
      n_dead=$((n_dead+1))
    fi
  done < <(grep -oE '\]\([^)]+\.md[^)]*\)' "$f" | sed -E 's/^\]\(//; s/\)$//')
done < <(find "$WIKI" -type f -name '*.md' | sort)
echo "- 計 $n_dead 件"
echo

# 3. 陳腐化の疑い ----------------------------------------------------------
echo "## 3. 陳腐化の疑い（source_commit を主・mtime をフォールバック）"
echo "  source_commit(git SHA) があれば repo HEAD と照合（codewiki 方式・mtime 非依存で堅牢）。"
echo "  無ければ manifest の mtime > ページ mtime で代替（mtime は checkout でリセットされる発見的検査）。"
echo "  source_paths 未設定のページはスキップ。"
n_stale=0; n_no_src=0
while IFS= read -r page; do
  name="$(basename "$page" .md)"
  # frontmatter から source_paths の最初のエントリを抽出（$HOME 相対パス）
  src_rel=$(awk 'NR==1 && /^---$/ {in_fm=1; next} in_fm && /^---$/ {exit} in_fm && /^source_paths:/ {in_sp=1; next} in_sp && /^  - / {gsub(/^  - /,""); print; exit} in_sp && !/^  / {exit}' "$page")
  if [ -z "$src_rel" ]; then
    n_no_src=$((n_no_src+1))
    continue
  fi
  src="$HOME/$src_rel"
  # 末尾スラッシュを除去
  src="${src%/}"
  [ -d "$src" ] || continue
  sc=$(grep -m1 -oE 'source_commit:[^0-9a-fA-F]*[0-9a-fA-F]{7,40}' "$page" 2>/dev/null | grep -oiE '[0-9a-f]{7,40}' | head -1 || true)
  if git -C "$src" rev-parse --git-dir >/dev/null 2>&1 && [ -n "$sc" ]; then
    head_full=$(git -C "$src" rev-parse HEAD 2>/dev/null || true)
    sc_full=$(git -C "$src" rev-parse "$sc" 2>/dev/null || true)
    if [ -n "$head_full" ] && [ -n "$sc_full" ]; then
      if [ "$head_full" != "$sc_full" ]; then
        echo "- $name: source_commit ${sc} ≠ HEAD → 再 ingest 候補（git 検出）"
        n_stale=$((n_stale+1))
      fi
    else
      echo "- $name: source_commit ${sc} を repo で解決できない → 要確認"
      n_stale=$((n_stale+1))
    fi
  else
    newer=$(find "$src" -maxdepth 4 \( -name 'CLAUDE.md' -o -name 'package.json' -o -name '*lock*' -o -name 'gleam.toml' -o -name 'angular.json' -o -iname 'README*' \) -newer "$page" 2>/dev/null | head -1 || true)
    if [ -n "$newer" ]; then
      echo "- $name: ${newer#"$HOME"/} がページより新しい → 再 ingest 候補（mtime fallback）"
      n_stale=$((n_stale+1))
    fi
  fi
done < <(find "$WIKI/projects" -type f -name '*.md' | sort)
echo "- 計 $n_stale 件（source_paths 未設定スキップ: $n_no_src 件）"
echo

echo "---"
echo "summary: OKF frontmatter 欠落 $n_no_fm / OKF type 欠落 $n_no_type / 予約構造違反 $n_reserved_warn / description 欠落 $n_no_desc / description 複数文 $n_multi / index 不一致 $n_mismatch / index 書式違反 $n_badfmt / index 行なし $n_noline / 未登録 $n_missing / リンク切れ $n_dead / 陳腐化疑い $n_stale"
echo "（schema 準拠: 本検査は提案のみ。修正は skill/人間が判断する）"
