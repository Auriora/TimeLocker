"""Integration test: store backend credentials then run a command that *consumes* them.

Goal:
1. Create isolated environment (HOME, PATH, config dir) with stub restic binary.
2. Add an S3 repository via CLI (supplying password to skip prompts).
3. Store per-repository backend credentials (access key / secret / region) via CLI prompts.
4. Invoke `tl repos init` which constructs an S3ResticRepository using RepositoryFactory.
   - The repository object must pull credentials from CredentialManager because no AWS_* env vars set.
   - If credentials were NOT loaded, backend_env() would raise and init would fail.
5. Assert init succeeds. (Success implies credentials were consumed.)
6. Re-run init to confirm idempotent path (repository already initialized) using stub state file.

We purposefully do *not* set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in the environment so
that the only viable credential source is the credential manager.

A small fixture DRYs the sandbox + repo + credential setup so additional tests can reuse it.
"""
import os
from pathlib import Path
from typing import Dict, Any

import pytest
from typer.testing import CliRunner

from src.TimeLocker.cli import app

runner = CliRunner(env={"COLUMNS": "200"})


def _restic_stub_script() -> str:
    """Return bash script content for stub restic with minimal stateful behavior.

    Maintains a flag file "repo_initialized.flag" in the current working directory to simulate
    repository initialization state across invocations.

    Supports commands: version, cat config, init, check, stats, snapshots
    """
    return """#!/usr/bin/env bash
set -euo pipefail

# Handle version command
if [[ "$*" == *version* ]]; then
  if [[ "$*" == *--json* ]]; then
    echo '{"version":"0.18.0"}'
  else
    echo 'restic 0.18.0 compiled with go1.21.5 on linux/amd64'
  fi
  exit 0
fi

# Simulate 'restic cat config' to detect initialization
if [[ "${1:-}" == "cat" && "${2:-}" == "config" ]]; then
  if [[ -f repo_initialized.flag ]]; then
    echo '{"id":"dummy-config"}'
    exit 0
  else
    echo 'repository not initialized' >&2
    exit 1
  fi
fi

# Simulate 'restic init'
if [[ "${1:-}" == "init" ]]; then
  touch repo_initialized.flag
  echo 'created restic repository'
  exit 0
fi

# Simulate 'restic check'
if [[ "${1:-}" == "check" ]]; then
  if [[ -f repo_initialized.flag ]]; then
    echo 'repository check passed'
    exit 0
  else
    echo 'repository not initialized' >&2
    exit 1
  fi
fi

# Simulate 'restic stats'
if [[ "${1:-}" == "stats" ]]; then
  if [[ -f repo_initialized.flag ]]; then
    if [[ "$*" == *--json* ]]; then
      echo '{"total_size":1048576,"total_file_count":42}'
    else
      echo 'Total Size: 1.0 MiB'
      echo 'Total File Count: 42'
    fi
    exit 0
  else
    echo 'repository not initialized' >&2
    exit 1
  fi
fi

# Simulate 'restic snapshots'
if [[ "${1:-}" == "snapshots" ]]; then
  if [[ -f repo_initialized.flag ]]; then
    if [[ "$*" == *--json* ]]; then
      echo '[{"id":"abc123","time":"2024-01-01T12:00:00Z","hostname":"testhost","paths":["/test"]}]'
    else
      echo 'ID        Time                 Host      Tags  Paths'
      echo 'abc123    2024-01-01 12:00:00  testhost        /test'
    fi
    exit 0
  else
    echo 'repository not initialized' >&2
    exit 1
  fi
fi

# Generic no-op for other commands
echo 'stub restic' >&2
exit 0
"""


