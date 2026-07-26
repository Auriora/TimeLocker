"""Administrator-only immutable release selector command."""

import argparse

from .release_launcher import ImmutableReleaseResolver, ReleaseResolutionError


def main() -> None:
    """Select or roll back an already staged release."""
    parser = argparse.ArgumentParser(prog="timelocker-release-select")
    subcommands = parser.add_subparsers(dest="command", required=True)
    select = subcommands.add_parser("select")
    select.add_argument("release_id")
    subcommands.add_parser("rollback")
    arguments = parser.parse_args()
    resolver = ImmutableReleaseResolver()
    try:
        if arguments.command == "select":
            state = resolver.select(arguments.release_id)
        else:
            state = resolver.rollback()
    except ReleaseResolutionError as error:
        parser.exit(78, f"release selection failed: {error}\n")
    print(state.selected)


if __name__ == "__main__":
    main()
