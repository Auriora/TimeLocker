"""Stable launcher process entry point."""

import sys

from .release_launcher import ReleaseResolutionError, launch_selected


def main() -> None:
    """Launch the selected release with a bounded failure message."""
    try:
        launch_selected(sys.argv[1:])
    except ReleaseResolutionError:
        print(
            "TimeLocker system release is unavailable or invalid. "
            "Ask an administrator to validate /opt/timelocker/selected-release.json.",
            file=sys.stderr,
        )
        raise SystemExit(78) from None


if __name__ == "__main__":
    main()
