from app.providers.redaction import redact


def test_redaction_removes_configured_and_common_tokens():
    output = redact(
        "Authorization: Bearer abc123 api_key=hidden ghp-abcdefghijklmnop",
        ["abc123"],
    )
    assert "abc123" not in output
    assert "hidden" not in output
    assert "ghp-" not in output
    assert output.count("[REDACTED]") >= 3

