# TimeLocker Automation Examples

## Environment Variable Setup for Scheduled Runs

For scheduled/automated runs, environment variables are the most reliable approach.

### Option 1: Environment Variables (Recommended for Automation)

#### Set up environment variables:

```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
export TIMELOCKER_PASSWORD="your-repository-password"

# Or create a dedicated environment file
echo 'TIMELOCKER_PASSWORD="your-repository-password"' > ~/.config/timelocker/env
chmod 600 ~/.config/timelocker/env
```

#### Test the configuration:

```bash
# Source the environment
source ~/.config/timelocker/env

# Test TimeLocker can access the repository
cd /home/bcherrington/Projects/Auriora/TimeLocker
python3 -m src.TimeLocker.cli repo check local-test
```

### Option 2: Systemd Timer (Recommended for Linux)

#### Create systemd service file:

```bash
sudo tee /etc/systemd/system/timelocker-backup.service << 'EOF'
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

#### Create systemd timer file:

```bash
sudo tee /etc/systemd/system/timelocker-backup.timer << 'EOF'
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

#### Enable and start the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable timelocker-backup.timer
sudo systemctl start timelocker-backup.timer

# Check timer status
sudo systemctl status timelocker-backup.timer
sudo systemctl list-timers timelocker-backup.timer
```

### Option 3: Cron Job

#### Create a wrapper script:

```bash
cat > ~/.local/bin/timelocker-backup.sh << 'EOF'
#!/bin/bash

# Set environment
export TIMELOCKER_PASSWORD="your-repository-password"
export PATH="/usr/local/bin:/usr/bin:/bin"

# Change to TimeLocker directory
cd /home/bcherrington/Projects/Auriora/TimeLocker

# Run backup with logging
python3 -m src.TimeLocker.cli backup run my-backup-target >> ~/.local/share/timelocker/backup.log 2>&1
EOF

chmod +x ~/.local/bin/timelocker-backup.sh
```

#### Add to crontab:

```bash
# Edit crontab
crontab -e

# Add this line for daily backup at 2 AM
0 2 * * * /home/bcherrington/.local/bin/timelocker-backup.sh
```

### Option 4: Docker/Container Deployment

#### Dockerfile example:

```dockerfile
FROM python:3.11-slim

# Install TimeLocker dependencies
RUN pip install keyring

# Copy TimeLocker
COPY . /app/timelocker
WORKDIR /app/timelocker

# Set environment variables
ENV TIMELOCKER_PASSWORD=""

# Run backup
CMD ["python3", "-m", "src.TimeLocker.cli", "backup", "run", "my-backup-target"]
```

#### Docker Compose with secrets:

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

## Security Best Practices for Automation

### 1. Environment File Security

```bash
# Create secure environment file
mkdir -p ~/.config/timelocker
echo 'TIMELOCKER_PASSWORD="your-secure-password"' > ~/.config/timelocker/env
chmod 600 ~/.config/timelocker/env
chown $USER:$USER ~/.config/timelocker/env
```

### 2. Systemd Environment File

```bash
# Create systemd environment file
sudo mkdir -p /etc/timelocker
echo 'TIMELOCKER_PASSWORD=your-secure-password' | sudo tee /etc/timelocker/environment
sudo chmod 600 /etc/timelocker/environment
sudo chown root:root /etc/timelocker/environment

# Update systemd service to use environment file
[Service]
EnvironmentFile=/etc/timelocker/environment
```

### 3. Using systemd-creds (systemd 247+)

```bash
# Store password as systemd credential
echo "your-secure-password" | sudo systemd-creds encrypt --name=timelocker-password -

# Use in systemd service
[Service]
LoadCredential=timelocker-password
ExecStart=/bin/bash -c 'export TIMELOCKER_PASSWORD="$(cat $CREDENTIALS_DIRECTORY/timelocker-password)"; python3 -m src.TimeLocker.cli backup run my-target'
```

## Monitoring and Logging

### 1. Systemd Journal Monitoring

```bash
# View backup logs
journalctl -u timelocker-backup.service -f

# View timer logs
journalctl -u timelocker-backup.timer -f
```

### 2. Log Rotation

```bash
# Create logrotate config
sudo tee /etc/logrotate.d/timelocker << 'EOF'
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

### 3. Health Checks

```bash
# Add health check to backup script
#!/bin/bash
export TIMELOCKER_PASSWORD="your-password"
cd /home/bcherrington/Projects/Auriora/TimeLocker

# Run backup
if python3 -m src.TimeLocker.cli backup run my-target; then
    echo "$(date): Backup completed successfully" >> ~/.local/share/timelocker/backup.log
    # Optional: Send success notification
    # curl -X POST "https://api.healthchecks.io/ping/your-uuid"
else
    echo "$(date): Backup failed" >> ~/.local/share/timelocker/backup.log
    # Optional: Send failure notification
    # curl -X POST "https://api.healthchecks.io/ping/your-uuid/fail"
    exit 1
fi
```

## Recommended Setup for Your Use Case

Since you need scheduled intervals, I recommend:

1. **Use environment variables** for password management
2. **Use systemd timers** (if on Linux) or **cron** (if on other systems)
3. **Set up proper logging and monitoring**
4. **Use health checks** to ensure backups are working

Would you like me to help you set up any of these specific automation methods?
