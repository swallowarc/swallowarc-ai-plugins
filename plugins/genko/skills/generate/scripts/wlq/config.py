# ported from: internal/infrastructure/config/config.go:71-132 (QualityGate defaults),
#              internal/infrastructure/quality/checker.go:87-165 @ autopostd 20c740b
FORBIDDEN_WORDS = ["絶対", "必ず", "間違いなく", "TODO", "FIXME", "未検証", "たぶん", "おそらく"]
REQUIRED_FRONTMATTER = ["title", "date", "tags", "draft"]
DESCRIPTION_BOILERPLATE = ""
DESCRIPTION_MIN_LEN = 20
SENTENCE_MAX_LEN = 100
SENTENCE_WARN_LEN = 80
SENTENCE_MAX_COMMAS = 3
KANJI_RUN_MAX = 6
KANJI_RUN_ALLOWLIST: list[str] = []
BOLD_COLON_LIST_MAX = 2
CODE_LINE_MAX_LEN = 80
TITLE_LEN_MIN = 20
TITLE_LEN_MAX = 32
SENTENCE_ENDING_RUN_MAX = 3
RHETORICAL_CONTRAST_MAX = 3
CLICHE_PHRASES = [
    "が重要です", "がポイントです", "が鍵です", "言い換えると",
    # genko 独自拡張（Go に対応なし）: jp-writing:japanese-tech-writing
    # 「LLM っぽい表現の禁止」の空虚な形容・動詞・前置きを です/ます調に適応して
    # 追加（原典: k16shikano 氏 gist、Unlicense）。check_cliche_phrases は素朴な
    # count で数える（二重計上を防がない）ため、既存・追加フレーズ間で部分文字列の
    # 包含関係を作らないこと。
    "に他なりません", "重要なのは", "が不可欠です", "深掘り", "掘り下げ",
    "多角的", "包括的",
]
CLICHE_PHRASES_MAX = 3
RHETORICAL_NEGATION_PATTERNS = [
    "わけではありません", "ものではありません", "だけではありません", "ではありません",
    "とは限りません", "を指しません", "に閉じません", "というより",
]
RHETORICAL_NEGATION_MAX = 4
DESU_MASU_RATIO_MAX_PERCENT = 85
DESU_MASU_RATIO_MIN_SENTENCES = 30
PARAGRAPH_LENGTH_RUN_MAX = 7
PARAGRAPH_UNIFORMITY_MAX_PERCENT = 70
PARAGRAPH_UNIFORMITY_MIN_PARAGRAPHS = 20
HARD_LINE_BREAK_MAX_PERCENT = 50
HARD_LINE_BREAK_MIN_JOINTS = 10
FIRST_PERSON_PATTERNS = ["私は", "私が", "私の", "私なら", "筆者は", "筆者が", "筆者の", "筆者として"]
FIRST_PERSON_MAX = 8
REASON_TEMPLATE_PATTERNS = ["理由は", "根拠は", "ためです", "からです"]
REASON_TEMPLATE_MAX = 6
# genko 独自（Go に対応なし）: 進行実況チェック（checks_narration.py）の定型パターンと
# 上限。jp-writing:cognitive-rhythm-writing の「文書を更新する文（駄文）」のうち
# 定型化できるものを列挙する。導入の予告 1 回程度の正当な用途を許すため、
# 禁止ではなく頻度制限とする。
PROGRESS_NARRATION_PATTERNS = [
    "本記事では", "この記事では", "ここまで見てき",
    "見ていきましょう", "見ていきます",
    "次のセクションでは", "次の章では", "以降のセクションで",
    "紹介していきます", "解説していきます", "説明していきます",
    "いかがでしたか",
]
PROGRESS_NARRATION_MAX = 2
MAX_AUTO_FIX_RETRIES = 2  # REVIEW_MAX_AUTO_FIX_RETRIES 既定値
