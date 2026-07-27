"""Fail-closed resolution for root-owned immutable TimeLocker releases."""

import json
import os
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping, NoReturn

from .models import PROTOCOL_VERSION, STATUS_EVENT_PROTOCOL_VERSION
from .validation import require_exact_mapping, require_int, require_safe_identifier


DEFAULT_RELEASES_ROOT = Path("/opt/timelocker/releases")
DEFAULT_SELECTOR_PATH = Path("/opt/timelocker/selected-release.json")
LAUNCH_GUARD = "TIMELOCKER_SYSTEM_LAUNCH_ACTIVE"
_ENTRYPOINTS = {
    "cli": "venv/bin/timelocker",
    "backend": "venv/bin/timelocker-system-control",
    "tray": "venv/bin/timelocker-tray",
}


class ReleaseResolutionError(RuntimeError):
    """Raised when the selected immutable release cannot be trusted."""


@dataclass(frozen=True, slots=True)
class SelectedRelease:
    """Validated release selector state written by administrator tooling."""

    selected: str
    previous: str | None = None
    schema_version: int = 1

    @classmethod
    def from_mapping(cls, value: object) -> "SelectedRelease":
        mapping = require_exact_mapping(
            value,
            field="release selector",
            required=frozenset({"schema_version", "selected", "previous"}),
        )
        previous = mapping["previous"]
        if previous is not None:
            previous = _release_id(previous)
        return cls(
            schema_version=require_int(
                mapping["schema_version"],
                field="schema_version",
                minimum=1,
                maximum=1,
            ),
            selected=_release_id(mapping["selected"]),
            previous=previous,
        )

    def to_wire(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "selected": self.selected,
            "previous": self.previous,
        }


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    """Compatibility contract shipped inside one immutable release."""

    release_id: str
    package_version: str
    control_protocol_version: int
    event_protocol_version: int | None
    entrypoint: str = "venv/bin/timelocker"
    schema_version: int = 2

    @classmethod
    def from_mapping(cls, value: object) -> "ReleaseManifest":
        if not isinstance(value, Mapping):
            raise ReleaseResolutionError("release manifest is invalid")
        schema_version = require_int(
            value.get("schema_version"),
            field="schema_version",
            minimum=1,
            maximum=2,
        )
        if schema_version == 1:
            return cls._from_legacy_mapping(value)
        mapping = require_exact_mapping(
            value,
            field="release manifest",
            required=frozenset(
                {
                    "schema_version",
                    "release_id",
                    "package_version",
                    "control_protocol_version",
                    "event_protocol_version",
                    "entrypoint",
                }
            ),
        )
        entrypoint = mapping["entrypoint"]
        if entrypoint != "venv/bin/timelocker":
            raise ReleaseResolutionError("release entrypoint is not allowlisted")
        return cls(
            schema_version=schema_version,
            release_id=_release_id(mapping["release_id"]),
            package_version=require_safe_identifier(
                mapping["package_version"],
                field="package_version",
                maximum=64,
            ),
            control_protocol_version=require_int(
                mapping["control_protocol_version"],
                field="control_protocol_version",
                minimum=PROTOCOL_VERSION,
                maximum=PROTOCOL_VERSION,
            ),
            event_protocol_version=require_int(
                mapping["event_protocol_version"],
                field="event_protocol_version",
                minimum=STATUS_EVENT_PROTOCOL_VERSION,
                maximum=STATUS_EVENT_PROTOCOL_VERSION,
            ),
            entrypoint=entrypoint,
        )

    @classmethod
    def _from_legacy_mapping(cls, value: Mapping[str, object]) -> "ReleaseManifest":
        """Read schema 1 for rollback without claiming event compatibility."""
        mapping = require_exact_mapping(
            value,
            field="release manifest",
            required=frozenset(
                {
                    "schema_version",
                    "release_id",
                    "package_version",
                    "protocol_version",
                    "entrypoint",
                }
            ),
        )
        entrypoint = mapping["entrypoint"]
        if entrypoint != "venv/bin/timelocker":
            raise ReleaseResolutionError("release entrypoint is not allowlisted")
        return cls(
            schema_version=1,
            release_id=_release_id(mapping["release_id"]),
            package_version=require_safe_identifier(
                mapping["package_version"],
                field="package_version",
                maximum=64,
            ),
            control_protocol_version=require_int(
                mapping["protocol_version"],
                field="protocol_version",
                minimum=PROTOCOL_VERSION,
                maximum=PROTOCOL_VERSION,
            ),
            event_protocol_version=None,
            entrypoint=entrypoint,
        )


