---
title: "User Guide: Auto-Completion"
id: "user-guide-auto-completion"
type: [ guide ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "01-11-2025"
tags: [guide, user, cli]
links:
  tooling: []
---

# User Guide: Auto-Completion

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: End Users

## 1. Purpose

Enable command-line auto-completion for TimeLocker so users can quickly access repositories, snapshots, targets, and file paths without memorising names.

## 2. Goal

After completing this guide you will have shell completions installed for `timelocker`/`tl`, including repository URIs, snapshot IDs, and target names.

## 3. Prerequisites

- TimeLocker CLI installed.
- Access to your shell configuration (`~/.bashrc`, `~/.zshrc`, `~/.config/fish/`, etc.).
- Repository credentials available if you want snapshot ID completion (`TIMELOCKER_PASSWORD` or `RESTIC_PASSWORD`).

## 4. Step-by-Step Instructions

### 4.1 Generate Completion Scripts

```bash
# Bash
timelocker completion bash

# Zsh
timelocker completion zsh

# Fish
timelocker completion fish
```

### 4.2 Install Completion Scripts Automatically

```bash
# Bash
timelocker completion bash --install

# Zsh
timelocker completion zsh --install

# Fish
timelocker completion fish --install
```

### 4.3 Manual Installation Per Shell

#### Bash

1. Generate the script: `timelocker completion bash > ~/.bash_completion.d/timelocker-completion.bash`
2. Source it in `~/.bashrc`: `source ~/.bash_completion.d/timelocker-completion.bash`
3. Reload: `source ~/.bashrc`

#### Zsh

1. Ensure directory exists: `mkdir -p ~/.zsh/completions`
2. Generate script: `timelocker completion zsh > ~/.zsh/completions/_timelocker`
3. Update `~/.zshrc`:
   ```bash
   fpath=(~/.zsh/completions $fpath)
   autoload -U compinit && compinit
   ```
4. Reload: `source ~/.zshrc`

#### Fish

1. `mkdir -p ~/.config/fish/completions`
2. `timelocker completion fish > ~/.config/fish/completions/timelocker.fish`
3. Fish automatically loads the script on next session.

### 4.4 Use Completion

- Repository names and URIs:
  ```bash
  timelocker backup create /home/user --repository <TAB>
  timelocker config repositories add myrepo file://<TAB>
  ```
- Snapshot IDs and targets:
  ```bash
  timelocker snapshot <TAB>
  timelocker backup create --target <TAB>
  ```
- Works with the alias `tl` (`tl backup create <TAB>`).

### 4.5 Set Environment Variables for Snapshot Completion

```bash
export TIMELOCKER_PASSWORD="your-repository-password"
# or
export RESTIC_PASSWORD="your-repository-password"
```

## 5. Troubleshooting

- **Completions do not load**: Ensure your shell sources the generated file and restart the terminal.
- **Snapshot IDs missing**: Confirm `TIMELOCKER_PASSWORD` or `RESTIC_PASSWORD` is exported before running `timelocker snapshot <TAB>`.
- **Fish completion not updating**: Delete the existing file in `~/.config/fish/completions/` and regenerate it.

## 6. Frequently Asked Questions (FAQ)

- **Do completions work with `tl` instead of `timelocker`?**
  Yes, the alias is covered by the generated scripts.

- **Can I regenerate scripts after upgrading TimeLocker?**
  Re-run the commands in section 4.2 to update completions for the new version.

# References

- `timelocker completion --help`
- Repository management guide: `docs/guides/user/repository-management-guide.md`
