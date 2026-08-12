#!/usr/bin/env python3
"""Deprecated Spec 010 compatibility wrapper for ``timelocker-deploy``."""

from TimeLocker.system_control.deployment_entry import main


if __name__ == "__main__":
    raise SystemExit(main())
