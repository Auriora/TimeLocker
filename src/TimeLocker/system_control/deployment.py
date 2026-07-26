"""Compatibility-checked installation and activation of system assets."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil

from .models import PROTOCOL_VERSION
from .release_launcher import ImmutableReleaseResolver, SelectedRelease
from .validation import require_int, require_safe_identifier


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
        health_probe: Callable[[Path, Path, Path], bool],
    ) -> SelectedRelease:
        """Select a release only after CLI, backend, and tray probes pass."""
        executables = tuple(
            self.resolver._resolve_release(release_id, entrypoint=entrypoint)
            for entrypoint in (
                "venv/bin/timelocker",
                "venv/bin/timelocker-system-control",
                "venv/bin/timelocker-tray",
            )
        )
        if health_probe(*executables) is not True:
            raise DeploymentError("staged release compatibility probe failed")
        return self.resolver.select(release_id)

    def rollback(
        self,
        *,
        health_probe: Callable[[Path, Path, Path], bool],
    ) -> SelectedRelease:
        """Restore the prior selector only after its artifacts pass probes."""
        current = self.resolver._read_selector_optional()
        if current is None or current.previous is None:
            raise DeploymentError("no previous release is available")
        executables = tuple(
            self.resolver._resolve_release(current.previous, entrypoint=entrypoint)
            for entrypoint in (
                "venv/bin/timelocker",
                "venv/bin/timelocker-system-control",
                "venv/bin/timelocker-tray",
            )
        )
        if health_probe(*executables) is not True:
            raise DeploymentError("rollback release compatibility probe failed")
        return self.resolver.rollback()


def linux_asset_targets(
    *,
    bin_root: Path = Path("/usr/local/bin"),
    libexec_root: Path = Path("/usr/local/libexec"),
    unit_root: Path = Path("/etc/systemd/system"),
    config_root: Path = Path("/etc/timelocker"),
    autostart_root: Path = Path("/etc/xdg/autostart"),
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
