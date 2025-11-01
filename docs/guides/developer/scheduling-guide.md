---
title: "Developer Guide: Scheduling Backups"
id: "dev-guide-scheduling"
type: [ guide ]
status: [ approved ]
owner: "Operations Team"
last_reviewed: "01-11-2025"
tags: [guide, developer, scheduling]
links:
  tooling: []
---

# Developer Guide: Scheduling Backups

- **Owner**: Operations Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: Developers, Operators

## 1. Purpose

Provide actionable steps for scheduling recurring TimeLocker backups using systemd timers or cron, including validation, customization, and troubleshooting guidance.

## 2. Steps

### 2.1 Prepare Secrets
1. Edit the reusable environment file:
   ```bash
   nano ~/.config/timelocker/env
   TIMELOCKER_PASSWORD="your-actual-repository-password"
   ```
2. Validate the configuration:
   ```bash
   ~/.local/bin/timelocker-test.sh
   ```

### 2.2 Option A – systemd Timer (Recommended on Linux)
1. Install service and timer units:
   ```bash
   sudo cp ~/.config/timelocker/timelocker-backup.service /etc/systemd/system/
   sudo cp ~/.config/timelocker/timelocker-backup.timer /etc/systemd/system/
   ```
2. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now timelocker-backup.timer
   ```
3. Monitor runtime:
   ```bash
   journalctl -u timelocker-backup.service -f
   journalctl -u timelocker-backup.timer -f
   ```
4. Modify schedule by editing the timer and reloading:
   ```bash
   sudo nano /etc/systemd/system/timelocker-backup.timer
   sudo systemctl daemon-reload
   sudo systemctl restart timelocker-backup.timer
   ```

### 2.3 Option B – Cron Job
1. Edit crontab (`crontab -e`) and choose a schedule:
   ```bash
   # Daily at 2 AM
   0 2 * * * /home/bcherrington/.local/bin/timelocker-backup.sh
   # Every 6 hours
   0 */6 * * * /home/bcherrington/.local/bin/timelocker-backup.sh
   # Weekly on Sunday at 3 AM
   0 3 * * 0 /home/bcherrington/.local/bin/timelocker-backup.sh
   ```
2. Monitor logs:
   ```bash
   tail -f ~/.local/share/timelocker/backup.log
   grep CRON /var/log/syslog | tail
   ```

### 2.4 Customize Backup Script
1. Adjust target:
   ```bash
   python3 -m src.TimeLocker.cli backup run your-backup-target-name
   ```
2. Process multiple targets:
   ```bash
   for target in target1 target2 target3; do
       python3 -m src.TimeLocker.cli backup run "$target"
   done
   ```
3. Add health checks:
   ```bash
   if python3 -m src.TimeLocker.cli backup run my-target; then
       curl -fsS https://hc-ping.com/your-uuid
   else
       curl -fsS https://hc-ping.com/your-uuid/fail
       exit 1
   fi
   ```
4. Extend environment variables within `~/.config/timelocker/env` (repository overrides, cache location, bandwidth limits, AWS credentials, etc.).

## 3. Troubleshooting

- **Permission issues**:
  ```bash
  chmod +x ~/.local/bin/timelocker-backup.sh
  chmod 600 ~/.config/timelocker/env
  ```
- **Python import errors**:
  ```bash
  export PYTHONPATH="/home/bcherrington/Projects/Auriora/TimeLocker:$PYTHONPATH"
  ```
- **Repository not found**:
  ```bash
  python3 -m src.TimeLocker.cli config repositories show local-test
  ```
- **Verify manually**:
  ```bash
  ~/.local/bin/timelocker-backup.sh
  ```
- **Log locations**:
  - Backup logs: `~/.local/share/timelocker/backup.log`
  - systemd logs: `journalctl -u timelocker-backup.service`
  - Cron logs: `/var/log/syslog` or `/var/log/cron`

# References

- `docs/guides/developer/automation-examples.md`
- `docs/guides/user/per-repo-credentials.md`
- `docs/guides/user/installation.md`
