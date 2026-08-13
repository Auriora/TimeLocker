---
title: Independent System Tray Setup
doc_type: guide
status: active
owner: Auriora Team
last_reviewed: 2026-08-12
---

# Independent System Tray Setup

The TimeLocker tray is an optional, independent user-session process. Normal
CLI startup never initializes the tray, and the tray can disappear or restart
without affecting an active backup or retention run.

On launch, the tray performs one explicit protected status request; the helper
answers and exits. The tray then reads `/run/timelocker/status.json` and watches
that file directly, including waiting for its first creation after a clean boot.
Backup and retention workers replace the sanitized snapshot atomically after
durable state changes. Read/open filesystem notifications are ignored, so a
read cannot trigger another read. Explicit actions use the control socket and
start one short-lived protected helper; no privileged tray event service,
heartbeat, or resident backend is required.

## Accepted Presentation Contract

The reusable tray behavior can:

- show backend availability;
- show State, Activity, and Last Backup as three distinct rows;
- request the allowlisted system backup;
- request retention when supplied the exact approved policy fingerprint; and
- degrade to a warning state when protected state is unavailable or access is
  denied.

State describes backup health only. Activity describes transient backup or
retention work. Last Backup is the latest successful completion time, or
`Never`; a failed or interrupted run must not replace the last-success value.

`open_ui` is a reserved no-op. TimeLocker does not currently provide a full
desktop UI. The default system autostart does not contain the approved
retention fingerprint, so it hides `Run Retention`; operators can still request
retention with `timelocker system retention --policy-fingerprint ...`, and a
future managed tray configuration may enable the same action.

## Authorization

The tray runs as the signed-in desktop user, never as root. The user must be a
current member of `timelocker-operators`. Protected explicit actions must
reauthorize the caller for each bounded request. Status observation must expose
only the sanitized snapshot and must not wake or retain a privileged process.
After adding a user to the group, start a new login session before relying on
the tray.

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
- `System status unavailable` means the sanitized snapshot cannot be read or
  validated. It must not cause the tray to poll or keep a privileged service
  alive.
- A backup or retention conflict is reported by the backend and does not start
  overlapping repository work.
- Quitting the tray does not stop timers or active one-shot operations.

## Platform Status

The presentation contract is platform-neutral and the source contains a
Windows adapter. The daemonless Linux implementation has automated acceptance;
the protected 90-second live-host observation remains separately approved.
This document does not claim a live-accepted Windows installation.

## References

- [System Architecture](./2-architecture/system-architecture.md)
- [Installation](./guides/user/installation.md)
- [Backup Operations Troubleshooting](./guides/user/backup-operations-troubleshooting.md)
