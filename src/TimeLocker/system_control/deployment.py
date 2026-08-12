"""Compatibility-checked installation and activation of system assets."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil

from .models import PROTOCOL_VERSION, STATUS_EVENT_PROTOCOL_VERSION
from .release_launcher import (
    ImmutableReleaseResolver,
    ReleaseManifest,
    SelectedRelease,
)
from .validation import require_bool, require_int, require_safe_identifier


class DeploymentError(RuntimeError):
    """Raised before an incomplete or incompatible deployment is activated."""


@dataclass(frozen=True, slots=True)
class AssetTarget:
    """One packaged asset and its root-owned installation target."""

    source_name: str
    destination: Path
    mode: int
    preserve_existing: bool = False


@dataclass(frozen=True, slots=True)
class SystemAssetManifest:
    """Exact hashes and protocol identity for one packaged system asset set."""

    release_id: str
    package_version: str
    hashes: Mapping[str, str]
    protocol_version: int = PROTOCOL_VERSION
    schema_version: int = 1

    def __post_init__(self) -> None:
        require_safe_identifier(self.release_id, field="release_id", maximum=64)
        require_safe_identifier(
            self.package_version,
            field="package_version",
            maximum=64,
        )
        require_int(
            self.protocol_version,
            field="protocol_version",
            minimum=PROTOCOL_VERSION,
            maximum=PROTOCOL_VERSION,
        )
        require_int(
            self.schema_version,
            field="schema_version",
            minimum=1,
            maximum=1,
        )
        if not self.hashes:
            raise ValueError("asset manifest must contain hashes")
        for name, digest in self.hashes.items():
            require_safe_identifier(name, field="asset_name", maximum=128)
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError("asset hash must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class ReleaseProbeTargets:
    """Trusted artifacts and protocol versions a probe must exercise."""

    cli: Path
    backend: Path
    tray: Path
    control_protocol_version: int
    event_protocol_version: int | None


@dataclass(frozen=True, slots=True)
class ReleaseProbeResult:
    """Fail-closed activation evidence returned by the deployment probe."""

    cli_compatible: bool
    backend_compatible: bool
    tray_compatible: bool
    control_status_available: bool
    event_channel_available: bool
    backup_timer_active: bool
    backup_timer_enabled: bool
    retention_timer_active: bool
    retention_timer_enabled: bool
    control_protocol_version: int
    event_protocol_version: int | None

    def __post_init__(self) -> None:
        for field_name in (
            "cli_compatible",
            "backend_compatible",
            "tray_compatible",
            "control_status_available",
            "event_channel_available",
            "backup_timer_active",
            "backup_timer_enabled",
            "retention_timer_active",
            "retention_timer_enabled",
        ):
            require_bool(getattr(self, field_name), field=field_name)
        require_int(
            self.control_protocol_version,
            field="control_protocol_version",
            minimum=PROTOCOL_VERSION,
            maximum=PROTOCOL_VERSION,
        )
        if self.event_protocol_version is not None:
            require_int(
                self.event_protocol_version,
                field="event_protocol_version",
                minimum=STATUS_EVENT_PROTOCOL_VERSION,
                maximum=STATUS_EVENT_PROTOCOL_VERSION,
            )


ReleaseHealthProbe = Callable[[ReleaseProbeTargets], ReleaseProbeResult]


class SystemReleaseDeployment:
    """Install a validated asset set and activate only healthy staged releases."""

    def __init__(
        self,
        *,
        resolver: ImmutableReleaseResolver,
        targets: tuple[AssetTarget, ...],
        expected_owner_uid: int = 0,
    ) -> None:
        if not targets:
            raise ValueError("at least one asset target is required")
        self.resolver = resolver
        self.targets = targets
        self.expected_owner_uid = expected_owner_uid

    def install_assets(
        self,
        asset_root: Path,
        manifest: SystemAssetManifest,
    ) -> tuple[Path, ...]:
        """Validate all sources before atomically replacing install targets."""
        expected_names = {target.source_name for target in self.targets}
        if set(manifest.hashes) != expected_names:
            raise DeploymentError("asset manifest does not match install target set")
        sources: dict[str, Path] = {}
        for target in self.targets:
            source = asset_root / target.source_name
            if not source.is_file() or source.is_symlink():
                raise DeploymentError("required packaged asset is unavailable")
            if _sha256(source) != manifest.hashes[target.source_name]:
                raise DeploymentError("packaged asset hash mismatch")
            sources[target.source_name] = source

        installed: list[Path] = []
        for target in self.targets:
            if target.preserve_existing and target.destination.exists():
                continue
            _atomic_copy(
                sources[target.source_name],
                target.destination,
                mode=target.mode,
            )
            metadata = target.destination.lstat()
            if metadata.st_uid != self.expected_owner_uid:
                raise DeploymentError("installed asset has the wrong owner")
            if metadata.st_mode & 0o777 != target.mode:
                raise DeploymentError("installed asset has the wrong mode")
            installed.append(target.destination)
        return tuple(installed)

    def activate(
        self,
        release_id: str,
        *,
        health_probe: ReleaseHealthProbe,
    ) -> SelectedRelease:
        """Select a release only after its complete compatibility probe passes."""
        manifest = self.resolver.release_manifest(release_id)
        targets = self._probe_targets(release_id, manifest)
        result = health_probe(targets)
        if not self._probe_passed(result, targets, require_event=False):
            raise DeploymentError("staged release compatibility probe failed")
        return self.resolver.select(release_id)

    def _probe_targets(
        self,
        release_id: str,
        manifest: ReleaseManifest,
    ) -> ReleaseProbeTargets:
        return ReleaseProbeTargets(
            cli=self.resolver._resolve_release(
                release_id,
                entrypoint="venv/bin/timelocker",
            ),
            backend=self.resolver._resolve_release(
                release_id,
                entrypoint="venv/bin/timelocker-system-control",
            ),
            tray=self.resolver._resolve_release(
                release_id,
                entrypoint="venv/bin/timelocker-tray",
            ),
            control_protocol_version=manifest.control_protocol_version,
            event_protocol_version=manifest.event_protocol_version,
        )

    def rollback(
        self,
        *,
        health_probe: ReleaseHealthProbe,
    ) -> SelectedRelease:
        """Restore the prior selector while preserving control and timer health."""
        current = self.resolver._read_selector_optional()
        if current is None or current.previous is None:
            raise DeploymentError("no previous release is available")
        manifest = self.resolver.release_manifest(current.previous)
        if manifest.schema_version < 3:
            raise DeploymentError(
                "rollback release requires the rejected resident status service"
            )
        targets = self._probe_targets(current.previous, manifest)
        result = health_probe(targets)
        if not self._probe_passed(result, targets, require_event=False):
            raise DeploymentError("rollback release compatibility probe failed")
        return self.resolver.rollback()

    @staticmethod
    def _probe_passed(
        result: object,
        targets: ReleaseProbeTargets,
        *,
        require_event: bool,
    ) -> bool:
        if not isinstance(result, ReleaseProbeResult):
            return False
        if (
            result.control_protocol_version != targets.control_protocol_version
            or result.event_protocol_version != targets.event_protocol_version
        ):
            return False
        required = (
            result.cli_compatible,
            result.backend_compatible,
            result.tray_compatible,
            result.control_status_available,
            result.backup_timer_active,
            result.backup_timer_enabled,
            result.retention_timer_active,
            result.retention_timer_enabled,
        )
        return all(required) and (
            result.event_channel_available if require_event else True
        )


def linux_asset_targets(
    *,
    bin_root: Path = Path("/usr/local/bin"),
    admin_bin_root: Path = Path("/usr/local/sbin"),
    libexec_root: Path = Path("/usr/local/libexec"),
    unit_root: Path = Path("/etc/systemd/system"),
    config_root: Path = Path("/etc/timelocker"),
    autostart_root: Path = Path("/etc/xdg/autostart"),
    icon_root: Path = Path("/usr/local/share/icons/hicolor/1024x1024/apps"),
) -> tuple[AssetTarget, ...]:
    """Return the complete Linux launcher, backend, tray, and schedule asset set."""
    return (
        AssetTarget("timelocker-launcher", bin_root / "timelocker", 0o755),
        AssetTarget("tl-launcher", bin_root / "tl", 0o755),
        AssetTarget(
            "timelocker-release-select",
            bin_root / "timelocker-release-select",
            0o750,
        ),
        AssetTarget(
            "timelocker-deploy-launcher",
            admin_bin_root / "timelocker-deploy",
            0o750,
        ),
        AssetTarget(
            "timelocker-system-control-launcher",
            libexec_root / "timelocker-system-control",
            0o750,
        ),
        AssetTarget(
            "timelocker-tray-launcher",
            bin_root / "timelocker-tray",
            0o755,
        ),
        AssetTarget(
            "timelocker-control.service",
            unit_root / "timelocker-control.service",
            0o644,
        ),
        AssetTarget(
            "timelocker-control.socket",
            unit_root / "timelocker-control.socket",
            0o644,
        ),
        AssetTarget(
            "timelocker-retention.service",
            unit_root / "timelocker-retention.service",
            0o644,
        ),
        AssetTarget(
            "timelocker-retention.timer",
            unit_root / "timelocker-retention.timer",
            0o644,
        ),
        AssetTarget(
            "system-control-policy.json",
            config_root / "system-control-policy.json",
            0o640,
            preserve_existing=True,
        ),
        AssetTarget(
            "timelocker-tray.desktop",
            autostart_root / "timelocker-tray.desktop",
            0o644,
        ),
        AssetTarget(
            "timelocker-icon.png",
            icon_root / "timelocker.png",
            0o644,
        ),
        *(
            AssetTarget(
                f"timelocker-icon-{status}.png",
                icon_root / f"timelocker-{status}.png",
                0o644,
            )
            for status in (
                "connecting",
                "idle",
                "running",
                "success",
                "warning",
                "error",
            )
        ),
    )


def build_asset_manifest(
    *,
    asset_root: Path,
    release_id: str,
    package_version: str,
    asset_names: tuple[str, ...],
) -> SystemAssetManifest:
    """Create an exact manifest from a trusted build workspace."""
    return SystemAssetManifest(
        release_id=release_id,
        package_version=package_version,
        hashes={name: _sha256(asset_root / name) for name in asset_names},
    )


def build_release_manifest(
    *,
    release_id: str,
    package_version: str,
) -> dict[str, object]:
    """Build daemonless schema-3 metadata for one selected release."""
    mapping: dict[str, object] = {
        "schema_version": 3,
        "release_id": release_id,
        "package_version": require_safe_identifier(
            package_version,
            field="package_version",
            maximum=64,
        ),
        "control_protocol_version": PROTOCOL_VERSION,
        "entrypoint": "venv/bin/timelocker",
    }
    ReleaseManifest.from_mapping(mapping)
    return mapping


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise DeploymentError("required packaged asset is unavailable") from error


def _atomic_copy(source: Path, destination: Path, *, mode: int) -> None:
    if mode not in {0o600, 0o640, 0o644, 0o700, 0o750, 0o755}:
        raise DeploymentError("unsupported installed asset mode")
    destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        with source.open("rb") as input_stream, temporary.open("xb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
