"""Privacy guard.

Centralizes the rules that keep JARVIS-LOCAL local-first:

* Local privacy mode blocks ALL non-local network egress.
* The cloud provider must be explicitly enabled.
* Private data (files / memory) never goes to the cloud unless explicitly
  allowed.

These checks raise ``PrivacyViolation`` so callers fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from ..config import Settings

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"}


class PrivacyViolation(RuntimeError):
    pass


def is_local_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    if host in _LOCAL_HOSTS:
        return True
    # RFC1918 private ranges + .local mDNS
    if host.endswith(".local"):
        return True
    if host.startswith(("10.", "192.168.")):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) > 1 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    return False


@dataclass
class PrivacyGuard:
    settings: Settings

    # --- egress -----------------------------------------------------------
    def check_outbound(self, url: str, *, purpose: str = "network") -> None:
        """Block non-local egress when local privacy mode is on."""
        if self.settings.local_privacy_mode and not is_local_url(url):
            raise PrivacyViolation(
                f"Local Privacy Mode is ON: refused outbound {purpose} call to "
                f"{url}. Disable privacy mode or use a local endpoint."
            )

    # --- cloud model ------------------------------------------------------
    def check_cloud_model(self, provider: str) -> None:
        if provider.lower() != "cloud":
            return
        if self.settings.local_privacy_mode:
            raise PrivacyViolation(
                "Local Privacy Mode is ON: the cloud model is not allowed."
            )
        if not self.settings.enable_cloud_mode:
            raise PrivacyViolation(
                "Cloud model requested but cloud mode is disabled "
                "(set ENABLE_CLOUD_MODE=true)."
            )

    def check_private_data_to_cloud(self, provider: str, *, kind: str) -> None:
        """Guard sending file/memory content to a cloud model."""
        if provider.lower() != "cloud":
            return
        if not self.settings.allow_private_data_to_cloud:
            raise PrivacyViolation(
                f"Refusing to send private {kind} to the cloud model. Set "
                "ALLOW_PRIVATE_DATA_TO_CLOUD=true to explicitly allow this."
            )

    # --- warnings (non-fatal) --------------------------------------------
    def egress_warnings(self, provider: str, use_web: bool) -> list[str]:
        warns: list[str] = []
        if provider.lower() == "cloud":
            warns.append(
                "⚠ Cloud model is active — your prompt is sent to an external API."
            )
        if use_web and not self.settings.local_privacy_mode:
            if self.settings.search_provider in ("brave", "tavily", "serper"):
                warns.append(
                    f"⚠ Web search uses external provider '{self.settings.search_provider}'."
                )
        return warns
