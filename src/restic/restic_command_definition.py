from utils.command_builder import CommandParameter, ParameterStyle, CommandDefinition

restic_command_def = CommandDefinition(
    name="restic",
    parameters={
        "cacert": CommandParameter(
            name="cacert",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "cache-dir": CommandParameter(
            name="cache-dir",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "cleanup-cache": CommandParameter(
            name="cleanup-cache",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "compression": CommandParameter(
            name="compression",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "help": CommandParameter(
            name="help",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="h",
            short_style=ParameterStyle.SINGLE_DASH,

        ),
        "http-user-agent": CommandParameter(
            name="http-user-agent",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "insecure-no-password": CommandParameter(
            name="insecure-no-password",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "insecure-tls": CommandParameter(
            name="insecure-tls",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "json": CommandParameter(
            name="json",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "key-hint": CommandParameter(
            name="key-hint",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "limit-download": CommandParameter(
            name="limit-download",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "limit-upload": CommandParameter(
            name="limit-upload",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "no-cache": CommandParameter(
            name="no-cache",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "no-extra-verify": CommandParameter(
            name="no-extra-verify",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "no-lock": CommandParameter(
            name="no-lock",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "option": CommandParameter(
            name="option",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="o",
            short_style=ParameterStyle.SINGLE_DASH,

        ),
        "pack-size": CommandParameter(
            name="pack-size",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "password-command": CommandParameter(
            name="password-command",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "password-file": CommandParameter(
            name="password-file",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="p",
            short_style=ParameterStyle.SINGLE_DASH,

        ),
        "quiet": CommandParameter(
            name="quiet",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="q",
            short_style=ParameterStyle.SINGLE_DASH,

        ),
        "repo": CommandParameter(
            name="repo",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="r",
            short_style=ParameterStyle.SINGLE_DASH,

        ),
        "repository-file": CommandParameter(
            name="repository-file",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "retry-lock": CommandParameter(
            name="retry-lock",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "stuck-request-timeout": CommandParameter(
            name="stuck-request-timeout",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "tls-client-cert": CommandParameter(
            name="tls-client-cert",
            style=ParameterStyle.DOUBLE_DASH,

        ),
        "verbose": CommandParameter(
            name="verbose",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="v",
            short_style=ParameterStyle.SINGLE_DASH,

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

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "mode": CommandParameter(
                    name="mode",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "human-readable": CommandParameter(
                    name="human-readable",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "ignore-case": CommandParameter(
                    name="ignore-case",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="i",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "long": CommandParameter(
                    name="long",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="l",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "newest": CommandParameter(
                    name="newest",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="N",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "oldest": CommandParameter(
                    name="oldest",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="O",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "pack": CommandParameter(
                    name="pack",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "reverse": CommandParameter(
                    name="reverse",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="R",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "show-pack-id": CommandParameter(
                    name="show-pack-id",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "snapshot": CommandParameter(
                    name="snapshot",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="s",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tree": CommandParameter(
                    name="tree",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "fish-completion": CommandParameter(
                    name="fish-completion",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "man": CommandParameter(
                    name="man",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "powershell-completion": CommandParameter(
                    name="powershell-completion",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "zsh-completion": CommandParameter(
                    name="zsh-completion",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "max-age": CommandParameter(
                    name="max-age",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "no-size": CommandParameter(
                    name="no-size",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "no-default-permissions": CommandParameter(
                    name="no-default-permissions",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "owner-root": CommandParameter(
                    name="owner-root",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path-template": CommandParameter(
                    name="path-template",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "time-template": CommandParameter(
                    name="time-template",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "keep-hourly": CommandParameter(
                    name="keep-hourly",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "keep-daily": CommandParameter(
                    name="keep-daily",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="d",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "keep-weekly": CommandParameter(
                    name="keep-weekly",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="w",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "keep-monthly": CommandParameter(
                    name="keep-monthly",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="m",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "keep-yearly": CommandParameter(
                    name="keep-yearly",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="y",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "keep-within": CommandParameter(
                    name="keep-within",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "keep-within-hourly": CommandParameter(
                    name="keep-within-hourly",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "keep-within-daily": CommandParameter(
                    name="keep-within-daily",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "keep-within-weekly": CommandParameter(
                    name="keep-within-weekly",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "keep-within-monthly": CommandParameter(
                    name="keep-within-monthly",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "keep-within-yearly": CommandParameter(
                    name="keep-within-yearly",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "keep-tag": CommandParameter(
                    name="keep-tag",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "unsafe-allow-remove-all": CommandParameter(
                    name="unsafe-allow-remove-all",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "compact": CommandParameter(
                    name="compact",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="c",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "group-by": CommandParameter(
                    name="group-by",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="g",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "dry-run": CommandParameter(
                    name="dry-run",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="n",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "prune": CommandParameter(
                    name="prune",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "max-unused": CommandParameter(
                    name="max-unused",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "max-repack-size": CommandParameter(
                    name="max-repack-size",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "repack-cacheable-only": CommandParameter(
                    name="repack-cacheable-only",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "repack-small": CommandParameter(
                    name="repack-small",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "repack-uncompressed": CommandParameter(
                    name="repack-uncompressed",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "repack-smaller-than": CommandParameter(
                    name="repack-smaller-than",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

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

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "human-readable": CommandParameter(
                    name="human-readable",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "long": CommandParameter(
                    name="long",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="l",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "ncdu": CommandParameter(
                    name="ncdu",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "recursive": CommandParameter(
                    name="recursive",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "reverse": CommandParameter(
                    name="reverse",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "sort": CommandParameter(
                    name="sort",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="s",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "remove-all": CommandParameter(
                    name="remove-all",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "exclude": CommandParameter(
                    name="exclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="e",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "exclude-caches": CommandParameter(
                    name="exclude-caches",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "exclude-file": CommandParameter(
                    name="exclude-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "exclude-if-present": CommandParameter(
                    name="exclude-if-present",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "exclude-larger-than": CommandParameter(
                    name="exclude-larger-than",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "files-from": CommandParameter(
                    name="files-from",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "files-from-raw": CommandParameter(
                    name="files-from-raw",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "files-from-verbatim": CommandParameter(
                    name="files-from-verbatim",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "force": CommandParameter(
                    name="force",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="f",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "group-by": CommandParameter(
                    name="group-by",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="g",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "iexclude": CommandParameter(
                    name="iexclude",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "iexclude-file": CommandParameter(
                    name="iexclude-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "ignore-ctime": CommandParameter(
                    name="ignore-ctime",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "ignore-inode": CommandParameter(
                    name="ignore-inode",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "no-scan": CommandParameter(
                    name="no-scan",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "one-file-system": CommandParameter(
                    name="one-file-system",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="x",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "parent": CommandParameter(
                    name="parent",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "read-concurrency": CommandParameter(
                    name="read-concurrency",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "skip-if-unchanged": CommandParameter(
                    name="skip-if-unchanged",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "stdin": CommandParameter(
                    name="stdin",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "stdin-filename": CommandParameter(
                    name="stdin-filename",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "stdin-from-command": CommandParameter(
                    name="stdin-from-command",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "time": CommandParameter(
                    name="time",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "with-atime": CommandParameter(
                    name="with-atime",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "from-key-hint": CommandParameter(
                    name="from-key-hint",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-password-command": CommandParameter(
                    name="from-password-command",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-password-file": CommandParameter(
                    name="from-password-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-repo": CommandParameter(
                    name="from-repo",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-repository-file": CommandParameter(
                    name="from-repository-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "forget": CommandParameter(
                    name="forget",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "read-data": CommandParameter(
                    name="read-data",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "read-data-subset": CommandParameter(
                    name="read-data-subset",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "with-cache": CommandParameter(
                    name="with-cache",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "remove": CommandParameter(
                    name="remove",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "set": CommandParameter(
                    name="set",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "from-insecure-no-password": CommandParameter(
                    name="from-insecure-no-password",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-key-hint": CommandParameter(
                    name="from-key-hint",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-password-command": CommandParameter(
                    name="from-password-command",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-password-file": CommandParameter(
                    name="from-password-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-repo": CommandParameter(
                    name="from-repo",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "from-repository-file": CommandParameter(
                    name="from-repository-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "repository-version": CommandParameter(
                    name="repository-version",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

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

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "target": CommandParameter(
                    name="target",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="t",
                    short_style=ParameterStyle.SINGLE_DASH,

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

                ),
                "dry-run": CommandParameter(
                    name="dry-run",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "exclude": CommandParameter(
                    name="exclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="e",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "exclude-file": CommandParameter(
                    name="exclude-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "exclude-xattr": CommandParameter(
                    name="exclude-xattr",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "iexclude": CommandParameter(
                    name="iexclude",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "iexclude-file": CommandParameter(
                    name="iexclude-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "iinclude": CommandParameter(
                    name="iinclude",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "iinclude-file": CommandParameter(
                    name="iinclude-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "include": CommandParameter(
                    name="include",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="i",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "include-file": CommandParameter(
                    name="include-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "include-xattr": CommandParameter(
                    name="include-xattr",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "overwrite": CommandParameter(
                    name="overwrite",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "sparse": CommandParameter(
                    name="sparse",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "target": CommandParameter(
                    name="target",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="t",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "verify": CommandParameter(
                    name="verify",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "exclude": CommandParameter(
                    name="exclude",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="e",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "exclude-file": CommandParameter(
                    name="exclude-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "forget": CommandParameter(
                    name="forget",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "iexclude": CommandParameter(
                    name="iexclude",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "iexclude-file": CommandParameter(
                    name="iexclude-file",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "new-host": CommandParameter(
                    name="new-host",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "new-time": CommandParameter(
                    name="new-time",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "snapshot-summary": CommandParameter(
                    name="snapshot-summary",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="s",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "group-by": CommandParameter(
                    name="group-by",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="g",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "host": CommandParameter(
                    name="host",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="H",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "latest": CommandParameter(
                    name="latest",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "path": CommandParameter(
                    name="path",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "tag": CommandParameter(
                    name="tag",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.DOUBLE_DASH,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH,

                ),
                "max-repack-size": CommandParameter(
                    name="max-repack-size",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "max-unused": CommandParameter(
                    name="max-unused",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "repack-cacheable-only": CommandParameter(
                    name="repack-cacheable-only",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "repack-small": CommandParameter(
                    name="repack-small",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "repack-smaller-than": CommandParameter(
                    name="repack-smaller-than",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "repack-uncompressed": CommandParameter(
                    name="repack-uncompressed",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
                "unsafe-recover-no-free-space": CommandParameter(
                    name="unsafe-recover-no-free-space",
                    style=ParameterStyle.DOUBLE_DASH,

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

                ),
                "metadata": CommandParameter(
                    name="metadata",
                    style=ParameterStyle.DOUBLE_DASH,

                ),
            },
            default_param_style=ParameterStyle.SEPARATE
        ),
    },
    default_param_style=ParameterStyle.SEPARATE
)
