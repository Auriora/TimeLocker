# TimeLocker Scheduling Guide

## 🚀 Quick Start

Your TimeLocker automation is now set up! Here's how to get it running:

### 1. Set Your Repository Password

```bash
# Edit the environment file
nano ~/.config/timelocker/env

# Set your actual repository password
TIMELOCKER_PASSWORD="your-actual-repository-password"
```

### 2. Test Your Setup

```bash
# Run the test script
~/.local/bin/timelocker-test.sh
```

### 3. Choose Your Scheduling Method

## 🕐 Scheduling Options

### Option A: Systemd Timer (Recommended for Linux)

**Advantages:**

- Better logging integration
- Automatic retry on failure
- System-level management
- Handles missed runs when system was off

**Setup:**

```bash
# Install the systemd files
sudo cp ~/.config/timelocker/timelocker-backup.service /etc/systemd/system/
sudo cp ~/.config/timelocker/timelocker-backup.timer /etc/systemd/system/

# Enable and start the timer
sudo systemctl daemon-reload
sudo systemctl enable timelocker-backup.timer
sudo systemctl start timelocker-backup.timer

# Check status
sudo systemctl status timelocker-backup.timer
sudo systemctl list-timers timelocker-backup.timer
```

**Monitor logs:**

```bash
# View backup logs
journalctl -u timelocker-backup.service -f

# View timer logs
journalctl -u timelocker-backup.timer -f
```

**Modify schedule:**

```bash
# Edit timer file
sudo nano /etc/systemd/system/timelocker-backup.timer

# Common schedules:
# Daily at 2 AM: OnCalendar=daily
# Every 6 hours: OnCalendar=*-*-* 00,06,12,18:00:00
# Weekly on Sunday: OnCalendar=Sun *-*-* 02:00:00
# Monthly on 1st: OnCalendar=*-*-01 02:00:00

# Reload after changes
sudo systemctl daemon-reload
sudo systemctl restart timelocker-backup.timer
```

### Option B: Cron Job

**Advantages:**

- Simple and universal
- Works on all Unix-like systems
- Easy to understand and modify

**Setup:**

```bash
# Edit your crontab
crontab -e

# Add one of these lines:
# Daily at 2 AM:
0 2 * * * /home/bcherrington/.local/bin/timelocker-backup.sh

# Every 6 hours:
0 */6 * * * /home/bcherrington/.local/bin/timelocker-backup.sh

# Twice daily (6 AM and 6 PM):
0 6,18 * * * /home/bcherrington/.local/bin/timelocker-backup.sh

# Weekly on Sunday at 3 AM:
0 3 * * 0 /home/bcherrington/.local/bin/timelocker-backup.sh
```

**Monitor logs:**

```bash
# View backup logs
tail -f ~/.local/share/timelocker/backup.log

# View cron logs (system dependent)
grep CRON /var/log/syslog | tail
```

## 🔧 Customization

### Modify Backup Script

Edit `~/.local/bin/timelocker-backup.sh` to:

1. **Change backup target:**

```bash
# Replace 'my-backup-target' with your actual target name
python3 -m src.TimeLocker.cli backup run your-backup-target-name
```

2. **Add multiple targets:**

```bash
# Backup multiple targets
for target in target1 target2 target3; do
    echo "$(date): Starting backup for $target..." >> "$LOGS_DIR/backup.log"
    if python3 -m src.TimeLocker.cli backup run "$target"; then
        echo "$(date): Backup completed for $target" >> "$LOGS_DIR/backup.log"
    else
        echo "$(date): Backup failed for $target" >> "$LOGS_DIR/backup.log"
    fi
done
```

3. **Add health checks:**

```bash
# Add health check ping (optional)
if python3 -m src.TimeLocker.cli backup run my-target; then
    echo "$(date): Backup completed successfully" >> "$LOGS_DIR/backup.log"
    # Optional: Ping health check service
    # curl -fsS -m 10 --retry 5 -o /dev/null https://hc-ping.com/your-uuid
else
    echo "$(date): Backup failed" >> "$LOGS_DIR/backup.log"
    # Optional: Ping health check service with failure
    # curl -fsS -m 10 --retry 5 -o /dev/null https://hc-ping.com/your-uuid/fail
    exit 1
fi
```

### Environment Variables

You can add more environment variables to `~/.config/timelocker/env`:

```bash
# Repository password (required)
TIMELOCKER_PASSWORD="your-password"

# Optional: Override repository location
RESTIC_REPOSITORY="/path/to/repository"

# Optional: Set cache directory
RESTIC_CACHE_DIR="/home/bcherrington/.cache/restic"

# Optional: Bandwidth limits (KB/s)
RESTIC_LIMIT_UPLOAD=1000
RESTIC_LIMIT_DOWNLOAD=2000

# Optional: AWS credentials (for S3 repositories)
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"
AWS_DEFAULT_REGION="us-east-1"
```

## 🔍 Troubleshooting

### Test Individual Components

```bash
# Test environment loading
source ~/.config/timelocker/env && echo "Environment loaded: $TIMELOCKER_PASSWORD"

# Test TimeLocker CLI
cd /home/bcherrington/Projects/Auriora/TimeLocker
python3 -m src.TimeLocker.cli config repositories list

# Test repository access
python3 -m src.TimeLocker.cli repo check local-test

# Test backup script manually
~/.local/bin/timelocker-backup.sh
```

### Common Issues

1. **Permission denied:**

```bash
chmod +x ~/.local/bin/timelocker-backup.sh
chmod 600 ~/.config/timelocker/env
```

2. **Python module not found:**

```bash
# Make sure you're in the right directory
cd /home/bcherrington/Projects/Auriora/TimeLocker
# Or add to PYTHONPATH in your script
export PYTHONPATH="/home/bcherrington/Projects/Auriora/TimeLocker:$PYTHONPATH"
```

3. **Repository not found:**

```bash
# Check repository configuration
python3 -m src.TimeLocker.cli config repositories show local-test
```

### Log Locations

- **Backup logs:** `~/.local/share/timelocker/backup.log`
- **Systemd logs:** `journalctl -u timelocker-backup.service`
- **Cron logs:** `/var/log/syslog` or `/var/log/cron`

## 🎯 Recommended Setup

For most users, I recommend:

1. **Use systemd timer** (if on Linux)
2. **Daily backups at 2 AM** with random delay
3. **Monitor logs** with `journalctl -u timelocker-backup.service -f`
4. **Set up log rotation** to prevent disk space issues
5. **Add health checks** for monitoring

This provides the best balance of reliability, monitoring, and ease of management.
