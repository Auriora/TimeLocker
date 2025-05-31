# TimeLocker UI Mockups

This document provides detailed descriptions and text-based representations of the TimeLocker user interface. These mockups serve as a guide for implementing
the UI components described in the UX flow documentation.

## Table of Contents

1. [Dashboard](#dashboard)
2. [Repository Management](#repository-management)
3. [Backup Configuration](#backup-configuration)
4. [File Selection](#file-selection)
5. [Restore Operation](#restore-operation)
6. [Settings](#settings)
7. [Monitoring & Logs](#monitoring--logs)

## Dashboard

The dashboard provides an overview of the backup status and quick access to common operations.

```
+----------------------------------------------------------------------+
|                           TIMELOCKER                         [⚙️] [👤] |
+----------------------------------------------------------------------+
| [📁 REPOSITORIES] [🔄 BACKUPS] [🔍 RESTORE] [📊 MONITOR] [⚙️ SETTINGS] |
+----------------------------------------------------------------------+
|                                                                      |
|  📊 BACKUP STATUS                      🔔 RECENT ACTIVITY             |
|  +----------------------------+        +-------------------------+   |
|  | Repository Health          |        | Today 10:15 AM          |   |
|  | ┌────────────────────────┐ |        | Backup completed        |   |
|  | │ 3/4 Repositories OK    │ |        | Documents - 1.2GB       |   |
|  | └────────────────────────┘ |        |                         |   |
|  |                            |        | Today 09:30 AM          |   |
|  | Recent Backups             |        | Repository check        |   |
|  | ┌────────────────────────┐ |        | Photos - OK             |   |
|  | │ 12/15 Successful       │ |        |                         |   |
|  | └────────────────────────┘ |        | Yesterday 11:45 PM      |   |
|  |                            |        | Backup failed           |   |
|  | Storage Usage              |        | Projects - Error        |   |
|  | ┌────────────────────────┐ |        |                         |   |
|  | │ 1.2TB / 2TB (60%)      │ |        | [View All Activity]     |   |
|  | └────────────────────────┘ |        +-------------------------+   |
|  +----------------------------+                                      |
|                                                                      |
|  🔄 QUICK ACTIONS                      📅 SCHEDULED BACKUPS          |
|  +----------------------------+        +-------------------------+   |
|  | [+ New Repository]         |        | Today 11:00 PM          |   |
|  | [+ New Backup]             |        | Documents & Photos      |   |
|  | [Run Check]                |        |                         |   |
|  | [Restore Files]            |        | Tomorrow 03:00 AM       |   |
|  +----------------------------+        | Projects                |   |
|                                        |                         |   |
|                                        | [View All Schedules]    |   |
|                                        +-------------------------+   |
|                                                                      |
+----------------------------------------------------------------------+
```

### Dashboard Components

- **Header Bar**: Contains the application logo, settings button, and user profile
- **Main Navigation**: Tabs for different sections of the application
- **Backup Status**: Visual indicators of repository health, recent backup success rate, and storage usage
- **Recent Activity**: Timeline of recent backup operations and events
- **Quick Actions**: Buttons for common operations
- **Scheduled Backups**: List of upcoming scheduled backup jobs

## Repository Management

The repository management screen allows users to create, configure, and manage backup repositories.

```
+----------------------------------------------------------------------+
|                           TIMELOCKER                         [⚙️] [👤] |
+----------------------------------------------------------------------+
| [📁 REPOSITORIES] [🔄 BACKUPS] [🔍 RESTORE] [📊 MONITOR] [⚙️ SETTINGS] |
+----------------------------------------------------------------------+
|                                                                      |
|  📁 REPOSITORIES                                    [+ NEW REPOSITORY] |
|  +------------------------------------------------------------------+ |
|  | FILTER: [All Types ▼] [All Status ▼]                  [🔍 Search] | |
|  |                                                                  | |
|  | ┌────────────┬─────────────┬──────────┬────────────┬──────────┐ | |
|  | │ NAME       │ TYPE        │ LOCATION │ STATUS     │ ACTIONS  │ | |
|  | ├────────────┼─────────────┼──────────┼────────────┼──────────┤ | |
|  | │ Documents  │ Local       │ /backup  │ ✅ OK      │ [⚙️][🔍][❌]│ | |
|  | │            │             │          │            │          │ | |
|  | │ Photos     │ S3          │ s3://... │ ✅ OK      │ [⚙️][🔍][❌]│ | |
|  | │            │             │          │            │          │ | |
|  | │ Projects   │ B2          │ b2://... │ ⚠️ Warning │ [⚙️][🔍][❌]│ | |
|  | │            │             │          │            │          │ | |
|  | │ Archive    │ SFTP        │ sftp://..│ ❌ Error   │ [⚙️][🔍][❌]│ | |
|  | │            │             │          │            │          │ | |
|  | └────────────┴─────────────┴──────────┴────────────┴──────────┘ | |
|  |                                                                  | |
|  | [< Previous] Page 1 of 1 [Next >]                                | |
|  +------------------------------------------------------------------+ |
|                                                                      |
+----------------------------------------------------------------------+
```

### Repository Details Modal

```
+----------------------------------------------------------------------+
|  REPOSITORY DETAILS: DOCUMENTS                                   [X] |
+----------------------------------------------------------------------+
|                                                                      |
|  General Information                                                 |
|  +------------------------------------------------------------------+ |
|  | Name:        | Documents                                         | |
|  | Type:        | Local                                             | |
|  | Location:    | /backup/documents                                 | |
|  | Created:     | 2023-11-15 10:30 AM                               | |
|  | Last Access: | 2023-11-20 03:45 PM                               | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Statistics                                                          |
|  +------------------------------------------------------------------+ |
|  | Total Size:      | 256.4 GB                                      | |
|  | Snapshots:       | 15                                            | |
|  | Latest Snapshot: | 2023-11-20 03:45 PM                           | |
|  | Oldest Snapshot: | 2023-11-15 10:30 AM                           | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Actions                                                             |
|  +------------------------------------------------------------------+ |
|  | [🔍 Browse Snapshots] [🔄 Run Check] [⚙️ Edit] [❌ Delete]         | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|                                          [CLOSE] [EDIT REPOSITORY]   |
+----------------------------------------------------------------------+
```

### New Repository Modal

```
+----------------------------------------------------------------------+
|  CREATE NEW REPOSITORY                                           [X] |
+----------------------------------------------------------------------+
|                                                                      |
|  Repository Information                                              |
|  +------------------------------------------------------------------+ |
|  | Name:        | [                                              ]  | |
|  | Type:        | [Local       ▼]                                   | |
|  | Location:    | [                                              ]  | |
|  |              | [Browse...]                                       | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Security                                                            |
|  +------------------------------------------------------------------+ |
|  | Password:    | [••••••••••••••]                                  | |
|  | Confirm:     | [••••••••••••••]                                  | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Advanced Options (for cloud repositories)                           |
|  +------------------------------------------------------------------+ |
|  | [ ] Custom credentials                                           | |
|  |                                                                  | |
|  | Access Key:   | [                                             ]  | |
|  | Secret Key:   | [                                             ]  | |
|  | Region:       | [us-east-1    ▼]                                 | |
|  | Bucket:       | [                                             ]  | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|                                          [CANCEL] [CREATE REPOSITORY] |
+----------------------------------------------------------------------+
```

## Backup Configuration

The backup configuration screen allows users to create and manage backup jobs.

```
+----------------------------------------------------------------------+
|                           TIMELOCKER                         [⚙️] [👤] |
+----------------------------------------------------------------------+
| [📁 REPOSITORIES] [🔄 BACKUPS] [🔍 RESTORE] [📊 MONITOR] [⚙️ SETTINGS] |
+----------------------------------------------------------------------+
|                                                                      |
|  🔄 BACKUP JOBS                                        [+ NEW BACKUP] |
|  +------------------------------------------------------------------+ |
|  | FILTER: [All Repositories ▼] [All Status ▼]            [🔍 Search] | |
|  |                                                                  | |
|  | ┌────────────┬─────────────┬──────────┬────────────┬──────────┐ | |
|  | │ NAME       │ REPOSITORY  │ SCHEDULE │ STATUS     │ ACTIONS  │ | |
|  | ├────────────┼─────────────┼──────────┼────────────┼──────────┤ | |
|  | │ Daily Docs │ Documents   │ Daily    │ ✅ OK      │ [▶️][⚙️][❌]│ | |
|  | │            │             │ 11:00 PM │            │          │ | |
|  | │ Weekly     │ Projects    │ Weekly   │ ✅ OK      │ [▶️][⚙️][❌]│ | |
|  | │ Projects   │             │ Sunday   │            │          │ | |
|  | │            │             │ 03:00 AM │            │          │ | |
|  | │ Photos     │ Photos      │ Manual   │ ⚠️ Warning │ [▶️][⚙️][❌]│ | |
|  | │ Backup     │             │          │            │          │ | |
|  | │            │             │          │            │          │ | |
|  | └────────────┴─────────────┴──────────┴────────────┴──────────┘ | |
|  |                                                                  | |
|  | [< Previous] Page 1 of 1 [Next >]                                | |
|  +------------------------------------------------------------------+ |
|                                                                      |
+----------------------------------------------------------------------+
```

### New Backup Job Modal

```
+----------------------------------------------------------------------+
|  CREATE NEW BACKUP JOB                                           [X] |
+----------------------------------------------------------------------+
|                                                                      |
|  Basic Information                                                   |
|  +------------------------------------------------------------------+ |
|  | Name:        | [                                              ]  | |
|  | Repository:  | [Documents    ▼]                                  | |
|  | Tags:        | [                                              ]  | |
|  |              | (comma-separated, e.g., daily,documents)          | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Schedule                                                            |
|  +------------------------------------------------------------------+ |
|  | [ ] Manual only                                                  | |
|  | [x] Scheduled                                                    | |
|  |                                                                  | |
|  | Frequency:   | [Daily        ▼]                                  | |
|  | Time:        | [23:00        ▼]                                  | |
|  | Days:        | [✓] Mon [✓] Tue [✓] Wed [✓] Thu [✓] Fri [✓] Sat [✓] Sun |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Backup Targets                                                      |
|  +------------------------------------------------------------------+ |
|  | [+ ADD TARGET]                                                   | |
|  |                                                                  | |
|  | Target 1: Documents                                              | |
|  | File Selection: Personal Documents                     [Edit] [X] | |
|  |                                                                  | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|                                              [CANCEL] [CREATE BACKUP] |
+----------------------------------------------------------------------+
```

## File Selection

The file selection screen allows users to define which files to include or exclude in backups.

```
+----------------------------------------------------------------------+
|                           TIMELOCKER                         [⚙️] [👤] |
+----------------------------------------------------------------------+
| [📁 REPOSITORIES] [🔄 BACKUPS] [🔍 RESTORE] [📊 MONITOR] [⚙️ SETTINGS] |
+----------------------------------------------------------------------+
|                                                                      |
|  📂 FILE SELECTIONS                                [+ NEW SELECTION]  |
|  +------------------------------------------------------------------+ |
|  | FILTER: [All Types ▼]                               [🔍 Search]   | |
|  |                                                                  | |
|  | ┌────────────┬─────────────┬──────────────────┬────────────────┐ | |
|  | │ NAME       │ BASE PATHS  │ PATTERNS         │ ACTIONS        │ | |
|  | ├────────────┼─────────────┼──────────────────┼────────────────┤ | |
|  | │ Personal   │ /home/user/ │ 5 include        │ [⚙️][📋][❌]    │ | |
|  | │ Documents  │ documents   │ 3 exclude        │                │ | |
|  | │            │             │                  │                │ | |
|  | │ Work       │ /home/user/ │ 2 include        │ [⚙️][📋][❌]    │ | |
|  | │ Projects   │ projects    │ 4 exclude        │                │ | |
|  | │            │             │                  │                │ | |
|  | │ Photos     │ /home/user/ │ 1 include        │ [⚙️][📋][❌]    │ | |
|  | │            │ pictures    │ 0 exclude        │                │ | |
|  | │            │             │                  │                │ | |
|  | └────────────┴─────────────┴──────────────────┴────────────────┘ | |
|  |                                                                  | |
|  | [< Previous] Page 1 of 1 [Next >]                                | |
|  +------------------------------------------------------------------+ |
|                                                                      |
+----------------------------------------------------------------------+
```

### Edit File Selection Modal

```
+----------------------------------------------------------------------+
|  EDIT FILE SELECTION: PERSONAL DOCUMENTS                         [X] |
+----------------------------------------------------------------------+
|                                                                      |
|  Basic Information                                                   |
|  +------------------------------------------------------------------+ |
|  | Name:          | [Personal Documents                          ]  | |
|  | Base Paths:    | [/home/user/documents                        ]  | |
|  |                | [+ Add Path]                                    | |
|  | Case Sensitive:| [x] Yes [ ] No                                  | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Include/Exclude Patterns                                            |
|  +------------------------------------------------------------------+ |
|  | [+ ADD PATTERN]                                                  | |
|  |                                                                  | |
|  | ┌──────┬─────────────────────────────┬────────────────┐          | |
|  | │ TYPE │ PATTERN                     │ ACTIONS        │          | |
|  | ├──────┼─────────────────────────────┼────────────────┤          | |
|  | │ INC  │ *.docx                      │ [⚙️][❌]        │          | |
|  | │ INC  │ *.xlsx                      │ [⚙️][❌]        │          | |
|  | │ INC  │ *.pdf                       │ [⚙️][❌]        │          | |
|  | │ INC  │ *.txt                       │ [⚙️][❌]        │          | |
|  | │ INC  │ *.md                        │ [⚙️][❌]        │          | |
|  | │ EXC  │ *.tmp                       │ [⚙️][❌]        │          | |
|  | │ EXC  │ *~                          │ [⚙️][❌]        │          | |
|  | │ EXC  │ .git/                       │ [⚙️][❌]        │          | |
|  | └──────┴─────────────────────────────┴────────────────┘          | |
|  |                                                                  | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Pattern Groups                                                      |
|  +------------------------------------------------------------------+ |
|  | [+ ADD GROUP]                                                    | |
|  |                                                                  | |
|  | [x] office_documents (includes *.docx, *.xlsx, *.pptx)     [X]   | |
|  | [ ] source_code (includes *.py, *.js, *.java, *.cpp)       [X]   | |
|  | [ ] media_files (includes *.jpg, *.png, *.mp4, *.mp3)      [X]   | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|                                          [CANCEL] [SAVE SELECTION]    |
+----------------------------------------------------------------------+
```

## Restore Operation

The restore screen allows users to browse snapshots and restore files.

```
+----------------------------------------------------------------------+
|                           TIMELOCKER                         [⚙️] [👤] |
+----------------------------------------------------------------------+
| [📁 REPOSITORIES] [🔄 BACKUPS] [🔍 RESTORE] [📊 MONITOR] [⚙️ SETTINGS] |
+----------------------------------------------------------------------+
|                                                                      |
|  🔍 RESTORE                                                           |
|  +------------------------------------------------------------------+ |
|  | Repository: [Documents    ▼]                                      | |
|  |                                                                  | |
|  | Snapshots:                                                       | |
|  | ┌────────────────┬─────────────────┬──────────────┬───────────┐  | |
|  | │ DATE & TIME    │ TAGS            │ SIZE         │ ACTIONS   │  | |
|  | ├────────────────┼─────────────────┼──────────────┼───────────┤  | |
|  | │ 2023-11-20     │ daily           │ 256.4 GB     │ [🔍][↩️]   │  | |
|  | │ 03:45 PM       │                 │              │           │  | |
|  | │                │                 │              │           │  | |
|  | │ 2023-11-19     │ daily           │ 255.9 GB     │ [🔍][↩️]   │  | |
|  | │ 11:00 PM       │                 │              │           │  | |
|  | │                │                 │              │           │  | |
|  | │ 2023-11-18     │ daily           │ 254.3 GB     │ [🔍][↩️]   │  | |
|  | │ 11:00 PM       │                 │              │           │  | |
|  | └────────────────┴─────────────────┴──────────────┴───────────┘  | |
|  |                                                                  | |
|  | [< Previous] Page 1 of 5 [Next >]                                | |
|  +------------------------------------------------------------------+ |
|                                                                      |
+----------------------------------------------------------------------+
```

### Browse Snapshot Modal

```
+----------------------------------------------------------------------+
|  BROWSE SNAPSHOT: 2023-11-20 03:45 PM                            [X] |
+----------------------------------------------------------------------+
|                                                                      |
|  Path: /home/user/documents/                                 [🔍 Search] |
|  +------------------------------------------------------------------+ |
|  | [📁 ..] [📁 work] [📁 personal] [📁 projects]                     | |
|  |                                                                  | |
|  | ┌──────┬────────────────────┬──────────┬─────────────┬─────────┐ | |
|  | │ TYPE │ NAME               │ SIZE     │ MODIFIED    │ ACTIONS │ | |
|  | ├──────┼────────────────────┼──────────┼─────────────┼─────────┤ | |
|  | │ 📁   │ reports            │ 1.2 GB   │ 2023-11-15  │ [↩️][✓]  │ | |
|  | │      │                    │          │             │         │ | |
|  | │ 📁   │ presentations      │ 845 MB   │ 2023-11-18  │ [↩️][✓]  │ | |
|  | │      │                    │          │             │         │ | |
|  | │ 📄   │ budget-2023.xlsx   │ 2.4 MB   │ 2023-11-20  │ [↩️][✓]  │ | |
|  | │      │                    │          │             │         │ | |
|  | │ 📄   │ proposal.docx      │ 1.8 MB   │ 2023-11-19  │ [↩️][✓]  │ | |
|  | │      │                    │          │             │         │ | |
|  | │ 📄   │ notes.txt          │ 45 KB    │ 2023-11-17  │ [↩️][✓]  │ | |
|  | │      │                    │          │             │         │ | |
|  | └──────┴────────────────────┴──────────┴─────────────┴─────────┘ | |
|  |                                                                  | |
|  | Selected: 0 files, 0 folders                                     | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|  Restore Options                                                     |
|  +------------------------------------------------------------------+ |
|  | Target Path:  | [/home/user/restore                          ]   | |
|  |               | [Browse...]                                      | |
|  | [ ] Overwrite existing files                                     | |
|  +------------------------------------------------------------------+ |
|                                                                      |
|                                          [CANCEL] [RESTORE SELECTED] |
+----------------------------------------------------------------------+
```

## Settings

The settings screen allows users to configure application preferences.

```
+----------------------------------------------------------------------+
|                           TIMELOCKER                         [⚙️] [👤] |
+----------------------------------------------------------------------+
| [📁 REPOSITORIES] [🔄 BACKUPS] [🔍 RESTORE] [📊 MONITOR] [⚙️ SETTINGS] |
+----------------------------------------------------------------------+
|                                                                      |
|  ⚙️ SETTINGS                                                          |
|  +------------------------------------------------------------------+ |
|  | [General] [Appearance] [Notifications] [Advanced] [About]        | |
|  |                                                                  | |
|  | General Settings                                                 | |
|  | +----------------------------------------------------------------+ |
|  | | Application                                                    | |
|  | | Language:     | [English      ▼]                               | |
|  | | Start on boot:| [x] Yes [ ] No                                 | |
|  | | Minimize to tray when closed: [x] Yes [ ] No                   | |
|  | |                                                                | |
|  | | Default Paths                                                  | |
|  | | Default repository location: [/home/user/backups           ]   | |
|  | | Default restore location:    [/home/user/restore           ]   | |
|  | |                                                                | |
|  | | Performance                                                    | |
|  | | Bandwidth limit:     | [No limit    ▼]                         | |
|  | | Concurrent jobs:     | [2           ▼]                         | |
|  | | Compression level:   | [Auto        ▼]                         | |
|  | |                                                                | |
|  | | Security                                                       | |
|  | | Lock vault after inactivity: [15 minutes ▼]                    | |
|  | | Remember passwords:          [ ] Yes [x] No                    | |
|  | +----------------------------------------------------------------+ |
|  |                                                                  | |
|  |                                                [CANCEL] [SAVE]    | |
|  +------------------------------------------------------------------+ |
|                                                                      |
+----------------------------------------------------------------------+
```

## Monitoring & Logs

The monitoring screen provides detailed information about backup operations and system logs.

```
+----------------------------------------------------------------------+
|                           TIMELOCKER                         [⚙️] [👤] |
+----------------------------------------------------------------------+
| [📁 REPOSITORIES] [🔄 BACKUPS] [🔍 RESTORE] [📊 MONITOR] [⚙️ SETTINGS] |
+----------------------------------------------------------------------+
|                                                                      |
|  📊 MONITORING                                                        |
|  +------------------------------------------------------------------+ |
|  | [Dashboard] [Activity] [Logs] [Statistics] [Reports]             | |
|  |                                                                  | |
|  | System Logs                                                      | |
|  | +----------------------------------------------------------------+ |
|  | | FILTER: [All Levels ▼] [All Components ▼]           [🔍 Search] | |
|  | |                                                                | |
|  | | ┌────────────────┬─────┬────────────┬─────────────────────────┐| |
|  | | │ TIMESTAMP      │ LVL │ COMPONENT  │ MESSAGE                 │| |
|  | | ├────────────────┼─────┼────────────┼─────────────────────────┤| |
|  | | │ 2023-11-20     │ INFO│ Repository │ Backup job 'Daily Docs' │| |
|  | | │ 15:45:30       │     │            │ completed successfully  │| |
|  | | │                │     │            │                         │| |
|  | | │ 2023-11-20     │ WARN│ Repository │ Repository 'Archive'    │| |
|  | | │ 14:30:22       │     │            │ connection timeout      │| |
|  | | │                │     │            │                         │| |
|  | | │ 2023-11-20     │ INFO│ System     │ Application started     │| |
|  | | │ 09:15:05       │     │            │                         │| |
|  | | │                │     │            │                         │| |
|  | | │ 2023-11-19     │ ERR │ Backup     │ Backup job 'Projects'   │| |
|  | | │ 23:45:12       │     │            │ failed: permission      │| |
|  | | │                │     │            │ denied                  │| |
|  | | └────────────────┴─────┴────────────┴─────────────────────────┘| |
|  | |                                                                | |
|  | | [< Previous] Page 1 of 10 [Next >]                [Export Logs] | |
|  | +----------------------------------------------------------------+ |
|  |                                                                  | |
|  +------------------------------------------------------------------+ |
|                                                                      |
+----------------------------------------------------------------------+
```

### Statistics View

```
+----------------------------------------------------------------------+
|                           TIMELOCKER                         [⚙️] [👤] |
+----------------------------------------------------------------------+
| [📁 REPOSITORIES] [🔄 BACKUPS] [🔍 RESTORE] [📊 MONITOR] [⚙️ SETTINGS] |
+----------------------------------------------------------------------+
|                                                                      |
|  📊 MONITORING                                                        |
|  +------------------------------------------------------------------+ |
|  | [Dashboard] [Activity] [Logs] [Statistics] [Reports]             | |
|  |                                                                  | |
|  | Backup Statistics                                                | |
|  | +----------------------------------------------------------------+ |
|  | | Repository: [All Repositories ▼]    Time Range: [Last 30 days ▼] |
|  | |                                                                | |
|  | | Storage Growth                                                 | |
|  | | ┌────────────────────────────────────────────────────────────┐ | |
|  | | │                                                            │ | |
|  | | │ 2TB ┼                                          ●           │ | |
|  | | │     │                                        ●             │ | |
|  | | │     │                                      ●               │ | |
|  | | │     │                                    ●                 │ | |
|  | | │     │                                  ●                   │ | |
|  | | │ 1TB ┼                                ●                     │ | |
|  | | │     │                              ●                       │ | |
|  | | │     │                            ●                         │ | |
|  | | │     │                          ●                           │ | |
|  | | │     │                        ●                             │ | |
|  | | │  0  ┼────────────────────────────────────────────────────┐ │ | |
|  | | │