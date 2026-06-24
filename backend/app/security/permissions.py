"""Permission model for tools.

Tools declare a permission level. Sensitive operations (code execution,
deleting data, cloud egress, filesystem access outside the workspace) require
an explicit grant. By default the agent runs with a conservative grant set.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Permission(str, Enum):
    read = "read"               # read-only, always safe
    network_local = "network_local"   # talk to local services
    network_external = "network_external"  # outbound internet
    memory_write = "memory_write"
    memory_delete = "memory_delete"
    file_write = "file_write"
    code_exec = "code_exec"     # run code
    fs_outside_workspace = "fs_outside_workspace"


class PermissionDenied(RuntimeError):
    pass


# Permissions granted by default (safe, local-first).
DEFAULT_GRANTS: set[Permission] = {
    Permission.read,
    Permission.network_local,
    Permission.network_external,  # web research is a core feature; gated by privacy mode
    Permission.memory_write,
}


@dataclass
class PermissionContext:
    granted: set[Permission] = field(default_factory=lambda: set(DEFAULT_GRANTS))

    def grant(self, *perms: Permission) -> None:
        self.granted.update(perms)

    def revoke(self, *perms: Permission) -> None:
        self.granted.difference_update(perms)

    def has(self, perm: Permission) -> bool:
        return perm in self.granted

    def require(self, *perms: Permission) -> None:
        missing = [p.value for p in perms if p not in self.granted]
        if missing:
            raise PermissionDenied(
                f"Operation requires permission(s) not granted: {', '.join(missing)}. "
                "Approve them explicitly to proceed."
            )


def privacy_context(local_privacy: bool, allow_code: bool) -> PermissionContext:
    ctx = PermissionContext()
    if local_privacy:
        ctx.revoke(Permission.network_external)
    if allow_code:
        ctx.grant(Permission.code_exec)
    return ctx
