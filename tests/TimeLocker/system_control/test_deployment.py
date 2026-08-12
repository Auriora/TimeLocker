"""Manifest, upgrade, rollback, and preservation tests for system deployment."""

import json
import os
from pathlib import Path

import pytest

from TimeLocker.system_control.deployment import (
    AssetTarget,
    DeploymentError,
    ReleaseProbeResult,
    ReleaseProbeTargets,
    SystemReleaseDeployment,
    build_asset_manifest,
    build_release_manifest,
    linux_asset_targets,
)
from TimeLocker.system_control.release_launcher import ImmutableReleaseResolver


RELEASE_A = "a" * 40
RELEASE_B = "b" * 40


def _stage_release(root: Path, release_id: str) -> None:
    release = root / "releases" / release_id
    bin_dir = release / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    for name in ("timelocker", "timelocker-system-control", "timelocker-tray"):
        executable = bin_dir / name
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
    (release / "release.json").write_text(
        json.dumps(
            build_release_manifest(
                release_id=release_id,
                package_version="0.9.1",
            )
        )
    )
    (release / "release.json").chmod(0o644)
    release.chmod(0o755)
    (root / "releases").chmod(0o755)


def _resolver(root: Path) -> ImmutableReleaseResolver:
    return ImmutableReleaseResolver(
        releases_root=root / "releases",
        selector_path=root / "selected-release.json",
        expected_owner_uid=os.getuid(),
    )


def _passing_probe(targets: ReleaseProbeTargets) -> ReleaseProbeResult:
    return ReleaseProbeResult(
        cli_compatible=True,
        backend_compatible=True,
        tray_compatible=True,
        control_status_available=True,
        event_channel_available=True,
        backup_timer_active=True,
        backup_timer_enabled=True,
        retention_timer_active=True,
        retention_timer_enabled=True,
        control_protocol_version=targets.control_protocol_version,
        event_protocol_version=targets.event_protocol_version,
    )


@pytest.mark.unit
def test_install_validates_every_hash_before_replacing_any_asset(
    tmp_path: Path,
) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "launcher").write_text("new launcher")
    (assets / "service").write_text("new service")
    installed = tmp_path / "installed"
    existing = installed / "launcher"
    existing.parent.mkdir()
    existing.write_text("old launcher")
    targets = (
        AssetTarget("launcher", existing, 0o755),
        AssetTarget("service", installed / "service", 0o644),
    )
    manifest = build_asset_manifest(
        asset_root=assets,
        release_id=RELEASE_A,
        package_version="0.9.1",
        asset_names=("launcher", "service"),
    )
    (assets / "service").write_text("tampered")
    deployment = SystemReleaseDeployment(
        resolver=_resolver(tmp_path / "release-state"),
        targets=targets,
        expected_owner_uid=os.getuid(),
    )

    with pytest.raises(DeploymentError, match="hash mismatch"):
        deployment.install_assets(assets, manifest)

    assert existing.read_text() == "old launcher"
    assert not (installed / "service").exists()


@pytest.mark.unit
def test_upgrade_and_rollback_preserve_policy_and_run_records(tmp_path: Path) -> None:
    _stage_release(tmp_path, RELEASE_A)
    _stage_release(tmp_path, RELEASE_B)
    resolver = _resolver(tmp_path)
    deployment = SystemReleaseDeployment(
        resolver=resolver,
        targets=(AssetTarget("unused", tmp_path / "unused", 0o644),),
        expected_owner_uid=os.getuid(),
    )
    policy = tmp_path / "policy.json"
    record = tmp_path / "records" / "run.json"
    record.parent.mkdir()
    policy.write_text("approved-policy")
    record.write_text("durable-run")

    deployment.activate(RELEASE_A, health_probe=_passing_probe)
    deployment.activate(RELEASE_B, health_probe=_passing_probe)
    assert resolver.resolve({}).parts[-4] == RELEASE_B
    deployment.rollback(health_probe=_passing_probe)

    assert resolver.resolve({}).parts[-4] == RELEASE_A
    assert policy.read_text() == "approved-policy"
    assert record.read_text() == "durable-run"


@pytest.mark.unit
def test_failed_upgrade_probe_does_not_change_selected_release(tmp_path: Path) -> None:
    _stage_release(tmp_path, RELEASE_A)
    _stage_release(tmp_path, RELEASE_B)
    resolver = _resolver(tmp_path)
    deployment = SystemReleaseDeployment(
        resolver=resolver,
        targets=(AssetTarget("unused", tmp_path / "unused", 0o644),),
        expected_owner_uid=os.getuid(),
    )
    resolver.select(RELEASE_A)

    with pytest.raises(DeploymentError, match="probe failed"):
        deployment.activate(RELEASE_B, health_probe=lambda *_paths: False)

    assert resolver.resolve({}).parts[-4] == RELEASE_A


