import re
import pytest
from typer.testing import CliRunner

from src.TimeLocker.cli import app

# Set wider terminal width to prevent help text truncation in CI
runner = CliRunner(env={'COLUMNS': '200'})

def _combined_output(result):
    # Combine stdout and stderr for matching convenience across environments
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


@pytest.mark.unit
def test_umount_rejects_invalid_snapshot_id():
    result = runner.invoke(app, ["snapshots", "umount", "bad$$id"])  # repository not needed for umount
    combined = _combined_output(result)

    assert result.exit_code != 0
    # Check for our validation message
    assert re.search(r"Invalid\s+snapshot\s+ID\s+format", combined, flags=re.IGNORECASE)


@pytest.mark.parametrize("command", [
    ["snapshots", "umount", "bad$$id"],
    ["snapshots", "show", "bad$$id"],
    ["snapshots", "contents", "bad$$id"],
    ["snapshots", "mount", "bad$$id", "."],
    ["snapshots", "find-in", "bad$$id", "namepattern"],
    ["snapshots", "forget", "bad$$id"],
])
@pytest.mark.unit
def test_commands_reject_invalid_snapshot_id(command):
    result = runner.invoke(app, command)
    combined = _combined_output(result)
    assert result.exit_code != 0
    assert re.search(r"Invalid\s+snapshot\s+ID\s+format", combined, flags=re.IGNORECASE)
