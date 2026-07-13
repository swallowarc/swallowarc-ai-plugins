"""review_gate.py aspects サブコマンド（CLI エントリ）のテスト。

subprocess で sys.executable 実行する（tests/test_qualitycheck_cli.py と同じ流儀）。
対応する単一の Go テストは無い（review_gate.py は本移植独自の CLI 成果物のため）。

- test_cli_outputs_selected_aspects_to_stdout: rules.json fixture から facts を読み、
  aspects.json（key / allow_error / instruction のみ）を stdout に出す。
- test_cli_style_conformance_instruction_is_substituted: style_conformance の
  {article_type} が rules.json の article_type で置換されて出力されること。
- test_cli_research_flag_enables_source_fidelity_on_first_round_only
- test_cli_document_mode_reduced_set
- test_cli_writes_output_file
- test_cli_missing_rules_file_exits_nonzero
- test_cli_missing_aspects_file_exits_nonzero
- test_cli_invalid_mode_exits_nonzero
- test_cli_malformed_aspects_yaml_exits_nonzero
- test_cli_malformed_rules_json_exits_nonzero
- test_cli_missing_article_type_in_facts_exits_nonzero
- test_cli_exit_code_is_zero_even_when_zero_aspects_selected
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
YAML_PATH = SCRIPTS.parent / "references" / "judge-aspects.yaml"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "review_gate.py"), "aspects", *args],
        capture_output=True,
        text=True,
    )


def _write_rules(tmp_path, *, article_type="intro", has_fenced_block=False, contains_triple_backtick=False):
    rules = tmp_path / "rules.json"
    rules.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mode": "article",
                "findings": [],
                "facts": {
                    "article_type": article_type,
                    "has_fenced_block": has_fenced_block,
                    "contains_triple_backtick": contains_triple_backtick,
                    "prose_runes": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    return rules


def test_cli_outputs_selected_aspects_to_stdout(tmp_path):
    rules = _write_rules(tmp_path, article_type="intro")
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["schema_version"] == 1
    keys = [a["key"] for a in data["aspects"]]
    assert "concrete_examples" in keys
    assert "lead_quality" in keys
    assert "diagram_readability" not in keys
    for a in data["aspects"]:
        assert set(a.keys()) == {"key", "allow_error", "instruction"}


def test_cli_style_conformance_instruction_is_substituted(tmp_path):
    rules = _write_rules(tmp_path, article_type="news")
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    sc = next(a for a in data["aspects"] if a["key"] == "style_conformance")
    assert "記事タイプ: news" in sc["instruction"]
    assert "{article_type}" not in sc["instruction"]
    assert "style-guide.md" in sc["instruction"]


def test_cli_research_flag_enables_source_fidelity_on_first_round_only(tmp_path):
    rules = _write_rules(tmp_path, article_type="impl")

    r1 = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--research-present", "--out", "-",
    )
    assert r1.returncode == 0, r1.stderr
    keys1 = [a["key"] for a in json.loads(r1.stdout)["aspects"]]
    assert "source_fidelity" in keys1

    r2 = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "2", "--research-present", "--out", "-",
    )
    assert r2.returncode == 0, r2.stderr
    keys2 = [a["key"] for a in json.loads(r2.stdout)["aspects"]]
    assert "source_fidelity" not in keys2

    r3 = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r3.returncode == 0, r3.stderr
    keys3 = [a["key"] for a in json.loads(r3.stdout)["aspects"]]
    assert "source_fidelity" not in keys3


def test_cli_document_mode_reduced_set(tmp_path):
    rules = _write_rules(tmp_path, article_type="general")
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "document", "--round", "1", "--research-present", "--out", "-",
    )
    assert r.returncode == 0, r.stderr
    keys = [a["key"] for a in json.loads(r.stdout)["aspects"]]
    # 縮退セット + genko 独自の meta_commentary / redundancy（tests/test_aspects.py の
    # test_document_mode_reduced_set と同じ期待値）。
    assert keys == [
        "lead_quality", "heading_informativeness", "metaphor_discipline",
        "meta_commentary", "redundancy", "source_fidelity",
    ]


def test_cli_writes_output_file(tmp_path):
    rules = _write_rules(tmp_path, article_type="intro")
    out = tmp_path / "out" / "aspects.json"
    out.parent.mkdir()
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", str(out),
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert isinstance(data["aspects"], list)


def test_cli_missing_rules_file_exits_nonzero(tmp_path):
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(tmp_path / "nai.json"),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_missing_aspects_file_exits_nonzero(tmp_path):
    rules = _write_rules(tmp_path, article_type="intro")
    r = run_cli(
        "--aspects-file", str(tmp_path / "nai.yaml"), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_invalid_mode_exits_nonzero(tmp_path):
    rules = _write_rules(tmp_path, article_type="intro")
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "blog", "--round", "1", "--out", "-",
    )
    assert r.returncode != 0


def test_cli_malformed_aspects_yaml_exits_nonzero(tmp_path):
    rules = _write_rules(tmp_path, article_type="intro")
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("schema_version: 1\naspects: [unterminated\n", encoding="utf-8")
    r = run_cli(
        "--aspects-file", str(bad_yaml), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_malformed_rules_json_exits_nonzero(tmp_path):
    rules = tmp_path / "rules.json"
    rules.write_text("{not valid json", encoding="utf-8")
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_missing_article_type_in_facts_exits_nonzero(tmp_path):
    # rules.json は qualitycheck.py の出力であり facts.article_type を必ず持つ。
    # 欠落は入力データの破損なので黙って general にフォールバックせずエラーとする。
    rules = tmp_path / "rules.json"
    rules.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mode": "article",
                "findings": [],
                "facts": {
                    "has_fenced_block": False,
                    "contains_triple_backtick": False,
                    "prose_runes": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r.returncode != 0
    assert r.stderr.startswith("error:")
    assert "article_type" in r.stderr


def test_cli_exit_code_is_zero_even_when_zero_aspects_selected(tmp_path):
    # general + document モードでは lead/heading/metaphor は付くため実際には
    # ゼロにはならないが、選定結果の中身に関わらず exit 0 であることを固定する
    # 目的で、選定件数がどうであれ returncode==0 を検証する。
    rules = _write_rules(tmp_path, article_type="general")
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--out", "-",
    )
    assert r.returncode == 0, r.stderr


def test_cli_rejects_renamed_research_flag(tmp_path):
    """旧 --research（真偽フラグ）は廃止。argparse が exit 2 で拒否する。"""
    rules = _write_rules(tmp_path, article_type="intro")
    r = run_cli(
        "--aspects-file", str(YAML_PATH), "--rules", str(rules),
        "--mode", "article", "--round", "1", "--research", "--out", "-",
    )
    assert r.returncode == 2
