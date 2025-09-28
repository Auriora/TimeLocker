import re
from typer.testing import CliRunner

from src.TimeLocker.cli import app

runner = CliRunner()

def _combined_output(result):
    # Combine stdout and stderr for matching convenience across environments
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


def test_umount_rejects_invalid_snapshot_id():
    result = runner.invoke(app, ["snapshots", "umount", "bad$$id"])  # repository not needed for umount
    combined = _combined_output(result)

    assert result.exit_code != 0
    # Check for our validation message
    assert re.search(r"Invalid\s+snapshot\s+ID\s+format", combined, flags=re.IGNORECASE)

