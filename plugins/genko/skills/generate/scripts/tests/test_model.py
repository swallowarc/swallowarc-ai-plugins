from wlq.model import Finding, check_fail, check_pass


def test_to_dict_omits_empty_optional_fields():
    f = check_pass("frontmatter_yaml", "ok", "error")
    assert f.to_dict() == {
        "name": "frontmatter_yaml", "passed": True,
        "severity": "error", "detail": "ok",
    }


def test_to_dict_includes_optional_fields_when_set():
    f = Finding(name="llm_judge", passed=False, severity="warning",
                detail="d", category="lead_quality", location="L", suggestion="s")
    d = f.to_dict()
    assert d["category"] == "lead_quality"
    assert d["location"] == "L"
    assert d["suggestion"] == "s"


def test_check_fail_sets_suggestion():
    f = check_fail("body_length", "too short", "肉付けする", "error")
    assert (f.passed, f.severity, f.suggestion) == (False, "error", "肉付けする")