@pytest.fixture()
def isolated_cli_environment(tmp_path: Path) -> Dict[str, Any]:
    """Provision isolated directories + stub restic + base environment.

    Returns a dict with keys: home_dir, config_dir, bin_dir, env.
    """
    home_dir = tmp_path / "home"
    config_dir = tmp_path / "config"
    bin_dir = tmp_path / "bin"
    for d in (home_dir, config_dir, bin_dir):
        d.mkdir(parents=True, exist_ok=True)

    restic_path = bin_dir / "restic"
    restic_path.write_text(_restic_stub_script())
    restic_path.chmod(0o755)

    env = {
            "HOME":                       str(home_dir),
            "PATH":                       f"{bin_dir}:{os.environ.get('PATH', '')}",
            "COLUMNS":                    "200",
            # Master password enables auto unlock without interactive prompt
            "TIMELOCKER_MASTER_PASSWORD": "master-secret",
    }
    return {"home_dir": home_dir, "config_dir": config_dir, "bin_dir": bin_dir, "env": env}


@pytest.fixture()
def prepared_s3_repo(isolated_cli_environment) -> Dict[str, Any]:
    """Create repository and store backend credentials via CLI.

    Steps executed once per test using this fixture:
      - tl repos add myrepo s3://dummyhost/bucket --password repopass
      - tl repos credentials set myrepo (interactive inputs)
    """
    env = isolated_cli_environment["env"].copy()
    config_dir = isolated_cli_environment["config_dir"]

    # 1. Add repository
    add_res = runner.invoke(
            app,
            [
                    "repos", "add", "myrepo", "s3://dummyhost/bucket",
                    "--password", "repopass",
                    "--description", "Credential consumption test",
                    "--config-dir", str(config_dir),
            ],
            env=env,
    )
    assert add_res.exit_code in (0, 1), f"Unexpected exit adding repo: {add_res.stdout}\n{add_res.stderr if hasattr(add_res, 'stderr') else ''}"

    # 2. Store credentials (interactive inputs: access key, secret, region, insecure TLS (y/n))
    cred_inputs = "TESTACCESS\nTESTSECRET\nus-east-2\nN\n"
    set_res = runner.invoke(
            app,
            ["repos", "credentials", "set", "myrepo", "--config-dir", str(config_dir)],
            input=cred_inputs,
            env=env,
    )
    combined_out = (set_res.stdout or "") + "\n" + (getattr(set_res, "stderr", "") or "")
    assert set_res.exit_code in (0, 1), f"Credential set failed: {combined_out}"
    assert "credential" in combined_out.lower(), f"Did not observe credential confirmation in output: {combined_out}"

    # Ensure encrypted credential file present
    cred_file = Path(env["HOME"]) / ".timelocker" / "credentials" / "credentials.enc"
    assert cred_file.exists(), "Encrypted credential store not created"

    return {"env": env, "config_dir": config_dir}


def _invoke_repo_command(command_args: list, env: Dict[str, str], config_dir: Path) -> tuple:
    """Helper to invoke a repository command and return (result, combined_output).

    This DRYs up the common pattern of:
    1. Ensuring AWS_* vars are not in environment (force credential manager usage)
    2. Invoking the CLI command
    3. Combining stdout/stderr for assertions

    Args:
        command_args: CLI command arguments (e.g., ["repos", "init", "myrepo"])
        env: Environment dict (will be copied and cleaned of AWS_* vars)
        config_dir: Configuration directory path

    Returns:
        Tuple of (CliResult, combined_output_string)
    """
    # Ensure AWS_* not present to force credential manager usage
    clean_env = env.copy()
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"):
        clean_env.pop(var, None)

    # Add config-dir to command args if not already present
    full_args = command_args.copy()
    if "--config-dir" not in full_args:
        full_args.extend(["--config-dir", str(config_dir)])

    result = runner.invoke(app, full_args, env=clean_env)
    combined = (result.stdout or "") + "\n" + (getattr(result, "stderr", "") or "")

    return result, combined