@pytest.mark.unit
def test_linux_asset_set_covers_launchers_backend_tray_and_schedules(
    tmp_path: Path,
) -> None:
    targets = linux_asset_targets(
        bin_root=tmp_path / "bin",
        admin_bin_root=tmp_path / "sbin",
        libexec_root=tmp_path / "libexec",
        unit_root=tmp_path / "units",
        config_root=tmp_path / "etc",
        autostart_root=tmp_path / "autostart",
        icon_root=tmp_path / "icons",
    )
    sources = {target.source_name for target in targets}

    assert {
        "timelocker-launcher",
        "tl-launcher",
        "timelocker-system-control-launcher",
        "timelocker-deploy-launcher",
        "timelocker-tray-launcher",
        "timelocker-control.service",
        "timelocker-control.socket",
        "timelocker-retention.service",
        "timelocker-retention.timer",
        "timelocker-tray.desktop",
        "timelocker-icon.png",
        "timelocker-icon-connecting.png",
        "timelocker-icon-idle.png",
        "timelocker-icon-running.png",
        "timelocker-icon-success.png",
        "timelocker-icon-warning.png",
        "timelocker-icon-error.png",
    } <= sources
    deploy = next(
        target for target in targets if target.source_name == "timelocker-deploy-launcher"
    )
    assert deploy.destination == tmp_path / "sbin" / "timelocker-deploy"
    assert deploy.mode == 0o750
    assert "timelocker-status-events.socket" not in sources
    policy = next(
        target
        for target in targets
        if target.source_name == "system-control-policy.json"
    )
    assert policy.preserve_existing
    icon = next(
        target for target in targets if target.source_name == "timelocker-icon.png"
    )
    assert icon.destination == tmp_path / "icons" / "timelocker.png"
    assert icon.mode == 0o644
    error_icon = next(
        target
        for target in targets
        if target.source_name == "timelocker-icon-error.png"
    )
    assert error_icon.destination == tmp_path / "icons" / "timelocker-error.png"
    assert error_icon.mode == 0o644


@pytest.mark.unit
@pytest.mark.parametrize(
    "failed_field",
    [
        "control_status_available",
        "backup_timer_active",
        "backup_timer_enabled",
        "retention_timer_active",
        "retention_timer_enabled",
    ],
)
def test_activation_requires_protocol_socket_and_timer_health(
    tmp_path: Path,
    failed_field: str,
) -> None:
    _stage_release(tmp_path, RELEASE_A)
    resolver = _resolver(tmp_path)
    deployment = SystemReleaseDeployment(
        resolver=resolver,
        targets=(AssetTarget("unused", tmp_path / "unused", 0o644),),
        expected_owner_uid=os.getuid(),
    )

    def probe(targets: ReleaseProbeTargets) -> ReleaseProbeResult:
        values = {
            "cli_compatible": True,
            "backend_compatible": True,
            "tray_compatible": True,
            "control_status_available": True,
            "event_channel_available": True,
            "backup_timer_active": True,
            "backup_timer_enabled": True,
            "retention_timer_active": True,
            "retention_timer_enabled": True,
            "control_protocol_version": targets.control_protocol_version,
            "event_protocol_version": targets.event_protocol_version,
        }
        values[failed_field] = False
        return ReleaseProbeResult(**values)

    with pytest.raises(DeploymentError, match="probe failed"):
        deployment.activate(RELEASE_A, health_probe=probe)

    assert not resolver.selector_path.exists()


@pytest.mark.unit
def test_rollback_does_not_require_legacy_event_socket(
    tmp_path: Path,
) -> None:
    _stage_release(tmp_path, RELEASE_A)
    _stage_release(tmp_path, RELEASE_B)
    resolver = _resolver(tmp_path)
    resolver.select(RELEASE_A)
    resolver.select(RELEASE_B)
    deployment = SystemReleaseDeployment(
        resolver=resolver,
        targets=(AssetTarget("unused", tmp_path / "unused", 0o644),),
        expected_owner_uid=os.getuid(),
    )

    def rollback_probe(targets: ReleaseProbeTargets) -> ReleaseProbeResult:
        result = _passing_probe(targets)
        return ReleaseProbeResult(
            cli_compatible=result.cli_compatible,
            backend_compatible=result.backend_compatible,
            tray_compatible=result.tray_compatible,
            control_status_available=result.control_status_available,
            event_channel_available=False,
            backup_timer_active=result.backup_timer_active,
            backup_timer_enabled=result.backup_timer_enabled,
            retention_timer_active=result.retention_timer_active,
            retention_timer_enabled=result.retention_timer_enabled,
            control_protocol_version=result.control_protocol_version,
            event_protocol_version=result.event_protocol_version,
        )

    selected = deployment.rollback(health_probe=rollback_probe)

    assert selected.selected == RELEASE_A
