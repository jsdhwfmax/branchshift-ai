from __future__ import annotations

import re
from collections.abc import Iterable

TOKEN_PATTERNS = [
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[=:]\s*['\"]?[^\s'\"]+"),
    re.compile(r"\b(?:ghp|github_pat|sk)-[A-Za-z0-9_-]{12,}\b"),
]


def redact(text: str, configured_secrets: Iterable[str] = ()) -> str:
    result = text
    for secret in configured_secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    result = TOKEN_PATTERNS[0].sub(r"\1[REDACTED]", result)
    result = TOKEN_PATTERNS[1].sub(lambda match: f"{match.group(1)}=[REDACTED]", result)
    result = TOKEN_PATTERNS[2].sub("[REDACTED]", result)
    return result

