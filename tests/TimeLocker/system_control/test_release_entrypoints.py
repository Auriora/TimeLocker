"""Failure-safe tests for staged release administration entry points."""

from unittest.mock import Mock, patch

import pytest

from TimeLocker.system_control import launcher_entry, release_admin
from TimeLocker.system_control.release_launcher import (
    ReleaseResolutionError,
    SelectedRelease,
)


@pytest.mark.unit
def test_launcher_entry_translates_resolution_failure_without_details(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch.object(
        launcher_entry,
        "launch_selected",
        side_effect=ReleaseResolutionError("sensitive path detail"),
    ):
        with pytest.raises(SystemExit) as caught:
            launcher_entry.main()
    assert caught.value.code == 78
    output = capsys.readouterr()
    assert "selected-release.json" in output.err
    assert "sensitive path detail" not in output.err


@pytest.mark.unit
@pytest.mark.parametrize(
    ("arguments", "method"),
    [
        (["timelocker-release-select", "select", "a" * 40], "select"),
        (["timelocker-release-select", "rollback"], "rollback"),
    ],
)
def test_release_admin_uses_only_bounded_selector_operations(
    arguments: list[str],
    method: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolver = Mock()
    getattr(resolver, method).return_value = SelectedRelease(selected="a" * 40)
    with (
        patch.object(release_admin, "ImmutableReleaseResolver", return_value=resolver),
        patch("sys.argv", arguments),
    ):
        release_admin.main()
    getattr(resolver, method).assert_called_once()
    assert capsys.readouterr().out.strip() == "a" * 40


@pytest.mark.unit
def test_release_admin_returns_configuration_exit_on_invalid_release(
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolver = Mock()
    resolver.rollback.side_effect = ReleaseResolutionError("no previous release")
    with (
        patch.object(release_admin, "ImmutableReleaseResolver", return_value=resolver),
        patch("sys.argv", ["timelocker-release-select", "rollback"]),
    ):
        with pytest.raises(SystemExit) as caught:
            release_admin.main()
    assert caught.value.code == 78
    assert "release selection failed" in capsys.readouterr().err


@pytest.mark.unit
def test_release_admin_forwards_expected_current_compare_and_swap(
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolver = Mock()
    resolver.select.return_value = SelectedRelease(selected="b" * 40)
    with (
        patch.object(release_admin, "ImmutableReleaseResolver", return_value=resolver),
        patch(
            "sys.argv",
            [
                "timelocker-release-select",
                "select",
                "b" * 40,
                "--expected-current",
                "a" * 40,
            ],
        ),
    ):
        release_admin.main()

    resolver.select.assert_called_once_with(
        "b" * 40,
        expected_current="a" * 40,
    )
    assert capsys.readouterr().out.strip() == "b" * 40
