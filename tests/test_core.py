import pytest

from assistant_core import (
    AssistantError,
    clean_filename,
    format_post_crm,
    normalize_email,
    parse_json_response,
    validate_post_call,
)


def test_clean_filename():
    assert clean_filename("Coastal Surgical Center") == "Coastal_Surgical_Center"


def test_parse_json_with_markdown_fence():
    text = """```json
{"call_summary": "ok"}
```"""
    assert parse_json_response(text)["call_summary"] == "ok"


def test_normalize_email_without_commitment():
    text = "I will send pricing tomorrow."
    result = normalize_email(text, has_documented_commitments=False)
    assert "I can send" in result
    assert "I will send" not in result


def test_normalize_email_preserves_explicit_commitment():
    text = "I will send pricing tomorrow."
    result = normalize_email(text, has_documented_commitments=True)
    assert result == text


def test_post_crm_is_multiline():
    crm = {
        "contact_role": "OR Director",
        "summary": "Summary text",
        "key_issue": "Issue",
        "next_step": "Next",
        "timing": "Tuesday",
    }
    result = format_post_crm(crm)
    assert result.count("\n") == 4
    assert result.splitlines()[0] == "Contact / role: OR Director"


def test_validate_post_call_rejects_missing_structure():
    with pytest.raises(AssistantError):
        validate_post_call({"call_summary": "ok"})
