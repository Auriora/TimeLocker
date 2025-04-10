from utils.command_builder import CommandParameter, ParameterStyle, CommandDefinition

restic_command = CommandDefinition(
    name="restic",
    parameters={
        "cacert": CommandParameter(
            name="cacert",
            style=ParameterStyle.DOUBLE_DASH,
            description='file to load root certificates from',
        ),
        "cache-dir": CommandParameter(
            name="cache-dir",
            style=ParameterStyle.DOUBLE_DASH,
            description='set the cache directory\\',
        ),
        "cleanup-cache": CommandParameter(
            name="cleanup-cache",
            style=ParameterStyle.DOUBLE_DASH,
            description='auto remove old cache directories',
        ),
        "compression": CommandParameter(
            name="compression",
            style=ParameterStyle.DOUBLE_DASH,
            description='compression mode (only available for repository format version 2), one of (auto|off|max)',
        ),
        "help": CommandParameter(
            name="help",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="h",
            short_style=ParameterStyle.SINGLE_DASH,
            description='help for restic',
        ),
        "http-user-agent": CommandParameter(
            name="http-user-agent",
            style=ParameterStyle.DOUBLE_DASH,
            description='set a http user agent for outgoing http requests',
        ),
        "insecure-no-password": CommandParameter(
            name="insecure-no-password",
            style=ParameterStyle.DOUBLE_DASH,
            description='use an empty password for the repository, must be passed to every restic command (insecure)',
        ),
        "insecure-tls": CommandParameter(
            name="insecure-tls",
            style=ParameterStyle.DOUBLE_DASH,
            description='skip TLS certificate verification when connecting to the repository (insecure)',
        ),
        "json": CommandParameter(
            name="json",
            style=ParameterStyle.DOUBLE_DASH,
            description='set output mode to JSON for commands that support it',
        ),
        "key-hint": CommandParameter(
            name="key-hint",
            style=ParameterStyle.DOUBLE_DASH,
            description='key ID of key to try decrypting first',
        ),
        "limit-download": CommandParameter(
            name="limit-download",
            style=ParameterStyle.DOUBLE_DASH,
            description='limits downloads to a maximum rate in KiB/s.',
        ),
        "limit-upload": CommandParameter(
            name="limit-upload",
            style=ParameterStyle.DOUBLE_DASH,
            description='limits uploads to a maximum rate in KiB/s.',
        ),
        "no-cache": CommandParameter(
            name="no-cache",
            style=ParameterStyle.DOUBLE_DASH,
            description='do not use a local cache',
        ),
        "no-extra-verify": CommandParameter(
            name="no-extra-verify",
            style=ParameterStyle.DOUBLE_DASH,
            description='skip additional verification of data before upload (see documentation)',
        ),
        "no-lock": CommandParameter(
            name="no-lock",
            style=ParameterStyle.DOUBLE_DASH,
            description='do not lock the repository, this allows some operations on read-only repositories',
        ),
        "option": CommandParameter(
            name="option",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="o",
            short_style=ParameterStyle.SINGLE_DASH,
            description='set extended option (key=value, can be specified multiple times)',
        ),
        "pack-size": CommandParameter(
            name="pack-size",
            style=ParameterStyle.DOUBLE_DASH,
            description='set target pack size in MiB, created pack files may be larger',
        ),
        "password-command": CommandParameter(
            name="password-command",
            style=ParameterStyle.DOUBLE_DASH,
            description='shell command to obtain the repository password from',
        ),
        "password-file": CommandParameter(
            name="password-file",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="p",
            short_style=ParameterStyle.SINGLE_DASH,
            description='file to read the repository password from',
        ),
        "quiet": CommandParameter(
            name="quiet",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="q",
            short_style=ParameterStyle.SINGLE_DASH,
            description='do not output comprehensive progress report',
        ),
        "repo": CommandParameter(
            name="repo",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="r",
            short_style=ParameterStyle.SINGLE_DASH,
            description='repository to backup to or restore from',
        ),
        "repository-file": CommandParameter(
            name="repository-file",
            style=ParameterStyle.DOUBLE_DASH,
            description='file to read the repository location from',
        ),
        "retry-lock": CommandParameter(
            name="retry-lock",
            style=ParameterStyle.DOUBLE_DASH,
            description='retry to lock the repository if it is already locked, takes a value like 5m or 2h',
        ),
        "stuck-request-timeout": CommandParameter(
            name="stuck-request-timeout",
            style=ParameterStyle.DOUBLE_DASH,
            description='duration after which to retry stuck requests',
        ),
        "tls-client-cert": CommandParameter(
            name="tls-client-cert",
            style=ParameterStyle.DOUBLE_DASH,
            description='path to a file containing PEM encoded TLS client certificate and private key',
        ),
        "verbose": CommandParameter(
            name="verbose",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="v",
            short_style=ParameterStyle.SINGLE_DASH,
            description='be verbose (specify multiple times or a level using --verbose=n``, max level/times is 2)',
        ),
    },
    subcommands={
        "stats": CommandDefinition(
            name="stats",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for stats',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "mode": CommandParameter(
                    name="mode",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='counting mode: restore-size (default), files-by-contents, blobs-per-file or raw-data',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "find": CommandDefinition(
            name="find",
            parameters={
                "blob": CommandParameter(
                    name="blob",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='pattern is a blob-ID',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for find',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "human-readable": CommandParameter(
                    name="human-readable",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='print sizes in human readable format',
                ),
                "ignore-case": CommandParameter(
                    name="ignore-case",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="i",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='ignore case for pattern',
                ),
                "long": CommandParameter(
                    name="long",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="l",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='use a long listing format showing size and mode',
                ),
                "newest": CommandParameter(
                    name="newest",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="N",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='newest modification date/time',
                ),
                "oldest": CommandParameter(
                    name="oldest",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="O",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='oldest modification date/time',
                ),
                "pack": CommandParameter(
                    name="pack",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='pattern is a pack-ID',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "reverse": CommandParameter(
                    name="reverse",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="R",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='reverse sort order oldest to newest',
                ),
                "show-pack-id": CommandParameter(
                    name="show-pack-id",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='display the pack-ID the blobs belong to (with --blob or --tree)',
                ),
                "snapshot": CommandParameter(
                    name="snapshot",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="s",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='snapshot id to search in (can be given multiple times)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
                "tree": CommandParameter(
                    name="tree",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='pattern is a tree-ID',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "generate": CommandDefinition(
            name="generate",
            parameters={
                "bash-completion": CommandParameter(
                    name="bash-completion",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='write bash completion file (- for stdout)',
                ),
                "fish-completion": CommandParameter(
                    name="fish-completion",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='write fish completion file (- for stdout)',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for generate',
                ),
                "man": CommandParameter(
                    name="man",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='write man pages to directory',
                ),
                "powershell-completion": CommandParameter(
                    name="powershell-completion",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='write powershell completion file (- for stdout)',
                ),
                "zsh-completion": CommandParameter(
                    name="zsh-completion",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='write zsh completion file (- for stdout)',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "cache": CommandDefinition(
            name="cache",
            parameters={
                "cleanup": CommandParameter(
                    name="cleanup",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='remove old cache directories',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for cache',
                ),
                "max-age": CommandParameter(
                    name="max-age",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='max age in days for cache directories to be considered old',
                ),
                "no-size": CommandParameter(
                    name="no-size",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='do not output the size of the cache directories',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "mount": CommandDefinition(
            name="mount",
            parameters={
                "allow-other": CommandParameter(
                    name="allow-other",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='allow other users to access the data in the mounted directory',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for mount',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "no-default-permissions": CommandParameter(
                    name="no-default-permissions",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="for 'allow-other', ignore Unix permissions and allow users to read all snapshot files",
                ),
                "owner-root": CommandParameter(
                    name="owner-root",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="use 'root' as the owner of files and dirs",
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "path-template": CommandParameter(
                    name="path-template",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='set template for path names (can be specified multiple times)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
                "time-template": CommandParameter(
                    name="time-template",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='set template to use for times',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "forget": CommandDefinition(
            name="forget",
            parameters={
                "keep-last": CommandParameter(
                    name="keep-last",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="l",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="keep the last n snapshots (use 'unlimited' to keep all snapshots)",
                ),
                "keep-hourly": CommandParameter(
                    name="keep-hourly",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="keep the last n hourly snapshots (use 'unlimited' to keep all hourly snapshots)",
                ),
                "keep-daily": CommandParameter(
                    name="keep-daily",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="d",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="keep the last n daily snapshots (use 'unlimited' to keep all daily snapshots)",
                ),
                "keep-weekly": CommandParameter(
                    name="keep-weekly",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="w",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="keep the last n weekly snapshots (use 'unlimited' to keep all weekly snapshots)",
                ),
                "keep-monthly": CommandParameter(
                    name="keep-monthly",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="m",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="keep the last n monthly snapshots (use 'unlimited' to keep all monthly snapshots)",
                ),
                "keep-yearly": CommandParameter(
                    name="keep-yearly",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="y",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="keep the last n yearly snapshots (use 'unlimited' to keep all yearly snapshots)",
                ),
                "keep-within": CommandParameter(
                    name="keep-within",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='keep snapshots that are newer than duration (eg. 1y5m7d2h) relative to the latest snapshot',
                ),
                "keep-within-hourly": CommandParameter(
                    name="keep-within-hourly",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='keep hourly snapshots that are newer than duration (eg. 1y5m7d2h) relative to the latest snapshot',
                ),
                "keep-within-daily": CommandParameter(
                    name="keep-within-daily",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='keep daily snapshots that are newer than duration (eg. 1y5m7d2h) relative to the latest snapshot',
                ),
                "keep-within-weekly": CommandParameter(
                    name="keep-within-weekly",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='keep weekly snapshots that are newer than duration (eg. 1y5m7d2h) relative to the latest snapshot',
                ),
                "keep-within-monthly": CommandParameter(
                    name="keep-within-monthly",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='keep monthly snapshots that are newer than duration (eg. 1y5m7d2h) relative to the latest snapshot',
                ),
                "keep-within-yearly": CommandParameter(
                    name="keep-within-yearly",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='keep yearly snapshots that are newer than duration (eg. 1y5m7d2h) relative to the latest snapshot',
                ),
                "keep-tag": CommandParameter(
                    name="keep-tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='keep snapshots with this taglist (can be specified multiple times)',
                ),
                "unsafe-allow-remove-all": CommandParameter(
                    name="unsafe-allow-remove-all",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='allow deleting all snapshots of a snapshot group',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "compact": CommandParameter(
                    name="compact",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="c",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='use compact output format',
                ),
                "group-by": CommandParameter(
                    name="group-by",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="g",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="group snapshots by host, paths and/or tags, separated by comma (disable grouping with '')",
                ),
                "dry-run": CommandParameter(
                    name="dry-run",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="n",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='do not delete anything, just print what would be done',
                ),
                "prune": CommandParameter(
                    name="prune",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="automatically run the 'prune' command if snapshots have been removed",
                ),
                "max-unused": CommandParameter(
                    name="max-unused",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="tolerate given limit of unused data (absolute value in bytes with suffixes k/K, m/M, g/G, t/T, a value in % or the word 'unlimited')",
                ),
                "max-repack-size": CommandParameter(
                    name="max-repack-size",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='stop after repacking this much data in total (allowed suffixes for size: k/K, m/M, g/G, t/T)',
                ),
                "repack-cacheable-only": CommandParameter(
                    name="repack-cacheable-only",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only repack packs which are cacheable',
                ),
                "repack-small": CommandParameter(
                    name="repack-small",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='repack pack files below 80% of target pack size',
                ),
                "repack-uncompressed": CommandParameter(
                    name="repack-uncompressed",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='repack all uncompressed data',
                ),
                "repack-smaller-than": CommandParameter(
                    name="repack-smaller-than",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='pack below-limit packfiles (allowed suffixes: k/K, m/M)',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for forget',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "version": CommandDefinition(
            name="version",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for version',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "key": CommandDefinition(
            name="key",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for key',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "ls": CommandDefinition(
            name="ls",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for ls',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host, when snapshot ID "latest" is given (can be specified multiple times)',
                ),
                "human-readable": CommandParameter(
                    name="human-readable",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='print sizes in human readable format',
                ),
                "long": CommandParameter(
                    name="long",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="l",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='use a long listing format showing size and mode',
                ),
                "ncdu": CommandParameter(
                    name="ncdu",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="output NCDU export format (pipe into 'ncdu -f -')",
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path, when snapshot ID "latest" is given (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "recursive": CommandParameter(
                    name="recursive",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='include files in subfolders of the listed directories',
                ),
                "reverse": CommandParameter(
                    name="reverse",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='reverse sorted output',
                ),
                "sort": CommandParameter(
                    name="sort",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="s",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='sort output by (name|size|time=mtime|atime|ctime|extension)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...], when snapshot ID "latest" is given (can be specified multiple times)',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "unlock": CommandDefinition(
            name="unlock",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for unlock',
                ),
                "remove-all": CommandParameter(
                    name="remove-all",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='remove all locks, even non-stale ones',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "backup": CommandDefinition(
            name="backup",
            parameters={
                "dry-run": CommandParameter(
                    name="dry-run",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="n",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='do not upload or write any data, just show what would be done',
                ),
                "exclude": CommandParameter(
                    name="exclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="e",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='exclude a pattern (can be specified multiple times)',
                ),
                "exclude-caches": CommandParameter(
                    name="exclude-caches",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='excludes cache directories that are marked with a CACHEDIR.TAG file. See https://bford.info/cachedir/ for the Cache Directory Tagging Standard',
                ),
                "exclude-file": CommandParameter(
                    name="exclude-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read exclude patterns from a file (can be specified multiple times)',
                ),
                "exclude-if-present": CommandParameter(
                    name="exclude-if-present",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='takes filename[:header], exclude contents of directories containing filename (except filename itself) if header of that file is as provided (can be specified multiple times)',
                ),
                "exclude-larger-than": CommandParameter(
                    name="exclude-larger-than",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='max size of the files to be backed up (allowed suffixes: k/K, m/M, g/G, t/T)',
                ),
                "files-from": CommandParameter(
                    name="files-from",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read the files to backup from file (can be combined with file args; can be specified multiple times)',
                ),
                "files-from-raw": CommandParameter(
                    name="files-from-raw",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read the files to backup from file (can be combined with file args; can be specified multiple times)',
                ),
                "files-from-verbatim": CommandParameter(
                    name="files-from-verbatim",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read the files to backup from file (can be combined with file args; can be specified multiple times)',
                ),
                "force": CommandParameter(
                    name="force",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="f",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='force re-reading the source files/directories (overrides the "parent" flag)',
                ),
                "group-by": CommandParameter(
                    name="group-by",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="g",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="group snapshots by host, paths and/or tags, separated by comma (disable grouping with '')",
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for backup',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='set the hostname for the snapshot manually. To prevent an expensive rescan use the "parent" flag',
                ),
                "iexclude": CommandParameter(
                    name="iexclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='same as --exclude pattern but ignores the casing of filenames',
                ),
                "iexclude-file": CommandParameter(
                    name="iexclude-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='same as --exclude-file but ignores casing of filenames in patterns',
                ),
                "ignore-ctime": CommandParameter(
                    name="ignore-ctime",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='ignore ctime changes when checking for modified files',
                ),
                "ignore-inode": CommandParameter(
                    name="ignore-inode",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='ignore inode number and ctime changes when checking for modified files',
                ),
                "no-scan": CommandParameter(
                    name="no-scan",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='do not run scanner to estimate size of backup',
                ),
                "one-file-system": CommandParameter(
                    name="one-file-system",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="x",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description="exclude other file systems, don't cross filesystem boundaries and subvolumes",
                ),
                "parent": CommandParameter(
                    name="parent",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='use this parent snapshot',
                ),
                "read-concurrency": CommandParameter(
                    name="read-concurrency",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read n files concurrently',
                ),
                "skip-if-unchanged": CommandParameter(
                    name="skip-if-unchanged",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='skip snapshot creation if identical to parent snapshot',
                ),
                "stdin": CommandParameter(
                    name="stdin",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read backup from stdin',
                ),
                "stdin-filename": CommandParameter(
                    name="stdin-filename",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='filename to use when reading from stdin',
                ),
                "stdin-from-command": CommandParameter(
                    name="stdin-from-command",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='interpret arguments as command to execute and store its stdout',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='add tags for the new snapshot in the format tag[,tag,...] (can be specified multiple times)',
                ),
                "time": CommandParameter(
                    name="time",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="time of the backup (ex. '2012-11-01 22:08:41')",
                ),
                "with-atime": CommandParameter(
                    name="with-atime",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='store the atime for all files and directories',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "copy": CommandDefinition(
            name="copy",
            parameters={
                "from-insecure-no-password": CommandParameter(
                    name="from-insecure-no-password",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='use an empty password for the source repository (insecure)',
                ),
                "from-key-hint": CommandParameter(
                    name="from-key-hint",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='key ID of key to try decrypting the source repository first',
                ),
                "from-password-command": CommandParameter(
                    name="from-password-command",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='shell command to obtain the source repository password from',
                ),
                "from-password-file": CommandParameter(
                    name="from-password-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='file to read the source repository password from',
                ),
                "from-repo": CommandParameter(
                    name="from-repo",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='source repository to copy snapshots from',
                ),
                "from-repository-file": CommandParameter(
                    name="from-repository-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='file from which to read the source repository location to copy snapshots from',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for copy',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "repair": CommandDefinition(
            name="repair",
            parameters={
                "dry-run": CommandParameter(
                    name="dry-run",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="n",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='do not do anything, just print what would be done',
                ),
                "forget": CommandParameter(
                    name="forget",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='remove original snapshots after creating new ones',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for snapshots',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "check": CommandDefinition(
            name="check",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for check',
                ),
                "read-data": CommandParameter(
                    name="read-data",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read all data blobs',
                ),
                "read-data-subset": CommandParameter(
                    name="read-data-subset",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="read a subset of data packs, specified as 'n/t' for specific part, or either 'x%' or 'x.y%' or a size in bytes with suffixes k/K, m/M, g/G, t/T for a random subset",
                ),
                "with-cache": CommandParameter(
                    name="with-cache",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='use existing cache, only read uncached data from repository',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "options": CommandDefinition(
            name="options",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for options',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "tag": CommandDefinition(
            name="tag",
            parameters={
                "add": CommandParameter(
                    name="add",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='tags which will be added to the existing tags in the format tag[,tag,...] (can be given multiple times)',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for tag',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "remove": CommandParameter(
                    name="remove",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='tags which will be removed from the existing tags in the format tag[,tag,...] (can be given multiple times)',
                ),
                "set": CommandParameter(
                    name="set",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='tags which will replace the existing tags in the format tag[,tag,...] (can be given multiple times)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "init": CommandDefinition(
            name="init",
            parameters={
                "copy-chunker-params": CommandParameter(
                    name="copy-chunker-params",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='copy chunker parameters from the secondary repository (useful with the copy command)',
                ),
                "from-insecure-no-password": CommandParameter(
                    name="from-insecure-no-password",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='use an empty password for the source repository (insecure)',
                ),
                "from-key-hint": CommandParameter(
                    name="from-key-hint",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='key ID of key to try decrypting the source repository first',
                ),
                "from-password-command": CommandParameter(
                    name="from-password-command",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='shell command to obtain the source repository password from',
                ),
                "from-password-file": CommandParameter(
                    name="from-password-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='file to read the source repository password from',
                ),
                "from-repo": CommandParameter(
                    name="from-repo",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='source repository to copy chunker parameters from',
                ),
                "from-repository-file": CommandParameter(
                    name="from-repository-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='file from which to read the source repository location to copy chunker parameters from',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for init',
                ),
                "repository-version": CommandParameter(
                    name="repository-version",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="repository format version to use, allowed values are a format version, 'latest' and 'stable'",
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "migrate": CommandDefinition(
            name="migrate",
            parameters={
                "force": CommandParameter(
                    name="force",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="f",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='apply a migration a second time',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for migrate',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "dump": CommandDefinition(
            name="dump",
            parameters={
                "archive": CommandParameter(
                    name="archive",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="a",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='set archive format as "tar" or "zip"',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for dump',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host, when snapshot ID "latest" is given (can be specified multiple times)',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path, when snapshot ID "latest" is given (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...], when snapshot ID "latest" is given (can be specified multiple times)',
                ),
                "target": CommandParameter(
                    name="target",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="t",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='write the output to target path',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "restore": CommandDefinition(
            name="restore",
            parameters={
                "delete": CommandParameter(
                    name="delete",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="delete files from target directory if they do not exist in snapshot. Use '--dry-run -vv' to check what would be deleted",
                ),
                "dry-run": CommandParameter(
                    name="dry-run",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='do not write any data, just show what would be done',
                ),
                "exclude": CommandParameter(
                    name="exclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="e",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='exclude a pattern (can be specified multiple times)',
                ),
                "exclude-file": CommandParameter(
                    name="exclude-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read exclude patterns from a file (can be specified multiple times)',
                ),
                "exclude-xattr": CommandParameter(
                    name="exclude-xattr",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='exclude xattr by pattern (can be specified multiple times)',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for restore',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host, when snapshot ID "latest" is given (can be specified multiple times)',
                ),
                "iexclude": CommandParameter(
                    name="iexclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='same as --exclude pattern but ignores the casing of filenames',
                ),
                "iexclude-file": CommandParameter(
                    name="iexclude-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='same as --exclude-file but ignores casing of filenames in patterns',
                ),
                "iinclude": CommandParameter(
                    name="iinclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='same as --include pattern but ignores the casing of filenames',
                ),
                "iinclude-file": CommandParameter(
                    name="iinclude-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='same as --include-file but ignores casing of filenames in patterns',
                ),
                "include": CommandParameter(
                    name="include",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="i",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='include a pattern (can be specified multiple times)',
                ),
                "include-file": CommandParameter(
                    name="include-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read include patterns from a file (can be specified multiple times)',
                ),
                "include-xattr": CommandParameter(
                    name="include-xattr",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='include xattr by pattern (can be specified multiple times)',
                ),
                "overwrite": CommandParameter(
                    name="overwrite",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='overwrite behavior, one of (always|if-changed|if-newer|never)',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path, when snapshot ID "latest" is given (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "sparse": CommandParameter(
                    name="sparse",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='restore files as sparse',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...], when snapshot ID "latest" is given (can be specified multiple times)',
                ),
                "target": CommandParameter(
                    name="target",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="t",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='directory to extract data to',
                ),
                "verify": CommandParameter(
                    name="verify",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='verify restored files content',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "cat": CommandDefinition(
            name="cat",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for cat',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "recover": CommandDefinition(
            name="recover",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for recover',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "rewrite": CommandDefinition(
            name="rewrite",
            parameters={
                "dry-run": CommandParameter(
                    name="dry-run",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="n",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='do not do anything, just print what would be done',
                ),
                "exclude": CommandParameter(
                    name="exclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="e",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='exclude a pattern (can be specified multiple times)',
                ),
                "exclude-file": CommandParameter(
                    name="exclude-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='read exclude patterns from a file (can be specified multiple times)',
                ),
                "forget": CommandParameter(
                    name="forget",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='remove original snapshots after creating new ones',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for rewrite',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "iexclude": CommandParameter(
                    name="iexclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='same as --exclude pattern but ignores the casing of filenames',
                ),
                "iexclude-file": CommandParameter(
                    name="iexclude-file",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='same as --exclude-file but ignores casing of filenames in patterns',
                ),
                "new-host": CommandParameter(
                    name="new-host",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='replace hostname',
                ),
                "new-time": CommandParameter(
                    name="new-time",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='replace time of the backup',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "snapshot-summary": CommandParameter(
                    name="snapshot-summary",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="s",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='create snapshot summary record if it does not exist',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "list": CommandDefinition(
            name="list",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for list',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "features": CommandDefinition(
            name="features",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for features',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "snapshots": CommandDefinition(
            name="snapshots",
            parameters={
                "compact": CommandParameter(
                    name="compact",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="c",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='use compact output format',
                ),
                "group-by": CommandParameter(
                    name="group-by",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="g",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='group snapshots by host, paths and/or tags, separated by comma',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for snapshots',
                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='only consider snapshots for this host (can be specified multiple times)',
                ),
                "latest": CommandParameter(
                    name="latest",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only show the last n snapshots for each host and path',
                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including this (absolute) path (can be specified multiple times, snapshots must include all specified paths)',
                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only consider snapshots including tag[,tag,...] (can be specified multiple times)',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "prune": CommandDefinition(
            name="prune",
            parameters={
                "dry-run": CommandParameter(
                    name="dry-run",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="n",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='do not modify the repository, just print what would be done',
                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for prune',
                ),
                "max-repack-size": CommandParameter(
                    name="max-repack-size",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='stop after repacking this much data in total (allowed suffixes for size: k/K, m/M, g/G, t/T)',
                ),
                "max-unused": CommandParameter(
                    name="max-unused",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="tolerate given limit of unused data (absolute value in bytes with suffixes k/K, m/M, g/G, t/T, a value in % or the word 'unlimited')",
                ),
                "repack-cacheable-only": CommandParameter(
                    name="repack-cacheable-only",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='only repack packs which are cacheable',
                ),
                "repack-small": CommandParameter(
                    name="repack-small",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='repack pack files below 80% of target pack size',
                ),
                "repack-smaller-than": CommandParameter(
                    name="repack-smaller-than",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='pack below-limit packfiles (allowed suffixes: k/K, m/M)',
                ),
                "repack-uncompressed": CommandParameter(
                    name="repack-uncompressed",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='repack all uncompressed data',
                ),
                "unsafe-recover-no-free-space": CommandParameter(
                    name="unsafe-recover-no-free-space",
                    style=ParameterStyle.DOUBLE_DASH,
                    description="UNSAFE, READ THE DOCUMENTATION BEFORE USING! Try to recover a repository stuck with no free space. Do not use without trying out 'prune --max-repack-size 0' first.",
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
        "diff": CommandDefinition(
            name="diff",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,
                    description='help for diff',
                ),
                "metadata": CommandParameter(
                    name="metadata",
                    style=ParameterStyle.DOUBLE_DASH,
                    description='print changes in metadata',
                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
    },
    default_param_style=ParameterStyle.SEPARATE
)
