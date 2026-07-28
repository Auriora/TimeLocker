"""Safety contracts for the repository-owned T011 Linux deployment harness."""

from __future__ import annotations

import getpass
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[3]
RELEASE_A = "a" * 40
RELEASE_B = "b" * 40


def _load_harness() -> ModuleType:
    path = ROOT / "scripts/deploy_t011_linux.py"
    spec = importlib.util.spec_from_file_location("deploy_t011_linux", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeExecutor:
    """Capture commands and return deterministic candidate-probe output."""

    def __init__(self, harness: ModuleType, packaged_unit: Path) -> None:
        self.harness = harness
        self.packaged_unit = packaged_unit
        self.commands: list[list[str]] = []

    def run(
        self,
        arguments,
        *,
        timeout=30,
        output=None,
        capture=False,
        check=True,
    ) -> str:
        del timeout, check
        command = [str(argument) for argument in arguments]
        self.commands.append(command)
        result = ""
        if command[-2:] == ["-c", self.harness.BACKEND_IMPORT_PROBE]:
            result = "1:1\n"
        elif command[-2:] == ["-c", self.harness.PACKAGED_UNIT_PROBE]:
            result = f"{self.packaged_unit}\n"
        elif command[-2:] == ["-c", self.harness.DENIED_EVENT_PROBE]:
            result = "denied\n"
        elif command[-2:] == ["-c", self.harness.AUTHORIZED_EVENT_PROBE]:
            result = json.dumps(
                {
                    "kind": "snapshot",
                    "sequence": 1,
                    "session_id": "526719f9-4c46-42ac-b286-2623079bc335",
                }
            )
        if output is not None:
            self.harness._write_private_text(output, result)
        return result


class SimulatedHostExecutor(FakeExecutor):
    """Model the filesystem effects of venv, pip, and release selection."""

    def __init__(
        self,
        harness: ModuleType,
        packaged_unit: Path,
        paths,
        *,
        fail_activated_event: bool = False,
    ) -> None:
        super().__init__(harness, packaged_unit)
        self.paths = paths
        self.fail_activated_event = fail_activated_event
        self.authorized_event_calls = 0

    def run(
        self,
        arguments,
        *,
        timeout=30,
        output=None,
        capture=False,
        check=True,
    ) -> str:
        command = [str(argument) for argument in arguments]
        if command[:4] == ["python3", "-m", "venv", "--system-site-packages"]:
            release = Path(command[4]).parent
            python = release / "venv/bin/python"
            python.parent.mkdir(parents=True)
            python.write_text("#!/bin/sh\n", encoding="utf-8")
            python.chmod(0o755)
        elif len(command) >= 5 and command[1:4] == ["-m", "pip", "install"]:
            release = Path(command[0]).parents[2]
            python = release / "venv/bin/python"
            for name in self.harness.REQUIRED_ENTRYPOINTS:
                entrypoint = release / "venv/bin" / name
                entrypoint.write_text(f"#!{python}\n", encoding="utf-8")
                entrypoint.chmod(0o755)
            self.packaged_unit.parent.mkdir(parents=True)
            self.packaged_unit.write_text(
                "\n".join(
                    (
                        "[Unit]",
                        "Requires=timelocker-control.socket",
                        "Wants=timelocker-status-events.socket",
                        "[Service]",
                        (
                            "Sockets=timelocker-control.socket "
                            "timelocker-status-events.socket"
                        ),
                        "",
                    )
                ),
                encoding="utf-8",
            )
        elif (
            "TimeLocker.system_control.release_admin" in command
            and "select" in command
        ):
            state = json.loads(self.paths.selector.read_text(encoding="utf-8"))
            state["previous"] = state["selected"]
            state["selected"] = command[command.index("select") + 1]
            self.paths.selector.write_text(json.dumps(state), encoding="utf-8")
        result = super().run(
            arguments,
            timeout=timeout,
            output=output,
            capture=capture,
            check=check,
        )
        if command[-2:] == ["-c", self.harness.AUTHORIZED_EVENT_PROBE]:
            self.authorized_event_calls += 1
            if self.fail_activated_event and self.authorized_event_calls == 2:
                return "not-json"
        return result


def _paths(harness: ModuleType, root: Path):
    return harness.DeploymentPaths(
        releases_root=root / "opt/timelocker/releases",
        selector=root / "opt/timelocker/selected-release.json",
        service_unit=root / "etc/systemd/system/timelocker-control.service",
        evidence_root=root / "var/lib/timelocker/migration-backup",
        lock_file=root / "run/lock/timelocker-t011-deploy.lock",
    )


def _request(harness: ModuleType, root: Path):
    wheel = root / "timelocker-0.9.1-py3-none-any.whl"
    wheel.write_bytes(b"validated wheel")
    digest = harness._sha256(wheel)
    manifest = root / "release.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "release_id": RELEASE_B,
                "package_version": "0.9.1",
                "control_protocol_version": 2,
                "event_protocol_version": 1,
                "entrypoint": "venv/bin/timelocker",
            }
        ),
        encoding="utf-8",
    )
    return harness.DeploymentRequest(
        release_id=RELEASE_B,
        expected_current=RELEASE_A,
        wheel=wheel,
        wheel_sha256=digest,
        manifest=manifest,
        operator_user=getpass.getuser(),
    )


