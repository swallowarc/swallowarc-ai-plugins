# buntai

日本語の文体規範のスキル集。
k16shikano 氏（[@k16shikano](https://github.com/k16shikano)）が gist で公開している 2 つの執筆規範と、AI 臭除去の独自規範 1 つを収録したプラグイン。

## インストール

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
/plugin install buntai@swallowarc-ai-plugins
```

## 収録スキル

### japanese-tech-writing

日本語の技術文書と書籍原稿の文章規範。
整形（一文一行、脚注、記法）、段落と論証の構成、論証の厳密さ、読み手の負荷の管理、視点と語り、演出の抑制、LLM っぽい空句の禁止、冗長の排除を定める。
日本語で技術書の章、草稿、記事、解説文を書くとき、または推敲やリライトをするときに使う。

```
/buntai:japanese-tech-writing
```

### cognitive-rhythm-writing

説明的な文章に緩急を設計するための規範。
緩急を装飾ではなく、認知モードの切替（観察→逡巡→断定→再観察）と未回収の緊張の管理として扱う。
読み物として読ませたい章や記事を生成するとき、または「密度はあるが平坦でおもしろくない」文章を診断、修正するときに使う。
`japanese-tech-writing` との併用が前提である。

```
/buntai:cognitive-rhythm-writing
```

### japanese-anti-slop

日本語文章から AI 特有の定型パターン（AI 臭）を除去する規範。
Edit（最小限の編集で書き直す）、Detect（書き直さず指摘する）、執筆時併用（新規生成時にパターンを避け、書き上げ後に機械的点検を行う）の 3 つの使い方を定める。
意義の水増し、営業口調、曖昧な出典、三点セット、冗長表現、チャット痕跡など 24 パターンのカタログと、誤検出ガード、カウント式の点検手順を持つ。
記事・ブログ・ビジネス文書・チャットなどレジスタを問わず使える。
技術書・記事の執筆時は `japanese-tech-writing` の規範が優先で、本スキルは書き上げ後の点検を担う。

```
/buntai:japanese-anti-slop
```

## 出典

- `japanese-tech-writing`: <https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d>（収録リビジョン `209db7d`、2026-07-09）
- `cognitive-rhythm-writing`: <https://gist.github.com/k16shikano/eb2929f13ed19c97188393d297be8432>（収録リビジョン `a3b1e26`、2026-07-09）

上記 2 スキルの収録にあたっての変更は次の 2 点のみで、規範の本文は原文のまま。

- `cognitive-rhythm-writing` の「併用する規範」の参照表記を、プラグイン内のスキル参照形式に変更
- 各 SKILL.md 末尾に「出典」節を追記

`japanese-anti-slop` は原文収録ではなく、次の英語スキル（いずれも MIT ライセンス）の考え方を日本語向けに転用し、日本語固有のパターンを追加した独自の規範である。

- <https://github.com/harshaneel/humanize>
- <https://github.com/hardikpandya/stop-slop>
- <https://github.com/blader/humanizer>（原典: Wikipedia "Signs of AI writing"）
- <https://github.com/petergyang/no-ai-slop>

## ライセンス

`japanese-tech-writing` と `cognitive-rhythm-writing` の本文のライセンスは Unlicense（パブリックドメイン献呈）である。
作者が原典 gist のコメントで明言しており、作者のライセンス方針 gist にも public gist 全件へ Unlicense を適用すると明記されている。
`japanese-anti-slop` は本リポジトリのライセンス（MIT）に従う。

- 作者コメント: <https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d?permalink_comment_id=6210840#gistcomment-6210840>
- ライセンス方針 gist: <https://gist.github.com/k16shikano/67625f2a7d96e3bbdfae8d571a936063>
