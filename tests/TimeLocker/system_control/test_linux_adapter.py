"""Linux kernel-identity, NSS, socket, policy, and service-asset tests."""

import grp
import json
import os
from pathlib import Path
import pwd
import socket
import struct
from threading import Event
from types import SimpleNamespace

import pytest

from TimeLocker.system_control import PeerIdentity
from TimeLocker.system_control.linux_adapter import (
    LinuxNssGroupMembershipResolver,
    LinuxPeerIdentityProvider,
    LinuxUnixSocketTransport,
)
from TimeLocker.system_control.policy_loader import load_system_policy


ASSET_DIRECTORY = (
    Path(__file__).parents[3] / "src" / "TimeLocker" / "system_control" / "assets"
)


@pytest.mark.unit
@pytest.mark.security
class TestLinuxPeerIdentity:
    """Prove identity is derived from the connected socket and current NSS."""

    def test_peer_credentials_are_parsed_from_socket_option(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            monkeypatch.setattr(
                socket.socket,
                "getsockopt",
                lambda _socket, level, option, length: (
                    struct.pack("3i", 4321, 1000, 1000)
                    if (
                        level == socket.SOL_SOCKET
                        and option == socket.SO_PEERCRED
                        and length == struct.calcsize("3i")
                    )
                    else b""
                ),
            )
            identity = LinuxPeerIdentityProvider().peer_identity(server)
        finally:
            server.close()
            client.close()

        assert identity.platform_id == "linux-uid:1000"
        assert identity.process_id == 4321

    def test_primary_and_supplementary_membership_are_recognized(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        resolver = LinuxNssGroupMembershipResolver()
        identity = PeerIdentity("linux-uid:1000")
        monkeypatch.setattr(
            pwd,
            "getpwuid",
            lambda _uid: SimpleNamespace(pw_name="operator", pw_gid=2000),
        )
        monkeypatch.setattr(
            grp,
            "getgrnam",
            lambda _name: SimpleNamespace(gr_gid=2000, gr_mem=[]),
        )
        assert resolver.is_current_member(identity, "timelocker-operators")

        monkeypatch.setattr(
            pwd,
            "getpwuid",
            lambda _uid: SimpleNamespace(pw_name="operator", pw_gid=3000),
        )
        monkeypatch.setattr(
            grp,
            "getgrnam",
            lambda _name: SimpleNamespace(gr_gid=2000, gr_mem=["operator"]),
        )
        assert resolver.is_current_member(identity, "timelocker-operators")

    def test_missing_account_group_or_non_linux_identity_fails_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        resolver = LinuxNssGroupMembershipResolver()
        monkeypatch.setattr(
            pwd,
            "getpwuid",
            lambda _uid: (_ for _ in ()).throw(KeyError("missing")),
        )

        assert not resolver.is_current_member(
            PeerIdentity("linux-uid:1000"),
            "timelocker-operators",
        )
        assert not resolver.is_current_member(
            PeerIdentity("windows-sid:S-1-5-21"),
            "timelocker-operators",
        )


class EchoHandler:
    """Return a fixed response while recording the derived identity."""

    def __init__(self) -> None:
        self.identity: PeerIdentity | None = None

    def handle(self, request: bytes, identity: PeerIdentity) -> bytes:
        self.identity = identity
        return request + b"\n"


class MemoryConnection:
    """Minimal connection double for transport framing without sandbox sockets."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.response = b""
        self.timeout: float | None = None

    def recv(self, _maximum: int) -> bytes:
        payload, self.payload = self.payload, b""
        return payload

    def sendall(self, response: bytes) -> None:
        self.response += response

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout


@pytest.mark.unit
@pytest.mark.platform
class TestLinuxUnixSocketTransport:
    """Verify one bounded local request is handled with kernel identity."""

    def test_connection_uses_kernel_identity_not_payload_identity(
        self,
    ) -> None:
        listener, listener_peer = socket.socketpair(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
        )
        connection = MemoryConnection(b'{"uid":0}\n')
        handler = EchoHandler()
        transport = LinuxUnixSocketTransport(
            listener,
            max_request_bytes=1_024,
            stop_event=Event(),
        )
        transport.identity_provider = SimpleNamespace(
            peer_identity=lambda _connection: PeerIdentity(
                f"linux-uid:{os.getuid()}",
                os.getpid(),
            )
        )
        try:
            transport.serve_connection(connection, handler)  # type: ignore[arg-type]
            assert connection.response == b'{"uid":0}\n'
            assert connection.timeout == 5.0
        finally:
            listener.close()
            listener_peer.close()

        assert handler.identity is not None
        assert handler.identity.platform_id == f"linux-uid:{os.getuid()}"


@pytest.mark.unit
@pytest.mark.security
class TestSystemPolicyAndAssets:
    """Verify strict policy ownership and least-privilege staged units."""

    def test_packaged_policy_loads_with_explicit_retention_defaults(self) -> None:
        policy = load_system_policy(
            ASSET_DIRECTORY / "system-control-policy.json",
            expected_owner=os.getuid(),
        )

        assert policy.operator_group == "timelocker-operators"
        assert policy.transport_identifier == "/run/timelocker/control.sock"
        assert policy.retention.group_by == ("host", "paths")
        assert policy.retention.prune is False
        assert policy.retention.approved_fingerprint is None

    def test_policy_rejects_group_writable_or_unknown_fields(
        self,
        tmp_path: Path,
    ) -> None:
        source = ASSET_DIRECTORY / "system-control-policy.json"
        payload = json.loads(source.read_text())
        payload["repository_password"] = "secret"
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(json.dumps(payload))
        policy_path.chmod(0o640)

        with pytest.raises(ValueError, match="unknown fields"):
            load_system_policy(policy_path, expected_owner=os.getuid())

        payload.pop("repository_password")
        policy_path.write_text(json.dumps(payload))
        policy_path.chmod(0o660)
        with pytest.raises(PermissionError, match="writable"):
            load_system_policy(policy_path, expected_owner=os.getuid())

    def test_socket_and_service_templates_enforce_narrow_boundary(self) -> None:
        socket_unit = (ASSET_DIRECTORY / "timelocker-control.socket").read_text()
        service_unit = (ASSET_DIRECTORY / "timelocker-control.service").read_text()

        assert "ListenStream=/run/timelocker/control.sock" in socket_unit
        assert "SocketGroup=timelocker-operators" in socket_unit
        assert "SocketMode=0660" in socket_unit
        assert "User=root" in service_unit
        assert "UMask=0077" in service_unit
        assert "NoNewPrivileges=yes" in service_unit
        assert "ProtectSystem=strict" in service_unit
        assert "ProtectHome=yes" in service_unit
        assert "RestrictAddressFamilies=AF_UNIX" in service_unit
        assert (
            "ExecStart=/usr/local/libexec/timelocker-system-control --systemd-socket"
            in service_unit
        )
        assert "EnvironmentFile=" not in service_unit
        assert "DISPLAY=" not in service_unit
        assert "s3://" not in service_unit

        retention_service = (
            ASSET_DIRECTORY / "timelocker-retention.service"
        ).read_text()
        retention_timer = (ASSET_DIRECTORY / "timelocker-retention.timer").read_text()
        assert "ConditionPathExists=/etc/timelocker/retention-enabled" in retention_service
        assert "--scheduled-retention" in retention_service
        assert "Persistent=false" in retention_timer
