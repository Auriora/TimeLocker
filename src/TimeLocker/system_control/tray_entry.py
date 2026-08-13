"""Standalone tray entry point for user-session TimeLocker interactions."""

from __future__ import annotations

import argparse
import logging
import os
from queue import Empty, Full, Queue
import signal
import sys
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from threading import Event, Thread
from typing import Any

from .tray_client import (
    TrayControlClient,
    TrayDisplayState,
    TrayStatusSubscriptionClient,
)
from ..monitoring.system_tray_integration import (
    SystemTrayError,
    SystemTrayIntegration,
    TrayStatus,
    TrayStatusInfo,
)

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows-specific.
    fcntl = None

from .client import UnixSocketSystemControlClient

DEFAULT_REFRESH_SECONDS = 15
TRAY_STATUS_ACTIONS = {"status", "backup_now", "retention_now", "quit"}
_runtime_directory = os.environ.get("XDG_RUNTIME_DIR")
logger = logging.getLogger(__name__)
LOCK_PATH = (
    Path(_runtime_directory) / "timelocker" / "tray.lock"
    if _runtime_directory and Path(_runtime_directory).is_absolute()
    else Path.home() / ".cache" / "timelocker" / "tray.lock"
)


_STATUS_MAP = {
    "connecting": TrayStatus.CONNECTING,
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
    ]
    if state.last_successful_backup_completed_at:
        bits.append(
            "last_successful_backup_completed_at: "
            f"{state.last_successful_backup_completed_at.isoformat()}"
        )
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
    tray.update_status_info(
        TrayStatusInfo(
            status=_status_to_tray(state.status),
            tooltip=state.tooltip,
            health=state.health,
            activity=state.activity,
            backend_available=state.backend_available,
            last_successful_backup_time=(
                state.last_successful_backup_completed_at
            ),
            latest_backup_status=state.latest_backup_status,
            latest_retention_status=state.latest_retention_status,
            next_backup_time=state.next_backup_at,
            next_retention_time=state.next_retention_at,
            active_operations=state.active_operations,
        )
    )


def _build_client(
    target_id: str,
    retention_policy_fingerprint: str | None,
) -> TrayControlClient:
    return TrayControlClient(
        client_factory=UnixSocketSystemControlClient,
        target_id=target_id,
        retention_policy_fingerprint=retention_policy_fingerprint,
    )


def _tray_menu_actions(retention_policy_fingerprint: str | None) -> frozenset[str]:
    actions = {"backup_now", "quit"}
    if retention_policy_fingerprint:
        actions.add("retention_now")
    return frozenset(actions)


def _handle_action(
    action: str,
    client: TrayControlClient,
    *,
    tray: SystemTrayIntegration | None,
    dry_run_retention: bool,
) -> TrayDisplayState | None:
    if action == "quit":
        raise SystemExit(0)
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


def _offer_latest(
    updates: Queue[TrayDisplayState],
    state: TrayDisplayState,
) -> None:
    """Coalesce worker-to-desktop updates to the newest safe state."""
    try:
        updates.put_nowait(state)
    except Full:
        with suppress(Empty):
            updates.get_nowait()
        updates.put_nowait(state)


def main() -> None:
    startup_started = time.monotonic()
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

    client = _build_client(
        target_id=arguments.target_id,
        retention_policy_fingerprint=arguments.retention_policy_fingerprint,
    )
    if arguments.action != "serve":
        state = _handle_action(
            arguments.action,
            client,
            tray=None,
            dry_run_retention=arguments.dry_run_retention,
        )
        if state is not None:
            print(_render_status(state))
        return

    try:
        tray = SystemTrayIntegration(
            app_name="TimeLocker",
            menu_actions=_tray_menu_actions(arguments.retention_policy_fingerprint),
        )
    except SystemTrayError:
        tray = None
    if tray is not None and tray.is_available():
        tray.process_events()
        logger.debug(
            "Tray icon ready before status subscription (startup_ms=%.1f)",
            (time.monotonic() - startup_started) * 1_000,
        )

    stop_requested = False
    subscription_stop = Event()
    subscription_thread: Thread | None = None

    def _request_stop(*_args: Any) -> None:
        nonlocal stop_requested
        stop_requested = True
        subscription_stop.set()

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

            updates: Queue[TrayDisplayState] = Queue(maxsize=1)
            # An explicit tray launch may wake the one-shot helper once. The
            # helper answers and exits; subsequent updates come directly from
            # the sanitized status file without polling the privileged socket.
            _offer_latest(updates, client.refresh_status())
            subscription = TrayStatusSubscriptionClient()

            def _subscribe() -> None:
                subscription.serve(
                    subscription_stop,
                    on_snapshot=lambda snapshot: _offer_latest(
                        updates,
                        client.project_snapshot(snapshot),
                    ),
                    on_unavailable=lambda reason: _offer_latest(
                        updates,
                        client.unavailable_state(
                            (
                                "TimeLocker - Access denied"
                                if reason == "denied"
                                else "TimeLocker - System backend unavailable"
                            ),
                            backend_available=reason == "denied",
                        ),
                    ),
                )

            subscription_thread = Thread(
                target=_subscribe,
                name="timelocker-tray-status",
                daemon=True,
            )
            subscription_thread.start()
            logger.debug(
                "Tray status subscription worker started (startup_ms=%.1f)",
                (time.monotonic() - startup_started) * 1_000,
            )

            while not stop_requested:
                if tray is not None:
                    tray.process_events()
                try:
                    state = updates.get_nowait()
                except Empty:
                    time.sleep(0.05)
                    continue
                if tray and tray.is_available():
                    _apply_state(tray, state)
                if arguments.once:
                    break
    except RuntimeError as exc:
        print(f"{exc}", file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        subscription_stop.set()
        if subscription_thread is not None:
            subscription_thread.join(timeout=1.0)
        if tray is not None and tray.is_available():
            tray.shutdown()


if __name__ == "__main__":
    main()
