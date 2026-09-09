"""Conservative recursive redaction applied before trace persistence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

DEFAULT_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}

DEFAULT_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)\b(api[_ -]?key|password|secret|token)\s*[:=]\s*[^\s,;]+"),
)


@dataclass(frozen=True)
class Redactor:
    replacement: str = "[REDACTED]"
    sensitive_keys: set[str] = field(default_factory=lambda: set(DEFAULT_SENSITIVE_KEYS))
    patterns: tuple[re.Pattern[str], ...] = DEFAULT_PATTERNS

    def redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            redacted: dict[str, Any] = {}
            for key, item in value.items():
                normalized = key.lower().replace("-", "_")
                redacted[key] = (
                    self.replacement
                    if normalized in self.sensitive_keys
                    else self.redact(item)
                )
            return redacted
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, tuple):
            return [self.redact(item) for item in value]
        if isinstance(value, str):
            result = value
            for pattern in self.patterns:
                result = pattern.sub(self.replacement, result)
            return result
        return value
