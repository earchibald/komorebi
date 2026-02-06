"""Profile manager for execution profile loading and resolution.

Loads YAML-defined profiles from ``~/.komorebi/profiles.yaml``,
resolves inheritance chains, detects cycles, and enforces the
dangerous-env-var blacklist.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml

from ..models.profile import BlockingPolicy, ExecutionProfile, ResolvedProfile


# Environment variables that are never allowed in profiles
# unless explicitly whitelisted in config.yaml.
DANGEROUS_ENV_VARS: frozenset[str] = frozenset({
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "DYLD_FRAMEWORK_PATH",
    "LD_AUDIT",
    "LD_DEBUG",
    "PYTHONSTARTUP",
    "NODE_OPTIONS",
    "PERL5OPT",
    "RUBYOPT",
    "BASH_ENV",
})

DEFAULT_PROFILES_PATH = Path.home() / ".komorebi" / "profiles.yaml"


class ProfileError(Exception):
    """Raised for profile configuration issues."""


class ProfileManager:
    """Loads, validates, and resolves execution profiles.

    Profiles support single-parent inheritance via the ``parent`` key.
    Inheritance resolution merges env dicts (child wins), concatenates
    args (parent first), and child scalars override parent.
    """

    def __init__(
        self,
        profiles_path: Optional[Path] = None,
        allowed_dangerous: Optional[set[str]] = None,
    ) -> None:
        self._path = profiles_path or DEFAULT_PROFILES_PATH
        self._allowed_dangerous = allowed_dangerous or set()
        self._profiles: dict[str, ExecutionProfile] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load profiles from the YAML file.

        Raises:
            ProfileError: If the file is malformed or contains cycles.
            FileNotFoundError: If the profiles file does not exist.
        """
        if not self._path.exists():
            raise FileNotFoundError(f"Profiles file not found: {self._path}")

        raw = yaml.safe_load(self._path.read_text()) or {}
        profiles_raw: dict[str, Any] = raw.get("profiles", {})

        if not isinstance(profiles_raw, dict):
            raise ProfileError("'profiles' key must be a mapping")

        self._profiles = {}
        for name, data in profiles_raw.items():
            if not isinstance(data, dict):
                raise ProfileError(f"Profile '{name}' must be a mapping")
            data["name"] = name
            # Normalise blocking sub-key
            if "blocking" in data and isinstance(data["blocking"], dict):
                data["blocking"] = BlockingPolicy(**data["blocking"])
            self._profiles[name] = ExecutionProfile(**data)

        # Validate no cycles
        for name in self._profiles:
            self._check_cycle(name)

    def list_profiles(self) -> list[str]:
        """Return names of all loaded profiles."""
        return list(self._profiles.keys())

    def get(self, name: str) -> ExecutionProfile:
        """Return a raw (unresolved) profile by name.

        Raises:
            ProfileError: If the profile does not exist.
        """
        if name not in self._profiles:
            raise ProfileError(f"Profile '{name}' not found")
        return self._profiles[name]

    def resolve(self, name: str) -> ResolvedProfile:
        """Resolve a profile with full inheritance chain.

        Args:
            name: Profile name.

        Returns:
            A ``ResolvedProfile`` with all inherited values merged.

        Raises:
            ProfileError: On missing profile, cycle, or dangerous env vars.
        """
        chain = self._inheritance_chain(name)

        # Start with empty base, overlay each ancestor → child
        merged_env: dict[str, str] = {}
        merged_args: list[str] = []
        merged_blocking = BlockingPolicy()
        command: Optional[list[str]] = None
        redact_secrets = True
        stream_output = False
        capture_stdin = False

        for profile in chain:
            merged_env.update(profile.env)
            merged_args = list(profile.args) if profile.args else merged_args
            if profile.command is not None:
                command = profile.command
            if profile.blocking:
                merged_blocking = profile.blocking
            redact_secrets = profile.redact_secrets
            stream_output = profile.stream_output
            capture_stdin = profile.capture_stdin

        # Enforce dangerous env var blacklist
        self._check_dangerous_env(name, merged_env)

        return ResolvedProfile(
            name=name,
            command=command,
            args=merged_args,
            env=merged_env,
            blocking=merged_blocking,
            redact_secrets=redact_secrets,
            stream_output=stream_output,
            capture_stdin=capture_stdin,
        )

    def build_env(self, resolved: ResolvedProfile) -> dict[str, str]:
        """Build the full subprocess environment dict.

        Merges the current OS environment with the profile's env vars.
        Profile values override OS values.

        Args:
            resolved: A resolved profile.

        Returns:
            Combined environment dict safe for ``subprocess.Popen(env=...)``.
        """
        env = dict(os.environ)
        env.update(resolved.env)
        return env

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _inheritance_chain(self, name: str) -> list[ExecutionProfile]:
        """Return the inheritance chain from root ancestor → target.

        Raises:
            ProfileError: On missing profile or cycle.
        """
        chain: list[ExecutionProfile] = []
        visited: set[str] = set()
        current: Optional[str] = name

        while current is not None:
            if current in visited:
                raise ProfileError(
                    f"Circular inheritance detected: {' → '.join([*visited, current])}"
                )
            if current not in self._profiles:
                raise ProfileError(f"Profile '{current}' not found")
            visited.add(current)
            chain.append(self._profiles[current])
            current = self._profiles[current].parent

        # Reverse so root ancestor is first
        chain.reverse()
        return chain

    def _check_cycle(self, name: str) -> None:
        """Validate no circular inheritance from *name*."""
        visited: set[str] = set()
        current: Optional[str] = name
        while current is not None:
            if current in visited:
                raise ProfileError(
                    f"Circular inheritance detected starting from '{name}'"
                )
            visited.add(current)
            profile = self._profiles.get(current)
            current = profile.parent if profile else None

    def _check_dangerous_env(self, profile_name: str, env: dict[str, str]) -> None:
        """Raise if env contains blacklisted vars not in allow-list."""
        for var in env:
            if var in DANGEROUS_ENV_VARS and var not in self._allowed_dangerous:
                raise ProfileError(
                    f"Profile '{profile_name}' sets dangerous environment variable "
                    f"'{var}'. Add it to allowed_dangerous to override."
                )