def _baseline(paths) -> None:
    paths.selector.parent.mkdir(parents=True)
    paths.selector.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "selected": RELEASE_A,
                "previous": None,
            }
        ),
        encoding="utf-8",
    )
    paths.service_unit.parent.mkdir(parents=True)
    paths.service_unit.write_text("old service\n", encoding="utf-8")
    paths.evidence_root.mkdir(parents=True)
    paths.releases_root.mkdir(parents=True)


def _staged_release(deployer, packaged_unit: Path) -> None:
    python = deployer.release / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    python.chmod(0o755)
    for name in (
        "timelocker",
        "tl",
        "timelocker-tray",
        "timelocker-system-control",
    ):
        entrypoint = deployer.release / "venv/bin" / name
        entrypoint.write_text(f"#!{python}\n", encoding="utf-8")
        entrypoint.chmod(0o755)
    packaged_unit.parent.mkdir(parents=True)
    packaged_unit.write_text(
        "\n".join(
            (
                "[Unit]",
                "Requires=timelocker-control.socket",
                "Wants=timelocker-status-events.socket",
                "[Service]",
                "Sockets=timelocker-control.socket timelocker-status-events.socket",
                "",
            )
        ),
        encoding="utf-8",
    )


def test_identity_preflights_are_inline_and_precede_mutation_under_restrictive_umask(
    tmp_path: Path,
) -> None:
    harness = _load_harness()
    paths = _paths(harness, tmp_path)
    _baseline(paths)
    request = _request(harness, tmp_path)
    packaged_unit = (
        paths.releases_root
        / RELEASE_B
        / "venv/lib/python3.12/site-packages/TimeLocker/system_control/assets"
        / "timelocker-control.service"
    )
    executor = FakeExecutor(harness, packaged_unit)
    deployer = harness.T011LinuxDeployer(
        request,
        paths=paths,
        executor=executor,
        owner_uid=None,
        owner_gid=None,
    )
    deployer.validate_request()
    old_umask = os.umask(0o077)
    try:
        deployer.capture_baseline()
        _staged_release(deployer, packaged_unit)
        deployer.preflight_staged_release()
    finally:
        os.umask(old_umask)

    assert json.loads(paths.selector.read_text())["selected"] == RELEASE_A
    assert paths.service_unit.read_text() == "old service\n"
    target_identity_commands = [
        command
        for command in executor.commands
        if "runuser" in command or "setpriv" in command
    ]
    assert len(target_identity_commands) == 3
    assert all("-c" in command for command in target_identity_commands[1:])
    assert all(
        not any(argument.endswith(".py") for argument in command)
        for command in target_identity_commands
    )
    assert deployer.evidence is not None
    assert deployer.staged_wheel is not None
    assert deployer.staged_wheel.name == request.wheel.name
    evidence_modes = {
        path.name: path.stat().st_mode & 0o777
        for path in deployer.evidence.iterdir()
        if path.is_file()
    }
    assert evidence_modes
    assert set(evidence_modes.values()) == {0o600}


def test_invalid_wheel_filename_is_rejected_before_host_state(
    tmp_path: Path,
) -> None:
    harness = _load_harness()
    paths = _paths(harness, tmp_path)
    _baseline(paths)
    request = _request(harness, tmp_path)
    invalid_wheel = tmp_path / "candidate.whl"
    request.wheel.replace(invalid_wheel)
    request = harness.DeploymentRequest(
        release_id=request.release_id,
        expected_current=request.expected_current,
        wheel=invalid_wheel,
        wheel_sha256=harness._sha256(invalid_wheel),
        manifest=request.manifest,
        operator_user=request.operator_user,
    )
    deployer = harness.T011LinuxDeployer(
        request,
        paths=paths,
        executor=FakeExecutor(harness, tmp_path / "unused.service"),
        owner_uid=None,
        owner_gid=None,
    )

    with pytest.raises(harness.DeploymentFailure, match="valid wheel filename"):
        deployer.validate_request()

    assert list(paths.evidence_root.iterdir()) == []
    assert not deployer.release.exists()


