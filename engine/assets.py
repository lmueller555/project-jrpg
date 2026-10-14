"""Validated production PNG atlas registry and timeline player."""
import json
from pathlib import Path
import re
import struct
import zlib
import pygame

ASSET_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._][a-z0-9]+)*$")
LAYERS = ("ground", "ground_details", "below_entities", "entities",
          "foreground", "world_effects", "lighting_weather", "screen_ui")


class AssetError(ValueError):
    pass


def validate_png(path):
    """Decode every RGBA8 PNG scanline and reject corrupt IDAT/filter bytes."""
    data = path.read_bytes()
    if not data.startswith(bytes((137, 80, 78, 71, 13, 10, 26, 10))):
        raise AssetError(f"Invalid PNG signature: {path}")
    pos, ihdr, payload, ended = 8, None, bytearray(), False
    palette_present, transparency_present = False, False
    try:
        while pos + 12 <= len(data):
            length = struct.unpack_from(">I", data, pos)[0]
            kind = data[pos + 4:pos + 8]
            stop = pos + 12 + length
            if stop > len(data):
                raise ValueError("Truncated chunk")
            chunk = data[pos + 8:pos + 8 + length]
            crc = struct.unpack_from(">I", data, pos + 8 + length)[0]
            if zlib.crc32(kind + chunk) & 0xffffffff != crc:
                raise ValueError("CRC mismatch")
            if kind == b"IHDR":
                if ihdr is not None or length != 13:
                    raise ValueError("Invalid IHDR")
                ihdr = chunk
            elif kind == b"PLTE":
                palette_present = True
            elif kind == b"tRNS":
                transparency_present = True
            elif kind == b"IDAT":
                payload.extend(chunk)
            elif kind == b"IEND":
                ended = True
                if stop != len(data):
                    raise ValueError("Trailing data")
                break
            pos = stop
        if not ended or ihdr is None or not payload:
            raise ValueError("Missing PNG chunks")
        width, height, depth, color, comp, filt, interlace = struct.unpack(">IIBBBBB", ihdr)
        if not (width and height and depth == 8 and color in (3, 6) and comp == 0 and filt == 0 and interlace == 0):
            raise ValueError("Expected non-interlaced 8-bit RGBA or indexed PNG")
        if color == 3 and not (palette_present and transparency_present):
            raise ValueError("Indexed sprite atlas requires PLTE and tRNS transparency")
        raw = zlib.decompress(bytes(payload))
        stride = width * (4 if color == 6 else 1) + 1
        if len(raw) != stride * height:
            raise ValueError("Wrong decompressed image size")
        for y in range(height):
            if raw[y * stride] not in (0, 1, 2, 3, 4):
                raise ValueError(f"Invalid scanline filter at row {y}")
    except (ValueError, struct.error, zlib.error) as exc:
        raise AssetError(f"Corrupt PNG {path}: {exc}") from exc
    return width, height


def validate_manifest(doc, asset_root):
    if doc.get("schema_version") != 1 or not isinstance(doc.get("assets"), dict):
        raise AssetError("Manifest must have schema_version 1 and assets object")
    for name, spec in doc["assets"].items():
        if not ASSET_ID.fullmatch(name):
            raise AssetError(f"Invalid semantic ID: {name}")
        if spec.get("layer") not in LAYERS:
            raise AssetError(f"Invalid layer: {name}")
        atlas = spec.get("atlas")
        if not isinstance(atlas, str) or not atlas.endswith(".png"):
            raise AssetError(f"Invalid atlas reference: {name}")
        relative = Path(atlas)
        if relative.is_absolute() or ".." in relative.parts:
            raise AssetError(f"Unsafe atlas path: {name}")
        rect = spec.get("rect")
        if not isinstance(rect, list) or len(rect) != 4 or any(type(v) is not int for v in rect) or min(rect[:2]) < 0 or min(rect[2:]) <= 0:
            raise AssetError(f"Invalid rectangle: {name}")
        anchor = spec.get("anchor", [0, 0])
        if not isinstance(anchor, list) or len(anchor) != 2 or any(type(v) is not int for v in anchor):
            raise AssetError(f"Invalid anchor: {name}")
        path = asset_root / relative
        if not path.is_file():
            raise AssetError(f"Missing PNG: {path}")
        width, height = validate_png(path)
        x, y, w, h = rect
        if x + w > width or y + h > height:
            raise AssetError(f"Atlas bounds exceeded: {name}")
    for anim_id, clip in doc.get("animations", {}).items():
        if not ASSET_ID.fullmatch(anim_id) or clip.get("mode") not in {"loop", "once", "ping_pong", "hold_last"}:
            raise AssetError(f"Invalid animation: {anim_id}")
        frames = clip.get("frames")
        if not isinstance(frames, list) or not frames:
            raise AssetError(f"No frames: {anim_id}")
        for frame in frames:
            if frame.get("asset") not in doc["assets"] or type(frame.get("duration_ms")) is not int or frame["duration_ms"] <= 0:
                raise AssetError(f"Invalid animation frame: {anim_id}")
    return doc


class AtlasRegistry:
    def __init__(self, root):
        self.root = Path(root)
        with (self.root / "manifests/assets.json").open(encoding="utf-8") as stream:
            self.manifest = validate_manifest(json.load(stream), self.root)
        self.atlases = {}
        self.frames = {}

    def image(self, asset_id):
        if asset_id not in self.frames:
            spec = self.manifest["assets"][asset_id]
            atlas_name = spec["atlas"]
            if atlas_name not in self.atlases:
                self.atlases[atlas_name] = pygame.image.load(str(self.root / atlas_name)).convert_alpha()
            self.frames[asset_id] = self.atlases[atlas_name].subsurface(pygame.Rect(spec["rect"]))
        return self.frames[asset_id]

    def draw(self, surface, asset_id, x, y):
        spec = self.manifest["assets"][asset_id]
        ax, ay = spec.get("anchor", [0, 0])
        surface.blit(self.image(asset_id), (round(x - ax), round(y - ay)))


class AnimationPlayer:
    def __init__(self, registry, clip):
        self.registry = registry
        self.set_clip(clip)

    def set_clip(self, clip):
        if clip not in self.registry.manifest["animations"]:
            raise AssetError(f"Missing clip: {clip}")
        self.clip = clip
        self.elapsed_ms = 0

    def update(self, delta_ms):
        self.elapsed_ms += max(0, int(delta_ms))

    def frame(self):
        definition = self.registry.manifest["animations"][self.clip]
        frames = definition["frames"]
        durations = [f["duration_ms"] for f in frames]
        total = sum(durations)
        moment = self.elapsed_ms
        if definition["mode"] == "loop":
            moment %= total
        elif definition["mode"] == "ping_pong" and len(frames) > 1:
            sequence = frames + frames[-2:0:-1]
            total = sum(f["duration_ms"] for f in sequence)
            moment %= total
            frames = sequence
        else:
            moment = min(moment, total - 1)
        for frame in frames:
            if moment < frame["duration_ms"]:
                return frame["asset"]
            moment -= frame["duration_ms"]
        return frames[-1]["asset"]


class RenderQueue:
    """Stable layered ordering; collision remains controlled by map/world code."""
    def __init__(self):
        self.items = []

    def add(self, layer, foot_y, draw_fn):
        if layer not in LAYERS:
            raise AssetError(f"Invalid draw layer: {layer}")
        self.items.append((LAYERS.index(layer), foot_y, len(self.items), draw_fn))

    def flush(self):
        for _, _, _, draw_fn in sorted(self.items):
            draw_fn()
        self.items.clear()
