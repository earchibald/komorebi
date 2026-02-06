"""Redaction service for scrubbing secrets from text.

Applies regex-based patterns to remove sensitive data (API keys,
private keys, tokens) before content is sent to cloud LLMs. Local
models (Reflex/Ollama) can see raw data per policy.
"""

import re
from typing import Optional


# Compiled regex patterns for known secret formats
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # AWS Access Key IDs (20 uppercase alphanumeric chars starting with AKIA)
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    # AWS Secret Access Keys (40 base64-ish chars)
    ("AWS_SECRET_KEY", re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])")),
    # GitHub Personal Access Tokens (ghp_, gho_, ghu_, ghs_, ghr_)
    ("GITHUB_TOKEN", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}")),
    # OpenAI API keys — must appear before generic API_KEY to avoid
    # the generic pattern consuming the key value first.
    ("OPENAI_KEY", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    # Private key blocks (PEM format)
    ("PRIVATE_KEY", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
        r"[\s\S]*?"
        r"-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    )),
    # Slack tokens (xox[bpas]-...)
    ("SLACK_TOKEN", re.compile(r"xox[bpas]-[0-9a-zA-Z\-]{10,}")),
    # Generic Bearer tokens in authorization headers
    ("BEARER_TOKEN", re.compile(r"(?i)Bearer\s+[A-Za-z0-9_\-\.]{20,}")),
    # Stripe keys
    ("STRIPE_KEY", re.compile(r"(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{20,}")),
    # Generic API keys (hex or base64, 32+ chars labeled as key/token/secret)
    # Placed last among key patterns so specific patterns (OpenAI, Stripe, etc.)
    # match first.
    ("API_KEY", re.compile(
        r"(?i)(?:api[_-]?key|api[_-]?secret|access[_-]?token|auth[_-]?token)"
        r"\s*[:=]\s*['\"]?([A-Za-z0-9_\-/+=]{32,})['\"]?"
    )),
]


class RedactionService:
    """Scrubs sensitive data from text using regex patterns.

    Usage:
        svc = RedactionService()
        clean = svc.redact("My key is ghp_abcdef1234567890abcdef1234567890abcdef")
        # → "My key is [REDACTED:GITHUB_TOKEN]"

    Thread-safe: all patterns are compiled at module load time.
    """

    def __init__(self, extra_patterns: Optional[list[tuple[str, str]]] = None) -> None:
        """Initialise with optional additional patterns.

        Args:
            extra_patterns: List of (label, regex_string) tuples to add.
        """
        self._patterns = list(_PATTERNS)
        if extra_patterns:
            for label, pattern_str in extra_patterns:
                self._patterns.append((label, re.compile(pattern_str)))

    def redact(self, text: str) -> str:
        """Replace all detected secrets with [REDACTED:<LABEL>] placeholders.

        Args:
            text: Raw text potentially containing secrets.

        Returns:
            Sanitised text with secrets replaced.
        """
        result = text
        for label, pattern in self._patterns:
            # For patterns with groups, redact the captured group
            if pattern.groups:
                def _group_replacer(m: re.Match[str], lbl: str = label) -> str:
                    return m.group(0).replace(m.group(1), f"[REDACTED:{lbl}]")

                result = pattern.sub(_group_replacer, result)
            else:
                result = pattern.sub(f"[REDACTED:{label}]", result)
        return result

    def contains_secrets(self, text: str) -> bool:
        """Check whether text contains any detectable secrets.

        Args:
            text: Text to scan.

        Returns:
            True if at least one secret pattern matches.
        """
        for _, pattern in self._patterns:
            if pattern.search(text):
                return True
        return False

    def scan(self, text: str) -> list[str]:
        """Return labels of all secret types found in text.

        Args:
            text: Text to scan.

        Returns:
            Deduplicated list of matched secret labels.
        """
        found: list[str] = []
        for label, pattern in self._patterns:
            if pattern.search(text):
                found.append(label)
        return found
