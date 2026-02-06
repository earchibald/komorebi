"""Tests for Phase 1: RedactionService + ProfileManager.

TDD Red → Green:
- Redaction patterns for AWS, GitHub, PEM, Stripe, OpenAI
- Profile loading, inheritance, cycle detection, dangerous env vars
"""

import textwrap
from pathlib import Path

import pytest

from backend.app.core.redaction import RedactionService
from backend.app.core.profiles import ProfileManager, ProfileError
from backend.app.models.profile import (
    BlockingPolicy,
    ExecutionProfile,
    ResolvedProfile,
)


# ──────────────────────────────────────────────────────────────
# RedactionService tests
# ──────────────────────────────────────────────────────────────


class TestRedactionService:
    """Tests for the RedactionService."""

    def setup_method(self) -> None:
        self.svc = RedactionService()

    # --- AWS Keys ---

    def test_redacts_aws_access_key(self) -> None:
        text = "My key is AKIAIOSFODNN7EXAMPLE"
        result = self.svc.redact(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED:AWS_ACCESS_KEY]" in result

    # --- GitHub Tokens ---

    def test_redacts_github_pat(self) -> None:
        token = "ghp_" + "a" * 36
        text = f"export GITHUB_TOKEN={token}"
        result = self.svc.redact(text)
        assert token not in result
        assert "[REDACTED:GITHUB_TOKEN]" in result

    def test_redacts_github_oauth_token(self) -> None:
        token = "gho_" + "B" * 36
        text = f"token: {token}"
        result = self.svc.redact(text)
        assert token not in result
        assert "[REDACTED:GITHUB_TOKEN]" in result

    # --- Private Keys ---

    def test_redacts_pem_private_key(self) -> None:
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIBowIBAAJBALFakeKeyData1234==\n"
            "-----END RSA PRIVATE KEY-----"
        )
        text = f"Here is my key:\n{pem}\nDone"
        result = self.svc.redact(text)
        assert "MIIBowIBAAJ" not in result
        assert "[REDACTED:PRIVATE_KEY]" in result

    def test_redacts_ec_private_key(self) -> None:
        pem = (
            "-----BEGIN EC PRIVATE KEY-----\n"
            "SomeBase64Data==\n"
            "-----END EC PRIVATE KEY-----"
        )
        result = self.svc.redact(pem)
        assert "SomeBase64Data" not in result

    # --- Slack Tokens ---

    def test_redacts_slack_bot_token(self) -> None:
        token = "xoxb-123456789012-1234567890123-AbCdEfGhIjKl"
        result = self.svc.redact(f"SLACK_TOKEN={token}")
        assert token not in result
        assert "[REDACTED:SLACK_TOKEN]" in result

    # --- Stripe Keys ---

    def test_redacts_stripe_live_key(self) -> None:
        key = "sk_live_" + "a" * 24
        result = self.svc.redact(f"stripe: {key}")
        assert key not in result
        assert "[REDACTED:STRIPE_KEY]" in result

    # --- OpenAI Keys ---

    def test_redacts_openai_key(self) -> None:
        key = "sk-" + "a" * 48
        result = self.svc.redact(f"OPENAI_API_KEY={key}")
        assert key not in result
        assert "[REDACTED:OPENAI_KEY]" in result

    # --- Bearer Tokens ---

    def test_redacts_bearer_token(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        result = self.svc.redact(text)
        assert "eyJhbGciOiJIUzI1NiI" not in result
        assert "[REDACTED:BEARER_TOKEN]" in result

    # --- Negative / safe text ---

    def test_preserves_normal_text(self) -> None:
        text = "Hello world, this is a normal log message with no secrets."
        assert self.svc.redact(text) == text

    def test_preserves_short_strings(self) -> None:
        text = "key=abc123"
        assert self.svc.redact(text) == text  # Too short to be a real secret

    # --- contains_secrets ---

    def test_contains_secrets_true(self) -> None:
        assert self.svc.contains_secrets("ghp_" + "x" * 36)

    def test_contains_secrets_false(self) -> None:
        assert not self.svc.contains_secrets("no secrets here")

    # --- scan ---

    def test_scan_returns_labels(self) -> None:
        text = f"ghp_{'a' * 36} and AKIAIOSFODNN7EXAMPLE"
        labels = self.svc.scan(text)
        assert "GITHUB_TOKEN" in labels
        assert "AWS_ACCESS_KEY" in labels

    def test_scan_empty_for_clean_text(self) -> None:
        assert self.svc.scan("clean text") == []

    # --- Custom patterns ---

    def test_custom_pattern(self) -> None:
        svc = RedactionService(extra_patterns=[
            ("CUSTOM_SECRET", r"SECRET_[A-Z0-9]{16}"),
        ])
        text = "my token is SECRET_ABCDEF1234567890"
        result = svc.redact(text)
        assert "SECRET_ABCDEF1234567890" not in result
        assert "[REDACTED:CUSTOM_SECRET]" in result

    # --- Multiple secrets in one text ---

    def test_redacts_multiple_secrets(self) -> None:
        text = (
            f"GH: ghp_{'a' * 36}\n"
            f"AWS: AKIAIOSFODNN7EXAMPLE\n"
            f"Stripe: sk_live_{'b' * 24}"
        )
        result = self.svc.redact(text)
        assert "[REDACTED:GITHUB_TOKEN]" in result
        assert "[REDACTED:AWS_ACCESS_KEY]" in result
        assert "[REDACTED:STRIPE_KEY]" in result


# ──────────────────────────────────────────────────────────────
# ProfileManager tests
# ──────────────────────────────────────────────────────────────


class TestProfileManager:
    """Tests for profile loading, inheritance, and validation."""

    def _write_profiles(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "profiles.yaml"
        p.write_text(textwrap.dedent(content))
        return p

    # --- Loading ---

    def test_load_simple_profile(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              base:
                env:
                  FOO: bar
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        assert "base" in mgr.list_profiles()
        profile = mgr.get("base")
        assert profile.env == {"FOO": "bar"}

    def test_load_file_not_found(self, tmp_path: Path) -> None:
        mgr = ProfileManager(profiles_path=tmp_path / "nonexistent.yaml")
        with pytest.raises(FileNotFoundError):
            mgr.load()

    def test_load_empty_file(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, "")
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        assert mgr.list_profiles() == []

    def test_get_nonexistent_profile(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              base:
                env:
                  FOO: bar
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        with pytest.raises(ProfileError, match="not found"):
            mgr.get("nonexistent")

    # --- Inheritance ---

    def test_simple_inheritance(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              base:
                env:
                  TRACE: "1"
                  LOG_LEVEL: info
              child:
                parent: base
                env:
                  LOG_LEVEL: debug
                  NEW_VAR: hello
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        resolved = mgr.resolve("child")
        # Parent env merged, child overrides
        assert resolved.env["TRACE"] == "1"
        assert resolved.env["LOG_LEVEL"] == "debug"
        assert resolved.env["NEW_VAR"] == "hello"

    def test_deep_inheritance_chain(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              grandparent:
                env:
                  A: "1"
              parent:
                parent: grandparent
                env:
                  B: "2"
              child:
                parent: parent
                env:
                  C: "3"
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        resolved = mgr.resolve("child")
        assert resolved.env == {"A": "1", "B": "2", "C": "3"}

    def test_command_inherited_from_parent(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              base:
                command: ["ssh", "prod"]
              child:
                parent: base
                env:
                  TIER: prod
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        resolved = mgr.resolve("child")
        assert resolved.command == ["ssh", "prod"]
        assert resolved.env == {"TIER": "prod"}

    # --- Cycle Detection ---

    def test_cycle_detection_self_reference(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              loop:
                parent: loop
                env:
                  X: "1"
        """)
        mgr = ProfileManager(profiles_path=path)
        with pytest.raises(ProfileError, match="[Cc]ircular"):
            mgr.load()

    def test_cycle_detection_two_node(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              a:
                parent: b
              b:
                parent: a
        """)
        mgr = ProfileManager(profiles_path=path)
        with pytest.raises(ProfileError, match="[Cc]ircular"):
            mgr.load()

    # --- Dangerous Env Vars ---

    def test_blocks_ld_preload(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              evil:
                env:
                  LD_PRELOAD: /lib/evil.so
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        with pytest.raises(ProfileError, match="dangerous"):
            mgr.resolve("evil")

    def test_blocks_dyld_insert(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              evil:
                env:
                  DYLD_INSERT_LIBRARIES: /lib/evil.dylib
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        with pytest.raises(ProfileError, match="dangerous"):
            mgr.resolve("evil")

    def test_allowed_dangerous_override(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              special:
                env:
                  LD_PRELOAD: /lib/custom.so
        """)
        mgr = ProfileManager(
            profiles_path=path,
            allowed_dangerous={"LD_PRELOAD"},
        )
        mgr.load()
        # Should not raise
        resolved = mgr.resolve("special")
        assert resolved.env["LD_PRELOAD"] == "/lib/custom.so"

    # --- Blocking Policy ---

    def test_blocking_policy_parsed(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              restricted:
                blocking:
                  network: true
                  write_files:
                    - "/local/*"
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        resolved = mgr.resolve("restricted")
        assert resolved.blocking.network is True
        assert "/local/*" in resolved.blocking.write_files

    # --- build_env ---

    def test_build_env_merges_os_environ(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              prod:
                env:
                  MY_VAR: hello
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        resolved = mgr.resolve("prod")
        full_env = mgr.build_env(resolved)
        # Must contain OS PATH + profile var
        assert "PATH" in full_env
        assert full_env["MY_VAR"] == "hello"

    # --- Redact secrets flag ---

    def test_redact_secrets_default_true(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              default:
                env:
                  X: "1"
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        resolved = mgr.resolve("default")
        assert resolved.redact_secrets is True

    def test_redact_secrets_override(self, tmp_path: Path) -> None:
        path = self._write_profiles(tmp_path, """\
            profiles:
              audit:
                redact_secrets: false
        """)
        mgr = ProfileManager(profiles_path=path)
        mgr.load()
        resolved = mgr.resolve("audit")
        assert resolved.redact_secrets is False


# ──────────────────────────────────────────────────────────────
# Pydantic model validation tests
# ──────────────────────────────────────────────────────────────


class TestProfileModels:
    """Tests for Pydantic model validation."""

    def test_blocking_policy_defaults(self) -> None:
        bp = BlockingPolicy()
        assert bp.network is False
        assert bp.write_files == []

    def test_execution_profile_minimal(self) -> None:
        p = ExecutionProfile(name="test")
        assert p.name == "test"
        assert p.parent is None
        assert p.env == {}
        assert p.redact_secrets is True

    def test_execution_profile_name_required(self) -> None:
        with pytest.raises(Exception):
            ExecutionProfile(name="")  # min_length=1

    def test_resolved_profile_defaults(self) -> None:
        r = ResolvedProfile(name="test")
        assert r.command is None
        assert r.args == []
        assert r.redact_secrets is True
        assert r.stream_output is False
