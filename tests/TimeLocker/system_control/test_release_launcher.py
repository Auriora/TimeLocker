"""Immutable release resolution and rollback tests."""

import json
import os
from pathlib import Path

import pytest

from TimeLocker.system_control.release_launcher import (
    LAUNCH_GUARD,
    ImmutableReleaseResolver,
    ReleaseResolutionError,
)


RELEASE_A = "a" * 40
RELEASE_B = "b" * 40


def _stage_release(root: Path, release_id: str) -> Path:
    release = root / "releases" / release_id
    executable = release / "venv" / "bin" / "timelocker"
    executable.parent.mkdir(parents=True)
    (root / "releases").chmod(0o755)
    release.chmod(0o755)
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    for sibling in ("timelocker-system-control", "timelocker-tray"):
        sibling_executable = executable.with_name(sibling)
        sibling_executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        sibling_executable.chmod(0o755)
    manifest = release / "release.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "release_id": release_id,
                "package_version": "0.9.1",
                "protocol_version": 1,
                "entrypoint": "venv/bin/timelocker",
            }
        ),
        encoding="utf-8",
    )
    manifest.chmod(0o644)
    return executable


def _resolver(root: Path) -> ImmutableReleaseResolver:
    return ImmutableReleaseResolver(
        releases_root=root / "releases",
        selector_path=root / "selected-release.json",
        expected_owner_uid=os.getuid(),
    )


@pytest.mark.unit
def test_timelocker_and_tl_share_one_selected_release(tmp_path: Path) -> None:
    expected = _stage_release(tmp_path, RELEASE_A)
    resolver = _resolver(tmp_path)
    resolver.select(RELEASE_A)

    assert resolver.resolve({}) == expected
    assert resolver.resolve({}) == expected
    assert resolver.resolve_entrypoint("backend", {}) == expected.with_name(
        "timelocker-system-control"
    )
    assert resolver.resolve_entrypoint("tray", {}) == expected.with_name(
        "timelocker-tray"
    )


@pytest.mark.unit
def test_non_allowlisted_release_entrypoint_is_rejected(tmp_path: Path) -> None:
    _stage_release(tmp_path, RELEASE_A)
    resolver = _resolver(tmp_path)
    resolver.select(RELEASE_A)

    with pytest.raises(ReleaseResolutionError, match="allowlisted"):
        resolver.resolve_entrypoint("../../bin/sh", {})


@pytest.mark.unit
def test_release_switch_and_rollback_are_atomic_and_symmetric(tmp_path: Path) -> None:
    release_a = _stage_release(tmp_path, RELEASE_A)
    release_b = _stage_release(tmp_path, RELEASE_B)
    resolver = _resolver(tmp_path)

    resolver.select(RELEASE_A)
    resolver.select(RELEASE_B)
    assert resolver.resolve({}) == release_b

    state = resolver.rollback()
    assert state.selected == RELEASE_A
    assert state.previous == RELEASE_B
    assert resolver.resolve({}) == release_a


@pytest.mark.unit
def test_missing_selected_release_never_falls_back_to_user_environment(
    tmp_path: Path,
) -> None:
    selector = tmp_path / "selected-release.json"
    selector.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "selected": RELEASE_A,
                "previous": None,
            }
        ),
        encoding="utf-8",
    )
    resolver = _resolver(tmp_path)

    with pytest.raises(ReleaseResolutionError):
        resolver.resolve(
            {
                "PATH": str(tmp_path / "checkout"),
                "PYENV_VERSION": "3.12.6",
                "VIRTUAL_ENV": str(tmp_path / "venv"),
            }
        )


@pytest.mark.unit
def test_recursive_launch_is_rejected_before_release_resolution(
    tmp_path: Path,
) -> None:
    resolver = _resolver(tmp_path)
    with pytest.raises(ReleaseResolutionError, match="recursive"):
        resolver.resolve({LAUNCH_GUARD: "1"})


@pytest.mark.unit
@pytest.mark.parametrize("mode", [0o775, 0o777])
def test_writable_release_metadata_is_rejected(tmp_path: Path, mode: int) -> None:
    _stage_release(tmp_path, RELEASE_A)
    resolver = _resolver(tmp_path)
    resolver.select(RELEASE_A)
    manifest = tmp_path / "releases" / RELEASE_A / "release.json"
    manifest.chmod(mode)

    with pytest.raises(ReleaseResolutionError, match="writable"):
        resolver.resolve({})


@pytest.mark.unit
def test_symlinked_entrypoint_is_rejected(tmp_path: Path) -> None:
    executable = _stage_release(tmp_path, RELEASE_A)
    target = tmp_path / "outside"
    target.write_text("#!/bin/sh\n", encoding="utf-8")
    target.chmod(0o755)
    executable.unlink()
    executable.symlink_to(target)
    resolver = _resolver(tmp_path)
    resolver.selector_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "selected": RELEASE_A,
                "previous": None,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReleaseResolutionError):
        resolver.resolve({})


@pytest.mark.unit
def test_staged_launcher_has_no_pyenv_checkout_or_root_overlay_fallback() -> None:
    assets = (
        Path(__file__).parents[3] / "src" / "TimeLocker" / "system_control" / "assets"
    )
    primary = (assets / "timelocker-launcher").read_text(encoding="utf-8")
    alias = (assets / "tl-launcher").read_text(encoding="utf-8")
    backend = (assets / "timelocker-system-control-launcher").read_text(
        encoding="utf-8"
    )
    tray = (assets / "timelocker-tray-launcher").read_text(encoding="utf-8")
    for content in (primary, alias, backend, tray):
        assert "/opt/timelocker/launcher/venv/bin/python" in content
        assert "pyenv" not in content
        assert "/root/.timelocker" not in content
        assert "Projects/" not in content
    assert "-m TimeLocker.system_control.launcher_entry" in primary
    assert "-m TimeLocker.system_control.launcher_entry" in alias
    assert "-m TimeLocker.system_control.backend_launcher_entry" in backend
    assert "-m TimeLocker.system_control.tray_launcher_entry" in tray
