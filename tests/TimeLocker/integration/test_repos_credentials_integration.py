"""Integration test for repository backend credentials lifecycle.

Scenario:
1. Create isolated config and HOME.
2. Create stub restic executable on PATH to satisfy version checks.
3. Add an S3 repository via CLI (with password supplied to avoid prompt).
4. Store per-repository backend credentials using interactive prompts.
5. Show credentials and verify expected fields are reported.

This exercises real CredentialManager (environment master password) and retrieval logic without patching.
"""

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.TimeLocker.cli import app

runner = CliRunner(env={'COLUMNS': '200'})


def _combined_output(result):
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


def _create_stub_restic_script() -> str:
    """Create a stub restic script for version verification.

    Returns a bash script that responds to version commands with mock output.
    """
    return """#!/usr/bin/env bash
if [[ "$*" == *version* ]]; then
  if [[ "$*" == *--json* ]]; then
    echo '{"version":"0.18.0"}'
  else
    echo 'restic 0.18.0 compiled with go1.21.5 on linux/amd64'
  fi
else
  echo 'stub restic'
fi
"""


@pytest.mark.integration
def test_backend_credentials_store_and_show_s3():
    with runner.isolated_filesystem():
        # Prepare isolated HOME so credential manager writes inside sandbox
        home_dir = Path.cwd() / "home"
        home_dir.mkdir()
        config_dir = Path.cwd() / "config"
        config_dir.mkdir()
        bin_dir = Path.cwd() / "bin"
        bin_dir.mkdir()

        # Create stub restic executable to satisfy version verification
        restic_path = bin_dir / "restic"
        restic_path.write_text(_create_stub_restic_script())
        restic_path.chmod(0o755)

        base_path = os.environ.get('PATH', '')
        env = {
                'HOME':                       str(home_dir),
                'COLUMNS':                    '200',
                'PATH':                       f"{bin_dir}:{base_path}",
                # Provide master password so credential manager unlocks non-interactively
                'TIMELOCKER_MASTER_PASSWORD': 'master-secret'
        }

        # 1. Add repository (S3) - minimal host/bucket form
        add_result = runner.invoke(
                app,
                [
                        'repos', 'add', 'myrepo', 's3://dummyhost/bucket',
                        '--password', 'repopass',
                        '--description', 'Integration test repo',
                        '--config-dir', str(config_dir)
                ],
                env=env
        )
        assert add_result.exit_code in (0, 1), _combined_output(add_result)

        # 2. Store repository backend credentials (simulate interactive input)
        # Prompts expected in order: Access Key ID, Secret Access Key, Region, Confirm insecure TLS (y/n)
        credentials_input = "AKIAINT\nSECRETINT\nus-west-1\nn\n"
        set_result = runner.invoke(
                app,
                [
                        'repos', 'credentials', 'set', 'myrepo',
                        '--config-dir', str(config_dir)
                ],
                input=credentials_input,
                env=env
        )
        combined_set = _combined_output(set_result).lower()
        assert set_result.exit_code in (0, 1), combined_set
        assert 'credential' in combined_set

        # 3. Show credentials to verify retrieval
        show_result = runner.invoke(
                app,
                [
                        'repos', 'credentials', 'show', 'myrepo',
                        '--config-dir', str(config_dir)
                ],
                env=env
        )
        combined_show = _combined_output(show_result).lower()
        assert show_result.exit_code in (0, 1), combined_show
        # Validate that Access Key line and region appear
        assert 'access key' in combined_show
        assert 'region' in combined_show
        assert 'us-west-1' in combined_show

        # Sanity check that encrypted credential file was created
        cred_file = home_dir / '.timelocker' / 'credentials' / 'credentials.enc'
        assert cred_file.exists(), 'Encrypted credential store not created'
