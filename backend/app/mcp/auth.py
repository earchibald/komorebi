"""Modular Secret Provider for MCP server authentication.

Resolves secret URIs from config into actual values at runtime.
Supported schemes:
  - env://VAR_NAME    → reads from os.environ
  - keyring://service/username → reads from system keyring (macOS Keychain, etc.)

Security: NEVER store raw API keys in config files. Use URI references only.
"""

from abc import ABC, abstractmethod
import logging
import os

logger = logging.getLogger(__name__)

# Keyring is optional - graceful fallback if not installed
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    logger.info("keyring package not installed - keyring:// URIs will be unavailable")


class SecretProvider(ABC):
    """Abstract base class for secret resolution."""

    @abstractmethod
    def get_secret(self, key_uri: str) -> str:
        """Resolves a secret URI to a plaintext string."""
        pass


class SystemKeyringProvider(SecretProvider):
    """Resolves secrets from the OS keyring (macOS Keychain, GNOME Keyring, etc.).

    URI format: keyring://service_name/username
    """

    def get_secret(self, key_uri: str) -> str:
        if not HAS_KEYRING:
            raise RuntimeError(
                "keyring package is not installed. "
                "Install with: pip install keyring"
            )

        if not key_uri.startswith("keyring://"):
            return ""

        _, _, path = key_uri.partition("keyring://")
        try:
            service, username = path.split("/", 1)
        except ValueError:
            raise ValueError(f"Invalid keyring URI format: {key_uri} (expected keyring://service/username)")

        secret = keyring.get_password(service, username)
        if not secret:
            raise ValueError(f"Secret not found in keyring: {service}/{username}")
        return secret


class EnvProvider(SecretProvider):
    """Resolves secrets from environment variables.

    URI format: env://MY_ENV_VAR
    """

    def get_secret(self, key_uri: str) -> str:
        if not key_uri.startswith("env://"):
            return ""

        var_name = key_uri.replace("env://", "", 1)
        value = os.environ.get(var_name, "")
        if not value:
            logger.warning(f"Environment variable '{var_name}' is empty or not set")
        return value


class SecretFactory:
    """Resolves an env config dict, replacing URI values with actual secrets."""

    _providers: dict[str, SecretProvider] = {
        "keyring": SystemKeyringProvider(),
        "env": EnvProvider(),
    }

    @staticmethod
    def resolve_env_vars(env_config: dict[str, str]) -> dict[str, str]:
        """Iterate through a config dict and resolve values that use secret URI schemes.

        Plain values (no recognized scheme) are passed through unchanged.
        Resolution failures log a warning but do NOT crash the process.
        """
        resolved: dict[str, str] = {}

        for key, value in env_config.items():
            if "://" in value:
                scheme = value.split("://")[0]
                provider = SecretFactory._providers.get(scheme)
                if provider:
                    try:
                        resolved[key] = provider.get_secret(value)
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to resolve secret '{key}': {e}")
                        # Don't crash – leave empty to surface auth errors downstream
                        resolved[key] = ""
                        continue

            # Plain value – pass through
            resolved[key] = value

        return resolved
