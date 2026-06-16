# スタイル部品の一覧と使いどころ

`assets/style.css` が提供するグラフィカル部品。視認性と理解しやすさのために使う。
**注意**：部品に入れる文言も `writing-rules.md` に従う（本にない情報・比喩・誇張を入れない）。

各ページは `<style>:root{ --accent:#色; --accent-soft:#薄い色; }</style>` でアクセント色を設定する（部ごと・章ごとに色分けすると見分けやすい）。

## 基本構造

- `.topbar` … 上部固定ナビ（目次＋他ページへのリンク）
- `.hero` … ページ見出し（`.eyebrow` ラベル＋`h1`＋`.lead` 説明）
- `.toc` … ページ内目次（章リスト）
- `.chapter` + `.chapter-head`（`.num`＋`h2`）… 章ブロック
- `.topic` … 「要点＋解説」の基本カード。`h3.ic`（`.emoji` 枠つき）＋`.summary`＋`ul`
- `.keywords`（`.k`）… 章末のキーワードタグ
- `.pager` … 前後ページ送り
- index 専用：`.bibliography`（書誌情報）/ `.book-overview` / `.part-grid`＋`.part-card` / `.section-label`
- index 専用：`.persona-grid`＋`.persona`（ターゲット読者カード。`.emoji`＋`h3`＋`p`）
- index 専用：`.ai-analysis`（**AIによる分析の囲み**。`.ai-badge` で本書外を明示、`.path-row`＝`.who`＋`.route` で立場別の読み順を示す）

## 強調

- `<mark>` … 文中の最重要句のハイライト（章につき数か所まで。乱用しない）
- `<span class="term">…</span>` … 重要な専門用語（点線下線＋アクセント色）

## コールアウト

- `.in-a-nutshell`（`.emoji`＋`.label`「この章を一言で」＋`p`）… 章冒頭の要旨
- `.callout.why` … 「なぜそうなるか」の補足説明
- `.callout.tip` … 言い換え・読み解きの補助
- `.callout.warn` … 注意・落とし穴
- `.callout.supplement`（**本書外マーク**）… 本にない補足。`.ctitle` に「補足（本書外）」と書く。本書由来でない情報はこれで囲む

インラインで本書外の語を示す場合は `<span class="supp">語<span class="supp-tag">補足</span></span>`。

## 図解

- `.versus`（`.side.a` / `.vs` / `.side.b`）… A対Bの対比（Dev対Ops、Before対After など）
- `.steps`（`.step`＋`.badge`、悪化の連鎖は `.steps.escalate`）… 段階・手順・幕
- `.metrics`（`.metric`＋`.big`/`.name`/`.dir`、`.up`/`.down`）… 指標カード
- `.flow`（`.node`＋`.arrow`）… 横方向のフロー図
- `.ways-map`（`.way-row`、`--wc` で色指定）… 並列する原則・分類のまとめ図

## 使い分けの目安

| 見せたいもの | 部品 |
|---|---|
| 章の要旨を最初に | `.in-a-nutshell` |
| 要点と解説 | `.topic` |
| 2つの立場・状態の対比 | `.versus` |
| 段階・連鎖・手順 | `.steps`（悪化は `.escalate`） |
| 指標の方向（増減） | `.metrics` |
| 一連の流れ | `.flow` |
| 並列する複数の原則 | `.ways-map` |
| 本にない補足 | `.callout.supplement` / `.supp` |

絵文字は各部品の `.emoji` 枠やアイコン位置にのみ置く。解説文に混ぜない。
