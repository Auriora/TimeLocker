#!/usr/bin/env python3
"""Generate deterministic status-badged variants of the TimeLocker tray icon."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "src" / "TimeLocker" / "system_control" / "assets"
BASE_ICON = ASSET_ROOT / "timelocker-icon.png"

BADGE_BOX = (676, 636, 988, 948)
BADGE_OUTLINE_WIDTH = 26
GLYPH_WIDTH = 38


def _draw_circle_badge(
    draw: ImageDraw.ImageDraw,
    *,
    fill: str,
) -> None:
    draw.ellipse(
        BADGE_BOX,
        fill=fill,
        outline="white",
        width=BADGE_OUTLINE_WIDTH,
    )


def _draw_idle(draw: ImageDraw.ImageDraw) -> None:
    _draw_circle_badge(draw, fill="#667085")
    draw.arc(
        (755, 700, 907, 840),
        start=195,
        end=520,
        fill="white",
        width=GLYPH_WIDTH,
    )
    draw.line((831, 822, 831, 858), fill="white", width=GLYPH_WIDTH)
    draw.ellipse((812, 876, 850, 914), fill="white")


def _draw_running(draw: ImageDraw.ImageDraw) -> None:
    _draw_circle_badge(draw, fill="#1570EF")
    draw.ellipse(
        (746, 706, 918, 878),
        outline="white",
        width=GLYPH_WIDTH,
    )
    draw.line((832, 750, 832, 801, 874, 830), fill="white", width=GLYPH_WIDTH)


def _draw_success(draw: ImageDraw.ImageDraw) -> None:
    _draw_circle_badge(draw, fill="#16803C")
    draw.line(
        ((754, 810), (810, 866), (912, 746)),
        fill="white",
        width=GLYPH_WIDTH,
        joint="curve",
    )


def _draw_warning(draw: ImageDraw.ImageDraw) -> None:
    triangle = ((832, 646), (984, 932), (680, 932))
    draw.polygon(triangle, fill="#B54708", outline="white")
    draw.line(
        (832, 724, 832, 838),
        fill="white",
        width=GLYPH_WIDTH,
    )
    draw.ellipse((812, 866, 852, 906), fill="white")


def _draw_error(draw: ImageDraw.ImageDraw) -> None:
    _draw_circle_badge(draw, fill="#B42318")
    draw.line((764, 744, 900, 880), fill="white", width=GLYPH_WIDTH)
    draw.line((900, 744, 764, 880), fill="white", width=GLYPH_WIDTH)


DRAWERS = {
    "idle": _draw_idle,
    "running": _draw_running,
    "success": _draw_success,
    "warning": _draw_warning,
    "error": _draw_error,
}


def generate(output_root: Path) -> tuple[Path, ...]:
    """Generate all status icon variants under *output_root*."""
    with Image.open(BASE_ICON) as source:
        base = source.convert("RGBA")
    generated = []
    for status, drawer in DRAWERS.items():
        image = base.copy()
        drawer(ImageDraw.Draw(image))
        target = output_root / f"timelocker-icon-{status}.png"
        image.save(target, format="PNG", optimize=False, compress_level=9)
        generated.append(target)
    return tuple(generated)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ASSET_ROOT,
        help="Directory that receives the generated PNG assets.",
    )
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    for path in generate(args.output_root):
        print(path)


if __name__ == "__main__":
    main()
