"""Supported daemonless protected deployment entrypoint contracts."""

from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from TimeLocker.system_control import deployment_entry as entry
from TimeLocker.system_control.deployment import AssetTarget, linux_asset_targets


RELEASE_A = "a" * 40


def _paths(root: Path) -> entry.DeploymentPaths:
    return entry.DeploymentPaths(
        releases_root=root / "opt/timelocker/releases",
        selector=root / "opt/timelocker/selected-release.json",
        service_unit=root / "etc/systemd/system/timelocker-control.service",
        evidence_root=root / "var/lib/timelocker/deployments",
        lock_file=root / "run/lock/timelocker-deploy.lock",
        launcher_venv=root / "opt/timelocker/launcher/venv",
        legacy_event_socket=root / "run/timelocker/status-events.sock",
        attention_file=root / "var/lib/timelocker/deployment-attention.json",
        expected_owner_uid=os.getuid(),
    )


def _wheel(root: Path, *, include_legacy_event: bool = False) -> Path:
    wheel = root / "timelocker-0.9.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "timelocker-0.9.1.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: timelocker\nVersion: 0.9.1\n",
        )
        for target in linux_asset_targets():
            content = "asset\n"
            if target.source_name == "timelocker-control.service":
                content = (
                    "[Unit]\nRequires=timelocker-control.socket\n"
                    "[Service]\nType=exec\nSockets=timelocker-control.socket\n"
                    "RuntimeDirectoryPreserve=yes\n"
                )
            archive.writestr(
                f"TimeLocker/system_control/assets/{target.source_name}", content
            )
        if include_legacy_event:
            archive.writestr(
                "TimeLocker/system_control/assets/timelocker-status-events.socket",
                "legacy\n",
            )
    return wheel


def _prepare_roots(paths: entry.DeploymentPaths) -> None:
    entry._prepare_protected_roots(paths)


