# buntai

日本語の文体規範のスキル集。
k16shikano 氏（[@k16shikano](https://github.com/k16shikano)）が gist で公開している 2 つの SKILL.md を収録したプラグイン。

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

## 出典

- `japanese-tech-writing`: <https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d>（収録リビジョン `209db7d`、2026-07-09）
- `cognitive-rhythm-writing`: <https://gist.github.com/k16shikano/eb2929f13ed19c97188393d297be8432>（収録リビジョン `a3b1e26`、2026-07-09）

収録にあたっての変更は次の 2 点のみで、規範の本文は原文のまま。

- `cognitive-rhythm-writing` の「併用する規範」の参照表記を、プラグイン内のスキル参照形式に変更
- 各 SKILL.md 末尾に「出典」節を追記

## ライセンス

収録スキル本文のライセンスは Unlicense（パブリックドメイン献呈）である。
作者が原典 gist のコメントで明言しており、作者のライセンス方針 gist にも public gist 全件へ Unlicense を適用すると明記されている。

- 作者コメント: <https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d?permalink_comment_id=6210840#gistcomment-6210840>
- ライセンス方針 gist: <https://gist.github.com/k16shikano/67625f2a7d96e3bbdfae8d571a936063>