class ImmutableReleaseResolver:
    """Resolve the selected release without consulting user or shell state."""

    def __init__(
        self,
        *,
        releases_root: Path = DEFAULT_RELEASES_ROOT,
        selector_path: Path = DEFAULT_SELECTOR_PATH,
        expected_owner_uid: int = 0,
    ) -> None:
        self.releases_root = releases_root
        self.selector_path = selector_path
        self.expected_owner_uid = expected_owner_uid

    def resolve(self, environment: Mapping[str, str] | None = None) -> Path:
        """Return the selected executable or fail before any fallback."""
        return self.resolve_entrypoint("cli", environment)

    def resolve_entrypoint(
        self,
        target: str,
        environment: Mapping[str, str] | None = None,
    ) -> Path:
        """Return an allowlisted executable from the selected release."""
        environment = os.environ if environment is None else environment
        if environment.get(LAUNCH_GUARD):
            raise ReleaseResolutionError("recursive system launcher invocation")
        try:
            entrypoint = _ENTRYPOINTS[target]
        except KeyError as error:
            raise ReleaseResolutionError(
                "release entrypoint is not allowlisted"
            ) from error
        self._require_trusted_directory(self.selector_path.parent)
        self._require_trusted_file(self.selector_path)
        selector = SelectedRelease.from_mapping(_read_json(self.selector_path))
        return self._resolve_release(selector.selected, entrypoint=entrypoint)

    def select(
        self,
        release_id: str,
        *,
        expected_current: str | None = None,
    ) -> SelectedRelease:
        """Atomically select a validated staged release for administrator tooling."""
        release_id = _release_id(release_id)
        if expected_current is not None:
            expected_current = _release_id(expected_current)
        self._require_trusted_directory(self.selector_path.parent)
        self._resolve_release(release_id)
        with self._selector_lock():
            current = self._read_selector_optional()
            if expected_current is not None and (
                current is None or current.selected != expected_current
            ):
                raise ReleaseResolutionError(
                    "selected release changed before activation"
                )
            next_state = SelectedRelease(
                selected=release_id,
                previous=current.selected
                if current and current.selected != release_id
                else (current.previous if current else None),
            )
            _atomic_write_json(self.selector_path, next_state.to_wire())
        return next_state

    def rollback(self) -> SelectedRelease:
        """Atomically swap selected and previous validated releases."""
        with self._selector_lock():
            current = self._read_selector_optional()
            if current is None or current.previous is None:
                raise ReleaseResolutionError("no previous release is available")
            self._resolve_release(current.previous)
            next_state = SelectedRelease(
                selected=current.previous,
                previous=current.selected,
            )
            _atomic_write_json(self.selector_path, next_state.to_wire())
        return next_state

    @contextmanager
    def _selector_lock(self) -> Iterator[None]:
        """Serialize administrator writes without affecting atomic readers."""
        try:
            import fcntl
        except ImportError as error:  # pragma: no cover - Linux deployment only
            raise ReleaseResolutionError(
                "release selection locking is unavailable"
            ) from error
        lock_path = self.selector_path.with_suffix(
            f"{self.selector_path.suffix}.lock"
        )
        try:
            flags = os.O_RDWR | os.O_CREAT
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as error:
            raise ReleaseResolutionError(
                "release selection lock is unavailable"
            ) from error
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != self.expected_owner_uid
                or metadata.st_mode & 0o022
            ):
                raise ReleaseResolutionError(
                    "release selection lock is not trusted"
                )
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def _read_selector_optional(self) -> SelectedRelease | None:
        self._require_trusted_directory(self.selector_path.parent)
        if not self.selector_path.exists():
            return None
        self._require_trusted_file(self.selector_path)
        return SelectedRelease.from_mapping(_read_json(self.selector_path))

    def _resolve_release(
        self,
        release_id: str,
        *,
        entrypoint: str = _ENTRYPOINTS["cli"],
    ) -> Path:
        self._require_trusted_directory(self.releases_root)
        release_dir = self.releases_root / release_id
        self._require_trusted_directory(release_dir)
        manifest_path = release_dir / "release.json"
        self._require_trusted_file(manifest_path)
        manifest = ReleaseManifest.from_mapping(_read_json(manifest_path))
        if manifest.release_id != release_id:
            raise ReleaseResolutionError("release manifest identity mismatch")
        executable = release_dir / entrypoint
        self._require_trusted_file(executable, executable=True)
        if executable.resolve().parent.parent.parent != release_dir.resolve():
            raise ReleaseResolutionError("release entrypoint escapes release directory")
        return executable

    def release_manifest(self, release_id: str) -> ReleaseManifest:
        """Return trusted compatibility metadata for one staged release."""
        release_id = _release_id(release_id)
        self._require_trusted_directory(self.releases_root)
        release_dir = self.releases_root / release_id
        self._require_trusted_directory(release_dir)
        manifest_path = release_dir / "release.json"
        self._require_trusted_file(manifest_path)
        manifest = ReleaseManifest.from_mapping(_read_json(manifest_path))
        if manifest.release_id != release_id:
            raise ReleaseResolutionError("release manifest identity mismatch")
        return manifest

    def _require_trusted_file(self, path: Path, *, executable: bool = False) -> None:
        try:
            metadata = path.lstat()
        except OSError as error:
            raise ReleaseResolutionError(
                "required release file is unavailable"
            ) from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ReleaseResolutionError("required release file is not regular")
        if metadata.st_uid != self.expected_owner_uid:
            raise ReleaseResolutionError("required release file has the wrong owner")
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ReleaseResolutionError(
                "required release file is group/world writable"
            )
        if executable and not metadata.st_mode & stat.S_IXUSR:
            raise ReleaseResolutionError("release entrypoint is not executable")

    def _require_trusted_directory(self, path: Path) -> None:
        try:
            metadata = path.lstat()
        except OSError as error:
            raise ReleaseResolutionError(
                "required release directory is unavailable"
            ) from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ReleaseResolutionError("required release directory is invalid")
        if metadata.st_uid != self.expected_owner_uid:
            raise ReleaseResolutionError(
                "required release directory has the wrong owner"
            )
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ReleaseResolutionError(
                "required release directory is group/world writable"
            )


def launch_selected(
    arguments: list[str],
    *,
    target: str = "cli",
    resolver: ImmutableReleaseResolver | None = None,
    environment: Mapping[str, str] | None = None,
) -> NoReturn:
    """Replace this process with the selected immutable CLI entry point."""
    resolver = resolver or ImmutableReleaseResolver()
    source_environment = dict(os.environ if environment is None else environment)
    executable = resolver.resolve_entrypoint(target, source_environment)
    source_environment[LAUNCH_GUARD] = "1"
    os.execve(
        executable,
        [str(executable), *arguments],
        source_environment,
    )


def _release_id(value: object) -> str:
    release_id = require_safe_identifier(
        value,
        field="release_id",
        maximum=64,
    )
    if len(release_id) < 7 or any(
        character not in "0123456789abcdef" for character in release_id
    ):
        raise ReleaseResolutionError("release_id must be a lowercase commit digest")
    return release_id


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseResolutionError("release metadata is invalid") from error


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o644)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