@pytest.mark.unit
def test_local_wheel_identity_and_daemonless_manifest_are_derived(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _prepare_roots(paths)
    wheel = _wheel(tmp_path)

    request = entry._derive_request(
        wheel,
        expected_current=RELEASE_A,
        operator_user=getpass.getuser(),
        paths=paths,
    )

    assert request.release_id == entry._sha256(wheel)[:40]
    assert request.wheel_sha256 == entry._sha256(wheel)
    manifest = json.loads(request.manifest.read_text())
    assert manifest == {
        "schema_version": 3,
        "release_id": request.release_id,
        "package_version": "0.9.1",
        "control_protocol_version": 2,
        "entrypoint": "venv/bin/timelocker",
    }


@pytest.mark.unit
def test_local_wheel_rejects_legacy_event_service_asset(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _prepare_roots(paths)

    with pytest.raises(entry.DeploymentFailure, match="asset set"):
        entry._derive_request(
            _wheel(tmp_path, include_legacy_event=True),
            expected_current=None,
            operator_user=getpass.getuser(),
            paths=paths,
        )


@pytest.mark.unit
def test_verified_release_retry_is_idempotent() -> None:
    assert (
        entry._release_request_disposition(
            "install", current=RELEASE_A, candidate=RELEASE_A
        )
        == "already_selected"
    )
    assert (
        entry._release_request_disposition(
            "upgrade", current=RELEASE_A, candidate=RELEASE_A
        )
        == "already_selected"
    )
    assert (
        entry._release_request_disposition(
            "install", current=RELEASE_A, candidate="b" * 40
        )
        == "already_installed"
    )


@pytest.mark.unit
def test_packaged_service_requires_single_control_socket_and_no_event_service(
    tmp_path: Path,
) -> None:
    release = tmp_path / ("b" * 40)
    unit = release / "assets/timelocker-control.service"
    unit.parent.mkdir(parents=True)
    unit.write_text(
        "[Unit]\nRequires=timelocker-control.socket\n"
        "[Service]\nType=exec\nSockets=timelocker-control.socket\n"
        "RuntimeDirectoryPreserve=yes\n"
    )
    request = entry.DeploymentRequest(
        release_id="b" * 40,
        expected_current=None,
        wheel=tmp_path / "unused.whl",
        wheel_sha256="c" * 64,
        manifest=tmp_path / "release.json",
        operator_user=getpass.getuser(),
    )
    deployer = entry.T011LinuxDeployer(request, owner_uid=os.getuid())
    deployer.release = release

    deployer._validate_packaged_unit(unit)
    unit.write_text(unit.read_text() + "Wants=timelocker-status-events.socket\n")
    with pytest.raises(entry.DeploymentFailure, match="event socket"):
        deployer._validate_packaged_unit(unit)


@pytest.mark.unit
def test_initial_install_validation_does_not_require_running_units(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    _prepare_roots(paths)
    wheel = tmp_path / "timelocker-0.9.1-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    manifest = tmp_path / "release.json"
    manifest.write_text("{}")
    commands: list[list[str]] = []

    class Executor:
        def run(self, arguments, **_kwargs):
            commands.append([str(value) for value in arguments])
            return ""

    deployer = entry.T011LinuxDeployer(
        entry.DeploymentRequest(
            release_id="b" * 40,
            expected_current=None,
            wheel=wheel,
            wheel_sha256=entry._sha256(wheel),
            manifest=manifest,
            operator_user=getpass.getuser(),
        ),
        paths=paths,
        executor=Executor(),
        owner_uid=os.getuid(),
        owner_gid=os.getgid(),
        asset_targets=(
            AssetTarget("timelocker-control.service", paths.service_unit, 0o644),
        ),
    )

    deployer.validate_request()
    assert commands == []


@pytest.mark.unit
def test_upgrade_validation_allows_stopped_legacy_control_socket(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    _prepare_roots(paths)
    paths.launcher_venv.mkdir(parents=True)
    paths.launcher_venv.chmod(0o755)
    launcher_python = paths.launcher_venv / "bin/python"
    launcher_python.parent.mkdir()
    launcher_python.parent.chmod(0o755)
    launcher_python.write_text("#!/bin/sh\n")
    launcher_python.chmod(0o755)
    paths.selector.write_text(
        json.dumps(
            {"schema_version": 1, "selected": RELEASE_A, "previous": None}
        )
    )
    paths.selector.chmod(0o644)
    wheel = tmp_path / "timelocker-0.9.1-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    manifest = tmp_path / "release.json"
    manifest.write_text("{}")
    commands: list[list[str]] = []

    class Executor:
        def run(self, arguments, **_kwargs):
            commands.append([str(value) for value in arguments])
            return ""

    deployer = entry.T011LinuxDeployer(
        entry.DeploymentRequest(
            release_id="b" * 40,
            expected_current=RELEASE_A,
            wheel=wheel,
            wheel_sha256=entry._sha256(wheel),
            manifest=manifest,
            operator_user=getpass.getuser(),
        ),
        paths=paths,
        executor=Executor(),
        owner_uid=os.getuid(),
        owner_gid=os.getgid(),
    )

    deployer.validate_request()

    assert ["systemctl", "is-active", "--quiet", "timelocker-control.socket"] not in commands
    for unit in entry.PRE_ACTIVATION_ACTIVE_UNITS:
        assert ["systemctl", "is-active", "--quiet", unit] in commands
    for unit in entry.REQUIRED_ENABLED_UNITS:
        assert ["systemctl", "is-enabled", "--quiet", unit] in commands


@pytest.mark.unit
def test_status_reports_zero_resident_service_contract(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.selector.parent.mkdir(parents=True)
    paths.selector.parent.chmod(0o755)
    paths.selector.write_text(
        json.dumps(
            {"schema_version": 1, "selected": RELEASE_A, "previous": None}
        )
    )
    paths.selector.chmod(0o644)
    paths.service_unit.parent.mkdir(parents=True)
    paths.service_unit.write_text(
        "[Service]\nType=exec\nSockets=timelocker-control.socket\n"
        "RuntimeDirectoryPreserve=yes\n"
    )

    assert entry._deployment_status(paths, unit_probe=lambda _action, _unit: True) == {
        "operation": "status",
        "result_code": "installed",
        "selected_release": RELEASE_A,
        "previous_release": None,
        "one_shot_helper_ready": True,
        "resident_service_required": False,
        "attention_required": False,
        "control_socket_active": True,
        "control_socket_enabled": True,
        "backup_timer_active": True,
        "backup_timer_enabled": True,
        "retention_timer_active": True,
        "retention_timer_enabled": True,
    }


@pytest.mark.unit
def test_status_on_clean_host_is_not_installed_and_reports_unit_health(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)

    payload = entry._deployment_status(
        paths,
        unit_probe=lambda _action, _unit: False,
    )

    assert payload["result_code"] == "not_installed"
    assert payload["one_shot_helper_ready"] is False
    assert payload["backup_timer_active"] is False
    assert payload["retention_timer_enabled"] is False


@pytest.mark.unit
def test_private_evidence_writer_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("unchanged")
    link = tmp_path / "evidence.json"
    link.symlink_to(target)

    with pytest.raises(OSError):
        entry._write_private_text(link, "replacement")

    assert target.read_text() == "unchanged"


@pytest.mark.unit
def test_activation_enables_only_the_on_demand_control_socket(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    _prepare_roots(paths)
    release_id = "b" * 40
    manifest = tmp_path / "release.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "release_id": release_id,
                "package_version": "0.9.1",
                "control_protocol_version": 2,
                "entrypoint": "venv/bin/timelocker",
            }
        )
    )
    wheel = tmp_path / "timelocker-0.9.1-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    commands: list[list[str]] = []
    packaged_unit = tmp_path / "packaged/timelocker-control.service"
    packaged_unit.parent.mkdir()
    packaged_unit.write_text("[Service]\nType=exec\n")

    class Executor:
        def run(self, arguments, **kwargs):
            command = [str(value) for value in arguments]
            commands.append(command)
            if "PACKAGED_UNIT_PROBE" in str(arguments):
                return str(packaged_unit)
            if "importlib.resources" in str(arguments):
                return str(packaged_unit)
            return ""

    class AssetInstaller:
        def __init__(self, **_kwargs):
            pass

        def install_assets(self, _root, _manifest):
            return None

    request = entry.DeploymentRequest(
        release_id=release_id,
        expected_current=None,
        wheel=wheel,
        wheel_sha256=entry._sha256(wheel),
        manifest=manifest,
        operator_user=getpass.getuser(),
    )
    deployer = entry.T011LinuxDeployer(
        request,
        paths=paths,
        executor=Executor(),
        owner_uid=os.getuid(),
        owner_gid=os.getgid(),
        asset_targets=(
            AssetTarget("timelocker-control.service", paths.service_unit, 0o644),
        ),
    )
    deployer.release.mkdir(parents=True)
    (deployer.release / "venv/bin").mkdir(parents=True)
    deployer.staged_launcher.mkdir(parents=True)
    deployer.evidence = tmp_path / "evidence"
    deployer.evidence.mkdir()
    deployer.staged_manifest = manifest
    monkeypatch.setattr(entry, "SystemReleaseDeployment", AssetInstaller)
    monkeypatch.setattr(entry, "build_asset_manifest", lambda **_kwargs: object())
    monkeypatch.setattr(entry, "_selected_release_optional", lambda _path: None)

    deployer.activate()

    enable_commands = [command for command in commands if "enable" in command]
    assert enable_commands == [
        ["systemctl", "enable", "--now", "timelocker-control.socket"]
    ]
    assert all("timelocker-retention.timer" not in command for command in commands)
    assert all(
        "timelocker-npbackup-migration.timer" not in command for command in commands
    )


@pytest.mark.unit
def test_mutating_command_returns_one_json_elevation_instruction(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(entry.os, "geteuid", lambda: 1000)

    assert entry.main(["upgrade", "/not/read.whl", "--operator-user", "user"]) == 77
    payload = json.loads(capsys.readouterr().out)
    assert payload["result_code"] == "elevation_required"
    assert payload["next_action"] == "run this command with sudo"


@pytest.mark.unit
def test_rollback_rejects_release_that_requires_resident_event_service(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _paths(tmp_path)
    _prepare_roots(paths)
    for release_id in (RELEASE_A, "b" * 40):
        executable = paths.releases_root / release_id / "venv/bin/timelocker"
        executable.parent.mkdir(parents=True)
        executable.write_text("#!/bin/sh\n")
        executable.chmod(0o755)
        for name in ("timelocker-system-control", "timelocker-tray"):
            sibling = executable.with_name(name)
            sibling.write_text("#!/bin/sh\n")
            sibling.chmod(0o755)
        (executable.parents[2] / "release.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "release_id": release_id,
                    "package_version": "0.9.1",
                    "control_protocol_version": 2,
                    "event_protocol_version": 1,
                    "entrypoint": "venv/bin/timelocker",
                }
            )
        )
    paths.selector.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "selected": "b" * 40,
                "previous": RELEASE_A,
            }
        )
    )

    assert entry._run_rollback(paths) == 1
    assert json.loads(capsys.readouterr().out)["result_code"] == "rollback_failed"


