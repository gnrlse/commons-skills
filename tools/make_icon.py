#!/usr/bin/env python3
"""Render the directory icons: plugins/<name>/.claude-plugin/icon.png.

A ring of six nodes around a gold centre: agents around a shared commons.
`commons` is light on green, `commons-maintainer` green on light. The plugin
directory captures a listing's icon once, at the first save in the developer
portal, so regenerate and commit before that. Needs numpy (dev only):

    python3 tools/make_icon.py
"""
import struct
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SIZE = 1024
GREEN, CREAM, GOLD = (0x24, 0x58, 0x4A), (0xF3, 0xEF, 0xE4), (0xE3, 0xA9, 0x3B)
VARIANTS = {"commons": (GREEN, CREAM), "commons-maintainer": (CREAM, GREEN)}


def coverage(distance):
    """Anti-aliased coverage from a signed distance in pixels (negative inside)."""
    return np.clip(0.5 - distance, 0.0, 1.0)


def render(background, foreground):
    y, x = np.mgrid[0:SIZE, 0:SIZE] + 0.5
    x, y = x - SIZE / 2, y - SIZE / 2
    r = np.hypot(x, y)
    ring_radius, ring_width, node_radius, gap = 300, 46, 66, 22
    angles = np.deg2rad(np.arange(6) * 60 - 90)
    nodes = [(ring_radius * np.cos(a), ring_radius * np.sin(a)) for a in angles]
    node_dist = np.min([np.hypot(x - cx, y - cy) for cx, cy in nodes], axis=0)

    ring = coverage(np.abs(r - ring_radius) - ring_width / 2) * (1 - coverage(node_dist - node_radius - gap))
    glyph = np.maximum(ring, coverage(node_dist - node_radius))
    centre = coverage(r - 128)

    img = np.empty((SIZE, SIZE, 3))
    img[:] = background
    for mask, colour in ((glyph, foreground), (centre, GOLD)):
        img = img * (1 - mask[..., None]) + np.array(colour) * mask[..., None]
    return np.round(img).astype(np.uint8)


def png(pixels):
    height, width, _ = pixels.shape
    raw = b"".join(b"\0" + pixels[row].tobytes() for row in range(height))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def main():
    for name, (background, foreground) in VARIANTS.items():
        out = ROOT / "plugins" / name / ".claude-plugin" / "icon.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(png(render(background, foreground)))
        print(f"{out.relative_to(ROOT)}: {out.stat().st_size} bytes")


if __name__ == "__main__":
    main()
