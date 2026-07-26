"""Stable launcher entry point for the selected desktop tray process."""

import sys

from .release_launcher import ReleaseResolutionError, launch_selected


def main() -> None:
    """Launch the selected tray without consulting user-managed paths."""
    try:
        launch_selected(sys.argv[1:], target="tray")
    except ReleaseResolutionError:
        print(
            "TimeLocker tray release is unavailable or invalid.",
            file=sys.stderr,
        )
        raise SystemExit(78) from None


if __name__ == "__main__":
    main()
