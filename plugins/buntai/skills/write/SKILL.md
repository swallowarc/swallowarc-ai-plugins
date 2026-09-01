---
name: write
description: 日本語文章の執筆エントリポイント。buntai の規範群（japanese-tech-writing・cognitive-rhythm-writing・japanese-anti-slop）を文章の種類に応じて束ね、執筆から AI 臭点検までを 1 回の依頼で行う。ユーザーが /buntai:write で明示的に呼んだとき、または「buntai の規範で書いて」のようにプラグインの規範に従った執筆を求められたときに使用する。既存文章の推敲・AI 臭の指摘だけの依頼では使わず、各規範スキルを直接使う。
---

# buntai 執筆ワークフロー

依頼された日本語文章を、buntai の規範群を束ねて執筆する。
本スキル自体は文章規範を持たない。次の手順で規範を選び、該当する SKILL.md を Read で読み、それに従う。

## 手順

1. **規範の選択**。依頼から文章の種類を判定する。
   - 技術書・技術記事・解説文: `../japanese-tech-writing/SKILL.md` を読む。読み物として緩急が要るもの（章、記事、エッセイ的解説）なら `../cognitive-rhythm-writing/SKILL.md` も読む。リファレンス・手順書・README など緩急が不要なものでは省略する。
   - それ以外（ビジネス文書、ブログ、チャット、汎用ドキュメント）: 上記 2 つは読まない。
   - 種類が判定できないときは、読み手と発表媒体を一問だけ確認する。
2. **点検規範の読み込み**。文章の種類によらず `../japanese-anti-slop/SKILL.md` を読み、「執筆時併用」の使い方で適用する。
3. **執筆**。規範の指示が重なった場合の優先順位は japanese-tech-writing > cognitive-rhythm-writing > japanese-anti-slop。
4. **点検と納品**。書き上げたら同一ターン内で japanese-anti-slop の「機械的点検手順」を実施し、見つかった問題を修正した最終稿を納品する。点検の経過や結果は、求められない限り出力しない。

## 使い分け

- 既存の草稿を直したい・AI 臭を指摘してほしい → 本スキルではなく `buntai:japanese-anti-slop` を直接使う（Edit / Detect モード）。
- 単一の規範だけ適用したい → 該当スキルを直接使う。
- 本スキルは新規執筆の入口専用であり、規範の中身をここに複製しない。規範の変更は各 SKILL.md 側だけで行う。