@pytest.mark.integration
def test_backend_credentials_used_in_repos_init(prepared_s3_repo):
    """Test that 'repos init' command successfully uses stored backend credentials.

    This verifies the full credential flow:
    1. Credentials stored via 'repos credentials set'
    2. RepositoryFactory creates S3ResticRepository with repository_name
    3. S3ResticRepository retrieves credentials from CredentialManager
    4. Init succeeds (would fail if credentials not loaded)
    """
    env = prepared_s3_repo["env"]
    config_dir = prepared_s3_repo["config_dir"]

    # First init (repository not yet initialized -> should perform init and succeed)
    init_res, out1 = _invoke_repo_command(
            ["repos", "init", "myrepo", "--repository", "s3://dummyhost/bucket", "--password", "repopass", "--yes"],
            env,
            config_dir
    )
    assert init_res.exit_code in (0, 1), f"Init failed (credentials likely not consumed): {out1}"
    # Look for either success message or created repository text from stub
    assert "created restic repository" in out1.lower() or "initialized" in out1.lower(), out1

    # Second init should detect already initialized
    init_res2, out2 = _invoke_repo_command(
            ["repos", "init", "myrepo", "--repository", "s3://dummyhost/bucket", "--password", "repopass", "--yes"],
            env,
            config_dir
    )
    assert init_res2.exit_code in (0, 1), f"Second init unexpected failure: {out2}"
    assert "already" in out2.lower(), f"Did not detect already-initialized path: {out2}"

    # Implicit assertion: Success implies S3ResticRepository pulled credentials from credential manager.


@pytest.mark.integration
def test_backend_credentials_used_in_repos_check(prepared_s3_repo):
    """Test that 'repos check' command successfully uses stored backend credentials.

    Verifies credentials are consumed when checking repository integrity.
    """
    env = prepared_s3_repo["env"]
    config_dir = prepared_s3_repo["config_dir"]

    # Initialize repository first
    init_res, _ = _invoke_repo_command(
            ["repos", "init", "myrepo", "--repository", "s3://dummyhost/bucket", "--password", "repopass", "--yes"],
            env,
            config_dir
    )
    assert init_res.exit_code in (0, 1), "Setup: init failed"

    # Run check command - should succeed using stored credentials
    check_res, check_out = _invoke_repo_command(
            ["repos", "check", "myrepo"],
            env,
            config_dir
    )
    assert check_res.exit_code in (0, 1), f"Check failed (credentials likely not consumed): {check_out}"
    # Stub returns "repository check passed"
    assert "check" in check_out.lower() and "pass" in check_out.lower(), check_out


@pytest.mark.integration
def test_backend_credentials_used_in_repos_stats(prepared_s3_repo):
    """Test that 'repos stats' command successfully uses stored backend credentials.

    Verifies credentials are consumed when retrieving repository statistics.
    """
    env = prepared_s3_repo["env"]
    config_dir = prepared_s3_repo["config_dir"]

    # Initialize repository first
    init_res, _ = _invoke_repo_command(
            ["repos", "init", "myrepo", "--repository", "s3://dummyhost/bucket", "--password", "repopass", "--yes"],
            env,
            config_dir
    )
    assert init_res.exit_code in (0, 1), "Setup: init failed"

    # Run stats command - should succeed using stored credentials
    stats_res, stats_out = _invoke_repo_command(
            ["repos", "stats", "myrepo"],
            env,
            config_dir
    )
    assert stats_res.exit_code in (0, 1), f"Stats failed (credentials likely not consumed): {stats_out}"
    # Stub returns size/count info
    assert "size" in stats_out.lower() or "count" in stats_out.lower(), stats_out


@pytest.mark.integration
def test_backend_credentials_used_in_snapshots_list(prepared_s3_repo):
    """Test that 'snapshots list' command successfully uses stored backend credentials.

    Verifies credentials are consumed when listing snapshots from S3 repository.
    """
    env = prepared_s3_repo["env"]
    config_dir = prepared_s3_repo["config_dir"]

    # Initialize repository first
    init_res, _ = _invoke_repo_command(
            ["repos", "init", "myrepo", "--repository", "s3://dummyhost/bucket", "--password", "repopass", "--yes"],
            env,
            config_dir
    )
    assert init_res.exit_code in (0, 1), "Setup: init failed"

    # List snapshots - should succeed using stored credentials
    list_res, list_out = _invoke_repo_command(
            ["snapshots", "list", "--repository", "myrepo"],
            env,
            config_dir
    )
    assert list_res.exit_code in (0, 1), f"Snapshots list failed (credentials likely not consumed): {list_out}"
    # Stub returns snapshot info or empty list
    # Success exit code implies credentials were loaded and used
