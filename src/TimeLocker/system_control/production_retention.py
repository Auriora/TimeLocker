"""Root-configured Restic retention adapter for the system-control backend."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from .models import RetentionPolicy, SystemPolicy
from .retention import RetentionExecutionResult, RetentionPlan
from .validation import require_exact_mapping, require_safe_identifier


DEFAULT_PRODUCTION_TARGET_PATH = Path("/etc/timelocker/production-target.json")
DEFAULT_RETENTION_ENABLE_MARKER = Path("/etc/timelocker/retention-enabled")
_CONFIG_FIELDS = frozenset(
    {
        "schema_version",
        "target_id",
        "repository_name",
        "config_directory",
        "repository_config",
        "credential_source",
        "snapshot_filters",
    }
)
_REMOVED_PATTERN = re.compile(r"\bRemoved\s+([0-9]+)\s+snapshot")


@dataclass(frozen=True, slots=True)
class ProductionRetentionTarget:
    """Secret-free references to one root-owned production target."""

    target_id: str
    repository_name: str
    config_directory: Path
    repository_config: Path
    credential_source: Path
    snapshot_filters: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("target_id", "repository_name"):
            object.__setattr__(
                self,
                field_name,
                require_safe_identifier(
                    getattr(self, field_name),
                    field=field_name,
                    maximum=128,
                ),
            )
        for field_name in (
            "config_directory",
            "repository_config",
            "credential_source",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, Path) or not value.is_absolute():
                raise ValueError(f"{field_name} must be an absolute Path")
        if type(self.snapshot_filters) is not tuple:
            raise TypeError("snapshot_filters must be a tuple")
        for value in self.snapshot_filters:
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 1_024
                or "\x00" in value
            ):
                raise ValueError("snapshot_filters must contain bounded strings")

    @classmethod
    def load(
        cls,
        path: Path = DEFAULT_PRODUCTION_TARGET_PATH,
        *,
        expected_owner: int = 0,
    ) -> "ProductionRetentionTarget":
        """Load a strict root-owned target without exposing protected values."""
        _require_protected_file(path, expected_owner=expected_owner)
        value = json.loads(path.read_text(encoding="utf-8"))
        mapping = require_exact_mapping(
            value,
            field="production retention target",
            required=_CONFIG_FIELDS,
        )
        if mapping["schema_version"] != 1:
            raise ValueError("unsupported production target schema")
        filters = mapping["snapshot_filters"]
        if not isinstance(filters, list):
            raise TypeError("snapshot_filters must be a list")
        target = cls(
            target_id=mapping["target_id"],
            repository_name=mapping["repository_name"],
            config_directory=Path(mapping["config_directory"]),
            repository_config=Path(mapping["repository_config"]),
            credential_source=Path(mapping["credential_source"]),
            snapshot_filters=tuple(filters),
        )
        _require_protected_file(
            target.repository_config,
            expected_owner=expected_owner,
        )
        _require_protected_file(
            target.credential_source,
            expected_owner=expected_owner,
        )
        return target

    def plan(self, policy: SystemPolicy) -> RetentionPlan:
        """Build the exact reviewable plan using hashes, never secret contents."""
        if not isinstance(policy, SystemPolicy):
            raise TypeError("policy must be a SystemPolicy")
        return RetentionPlan(
            target_id=self.target_id,
            repository_identity=_file_identity(self.repository_config),
            credential_source=_file_identity(self.credential_source),
            snapshot_filters=self.snapshot_filters,
            policy=RetentionPolicy(
                keep_daily=policy.retention.keep_daily,
                keep_weekly=policy.retention.keep_weekly,
                keep_monthly=policy.retention.keep_monthly,
                keep_yearly=policy.retention.keep_yearly,
                group_by=policy.retention.group_by,
                prune=policy.retention.prune,
                approved_fingerprint=policy.retention.approved_fingerprint,
            ),
        )


class ProductionRetentionPlanProvider:
    """Resolve a policy-bound plan from protected root configuration."""

    def __init__(self, target: ProductionRetentionTarget) -> None:
        if not isinstance(target, ProductionRetentionTarget):
            raise TypeError("target must be a ProductionRetentionTarget")
        self.target = target

    def resolve_retention_plan(self, policy: SystemPolicy) -> RetentionPlan:
        return self.target.plan(policy)


class TimeLockerCliRetentionAdapter:
    """Invoke the existing repository service with a fixed, allowlisted command."""

    def __init__(
        self,
        target: ProductionRetentionTarget,
        *,
        python_executable: Path | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(target, ProductionRetentionTarget):
            raise TypeError("target must be a ProductionRetentionTarget")
        executable = python_executable or Path(sys.executable)
        if not executable.is_absolute():
            raise ValueError("python_executable must be absolute")
        self.target = target
        self.python_executable = executable
        self._runner = runner or subprocess.run
        self._environment = dict(environment) if environment is not None else None

    def execute(
        self,
        plan: RetentionPlan,
        *,
        dry_run: bool,
    ) -> RetentionExecutionResult:
        if not isinstance(plan, RetentionPlan):
            raise TypeError("plan must be a RetentionPlan")
        if type(dry_run) is not bool:
            raise TypeError("dry_run must be a bool")
        expected = self.target.plan(
            SystemPolicy(retention=plan.policy),
        )
        if (
            plan.target_id != expected.target_id
            or plan.repository_identity != expected.repository_identity
            or plan.credential_source != expected.credential_source
            or plan.snapshot_filters != expected.snapshot_filters
        ):
            raise PermissionError("retention plan does not match protected target")

        command = [
            str(self.python_executable),
            "-m",
            "TimeLocker.cli",
            "repos",
            "forget",
            self.target.repository_name,
            "--keep-daily",
            str(plan.policy.keep_daily),
            "--keep-weekly",
            str(plan.policy.keep_weekly),
            "--keep-monthly",
            str(plan.policy.keep_monthly),
            "--keep-yearly",
            str(plan.policy.keep_yearly),
            "--group-by",
            ",".join(plan.policy.group_by),
            "--no-prune",
            "--config-dir",
            str(self.target.config_directory),
        ]
        if dry_run:
            command.append("--dry-run")
        result = self._runner(
            command,
            capture_output=True,
            text=True,
            check=False,
            cwd="/",
            env=self._environment or os.environ.copy(),
            timeout=4 * 60 * 60,
        )
        if result.returncode != 0:
            raise RuntimeError("retention command failed")
        selected = _removed_count(result.stdout)
        return RetentionExecutionResult(
            selected_snapshots=selected,
            removed_snapshots=0 if dry_run else selected,
        )


def load_production_retention_components(
    *,
    target_path: Path = DEFAULT_PRODUCTION_TARGET_PATH,
    expected_owner: int = 0,
) -> tuple[TimeLockerCliRetentionAdapter, ProductionRetentionPlanProvider]:
    """Load the production components or fail before any repository access."""
    target = ProductionRetentionTarget.load(
        target_path,
        expected_owner=expected_owner,
    )
    return (
        TimeLockerCliRetentionAdapter(target),
        ProductionRetentionPlanProvider(target),
    )


def require_retention_enable_marker(
    path: Path = DEFAULT_RETENTION_ENABLE_MARKER,
    *,
    expected_owner: int = 0,
) -> None:
    """Refuse every retention mutation until the protected marker exists."""
    _require_protected_file(path, expected_owner=expected_owner)


def _removed_count(output: str) -> int:
    matches = _REMOVED_PATTERN.findall(output)
    if not matches:
        return 0
    return sum(int(value) for value in matches)


def _file_identity(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _require_protected_file(path: Path, *, expected_owner: int) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError("protected file path must be absolute")
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("protected path must be a regular file")
    if metadata.st_uid != expected_owner:
        raise PermissionError("protected file has an unexpected owner")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise PermissionError("protected file must be owner-only")


__all__: Sequence[str] = (
    "DEFAULT_PRODUCTION_TARGET_PATH",
    "DEFAULT_RETENTION_ENABLE_MARKER",
    "ProductionRetentionPlanProvider",
    "ProductionRetentionTarget",
    "TimeLockerCliRetentionAdapter",
    "load_production_retention_components",
    "require_retention_enable_marker",
)
