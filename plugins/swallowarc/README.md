# swallowarc

個人用の汎用スキル集。
特定のワークフローに属さない単発のスキルをここに集めていき、`/swallowarc:<スキル名>` で呼び出す。

## インストール

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
/plugin install swallowarc@swallowarc-ai-plugins
```

## 収録スキル

### book-summary-html

本の要点をまとめた HTML サイトを生成する。
出力は書誌情報つきの index ページと、章または部ごとの本文ページで構成する。

```
/swallowarc:book-summary-html <書名>
```

元になる情報は Web リサーチで集める。
PDF など本文ファイルが手元にある場合は、引数でパスを渡すとそれを主ソースにする。

### infographic-prompt

概念、文書、本の要点を手描きホワイトボード解説風の 1 枚絵にするための、画像生成プロンプトを作る。
かわいいマスコットと手書き風の日本語テキストで構成した 1 枚のイラストに、対象の要点を詰め込む。

```
/swallowarc:infographic-prompt <対象の概念や文書>
```

出力先は文字描画に強い画像モデルを想定している（Nano Banana Pro / Gemini 3 Pro Image、GPT Image 2 など）。