def test_preflight_failure_never_calls_activation() -> None:
    harness = _load_harness()
    calls: list[str] = []

    class FailingDeployer(harness.T011LinuxDeployer):
        def validate_request(self):
            calls.append("validate")

        def capture_baseline(self):
            calls.append("baseline")

        def stage_release(self):
            calls.append("stage")

        def preflight_staged_release(self):
            calls.append("preflight")
            raise harness.DeploymentFailure("preflight rejected")

        def activate(self):
            calls.append("activate")

        def recover(self):
            calls.append("recover")

    deployer = object.__new__(FailingDeployer)

    with pytest.raises(harness.DeploymentFailure, match="preflight rejected"):
        deployer.deploy()

    assert calls == ["validate", "baseline", "stage", "preflight", "recover"]


def test_interruption_after_mutation_runs_recovery() -> None:
    harness = _load_harness()
    calls: list[str] = []

    class InterruptedDeployer(harness.T011LinuxDeployer):
        def validate_request(self):
            calls.append("validate")

        def capture_baseline(self):
            calls.append("baseline")

        def stage_release(self):
            calls.append("stage")

        def preflight_staged_release(self):
            calls.append("preflight")

        def activate(self):
            calls.append("activate")
            raise KeyboardInterrupt

        def recover(self):
            calls.append("recover")

    deployer = object.__new__(InterruptedDeployer)

    with pytest.raises(KeyboardInterrupt):
        deployer.deploy()

    assert calls == [
        "validate",
        "baseline",
        "stage",
        "preflight",
        "activate",
        "recover",
    ]


def test_recovery_restores_selector_and_service_and_removes_candidate(
    tmp_path: Path,
) -> None:
    harness = _load_harness()
    paths = _paths(harness, tmp_path)
    _baseline(paths)
    request = _request(harness, tmp_path)
    packaged_unit = tmp_path / "packaged/timelocker-control.service"
    executor = FakeExecutor(harness, packaged_unit)
    deployer = harness.T011LinuxDeployer(
        request,
        paths=paths,
        executor=executor,
        owner_uid=None,
        owner_gid=None,
    )
    deployer.capture_baseline()
    deployer.release.mkdir(parents=True)
    (deployer.release / "inert").write_text("candidate", encoding="utf-8")
    paths.selector.write_text(
        json.dumps({"schema_version": 1, "selected": RELEASE_B}),
        encoding="utf-8",
    )
    paths.service_unit.write_text("candidate service\n", encoding="utf-8")
    deployer.mutation_started = True

    deployer.recover()

    assert json.loads(paths.selector.read_text())["selected"] == RELEASE_A
    assert paths.service_unit.read_text() == "old service\n"
    assert not deployer.release.exists()
    assert [
        command[:2]
        for command in executor.commands[:4]
    ] == [
        ["systemctl", "daemon-reload"],
        ["systemctl", "restart"],
        ["systemctl", "restart"],
        ["systemctl", "restart"],
    ]
    assert any("is-active" in command for command in executor.commands[4:])
    assert any("is-enabled" in command for command in executor.commands[4:])


def test_packaged_service_must_keep_event_socket_as_weak_dependency(
    tmp_path: Path,
) -> None:
    harness = _load_harness()
    paths = _paths(harness, tmp_path)
    _baseline(paths)
    request = _request(harness, tmp_path)
    packaged_unit = (
        paths.releases_root
        / RELEASE_B
        / "venv/lib/python3.12/site-packages/TimeLocker/system_control/assets"
        / "timelocker-control.service"
    )
    packaged_unit.parent.mkdir(parents=True)
    packaged_unit.write_text(
        "\n".join(
            (
                "Requires=timelocker-control.socket timelocker-status-events.socket",
                "Sockets=timelocker-control.socket timelocker-status-events.socket",
            )
        ),
        encoding="utf-8",
    )
    deployer = harness.T011LinuxDeployer(
        request,
        paths=paths,
        executor=FakeExecutor(harness, packaged_unit),
        owner_uid=None,
        owner_gid=None,
    )

    with pytest.raises(harness.DeploymentFailure, match="missing"):
        deployer._validate_packaged_unit(packaged_unit)


