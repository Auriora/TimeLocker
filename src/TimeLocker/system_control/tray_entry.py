"""Standalone tray entry point for user-session TimeLocker interactions."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any, Callable

from .tray_client import TrayControlClient, TrayDisplayState
from ..monitoring.system_tray_integration import (
    SystemTrayError,
    SystemTrayIntegration,
    TrayStatus,
)

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows-specific.
    fcntl = None

from .client import (
    ProtocolErrorCode,
    SystemControlClientError,
    UnixSocketSystemControlClient,
)
from .types import ResponseStatus

DEFAULT_REFRESH_SECONDS = 15
DEFAULT_POLL_SECONDS = 30
TRAY_STATUS_ACTIONS = {"status", "backup_now", "retention_now", "open_ui", "quit"}
_runtime_directory = os.environ.get("XDG_RUNTIME_DIR")
LOCK_PATH = (
    Path(_runtime_directory) / "timelocker" / "tray.lock"
    if _runtime_directory and Path(_runtime_directory).is_absolute()
    else Path.home() / ".cache" / "timelocker" / "tray.lock"
)


_STATUS_MAP = {
    "running": TrayStatus.RUNNING,
    "error": TrayStatus.ERROR,
    "warning": TrayStatus.WARNING,
    "success": TrayStatus.SUCCESS,
    "idle": TrayStatus.IDLE,
}


def _status_to_tray(status: str) -> TrayStatus:
    return _STATUS_MAP.get(status, TrayStatus.IDLE)


@contextmanager
def _single_instance(lock_path: Path = LOCK_PATH) -> Any:
    if fcntl is None:
        yield
        return

    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path.parent.chmod(0o700)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    os.fchmod(descriptor, 0o600)
    fd = os.fdopen(descriptor, "w", encoding="ascii")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        fd.close()
        raise RuntimeError("timelocker-tray is already running") from exc
    try:
        yield
    finally:
        with suppress(OSError):
            fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
        with suppress(OSError):
            fd.close()
        with suppress(OSError):
            lock_path.unlink(missing_ok=True)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="timelocker-tray", description=__doc__)
    parser.add_argument(
        "action",
        nargs="?",
        default="serve",
        choices=sorted(TRAY_STATUS_ACTIONS | {"serve"}),
        help="Action to execute in this invocation.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Perform a single refresh and exit.",
    )
    parser.add_argument(
        "--refresh-seconds",
        type=float,
        default=DEFAULT_REFRESH_SECONDS,
        dest="refresh_seconds",
    )
    parser.add_argument(
        "--target-id",
        default="production",
    )
    parser.add_argument(
        "--retention-policy-fingerprint",
        default=None,
        help="Required for retention_now action.",
    )
    parser.add_argument(
        "--dry-run-retention",
        action="store_true",
        help="Request retention in dry-run mode.",
    )
    return parser.parse_args(argv)


def _render_status(state: TrayDisplayState) -> str:
    bits = [
        f"status: {state.status}",
        f"active_operations: {state.active_operations}",
        f"backend_available: {state.backend_available}",
        f"repositories: {state.repository_count}",
    ]
    if state.next_backup_at:
        bits.append(f"next_backup_at: {state.next_backup_at.isoformat()}")
    if state.next_retention_at:
        bits.append(f"next_retention_at: {state.next_retention_at.isoformat()}")
    return "\n".join(bits)


def _apply_state(
    tray: SystemTrayIntegration,
    state: TrayDisplayState,
) -> None:
    if not tray.is_available():
        return
    tray.update_status(_status_to_tray(state.status), tooltip=state.tooltip)


def _build_client(
    target_id: str,
    retention_policy_fingerprint: str | None,
) -> TrayControlClient:
    return TrayControlClient(
        client_factory=UnixSocketSystemControlClient,
        target_id=target_id,
        retention_policy_fingerprint=retention_policy_fingerprint,
    )


def _handle_action(
    action: str,
    client: TrayControlClient,
    *,
    tray: SystemTrayIntegration | None,
    dry_run_retention: bool,
) -> TrayDisplayState | None:
    if action == "quit":
        raise SystemExit(0)
    if action == "open_ui":
        print("open-ui not yet implemented")
        return None
    if action not in TRAY_STATUS_ACTIONS:
        raise SystemExit(f"unsupported action: {action}")
    return client.perform_action(action, dry_run_retention=dry_run_retention)


def _menu_action(
    action: str,
    client: TrayControlClient,
    tray: SystemTrayIntegration | None,
    dry_run_retention: bool,
) -> None:
    try:
        state = _handle_action(
            action,
            client,
            tray=tray,
            dry_run_retention=dry_run_retention,
        )
    except SystemExit:
        raise
    if state is not None and tray is not None and tray.is_available():
        _apply_state(tray, state)


def _wait_for_next_refresh(
    tray: SystemTrayIntegration | None,
    seconds: float,
    stop_requested: Callable[[], bool],
) -> None:
    """Keep the desktop event loop responsive between backend refreshes."""
    deadline = time.monotonic() + seconds
    while not stop_requested() and time.monotonic() < deadline:
        if tray is not None:
            tray.process_events()
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))


def main() -> None:
    arguments = _parse_args()
    if (
        arguments.action == "retention_now"
        and not arguments.retention_policy_fingerprint
    ):
        print(
            "retention_now requires --retention-policy-fingerprint",
            file=sys.stderr,
        )
        raise SystemExit(2)

    try:
        tray = SystemTrayIntegration(app_name="TimeLocker")
    except SystemTrayError:
        tray = None

    client = _build_client(
        target_id=arguments.target_id,
        retention_policy_fingerprint=arguments.retention_policy_fingerprint,
    )
    if arguments.action != "serve":
        state = _handle_action(
            arguments.action,
            client,
            tray=tray,
            dry_run_retention=arguments.dry_run_retention,
        )
        if state is not None:
            print(_render_status(state))
        return

    poll_interval = max(DEFAULT_POLL_SECONDS, arguments.refresh_seconds)

    stop_requested = False

    def _request_stop(*_args: Any) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    try:
        with _single_instance():
            if tray:
                if tray.is_available():
                    tray.set_on_menu_action_callback(
                        lambda action_name: _menu_action(
                            action_name,
                            client,
                            tray=tray,
                            dry_run_retention=arguments.dry_run_retention,
                        )
                    )
                tray.show_context_menu()

            while not stop_requested:
                try:
                    state = client.refresh_status()
                except Exception as exc:
                    if isinstance(exc, SystemControlClientError):
                        if (
                            exc.error_code
                            is ProtocolErrorCode.SYSTEM_BACKEND_UNAVAILABLE
                            and exc.status == ResponseStatus.UNAVAILABLE
                        ):
                            # Keep tray alive; retry on background interval.
                            print("backend unavailable, retrying...", file=sys.stderr)
                            _wait_for_next_refresh(
                                tray,
                                poll_interval,
                                lambda: stop_requested,
                            )
                            continue
                    print(f"{exc}", file=sys.stderr)
                    _wait_for_next_refresh(
                        tray,
                        poll_interval,
                        lambda: stop_requested,
                    )
                    continue

                if state:
                    if tray and tray.is_available():
                        _apply_state(tray, state)
                    print(_render_status(state))

                if arguments.once:
                    break
                _wait_for_next_refresh(
                    tray,
                    poll_interval,
                    lambda: stop_requested,
                )
    except RuntimeError as exc:
        print(f"{exc}", file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        if tray is not None and tray.is_available():
            tray.shutdown()


if __name__ == "__main__":
    main()
