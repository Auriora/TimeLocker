# TimeLocker Auto-Completion Guide

TimeLocker provides intelligent auto-completion for shell environments, making it easier to work with repositories, snapshots, targets, and file paths.

## Features

### Smart Completion Types

1. **Repository Names**: Auto-completes configured repository names from your TimeLocker configuration
2. **Repository URIs**: Suggests common URI patterns (file://, s3:, sftp:, rest:) and completes file paths
3. **Snapshot IDs**: Completes snapshot IDs from repositories (requires password in environment)
4. **Target Names**: Auto-completes configured backup target names
5. **File Paths**: Standard file and directory path completion

### Supported Commands

#### Backup Operations

- `timelocker backup create <paths>` - File path completion for source paths
- `timelocker backup create --repository <uri>` - Repository URI completion
- `timelocker backup create --target <name>` - Target name completion

#### Snapshot Operations

- `timelocker snapshot <id>` - Snapshot ID completion
- `timelocker snapshot <id> restore <path>` - File path completion for restore target
- `timelocker snapshots list --repository <name>` - Repository name/URI completion

#### Repository Operations

- `timelocker repo <name> init` - Repository name completion
- `timelocker repo <name> init --repository <uri>` - Repository URI completion

#### Configuration Operations

- `timelocker config repositories add <name> <uri>` - Repository URI completion
- `timelocker config repositories remove <name>` - Repository name completion
- `timelocker config repositories default <name>` - Repository name completion
- `timelocker config targets add <name> <paths>` - File path completion

## Installation

### Generate Completion Scripts

TimeLocker includes a built-in command to generate completion scripts for different shells:

```bash
# Generate bash completion script
timelocker completion bash

# Generate zsh completion script  
timelocker completion zsh

# Generate fish completion script
timelocker completion fish
```

### Install Completion Scripts

Use the `--install` flag to automatically install completion scripts:

```bash
# Install bash completion
timelocker completion bash --install

# Install zsh completion
timelocker completion zsh --install

# Install fish completion
timelocker completion fish --install
```

### Manual Installation

#### Bash

1. Generate the completion script:
   ```bash
   timelocker completion bash > ~/.bash_completion.d/timelocker-completion.bash
   ```

2. Add to your `~/.bashrc`:
   ```bash
   source ~/.bash_completion.d/timelocker-completion.bash
   ```

3. Reload your shell:
   ```bash
   source ~/.bashrc
   ```

#### Zsh

1. Create completion directory (if it doesn't exist):
   ```bash
   mkdir -p ~/.zsh/completions
   ```

2. Generate the completion script:
   ```bash
   timelocker completion zsh > ~/.zsh/completions/_timelocker
   ```

3. Add to your `~/.zshrc`:
   ```bash
   fpath=(~/.zsh/completions $fpath)
   autoload -U compinit && compinit
   ```

4. Reload your shell:
   ```bash
   source ~/.zshrc
   ```

#### Fish

1. Create completion directory (if it doesn't exist):
   ```bash
   mkdir -p ~/.config/fish/completions
   ```

2. Generate the completion script:
   ```bash
   timelocker completion fish > ~/.config/fish/completions/timelocker.fish
   ```

3. Fish will automatically load the completion script.

## Usage Examples

### Repository Completion

```bash
# Type and press TAB to see available repositories
timelocker backup create /home/user --repository <TAB>
# Shows: myrepo, backup-server, local-backup, file://, s3:, sftp:, rest:

# Complete repository URIs
timelocker config repositories add myrepo file://<TAB>
# Shows: file:///home/, file:///backup/, file:///mnt/
```

### Snapshot Completion

```bash
# Complete snapshot IDs (requires TIMELOCKER_PASSWORD or RESTIC_PASSWORD)
timelocker snapshot <TAB>
# Shows: abc123def456, xyz789abc123, def456ghi789

# Complete with partial ID
timelocker snapshot abc<TAB>
# Shows: abc123def456
```

### Target Completion

```bash
# Complete target names
timelocker backup create --target <TAB>
# Shows: documents, photos, system-backup, home-folder
```

### File Path Completion

```bash
# Complete source paths for backup
timelocker backup create /home/<TAB>
# Shows: /home/user/, /home/backup/, /home/shared/

# Complete restore target paths
timelocker snapshot abc123 restore /tmp/<TAB>
# Shows: /tmp/restore/, /tmp/backup/, /tmp/
```

## Environment Variables

For snapshot ID completion to work, you need to set one of these environment variables:

```bash
# TimeLocker-specific (recommended)
export TIMELOCKER_PASSWORD="your-repository-password"

# Or standard restic environment variable
export RESTIC_PASSWORD="your-repository-password"
```

## Aliases

Completion works with the `tl` alias as well:

```bash
# All these work the same
timelocker backup create <TAB>
tl backup create <TAB>

timelocker snapshot <TAB>
tl snapshot <TAB>
```

## Troubleshooting

### Completion Not Working

1. **Check installation**: Verify the completion script is installed and sourced
2. **Restart shell**: Close and reopen your terminal
3. **Check permissions**: Ensure completion files are readable
4. **Test manually**: Try `timelocker completion bash` to verify script generation

### Snapshot Completion Not Working

1. **Check password**: Ensure `TIMELOCKER_PASSWORD` or `RESTIC_PASSWORD` is set
2. **Check repository**: Verify repository is accessible and contains snapshots
3. **Check network**: For remote repositories, ensure network connectivity

### Repository Completion Not Working

1. **Check configuration**: Verify `~/.timelocker/config.json` exists and contains repositories
2. **Check permissions**: Ensure configuration file is readable

## Advanced Configuration

### Custom Completion Functions

The completion system is extensible. You can create custom completion functions by importing from `TimeLocker.completion`:

```python
from TimeLocker.completion import (
    complete_repository_names,
    complete_snapshot_ids,
    complete_target_names,
    complete_repository_uris,
    complete_file_paths
)

# Use in your own scripts
repos = complete_repository_names("my")  # Returns repositories starting with "my"
snapshots = complete_snapshot_ids("abc")  # Returns snapshot IDs starting with "abc"
```

### Performance Optimization

- Snapshot completion caches results for better performance
- Repository and target completion reads from local configuration files
- File path completion uses standard shell mechanisms

## Security Considerations

- Completion functions may access repository passwords from environment variables
- Snapshot IDs are cached temporarily for performance
- No sensitive data is written to completion scripts
- Repository URIs in completion may be visible in shell history
