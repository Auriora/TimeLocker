"""Production retention boundary tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from TimeLocker.system_control.models import RetentionPolicy, SystemPolicy
from TimeLocker.system_control.production_retention import (
    ProductionRetentionPlanProvider,
    ProductionRetentionTarget,
    TimeLockerCliRetentionAdapter,
    require_retention_enable_marker,
)


def _target(tmp_path: Path) -> ProductionRetentionTarget:
    config_directory = tmp_path / "repository-config"
    config_directory.mkdir()
    repository_config = config_directory / "config.json"
    repository_config.write_text('{"repositories":{}}\n', encoding="utf-8")
    credential_source = tmp_path / "retention.env"
    credential_source.write_text("RESTIC_PASSWORD=protected\n", encoding="utf-8")
    repository_config.chmod(0o600)
    credential_source.chmod(0o600)
    return ProductionRetentionTarget(
        target_id="production",
        repository_name="production-repository",
        config_directory=config_directory,
        repository_config=repository_config,
        credential_source=credential_source,
    )


@pytest.mark.unit
def test_loads_strict_root_config_without_embedding_protected_values(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path)
    path = tmp_path / "production-target.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "target_id": target.target_id,
                "repository_name": target.repository_name,
                "config_directory": str(target.config_directory),
                "repository_config": str(target.repository_config),
                "credential_source": str(target.credential_source),
                "snapshot_filters": [],
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)

    loaded = ProductionRetentionTarget.load(path, expected_owner=os.getuid())
    plan = loaded.plan(SystemPolicy())

    assert loaded == target
    assert plan.repository_identity.startswith("sha256:")
    assert plan.credential_source.startswith("sha256:")
    assert "protected" not in plan.credential_source


@pytest.mark.unit
def test_rejects_writable_production_target(tmp_path: Path) -> None:
    path = tmp_path / "production-target.json"
    path.write_text("{}\n", encoding="utf-8")
    path.chmod(0o666)

    with pytest.raises(PermissionError, match="must not be group/world writable"):
        ProductionRetentionTarget.load(path, expected_owner=os.getuid())


@pytest.mark.unit
def test_retention_enable_marker_must_be_protected(tmp_path: Path) -> None:
    marker = tmp_path / "retention-enabled"
    marker.touch(mode=0o600)

    require_retention_enable_marker(marker, expected_owner=os.getuid())

    marker.chmod(0o666)
    with pytest.raises(PermissionError, match="must not be group/world writable"):
        require_retention_enable_marker(marker, expected_owner=os.getuid())


@pytest.mark.unit
def test_adapter_runs_only_fixed_retention_command_and_counts_candidates(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path)
    calls: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="Retention policy applied. Removed 3 snapshots. (dry run)\n",
            stderr="",
        )

    policy = SystemPolicy(
        retention=RetentionPolicy(
            keep_daily=5,
            keep_weekly=4,
            keep_monthly=12,
            keep_yearly=3,
            group_by=("host", "paths"),
            prune=False,
        )
    )
    plan = ProductionRetentionPlanProvider(target).resolve_retention_plan(policy)
    adapter = TimeLockerCliRetentionAdapter(
        target,
        python_executable=Path("/usr/bin/python3"),
        runner=runner,
        environment={"RESTIC_PASSWORD": "protected"},
    )

    result = adapter.execute(plan, dry_run=True)

    assert result.selected_snapshots == 3
    assert result.removed_snapshots == 0
    assert calls == [
        [
            "/usr/bin/python3",
            "-m",
            "TimeLocker.cli",
            "repos",
            "forget",
            "production-repository",
            "--keep-daily",
            "5",
            "--keep-weekly",
            "4",
            "--keep-monthly",
            "12",
            "--keep-yearly",
            "3",
            "--group-by",
            "host,paths",
            "--no-prune",
            "--config-dir",
            str(target.config_directory),
            "--dry-run",
        ]
    ]


@pytest.mark.unit
def test_adapter_rejects_changed_repository_configuration(tmp_path: Path) -> None:
    target = _target(tmp_path)
    plan = target.plan(SystemPolicy())
    target.repository_config.write_text('{"repositories":{"changed":{}}}\n')
    adapter = TimeLockerCliRetentionAdapter(
        target,
        python_executable=Path("/usr/bin/python3"),
        runner=lambda *_args, **_kwargs: pytest.fail("runner must not be called"),
    )

    with pytest.raises(PermissionError, match="does not match protected target"):
        adapter.execute(plan, dry_run=True)
