"""Fail-closed resolution for root-owned immutable TimeLocker releases."""

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, NoReturn

from .models import PROTOCOL_VERSION
from .validation import require_exact_mapping, require_int, require_safe_identifier


DEFAULT_RELEASES_ROOT = Path("/opt/timelocker/releases")
DEFAULT_SELECTOR_PATH = Path("/opt/timelocker/selected-release.json")
LAUNCH_GUARD = "TIMELOCKER_SYSTEM_LAUNCH_ACTIVE"


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
    protocol_version: int
    entrypoint: str = "venv/bin/timelocker"
    schema_version: int = 1

    @classmethod
    def from_mapping(cls, value: object) -> "ReleaseManifest":
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
            schema_version=require_int(
                mapping["schema_version"],
                field="schema_version",
                minimum=1,
                maximum=1,
            ),
            release_id=_release_id(mapping["release_id"]),
            package_version=require_safe_identifier(
                mapping["package_version"],
                field="package_version",
                maximum=64,
            ),
            protocol_version=require_int(
                mapping["protocol_version"],
                field="protocol_version",
                minimum=PROTOCOL_VERSION,
                maximum=PROTOCOL_VERSION,
            ),
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
        environment = os.environ if environment is None else environment
        if environment.get(LAUNCH_GUARD):
            raise ReleaseResolutionError("recursive system launcher invocation")
        self._require_trusted_directory(self.selector_path.parent)
        self._require_trusted_file(self.selector_path)
        selector = SelectedRelease.from_mapping(_read_json(self.selector_path))
        return self._resolve_release(selector.selected)

    def select(self, release_id: str) -> SelectedRelease:
        """Atomically select a validated staged release for administrator tooling."""
        release_id = _release_id(release_id)
        self._require_trusted_directory(self.selector_path.parent)
        self._resolve_release(release_id)
        current = self._read_selector_optional()
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

    def _read_selector_optional(self) -> SelectedRelease | None:
        self._require_trusted_directory(self.selector_path.parent)
        if not self.selector_path.exists():
            return None
        self._require_trusted_file(self.selector_path)
        return SelectedRelease.from_mapping(_read_json(self.selector_path))

    def _resolve_release(self, release_id: str) -> Path:
        self._require_trusted_directory(self.releases_root)
        release_dir = self.releases_root / release_id
        self._require_trusted_directory(release_dir)
        manifest_path = release_dir / "release.json"
        self._require_trusted_file(manifest_path)
        manifest = ReleaseManifest.from_mapping(_read_json(manifest_path))
        if manifest.release_id != release_id:
            raise ReleaseResolutionError("release manifest identity mismatch")
        executable = release_dir / manifest.entrypoint
        self._require_trusted_file(executable, executable=True)
        if executable.resolve().parent.parent.parent != release_dir.resolve():
            raise ReleaseResolutionError("release entrypoint escapes release directory")
        return executable

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
    resolver: ImmutableReleaseResolver | None = None,
    environment: Mapping[str, str] | None = None,
) -> NoReturn:
    """Replace this process with the selected immutable CLI entry point."""
    resolver = resolver or ImmutableReleaseResolver()
    source_environment = dict(os.environ if environment is None else environment)
    executable = resolver.resolve(source_environment)
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
