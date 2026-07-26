"""Central classification for public TimeLocker operations."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class ActionClass(StrEnum):
    """Privilege boundary used when routing a public command."""

    USER_LOCAL_READ = "user_local_read"
    USER_LOCAL_MUTATION = "user_local_mutation"
    SYSTEM_READ = "system_read"
    SYSTEM_ACTION = "system_action"
    ADMINISTRATOR_MAINTENANCE = "administrator_maintenance"


class UnknownPublicActionError(ValueError):
    """Raised when an operation has no explicit routing policy."""


@dataclass(frozen=True, slots=True)
class ActionRoute:
    """One normalized public action and its required execution boundary."""

    path: tuple[str, ...]
    action_class: ActionClass

    @property
    def uses_system_backend(self) -> bool:
        """Return whether this action must cross the protected local contract."""
        return self.action_class in {
            ActionClass.SYSTEM_READ,
            ActionClass.SYSTEM_ACTION,
        }


_USER_LOCAL_READ = frozenset(
    {
        ("version",),
        ("help",),
        ("completion",),
        ("config", "show"),
        ("config", "performance"),
        ("config", "validate"),
        ("config", "diff"),
        ("snapshots", "list"),
        ("snapshots", "show"),
        ("snapshots", "find"),
        ("snapshots", "diff"),
        ("repos", "list"),
        ("repos", "show"),
        ("repos", "check"),
        ("repos", "stats"),
        ("repos", "validate"),
        ("repos", "validate-all"),
        ("restore", "list"),
        ("restore", "browse"),
        ("restore", "verify"),
        ("restore", "find"),
        ("restore", "diff"),
        ("selections", "list"),
        ("selections", "show"),
        ("selections", "test"),
        ("selections", "export"),
        ("schedule", "list"),
        ("schedule", "show"),
        ("schedule", "test"),
        ("monitor", "status"),
        ("monitor", "operations"),
        ("monitor", "health"),
        ("monitor", "history"),
        ("monitor", "stats"),
        ("logs", "search"),
        ("logs", "recent"),
        ("logs", "view"),
        ("reports", "generate"),
        ("policy", "status"),
        ("policy", "audit"),
        ("policy", "simulate"),
        ("policy", "backup", "list"),
        ("policy", "backup", "show"),
        ("policy", "retention", "list"),
        ("policy", "retention", "show"),
        ("policy", "assignment", "list"),
        ("credentials", "list"),
        ("repos", "credentials", "show"),
    }
)

_USER_LOCAL_MUTATION = frozenset(
    {
        ("backup", "create"),
        ("backup", "verify"),
        ("config", "setup"),
        ("config", "import", "restic"),
        ("config", "import", "timeshift"),
        ("config", "import", "config"),
        ("config", "export", "config"),
        ("migrate", "validate"),
        ("snapshots", "forget"),
        ("snapshots", "prune"),
        ("repos", "add"),
        ("repos", "remove"),
        ("repos", "update"),
        ("repos", "edit"),
        ("repos", "default"),
        ("repos", "lock"),
        ("repos", "mode"),
        ("repos", "init"),
        ("repos", "unlock"),
        ("repos", "migrate"),
        ("repos", "forget"),
        ("repos", "prune"),
        ("repos", "credentials", "set"),
        ("repos", "credentials", "remove"),
        ("restore", "full"),
        ("restore", "files"),
        ("restore", "mount"),
        ("restore", "umount"),
        ("selections", "create"),
        ("selections", "edit"),
        ("selections", "delete"),
        ("selections", "import"),
        ("schedule", "create"),
        ("schedule", "edit"),
        ("schedule", "delete"),
        ("schedule", "enable"),
        ("schedule", "disable"),
        ("schedule", "generate-scripts"),
        ("logs", "clear"),
        ("credentials", "unlock"),
        ("credentials", "store"),
        ("credentials", "set"),
        ("credentials", "remove"),
        ("policy", "enforce"),
        ("policy", "backup", "create"),
        ("policy", "backup", "delete"),
        ("policy", "retention", "create"),
        ("policy", "retention", "delete"),
        ("policy", "assignment", "create"),
        ("policy", "assignment", "delete"),
        ("security", "audit"),
        ("security", "status"),
        ("security", "logs"),
        ("security", "notifications"),
        ("security", "sessions"),
        ("security", "cleanup"),
        ("security", "config"),
    }
)

_SYSTEM_READ = frozenset(
    {
        ("runs", "list"),
        ("runs", "show"),
        ("logs", "view", "system"),
    }
)

_SYSTEM_ACTION = frozenset(
    {
        ("system", "backup"),
        ("system", "retention"),
    }
)

_ADMINISTRATOR_MAINTENANCE = frozenset(
    {
        ("system", "install"),
        ("system", "upgrade"),
        ("system", "rollback"),
        ("system", "operators"),
        ("system", "service"),
    }
)


def classify_public_action(
    path: Iterable[str],
    *,
    scope: str | None = None,
) -> ActionRoute:
    """Classify an exact public action, rejecting every unregistered path."""
    normalized = tuple(_normalize_part(part) for part in path)
    if normalized == ("logs", "view") and scope is not None:
        normalized_scope = _normalize_part(scope)
        if normalized_scope == "system":
            normalized = (*normalized, normalized_scope)
        elif normalized_scope != "local":
            raise UnknownPublicActionError(f"unsupported log scope: {scope!r}")

    tables = (
        (_USER_LOCAL_READ, ActionClass.USER_LOCAL_READ),
        (_USER_LOCAL_MUTATION, ActionClass.USER_LOCAL_MUTATION),
        (_SYSTEM_READ, ActionClass.SYSTEM_READ),
        (_SYSTEM_ACTION, ActionClass.SYSTEM_ACTION),
        (_ADMINISTRATOR_MAINTENANCE, ActionClass.ADMINISTRATOR_MAINTENANCE),
    )
    for actions, action_class in tables:
        if normalized in actions:
            return ActionRoute(normalized, action_class)
    raise UnknownPublicActionError(
        f"public action has no routing policy: {' '.join(normalized)}"
    )


def _normalize_part(value: object) -> str:
    if not isinstance(value, str):
        raise UnknownPublicActionError("action path parts must be strings")
    normalized = value.strip().lower()
    if not normalized or any(character.isspace() for character in normalized):
        raise UnknownPublicActionError("action path parts must be single tokens")
    return normalized