def test_packaged_service_cannot_escape_staged_release(tmp_path: Path) -> None:
    harness = _load_harness()
    paths = _paths(harness, tmp_path)
    _baseline(paths)
    request = _request(harness, tmp_path)
    packaged_unit = tmp_path / "outside/timelocker-control.service"
    packaged_unit.parent.mkdir()
    packaged_unit.write_text(
        "\n".join(
            (
                "Requires=timelocker-control.socket",
                "Wants=timelocker-status-events.socket",
                "Sockets=timelocker-control.socket timelocker-status-events.socket",
            )
        ),
        encoding="utf-8",
    )
    deployer = harness.T011LinuxDeployer(
        request,
        paths=paths,
        executor=FakeExecutor(harness, packaged_unit),
        owner_uid=None,
        owner_gid=None,
    )

    with pytest.raises(harness.DeploymentFailure, match="escapes"):
        deployer._validate_packaged_unit(packaged_unit)


def test_private_writer_overrides_permissive_umask(tmp_path: Path) -> None:
    harness = _load_harness()
    output = tmp_path / "evidence.json"
    old_umask = os.umask(0)
    try:
        harness._write_private_text(output, "{}\n")
    finally:
        os.umask(old_umask)

    assert output.stat().st_mode & 0o777 == 0o600


def test_signal_handler_converts_termination_to_transaction_exception() -> None:
    harness = _load_harness()

    with pytest.raises(harness.DeploymentInterrupted, match="SIGTERM"):
        harness._signal_handler(15, None)


def test_full_simulated_transaction_runs_preflight_before_selection(
    tmp_path: Path,
) -> None:
    harness = _load_harness()
    paths = _paths(harness, tmp_path)
    _baseline(paths)
    request = _request(harness, tmp_path)
    packaged_unit = (
        paths.releases_root
        / RELEASE_B
        / "venv/lib/python3.12/site-packages/TimeLocker/system_control/assets"
        / "timelocker-control.service"
    )
    executor = SimulatedHostExecutor(harness, packaged_unit, paths)
    deployer = harness.T011LinuxDeployer(
        request,
        paths=paths,
        executor=executor,
        owner_uid=None,
        owner_gid=None,
    )
    old_umask = os.umask(0o077)
    try:
        evidence = deployer.deploy()
    finally:
        os.umask(old_umask)

    assert json.loads(paths.selector.read_text())["selected"] == RELEASE_B
    denied_index = next(
        index
        for index, command in enumerate(executor.commands)
        if command[-2:] == ["-c", harness.DENIED_EVENT_PROBE]
    )
    selection_index = next(
        index
        for index, command in enumerate(executor.commands)
        if "TimeLocker.system_control.release_admin" in command
        and "select" in command
    )
    pip_command = next(
        command
        for command in executor.commands
        if len(command) >= 5 and command[1:4] == ["-m", "pip", "install"]
    )
    assert denied_index < selection_index
    assert Path(pip_command[-1]).name == request.wheel.name
    assert deployer.release.exists()
    assert paths.service_unit.read_text() == packaged_unit.read_text()
    assert all(
        path.stat().st_mode & 0o022 == 0
        for path in deployer.release.rglob("*")
        if not path.is_symlink()
    )
    assert evidence.stat().st_mode & 0o777 == 0o750


def test_full_simulated_post_activation_failure_rolls_back(
    tmp_path: Path,
) -> None:
    harness = _load_harness()
    paths = _paths(harness, tmp_path)
    _baseline(paths)
    request = _request(harness, tmp_path)
    packaged_unit = (
        paths.releases_root
        / RELEASE_B
        / "venv/lib/python3.12/site-packages/TimeLocker/system_control/assets"
        / "timelocker-control.service"
    )
    executor = SimulatedHostExecutor(
        harness,
        packaged_unit,
        paths,
        fail_activated_event=True,
    )
    deployer = harness.T011LinuxDeployer(
        request,
        paths=paths,
        executor=executor,
        owner_uid=None,
        owner_gid=None,
    )

    with pytest.raises(harness.DeploymentFailure, match="invalid JSON"):
        deployer.deploy()

    assert json.loads(paths.selector.read_text())["selected"] == RELEASE_A
    assert paths.service_unit.read_text() == "old service\n"
    assert not deployer.release.exists()
