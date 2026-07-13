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
CLICHE_PHRASES = ["が重要です", "がポイントです", "が鍵です", "言い換えると"]
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
MAX_AUTO_FIX_RETRIES = 2  # REVIEW_MAX_AUTO_FIX_RETRIES 既定値
