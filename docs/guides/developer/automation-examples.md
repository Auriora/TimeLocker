---
title: "Developer Guide: Automation Examples"
id: "dev-guide-automation-examples"
type: [ guide ]
status: [ approved ]
owner: "Operations Team"
last_reviewed: "01-11-2025"
tags: [guide, developer, automation]
links:
  tooling: []
---

# Developer Guide: Automation Examples

- **Owner**: Operations Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: Developers, Operators

## 1. Purpose

Describe common automation patterns for running TimeLocker on schedules and unattended environments. Use this guide to configure environment variables, timers, cron jobs, or container-based automation with appropriate security controls.

## 2. Steps

### 2.1 Configure Environment Variables (Recommended Baseline)
1. Create a secure environment file:
   ```bash
   mkdir -p ~/.config/timelocker
   echo 'TIMELOCKER_PASSWORD="your-repository-password"' > ~/.config/timelocker/env
   chmod 600 ~/.config/timelocker/env
   ```
2. Source the file before invoking TimeLocker:
   ```bash
   source ~/.config/timelocker/env
   cd /home/bcherrington/Projects/Auriora/TimeLocker
   python3 -m src.TimeLocker.cli repo check local-test
   ```

### 2.2 Automate With systemd Timers (Linux)
1. Create the service definition:
   ```bash
   sudo tee /etc/systemd/system/timelocker-backup.service <<'EOF'
   [Unit]
   Description=TimeLocker Backup Service
   After=network.target

   [Service]
   Type=oneshot
   User=bcherrington
   Group=bcherrington
   WorkingDirectory=/home/bcherrington/Projects/Auriora/TimeLocker
   Environment=TIMELOCKER_PASSWORD=your-repository-password
   ExecStart=/usr/bin/python3 -m src.TimeLocker.cli backup run my-backup-target
   StandardOutput=journal
   StandardError=journal
   EOF
   ```
2. Create the timer:
   ```bash
   sudo tee /etc/systemd/system/timelocker-backup.timer <<'EOF'
   [Unit]
   Description=Run TimeLocker backup daily
   Requires=timelocker-backup.service

   [Timer]
   OnCalendar=daily
   Persistent=true
   RandomizedDelaySec=1800

   [Install]
   WantedBy=timers.target
   EOF
   ```
3. Enable and monitor:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now timelocker-backup.timer
   journalctl -u timelocker-backup.timer -f
   ```

### 2.3 Automate With Cron
1. Create a wrapper script:
   ```bash
   cat > ~/.local/bin/timelocker-backup.sh <<'EOF'
   #!/bin/bash
   export TIMELOCKER_PASSWORD="your-repository-password"
   export PATH="/usr/local/bin:/usr/bin:/bin"
   cd /home/bcherrington/Projects/Auriora/TimeLocker
   python3 -m src.TimeLocker.cli backup run my-backup-target >> ~/.local/share/timelocker/backup.log 2>&1
   EOF
   chmod +x ~/.local/bin/timelocker-backup.sh
   ```
2. Schedule via `crontab -e`:
   ```bash
   0 2 * * * /home/bcherrington/.local/bin/timelocker-backup.sh
   ```

### 2.4 Automate With Containers
1. Minimal Dockerfile:
   ```dockerfile
   FROM python:3.11-slim
   RUN pip install keyring
   COPY . /app/timelocker
   WORKDIR /app/timelocker
   ENV TIMELOCKER_PASSWORD=""
   CMD ["python3", "-m", "src.TimeLocker.cli", "backup", "run", "my-backup-target"]
   ```
2. Docker Compose with secrets:
   ```yaml
   version: '3.8'
   services:
     timelocker-backup:
       build: .
       environment:
         - TIMELOCKER_PASSWORD_FILE=/run/secrets/repo_password
       secrets:
         - repo_password
       volumes:
         - backup_data:/data
         - ./config:/app/config
   secrets:
     repo_password:
       file: ./secrets/repository_password.txt
   volumes:
     backup_data:
   ```

## 3. Troubleshooting

- **Secure environment files**:
  ```bash
  chmod 600 ~/.config/timelocker/env
  chown $USER:$USER ~/.config/timelocker/env
  ```
- **systemd environment overrides**:
  ```bash
  sudo mkdir -p /etc/timelocker
  echo 'TIMELOCKER_PASSWORD=your-secure-password' | sudo tee /etc/timelocker/environment
  sudo chmod 600 /etc/timelocker/environment
  ```
- **systemd-creds (247+)**:
  ```bash
  echo "your-secure-password" | sudo systemd-creds encrypt --name=timelocker-password -
  ```
- **Monitoring & logging**:
  ```bash
  journalctl -u timelocker-backup.service -f
  tail -f ~/.local/share/timelocker/backup.log
  ```
- **Log rotation**:
  ```bash
  sudo tee /etc/logrotate.d/timelocker <<'EOF'
  /home/bcherrington/.local/share/timelocker/*.log {
      daily
      rotate 30
      compress
      delaycompress
      missingok
      notifempty
      create 644 bcherrington bcherrington
  }
  EOF
  ```
- **Health checks** (optional):
  ```bash
  if python3 -m src.TimeLocker.cli backup run my-target; then
      curl -fsS https://api.healthchecks.io/ping/your-uuid
  else
      curl -fsS https://api.healthchecks.io/ping/your-uuid/fail
  fi
  ```

# References

- `docs/guides/developer/scheduling-guide.md`
- `docs/guides/user/per-repo-credentials.md`
- `docs/guides/user/repository-management-guide.md`
