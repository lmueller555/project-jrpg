"""Shared registration helpers for authored cinematic image exports."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    with Image.open(path) as image:
        dimensions = list(image.size)
    return {'file': path.relative_to(ROOT).as_posix(),
            'dimensions': dimensions, 'sha256': digest(path)}


def pixel_alpha(image):
    """Remove faint matte residue without changing any authored RGB pixels."""
    image = image.convert('RGBA')
    image.putalpha(image.getchannel('A').point(lambda value: 255 if value >= 128 else 0))
    return image
