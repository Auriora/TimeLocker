"""Tests for deterministic, accessible TimeLocker tray icon variants."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops
from pytest import mark


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ASSET_ROOT = (
    PROJECT_ROOT / "src" / "TimeLocker" / "system_control" / "assets"
)
BASE_ICON = ASSET_ROOT / "timelocker-icon.png"
STATUSES = ("idle", "running", "success", "warning", "error")


@mark.unit
def test_status_icons_are_deterministic_logo_variants(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "generate_tray_status_icons.py"),
            "--output-root",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with Image.open(BASE_ICON) as source:
        base = source.convert("RGBA")
    hashes = set()
    for status in STATUSES:
        packaged = ASSET_ROOT / f"timelocker-icon-{status}.png"
        generated = tmp_path / packaged.name
        assert packaged.read_bytes() == generated.read_bytes()
        with Image.open(packaged) as source:
            image = source.convert("RGBA")
        assert image.size == (1024, 1024)
        assert image.mode == "RGBA"
        unchanged = ImageChops.difference(
            base.crop((0, 0, 676, 1024)),
            image.crop((0, 0, 676, 1024)),
        )
        assert unchanged.getbbox() is None
        hashes.add(hashlib.sha256(packaged.read_bytes()).hexdigest())

    assert len(hashes) == len(STATUSES)
