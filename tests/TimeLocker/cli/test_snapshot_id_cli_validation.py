import re
import tempfile
from pathlib import Path
import pytest
from typer.testing import CliRunner

from TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import patch_restore_commands

# Set wider terminal width to prevent help text truncation in CI
runner = CliRunner(env={'COLUMNS': '200'})

def _combined_output(result):
    # Combine stdout and stderr for matching convenience across environments
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


@pytest.mark.unit
def test_restore_umount_reports_not_implemented():
    result = runner.invoke(app, ["restore", "umount", "bad$$id"])
    combined = _combined_output(result)

    assert result.exit_code != 0
    assert "not implemented" in combined.lower()


@pytest.mark.parametrize("command", [
    ["snapshots", "show", "bad$$id"],
    ["snapshots", "forget", "bad$$id"],
])
@pytest.mark.unit
def test_snapshots_commands_reject_invalid_snapshot_id(command):
    result = runner.invoke(app, command)
    combined = _combined_output(result)
    assert result.exit_code != 0
    assert re.search(r"Invalid\s+snapshot\s+ID\s+format", combined, flags=re.IGNORECASE)


@pytest.mark.unit
def test_restore_commands_reject_invalid_snapshot_id():
    command_factories = [
            lambda snapshot_id, paths: ["restore", "browse", "test-repo", snapshot_id],
            lambda snapshot_id, paths: ["restore", "full", "test-repo", snapshot_id, paths["target"]],
            lambda snapshot_id, paths: ["restore", "files", "test-repo", snapshot_id, "/var/log/syslog", "--target", paths["target"]],
            lambda snapshot_id, paths: ["restore", "mount", "test-repo", snapshot_id, paths["mount"]],
            lambda snapshot_id, paths: ["restore", "find", "test-repo", "namepattern", "--snapshot", snapshot_id],
    ]

    with patch_restore_commands(mode="invalid_snapshot"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            mount_dir = Path(tmp_dir) / "mount"
            mount_dir.mkdir()
            target_dir = Path(tmp_dir) / "target"
            target_dir.mkdir()
            paths = {"mount": str(mount_dir), "target": str(target_dir)}

            snapshot_id = "bad$$id"
            for factory in command_factories:
                command = factory(snapshot_id, paths)
                result = runner.invoke(app, command)
                combined = _combined_output(result)
                assert result.exit_code != 0
                assert "invalid snapshot id" in combined.lower()
