#!/usr/bin/env python3
"""Generate a visual diff between two plot images.

Uses the same algorithm as matplotlib's testing infrastructure (pytest-mpl):
  diff = |before - after| * 10, clipped to [0,255]

The 10x amplification makes subtle changes clearly visible.

Produces a 3-panel image: [BEFORE | AFTER | DIFF]
Also reports RMS difference for programmatic use.

Usage:
    python plot_diff.py before.png after.png diff_output.png
"""

import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def calculate_rms(arr_before, arr_after):
    """RMS per-pixel error, same as matplotlib.testing.compare.calculate_rms."""
    return float(np.sqrt(((arr_before - arr_after) ** 2).mean()))


def make_diff_image(arr_before, arr_after):
    """Generate diff panel: |before - after| * 10, clipped.
    Same algorithm as matplotlib.testing.compare.save_diff_image."""
    abs_diff = np.abs(arr_before - arr_after)
    abs_diff *= 10
    abs_diff = np.clip(abs_diff, 0, 255).astype(np.uint8)
    return abs_diff


def make_diff(before_path, after_path, output_path):
    """Create a 3-panel diff image and return stats."""
    img_before = Image.open(before_path).convert("RGB")
    img_after = Image.open(after_path).convert("RGB")

    # Resize to match if needed
    w = max(img_before.width, img_after.width)
    h = max(img_before.height, img_after.height)
    img_before = img_before.resize((w, h), Image.LANCZOS)
    img_after = img_after.resize((w, h), Image.LANCZOS)

    arr_before = np.array(img_before, dtype=np.float64)
    arr_after = np.array(img_after, dtype=np.float64)

    rms = calculate_rms(arr_before, arr_after)
    diff_panel = make_diff_image(arr_before, arr_after)

    # Build 3-panel: BEFORE | AFTER | DIFF
    gap = 4
    label_h = 30
    total_w = w * 3 + gap * 2
    total_h = h + label_h
    canvas = np.full((total_h, total_w, 3), 255, dtype=np.uint8)

    y0 = label_h
    canvas[y0:y0+h, 0:w] = arr_before.astype(np.uint8)
    canvas[y0:y0+h, w+gap:2*w+gap] = arr_after.astype(np.uint8)
    canvas[y0:y0+h, 2*w+2*gap:3*w+2*gap] = diff_panel

    result = Image.fromarray(canvas)

    # Labels
    try:
        draw = ImageDraw.Draw(result)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        except (OSError, IOError):
            font = ImageFont.load_default()
        draw.text((w//2 - 40, 5), "BEFORE", fill=(0, 0, 0), font=font)
        draw.text((w + gap + w//2 - 30, 5), "AFTER", fill=(0, 0, 0), font=font)
        draw.text((2*w + 2*gap + w//2 - 50, 5), f"DIFF (x10)", fill=(200, 0, 0), font=font)
    except Exception:
        pass

    result.save(output_path, dpi=(200, 200))
    return {"rms": round(rms, 2), "changed_pct": round(100.0 * np.sum(np.any(diff_panel > 0, axis=2)) / (w * h), 2)}


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} before.png after.png diff_output.png")
        sys.exit(1)
    stats = make_diff(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"RMS: {stats['rms']}, Changed: {stats['changed_pct']}%")