@pytest.mark.unit
def test_rollback_verifies_control_and_timer_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _paths(tmp_path)
    _prepare_roots(paths)
    commands: list[list[str]] = []

    class Resolver:
        def __init__(self, **_kwargs):
            pass

        def _read_selector_optional(self):
            return SimpleNamespace(selected="b" * 40, previous=RELEASE_A)

        def release_manifest(self, _release_id):
            return SimpleNamespace(schema_version=3)

        def rollback(self):
            return SimpleNamespace(selected=RELEASE_A, previous="b" * 40)

    class Executor:
        def run(self, arguments, **_kwargs):
            commands.append([str(value) for value in arguments])
            return ""

    monkeypatch.setattr(entry, "ImmutableReleaseResolver", Resolver)
    monkeypatch.setattr(entry, "CommandExecutor", Executor)

    assert entry._run_rollback(paths) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["result_code"] == "rolled_back"
    assert ["systemctl", "restart", "timelocker-control.socket"] in commands
    for unit in entry.REQUIRED_ACTIVE_UNITS:
        assert ["systemctl", "is-active", "--quiet", unit] in commands
    for unit in entry.REQUIRED_ENABLED_UNITS:
        assert ["systemctl", "is-enabled", "--quiet", unit] in commands


@pytest.mark.unit
def test_compatibility_wrapper_routes_to_installed_entrypoint() -> None:
    wrapper = Path("scripts/deploy_t011_linux.py").read_text()
    assert "Deprecated Spec 010 compatibility wrapper" in wrapper
    assert "deployment_entry" in wrapper
