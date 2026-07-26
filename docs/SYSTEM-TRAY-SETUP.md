# Independent System Tray Setup

The TimeLocker tray is an optional, independent user-session process. Normal
CLI startup never initializes the tray. The tray communicates with the
protected local backend and can disappear or restart without affecting an
active backup or retention run.

## Current Capability

The tray can:

- show backend availability;
- show active operation count;
- show the latest backup and retention status;
- show the next known backup and retention times;
- request the allowlisted system backup;
- request retention when supplied the exact approved policy fingerprint; and
- degrade to a warning state when the backend is unavailable or access is
  denied.

`open_ui` is a reserved no-op. TimeLocker does not currently provide a full
desktop UI. The default system autostart does not contain the approved
retention fingerprint, so it hides `Run Retention`; operators can still request
retention with `timelocker system retention --policy-fingerprint ...`, and a
future managed tray configuration may enable the same action.

## Authorization

The tray runs as the signed-in desktop user, never as root. The user must be a
current member of `timelocker-operators`; the backend rechecks group membership
for each request. After adding a user to the group, start a new login session
before relying on the tray.

## Linux Setup

The protected installer places:

```text
/usr/local/bin/timelocker-tray
/etc/xdg/autostart/timelocker-tray.desktop
/usr/local/share/icons/hicolor/1024x1024/apps/timelocker.png
```

The packaged TimeLocker logo is the tray and desktop-entry icon. Backup,
retention, and backend state remain available through the tray menu and status
text rather than replacing the application identity with unrelated theme
icons. On Linux, the tray menu includes the latest backup date and time in the
desktop session's local timezone.

On Linux Mint/Ubuntu with Cinnamon or GNOME-compatible panels, install the GTK
and AppIndicator runtime:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 \
  gir1.2-ayatanaappindicator3-0.1
```

Log out and back in to load the system autostart entry. For a one-shot
diagnostic that does not create a persistent tray icon:

```bash
timelocker-tray status --once
```

To run the foreground process for troubleshooting:

```bash
timelocker-tray serve
```

## Failure Behavior

- `Access denied` means the desktop user is not currently authorized.
- `System backend unavailable` means the local socket/backend is unavailable;
  the tray retries with bounded backoff.
- A backup or retention conflict is reported by the backend and does not start
  overlapping repository work.
- Quitting the tray does not stop backend services, timers, or operations.

## Platform Status

The process boundary is platform-neutral and the source contains a Windows
adapter. The independently installed protected tray/backend deployment has live
acceptance evidence on Linux Mint. This document does not claim a live-accepted
Windows installation.

## References

- [System Architecture](./2-architecture/system-architecture.md)
- [Installation](./guides/user/installation.md)
- [Backup Operations Troubleshooting](./guides/user/backup-operations-troubleshooting.md)
