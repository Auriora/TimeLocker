"""Routing policy tests for public CLI actions."""

import pytest

from TimeLocker.system_control.action_policy import (
    ActionClass,
    UnknownPublicActionError,
    classify_public_action,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("path", "scope", "expected", "uses_backend"),
    [
        (("version",), None, ActionClass.USER_LOCAL_READ, False),
        (("snapshots", "list"), None, ActionClass.USER_LOCAL_READ, False),
        (("selections", "create"), None, ActionClass.USER_LOCAL_MUTATION, False),
        (("logs", "view"), None, ActionClass.USER_LOCAL_READ, False),
        (("logs", "view"), "local", ActionClass.USER_LOCAL_READ, False),
        (("logs", "view"), "system", ActionClass.SYSTEM_READ, True),
        (("runs", "list"), None, ActionClass.SYSTEM_READ, True),
        (("system", "status"), None, ActionClass.SYSTEM_READ, True),
        (("system", "backup"), None, ActionClass.SYSTEM_ACTION, True),
        (
            ("system", "rollback"),
            None,
            ActionClass.ADMINISTRATOR_MAINTENANCE,
            False,
        ),
    ],
)
def test_classifier_routes_only_explicit_actions(
    path: tuple[str, ...],
    scope: str | None,
    expected: ActionClass,
    uses_backend: bool,
) -> None:
    route = classify_public_action(path, scope=scope)
    assert route.action_class is expected
    assert route.uses_system_backend is uses_backend


@pytest.mark.unit
@pytest.mark.parametrize(
    ("path", "scope"),
    [
        (("unknown",), None),
        (("logs", "view"), "protected"),
        (("runs", "delete"), None),
        (("system", "shell"), None),
        (("repos prune",), None),
    ],
)
def test_classifier_fails_closed_for_unknown_actions(
    path: tuple[str, ...],
    scope: str | None,
) -> None:
    with pytest.raises(UnknownPublicActionError):
        classify_public_action(path, scope=scope)
