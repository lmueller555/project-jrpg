#!/usr/bin/env python3
"""Offline, georeferenced Regent crossroads scenery from retained raw artwork.

No image-generation service, runtime renderer, actor image, exported map, or
24px runtime material is used. Only the two new crossroads asset trees and
crossroads/geography/bridge-prefixed review PNGs can be written by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import zlib

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/cinematics/regent_arrival/crossroads"
OUTPUT = ROOT / "assets/story/regent_arrival/crossroads"
REVIEW = ROOT / "docs/reviews/regent_crossroads"
REGION = ROOT / "assets/maps/overworld/elden_vale/region.json"
POLISH = ROOT / "assets/source/terrain/overworld/elden_vale/polish"
RECIPE = SOURCE / "recipe.json"
Point = tuple[float, float]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def png_bytes(image: Image.Image) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG", compress_level=9, optimize=False)
    return stream.getvalue()


def pixel_sha256(image: Image.Image) -> str:
    """Pixels, not zlib-specific compressed bytes, are the portable contract."""
    return sha256(image.convert("RGBA").tobytes())


def verified_inputs(recipe: dict) -> list[dict]:
    records = []
    for spec in recipe["source_records"]:
        path = ROOT / spec["file"]
        actual = sha256(path.read_bytes())
        if actual != spec["sha256"]:
            raise ValueError(f"Retained input changed; do not silently re-author: {spec['file']}")
        records.append(dict(spec))
    return records


def distance_to_polyline(point: Point, points: list) -> float:
    best = math.inf
    for a, b in zip(points, points[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length2 = dx * dx + dy * dy
        t = 0.0 if not length2 else max(0.0, min(1.0,
            ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2))
        best = min(best, math.hypot(point[0] - a[0] - dx * t,
                                   point[1] - a[1] - dy * t))
    return best


def inside_polygon(point: Point, polygon: list) -> bool:
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            if x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                inside = not inside
    return inside


class Projection:
    """One invertible, east-right/south-down affine map for every feature."""

    def __init__(self, spec: dict):
        self.origin = tuple(spec["origin_tiles"])
        self.scale = tuple(spec["pixels_per_tile"])
        self.offset = tuple(spec.get("offset_pixels", (0, 0)))

    def point(self, point: Point | list) -> Point:
        return tuple((point[i] - self.origin[i]) * self.scale[i] + self.offset[i]
                     for i in (0, 1))

    def inverse(self, point: Point | list) -> Point:
        return tuple((point[i] - self.offset[i]) / self.scale[i] + self.origin[i]
                     for i in (0, 1))

    def rect(self, rect: list) -> tuple[int, int, int, int]:
        x, y, w, h = rect
        a = self.point((x, y))
        b = self.point((x + w, y + h))
        return tuple(round(v) for v in (*a, *b))


def route_contract(region: dict, recipe: dict, project: Projection) -> dict:
    """Sample the already-densified canonical road by actual tile arc length."""
    road = next(road for road in region["roads"] if road["id"] == "south_town_road")
    first = road["points"].index(recipe["junction_tile"])
    last = road["points"].index(recipe["bridge_tile"])
    points = np.asarray(road["points"][first:last + 1], dtype=np.float64)
    arcs = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    pixel_points = np.asarray([project.point(p) for p in points])
    pixel_arcs = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pixel_points, axis=0), axis=1))]
    count = math.ceil(float(arcs[-1]) / recipe["route_max_step_tiles"]) + 1
    samples = np.linspace(0.0, float(arcs[-1]), count)
    route = np.stack([np.interp(samples, arcs, points[:, i]) for i in (0, 1)], axis=1)
    camera = []
    for point, distance in zip(route, samples):
        t = float(distance / arcs[-1])
        # A two-pixel horizontal / twenty-pixel vertical framing drift, not a
        # local projection or an invented route. Source centerline stays exact.
        anchor = [(1 - t) * a + t * b for a, b in
                  zip(recipe["junction_screen"], recipe["bridge_screen"])]
        pixel = project.point(point)
        camera.append([round(pixel[i] - anchor[i], 6) for i in (0, 1)])
    return {
        "road_id": road["id"],
        "source_point_indices": [first, last],
        "road_source_tile_points": points.tolist(),
        "route_tile_points": [[round(float(v), 8) for v in p] for p in route],
        "route_arc_distances_tiles": [round(float(v), 8) for v in samples],
        "route_arc_distances_pixels": [round(float(v), 6) for v in
                                      np.interp(samples, arcs, pixel_arcs)],
        "route_length_tiles": round(float(arcs[-1]), 8),
        "route_length_pixels": round(float(pixel_arcs[-1]), 6),
        "camera_path": camera,
        "camera_junction": [round(v) for v in camera[0]],
        "camera_bridge": [round(v) for v in camera[-1]],
        "road_reference_in_viewport": {
            "from": recipe["junction_screen"], "to": recipe["bridge_screen"],
            "interpolation": "linear in canonical tile arc length"
        },
        "sampling_note": "At most 1 tile between arc samples. Canonical short bridge-approach eastward nudge is retained in road_source_tile_points; these exact centerline arc samples and camera x positions are strictly westward."
    }


def polyline_mask(size: tuple[int, int], points: list, width: float,
                  project: Projection) -> Image.Image:
    """Stroke in world tiles BEFORE projection, preserving anisotropic widths."""
    image = Image.new("L", size)
    draw = ImageDraw.Draw(image)
    half = width / 2
    sx, sy = project.scale
    for a, b in zip(points, points[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if not length:
            continue
        nx, ny = -dy / length * half, dx / length * half
        corners = [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                   (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]
        draw.polygon([project.point(p) for p in corners], fill=255)
    for point in points:
        x, y = project.point(point)
        draw.ellipse((round(x - half * sx), round(y - half * sy),
                      round(x + half * sx), round(y + half * sy)), fill=255)
    return image


def polygon_mask(size: tuple[int, int], points: list,
                 project: Projection) -> Image.Image:
    image = Image.new("L", size)
    ImageDraw.Draw(image).polygon([project.point(p) for p in points], fill=255)
    return image


def offset_path(points: list, distance: float) -> list:
    result = []
    for i, point in enumerate(points):
        a = points[max(0, i - 1)]
        b = points[min(len(points) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1.0
        result.append([point[0] - dy / length * distance,
                       point[1] + dx / length * distance])
    return result


def _minimum_cut(cost: np.ndarray) -> np.ndarray:
    """Vertical minimum-error seam; True means retain the old overlap pixel."""
    height, width = cost.shape
    previous = cost[0].copy()
    parents = np.zeros((height, width), dtype=np.int8)
    columns = np.arange(width)
    for y in range(1, height):
        choices = np.stack((np.r_[np.inf, previous[:-1]], previous,
                            np.r_[previous[1:], np.inf]))
        choice = np.argmin(choices, axis=0)
        parents[y] = choice.astype(np.int8) - 1
        previous = cost[y] + choices[choice, columns]
    x = int(np.argmin(previous))
    seam = np.zeros(height, dtype=np.int32)
    for y in range(height - 1, -1, -1):
        seam[y] = x
        x += int(parents[y, x])
    return columns[None, :] <= seam[:, None]


class Materials:
    """Native raw samples, nonperiodic minimum-cut quilting, no tiny tiles."""

    def __init__(self, recipe: dict):
        self.recipe = recipe
        self.images: dict[str, Image.Image] = {}
        self.samples: list[dict] = []

    def source(self, key: str) -> Image.Image:
        if key not in self.images:
            spec = self.recipe["materials"][key]
            path = ROOT / spec["file"] if "file" in spec else POLISH / spec["sheet"]
            with Image.open(path) as raw:
                crop = raw.convert("RGB").crop(spec["crop"])
            scale = spec["scale"]
            if not 0 < scale <= 1:
                raise ValueError("Material must be retained raw detail, never enlarged")
            crop = crop.resize((round(crop.width * scale), round(crop.height * scale)),
                               Image.Resampling.NEAREST)
            if "contrast" in spec or "rgb_multiply" in spec:
                # Offline water-only color treatment, never new painted detail
                # or a change to the original retained source image.
                contrast = spec.get("contrast", 1.0)
                if not 0 <= contrast <= 1:
                    raise ValueError("Material contrast treatment may only subdue retained detail")
                rgb = np.asarray(crop).astype(np.float32)
                mean = rgb.mean(axis=(0, 1), keepdims=True)
                rgb = (mean + (rgb - mean) * contrast) * np.asarray(spec.get("rgb_multiply", (1, 1, 1)))
                crop = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
            self.images[key] = crop
        return self.images[key]

    def quilt(self, size: tuple[int, int], key: str, origin: tuple[int, int] = (0, 0),
              angle: float = 0.0) -> Image.Image:
        """Cut seams around illustrated blades/stones instead of square swatches.

        Candidate crop coordinates and flips are retained in material_samples.
        Rotated field layers sample a larger quilt then crop; no enlargement.
        """
        if angle:
            span = math.ceil(math.hypot(*size)) + 8
            image = self.quilt((span, span), key, origin)
            image = image.rotate(-angle, resample=Image.Resampling.NEAREST)
            x, y = (span - size[0]) // 2, (span - size[1]) // 2
            return image.crop((x, y, x + size[0], y + size[1]))
        raw = np.asarray(self.source(key))
        patch = min(96, max(24, min(raw.shape[0], raw.shape[1]) * 2 // 3))
        overlap = max(8, patch // 4)
        step = patch - overlap
        field = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        seed = (self.recipe["seed"] + zlib.crc32(key.encode()) +
                origin[0] * 103 + origin[1] * 509) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        placements = []
        # Water's calm sample has deliberately horizontal highlights; do
        # not quarter-turn it or introduce source river/shoreline silhouettes.
        flip_axes = (0, 1, 2, 3) if key not in ("grain", "vegetables", "water") else (0, 1)
        for y in range(0, size[1], step):
            for x in range(0, size[0], step):
                h, w = min(patch, size[1] - y), min(patch, size[0] - x)
                old = field[y:y + h, x:x + w]
                best = None
                best_score = math.inf
                best_record = None
                for _ in range(3 if x or y else 1):
                    rx = int(rng.integers(0, raw.shape[1] - patch + 1))
                    ry = int(rng.integers(0, raw.shape[0] - patch + 1))
                    flip = int(rng.choice(flip_axes))
                    candidate = raw[ry:ry + patch, rx:rx + patch]
                    if flip & 1:
                        candidate = candidate[:, ::-1]
                    if flip & 2:
                        candidate = candidate[::-1]
                    candidate = candidate[:h, :w]
                    delta = (old.astype(np.float32) - candidate.astype(np.float32)) ** 2
                    score = 0.0
                    if x:
                        score += float(delta[:, :min(overlap, w)].mean())
                    if y:
                        score += float(delta[:min(overlap, h)].mean())
                    if score < best_score:
                        best, best_score = candidate, score
                        best_record = [x, y, rx, ry, flip]
                assert best is not None
                preserve = np.zeros((h, w), dtype=bool)
                difference = ((old.astype(np.float32) - best.astype(np.float32)) ** 2).mean(axis=2)
                if x:
                    ow = min(overlap, w)
                    preserve[:, :ow] |= _minimum_cut(difference[:, :ow])
                if y:
                    oh = min(overlap, h)
                    preserve[:oh] |= _minimum_cut(difference[:oh].T).T
                field[y:y + h, x:x + w] = np.where(preserve[..., None], old, best)
                placements.append(best_record)
        self.samples.append({"material": key, "origin_pixels": list(origin),
                             "size": list(size), "seed": seed, "patch": patch,
                             "overlap": overlap,
                             "placement_columns": ["x", "y", "source_x", "source_y", "flip_bits"],
                             "placements": placements})
        return Image.fromarray(field)


def slow_noise(size: tuple[int, int], seed: int, spacing: int = 96) -> np.ndarray:
    rng = np.random.default_rng(seed)
    grid = rng.integers(0, 256, (size[1] // spacing + 3, size[0] // spacing + 3), dtype=np.uint8)
    return np.asarray(Image.fromarray(grid).resize(size, Image.Resampling.BICUBIC)).astype(np.float32) / 255


class Scenery:
    def __init__(self, recipe: dict, region: dict):
        self.recipe, self.region = recipe, region
        self.size = tuple(recipe["canvas"])
        self.project = Projection(recipe["projection"])
        self.route = route_contract(region, recipe, self.project)
        self.materials = Materials(recipe)
        self.prop_recipe = json.loads((POLISH / "recipe.json").read_text())
        self.prop_cache: dict[tuple, Image.Image] = {}
        self.props: list[dict] = []
        self.prop_sources: dict[str, dict] = {}
        self.masks: dict[str, Image.Image] = {}
        self.camera = self.route["camera_junction"]
        self.actors = {key: [self.camera[i] + point[i] for i in (0, 1)]
                       for key, point in recipe["actors_screen"].items()}
        self.clear_rects = []
        for key, (x, y) in self.actors.items():
            if key == "parked_caravan":
                self.clear_rects.append((x - 160, y - 146, x + 160, y + 14))
            else:
                self.clear_rects.append((x - 46, y - 104, x + 46, y + 14))

    def stroke(self, points: list, width: float) -> Image.Image:
        return polyline_mask(self.size, points, width, self.project)

    def polygon(self, points: list) -> Image.Image:
        return polygon_mask(self.size, points, self.project)

    def paint(self, canvas: Image.Image, mask: Image.Image, key: str, *,
              feather: float = 0.0, opacity: float = 1.0, angle: float = 0.0,
              grade: tuple[float, float, float] | None = None) -> None:
        box = mask.getbbox()
        if not box:
            return
        pad = math.ceil(feather * 3)
        box = (max(0, box[0] - pad), max(0, box[1] - pad),
               min(self.size[0], box[2] + pad), min(self.size[1], box[3] + pad))
        size = box[2] - box[0], box[3] - box[1]
        crop = self.materials.quilt(size, key, box[:2], angle)
        if grade:
            array = np.asarray(crop).astype(np.float32) * np.asarray(grade)
            crop = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
        alpha = mask.crop(box)
        if feather:
            alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
        if opacity != 1.0:
            alpha = alpha.point(lambda a: round(a * opacity))
        canvas.paste(crop, box[:2], alpha)

    def prop_image(self, key: str, height: int) -> Image.Image:
        cache_key = key, height
        if cache_key not in self.prop_cache:
            spec = self.prop_recipe["props"][key]
            with Image.open(POLISH / spec["source"]) as raw:
                image = raw.convert("RGBA").crop(spec["crop"])
            image.putalpha(image.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
            box = image.getbbox()
            if box is None:
                raise ValueError(f"Empty retained prop crop: {key}")
            image = image.crop(box)
            factor = min(1.0, height / image.height)
            image = image.resize((round(image.width * factor), round(image.height * factor)),
                                 Image.Resampling.NEAREST)
            self.prop_cache[cache_key] = image
            self.prop_sources[key] = {
                "file": (POLISH / spec["source"]).relative_to(ROOT).as_posix(),
                "registered_crop": spec["crop"], "opaque_bbox_in_crop": list(box),
                "alpha_threshold": 128, "resampling": "nearest; uniform reduction only",
                "anchor": "bottom center of thresholded bounded source crop"
            }
        return self.prop_cache[cache_key]

    def add_prop(self, key: str, tile: list | Point, identifier: str,
                 height: int | None = None, flip: bool = False,
                 authority: str = "decorative vegetation; no new geographic feature") -> None:
        if key not in self.recipe["prop_height_pixels"]:
            return  # Do not freeze any source-sheet animal or smoke animation.
        height = height or self.recipe["prop_height_pixels"][key]
        image = self.prop_image(key, height)
        x, y = self.project.point(tile)
        left, top = round(x - image.width / 2), round(y - image.height)
        right, bottom = left + image.width, top + image.height
        if right <= 0 or bottom <= 0 or left >= self.size[0] or top >= self.size[1]:
            return
        if image.height >= 65:
            # A tree rooted outside a burn can still hide it with its canopy.
            # Protect the visible artwork footprint, not just its trunk point.
            damage = self.masks.get("scorch")
            if damage is not None and damage.crop((left - 7, top - 7, right + 7, bottom + 7)).getbbox():
                return
            deck = self.project.rect(self.region["bridge"]["deck_rect_tiles"])
            if left < deck[2] + 8 and right > deck[0] - 8 and top < deck[3] + 8 and bottom > deck[1] - 8:
                return
        for a, b, c, d in self.clear_rects:
            if left < c and right > a and top < d and bottom > b:
                return
        self.props.append({"id": identifier, "key": key,
                           "tile_position": [round(float(v), 6) for v in tile],
                           "anchor_pixels": [round(x, 6), round(y, 6)],
                           "height_pixels": image.height, "size_pixels": list(image.size),
                           "flip_horizontal": flip, "authority": authority})

    def reserved(self, tile: Point, padding: float = 0.0) -> bool:
        if any(distance_to_polyline(tile, road["points"]) < road["width"] / 2 + padding
               for road in self.region["roads"]):
            return True
        if any(distance_to_polyline(tile, river["points"]) < river["width"] / 2 + padding
               for river in self.region["terrain"]["rivers"]):
            return True
        terrain = self.region["terrain"]
        if any(inside_polygon(tile, feature["polygon"])
               for kind in ("fields", "yards", "scorched") for feature in terrain.get(kind, [])):
            return True
        if any(math.dist(tile, piece["tile_position"]) < piece.get("clearance_radius", 7) + padding
               for piece in self.region.get("setpieces", [])):
            return True
        # Town is off the north edge; never invent replacement houses/gates.
        x, y, w, h = self.region["town"]["entry_rect_tiles"]
        return x - 4 < tile[0] < x + w + 4 and y - 4 < tile[1] < y + h + 4

    def ground(self) -> Image.Image:
        print("Quilting retained native meadow detail...", flush=True)
        canvas = self.materials.quilt(self.size, "meadow")
        noise = slow_noise(self.size, self.recipe["seed"], 142)
        # Soft ecological transitions are masks, not enlarged material pixels.
        dry = Image.fromarray(np.clip((noise - 0.42) * 280, 0, 96).astype(np.uint8))
        self.paint(canvas, dry, "dry_grass", opacity=0.47)
        flowers = Image.fromarray(np.clip((0.39 - noise) * 340, 0, 85).astype(np.uint8))
        self.paint(canvas, flowers, "flower_meadow", opacity=0.65)
        field_mask = Image.new("L", self.size)
        for forest in self.region["terrain"].get("forests", []):
            self.paint(canvas, self.polygon(forest["polygon"]), "leaf_litter", feather=8, opacity=0.8)
        for field in self.region["terrain"]["fields"]:
            mask = self.polygon(field["polygon"])
            if not mask.getbbox():
                continue
            field_mask = ImageChops.lighter(field_mask, mask)
            crop = field["crop"]
            key = {"grain": "grain", "vegetables": "vegetables", "fallow": "furrows",
                   "pasture": "pasture", "orchard": "orchard"}[crop]
            # Project the canonical row angle with the same x/y metric.
            theta = math.radians(field.get("row_angle", 0))
            angle = math.degrees(math.atan2(math.sin(theta) * self.project.scale[1],
                                           math.cos(theta) * self.project.scale[0]))
            self.paint(canvas, mask.filter(ImageFilter.MaxFilter(9)), "dry_grass", feather=3)
            self.paint(canvas, mask, key, feather=1.5, angle=angle,
                       grade=(0.97, 0.94, 0.88) if field.get("palette_variant") else None)
        self.masks["fields"] = field_mask
        for yard in self.region["terrain"].get("yards", []):
            self.paint(canvas, self.polygon(yard["polygon"]),
                       "gravel" if yard["surface"] == "gravel" else "earth", feather=4)
        # A low-contrast, irregularly worn grassy verge, not an additional road
        # or invented formal court. It gives the side-facing conversation air.
        stage_points = [[1.7, 7.5], [4.1, 6.7], [7.6, 6.8], [9.5, 7.7],
                        [10.0, 9.0], [8.4, 10.1], [4.7, 10.2], [2.0, 9.3]]
        stage = self.polygon(stage_points)
        self.paint(canvas, stage, "dry_grass", feather=14, opacity=0.64)
        self.paint(canvas, stage, "earth", feather=17, opacity=0.13)
        self.masks["worn_verge_variation"] = stage
        return canvas

    def roads(self, canvas: Image.Image) -> None:
        print("Projecting the canonical roads and their measured widths...", flush=True)
        stone = Image.new("L", self.size)
        dirt = Image.new("L", self.size)
        verge = Image.new("L", self.size)
        roads = sorted(self.region["roads"], key=lambda road: {"foot": 0, "cart": 1, "stone": 2}[road["kind"]])
        for road in roads:
            mask = self.stroke(road["points"], road["width"])
            if not mask.getbbox():
                continue
            verge = ImageChops.lighter(verge, self.stroke(road["points"], road["width"] + 0.65))
            if road["kind"] == "stone":
                stone = ImageChops.lighter(stone, mask)
            else:
                dirt = ImageChops.lighter(dirt, mask)
        self.masks["stone_road"], self.masks["dirt_road"] = stone, dirt
        self.paint(canvas, verge, "dry_grass", feather=4, opacity=0.82)
        # Dark gravel contact is irregularly interrupted by the verge below.
        stone_edge = stone.filter(ImageFilter.MaxFilter(5))
        self.paint(canvas, stone_edge, "loam", feather=1.0, opacity=0.64)
        self.paint(canvas, dirt, "earth", feather=1.5)
        for road in roads:
            if road["kind"] == "cart" and road.get("ruts", True):
                median = self.stroke(road["points"], road["width"] * 0.25)
                self.paint(canvas, median, "dry_grass", feather=3, opacity=0.72)
                for side in (-1, 1):
                    rut = self.stroke(offset_path(road["points"], road["width"] * 0.29 * side),
                                      road["width"] * 0.16)
                    self.paint(canvas, rut, "loam", feather=1.2, opacity=0.55)
        self.paint(canvas, stone, "stone", feather=0.5)
        self.road_verge = ImageChops.subtract(verge, ImageChops.lighter(stone, dirt))

    def river_and_damage(self, canvas: Image.Image) -> None:
        print("Masking the western river and both canonical scorch parcels...", flush=True)
        scorch = Image.new("L", self.size)
        for feature in self.region["terrain"]["scorched"]:
            mask = self.polygon(feature["polygon"])
            scorch = ImageChops.lighter(scorch, mask)
            self.paint(canvas, mask.filter(ImageFilter.MaxFilter(9)), "loam", feather=5,
                       grade=(0.64, 0.60, 0.53))
            self.paint(canvas, mask, "leaf_litter", feather=2.0,
                       grade=(0.48, 0.47, 0.45))
            self.paint(canvas, mask, "loam", feather=1.5, opacity=0.38,
                       grade=(0.42, 0.42, 0.44))
        self.masks["scorch"] = scorch
        river_mask = Image.new("L", self.size)
        for river in self.region["terrain"]["rivers"]:
            mask = self.stroke(river["points"], river["width"])
            if not mask.getbbox():
                continue
            river_mask = ImageChops.lighter(river_mask, mask)
            self.paint(canvas, self.stroke(river["points"], river["width"] + 1.25),
                       "loam", feather=3, grade=(0.76, 0.79, 0.73))
            self.paint(canvas, self.stroke(river["points"], river["width"] + 0.4),
                       "gravel", feather=1.5, grade=(0.70, 0.76, 0.72))
            self.paint(canvas, mask, "water")
            # The contrast-subdued water-only sample receives the same broad
            # depth modulation; geographic flow remains the canonical N/S mask.
            box = mask.getbbox()
            if box:
                local = canvas.crop(box)
                noise = slow_noise(local.size, 11130, 75)
                rgb = np.asarray(local).astype(np.float32)
                rgb *= (0.82 + noise[..., None] * 0.20)
                shaded = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
                canvas.paste(shaded, box[:2], mask.crop(box))
        self.masks["river"] = river_mask

    def gather_props(self) -> None:
        # Foreground/upper-right framing uses real retained trees at explicitly
        # recorded meadow positions. It does not imply a new forest parcel.
        for key, screen, height in (("oak_a", (12, 306), 188),
                                    ("oak_b", (474, 108), 164)):
            absolute = (self.camera[0] + screen[0], self.camera[1] + screen[1])
            self.add_prop(key, self.project.inverse(absolute), f"junction_frame:{key}", height,
                          authority="decorative junction meadow tree; no geographic feature added")
        for piece in self.region.get("setpieces", []):
            for prop in piece.get("props", []):
                self.add_prop(prop["key"], prop["tile_position"], prop["id"],
                              authority=f"region.json setpiece {piece['id']}")
        for prop in self.region.get("decorations", []):
            self.add_prop(prop["key"], prop["tile_position"], prop["id"],
                          authority="region.json decoration")
        rng = np.random.default_rng(self.recipe["seed"])
        xmin, ymin = self.project.inverse((0, 0))
        xmax, ymax = self.project.inverse(self.size)
        for y in np.arange(ymin - 2, ymax + 4, 3.0):
            for x in np.arange(xmin - 2, xmax + 4, 3.0):
                tile = (float(x + rng.uniform(-0.9, 0.9)), float(y + rng.uniform(-0.9, 0.9)))
                if self.reserved(tile, 1.6):
                    continue
                value = float(rng.random())
                forest = any(inside_polygon(tile, f["polygon"]) for f in self.region["terrain"].get("forests", []))
                if value < (0.65 if forest else 0.08):
                    key = str(rng.choice(("oak_a", "oak_b", "oak_c")))
                    height = int(rng.integers(142, 194))
                elif value < 0.22:
                    key, height = "shrub", int(rng.integers(26, 43))
                elif value < 0.35:
                    key, height = "flowers_b", int(rng.integers(14, 23))
                elif value < 0.49:
                    key, height = "flowers_a", int(rng.integers(12, 21))
                elif value < 0.68:
                    key, height = "fern", int(rng.integers(17, 26))
                else:
                    continue
                self.add_prop(key, tile, f"meadow:{x:g}:{y:g}", height, bool(rng.integers(2)))
        # Small overlapping native tufts break the straight verge silhouette,
        # but their roots stay outside the measured canonical carriageway.
        for road in self.region["roads"]:
            for index, (a, b) in enumerate(zip(road["points"], road["points"][1:])):
                if index % 2:
                    continue
                dx, dy = b[0] - a[0], b[1] - a[1]
                length = math.hypot(dx, dy) or 1
                t = float(rng.uniform(0.15, 0.85))
                for side in (-1, 1):
                    d = (road["width"] / 2 + rng.uniform(0.12, 0.38)) * side
                    tile = (a[0] + t * dx - dy / length * d,
                            a[1] + t * dy + dx / length * d)
                    if any(distance_to_polyline(tile, river["points"]) < river["width"] / 2 + 0.3
                           for river in self.region["terrain"]["rivers"]):
                        continue
                    if any(inside_polygon(tile, s["polygon"]) for s in self.region["terrain"]["scorched"]):
                        continue
                    self.add_prop("grass_tuft", tile, f"verge:{road['id']}:{index}:{side}",
                                  int(rng.integers(9, 16)), bool(rng.integers(2)))
        # Riverbank plants follow the real north/south watercourse, never the
        # crossroads. Preserve clear broad approaches and the collapsed span.
        river = self.region["terrain"]["rivers"][0]
        for y in np.arange(ymin + 1, ymax, 2.2):
            for a, b in zip(river["points"], river["points"][1:]):
                if a[1] <= y < b[1]:
                    t = (y - a[1]) / (b[1] - a[1])
                    x = a[0] + (b[0] - a[0]) * t
                    break
            else:
                continue
            for side in (-1, 1):
                tile = (x + side * (river["width"] / 2 + rng.uniform(0.4, 0.9)), float(y))
                if abs(y - 29) < 5.5:
                    continue
                key = str(rng.choice(("reeds", "river_rocks", "fern")))
                self.add_prop(key, tile, f"bank:{y:g}:{side}")
        # Low rubble on the actual burned polygons, outside the broken deck.
        for feature in self.region["terrain"]["scorched"]:
            for index, tile in enumerate(feature["polygon"][::3]):
                if abs(tile[1] - 29) < 1.7:
                    continue
                self.add_prop("bridge_rubble", tile, f"damage:{feature['id']}:{index}",
                              height=19, authority=f"canonical scorch boundary {feature['id']}")

    def render_props(self, canvas: Image.Image) -> None:
        for prop in sorted(self.props, key=lambda p: (p["anchor_pixels"][1], p["id"])):
            image = self.prop_image(prop["key"], prop["height_pixels"])
            if prop["flip_horizontal"]:
                image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            x, y = prop["anchor_pixels"]
            # A local, translucent ground-contact shadow shares the source
            # art's upper-left light. No actor shadows are baked into scenery.
            if image.height >= 25:
                sw, sh = max(12, round(image.width * 0.7)), max(5, round(image.height * 0.11))
                shadow = Image.new("RGBA", (sw + 12, sh + 8))
                ImageDraw.Draw(shadow).ellipse((3, 1, sw + 3, sh + 1), fill=(24, 43, 29, 65))
                shadow = shadow.filter(ImageFilter.GaussianBlur(2))
                canvas.paste(shadow, (round(x - sw / 2 + 5), round(y - sh / 2)), shadow)
            canvas.paste(image, (round(x - image.width / 2), round(y - image.height)), image)

    def bridge(self, canvas: Image.Image) -> tuple[Image.Image, dict]:
        spec = self.recipe["bridge"]
        source = ROOT / "assets/source/terrain/overworld/elden_vale/composition/wide_bridge_generation.png"
        with Image.open(source) as raw:
            original_size = list(raw.size)
            image = raw.convert("RGBA")
        image.putalpha(image.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
        size = tuple(spec["uniform_resize"])
        if abs(size[0] / image.width - size[1] / image.height) > 1e-10:
            raise ValueError("Bridge stones must retain uniform source proportions")
        image = image.resize(size, Image.Resampling.NEAREST)
        bridge = Image.new("RGBA", (spec["physical_span_pixels"], size[1]))
        for crop, position in zip(spec["component_crops"], spec["component_positions_pixels"]):
            bridge.alpha_composite(image.crop(crop), tuple(position))
        # The source halves remain at their ONE uniform pixel scale. A longer
        # platform is explicitly assembled at each OUTER end, not obtained by
        # widening stones, repeating a fracture, or stretching the river/camera.
        # Full-height outer panel strips retain parapets/front masonry; the
        # additional deck courses have staggered joins over their outer seam.
        for column in spec["retained_outer_columns"]:
            side = ("west", "east").index(column["side"])
            a, b, c, d = column["crop"]
            x, y = column["position"]
            bounds = spec["retained_outer_source_bounds"][side]
            if not (bounds[0] <= a < c <= bounds[2] and bounds[1] <= b < d <= bounds[3]):
                raise ValueError("Additional bridge columns must be retained OUTER masonry")
            if not (0 <= x < x + c - a <= bridge.width and 0 <= y < y + d - b <= bridge.height):
                raise ValueError("Assembled bridge column leaves its physical canvas")
            west_x, east_x = [p[0] for p in spec["component_positions_pixels"]]
            if (side == 0 and x + c - a > west_x + 24) or (side == 1 and x < east_x + 92):
                raise ValueError("Outer-column assembly must not alter an inner broken face")
            bridge.alpha_composite(image.crop((a, b, c, d)), (x, y))
        deck = self.region["bridge"]["deck_rect_tiles"]
        left, deck_top = self.project.point(deck[:2])
        origin = [round(left), round(deck_top - spec["deck_top_in_component"])]
        canvas.paste(bridge, tuple(origin), bridge)
        alpha = np.asarray(bridge.getchannel("A"))
        empty = np.all(alpha == 0, axis=0)
        center = bridge.width // 2
        a = b = center
        while a > 0 and empty[a - 1]:
            a -= 1
        while b < bridge.width and empty[b]:
            b += 1
        if not 120 <= b - a <= 150:
            raise ValueError("Assembled bridge must retain a readable 120–150px central collapse")
        return bridge, {
            "world_anchor_tile": self.region["bridge"]["tile_position"],
            "deck_center_tile": self.recipe["bridge_tile"],
            "deck_rect_tiles": deck,
            "deck_rect_pixels": list(self.project.rect(deck)),
            "original_source_size": original_size,
            "uniform_source_scale": size[0] / original_size[0],
            "uniform_resize_pixels": list(size),
            "component_crops_after_uniform_scale": spec["component_crops"],
            "component_positions_pixels": spec["component_positions_pixels"],
            "assembled_abutment_width_pixels": spec["assembled_abutment_width_pixels"],
            "outer_extension_pixels": spec["outer_extension_pixels"],
            "retained_outer_source_bounds": spec["retained_outer_source_bounds"],
            "retained_outer_columns_after_uniform_scale": spec["retained_outer_columns"],
            "assembly_method": "New assembled art, not a simple crop export: copy retained outer masonry/parapet/arch-front columns 1:1 after the sole uniform source reduction, with split/staggered added cobble courses. Original inner jagged faces and approved runtime bridge images are unchanged.",
            "sprite_origin_pixels": origin, "sprite_size_pixels": list(bridge.size),
            "clear_deck_pixels": spec["deck_bottom_in_component"] - spec["deck_top_in_component"],
            "physical_span_tiles": spec["physical_span_tiles"],
            "physical_span_pixels": bridge.width,
            "transparent_gap_sprite_columns": [a, b],
            "transparent_gap_panorama_columns": [a + origin[0], b + origin[0]],
            "camera_zoom": 1,
            "framing_limitation": "480px viewport shows the central collapse, both broken abutment faces and inner portions of both damage parcels; the eastern terminal approach is partly cropped. Use the unscaled 960x480 bridge reference to inspect the whole 504px physical deck and both complete scorch parcels.",
            "note": spec["note"]
        }

    def render(self) -> tuple[Image.Image, Image.Image, dict]:
        canvas = self.ground()
        self.roads(canvas)
        self.river_and_damage(canvas)
        print("Composing bounded native vegetation and canonical farm/relief props...", flush=True)
        self.gather_props()
        self.render_props(canvas)
        bridge, bridge_metadata = self.bridge(canvas)
        # The same very light grade is applied once to the complete composition,
        # including props and bridge, rather than differently colored swatches.
        rgb = np.asarray(canvas).astype(np.float32)
        rgb = rgb * np.array((0.96, 0.97, 0.94)) + np.array((3, 2, 4))
        canvas = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
        stage = Image.new("L", self.size)
        draw = ImageDraw.Draw(stage)
        for rect in self.clear_rects:
            draw.rectangle(rect, fill=255)
        self.masks["actor_clearance"] = stage
        return canvas, bridge, bridge_metadata


def _font(size: int = 15) -> ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _label(draw: ImageDraw.ImageDraw, position: Point, text: str,
           fill: str = "#fff0c4", size: int = 15) -> None:
    x, y = position
    font = _font(size)
    box = draw.textbbox((x, y), text, font=font)
    draw.rectangle((box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3), fill="#233c36")
    draw.text((x, y), text, font=font, fill=fill)


def reference_rect(camera: list) -> list[int]:
    return [camera[0] - 240, camera[1] - 80, 960, 480]


def crop_rect(image: Image.Image, rect: list) -> Image.Image:
    x, y, w, h = rect
    if x < 0 or y < 0 or x + w > image.width or y + h > image.height:
        raise ValueError(f"Crop leaves opaque native canvas: {rect}")
    return image.crop((x, y, x + w, y + h))


def geographic_record(scenery: Scenery, bridge_metadata: dict) -> dict:
    region, project = scenery.region, scenery.project
    visible = []
    for road in region["roads"]:
        if scenery.stroke(road["points"], road["width"]).getbbox():
            visible.append(dict(road))
    fields = [dict(field) for field in region["terrain"]["fields"]
              if scenery.polygon(field["polygon"]).getbbox()]
    anchors = {
        "junction": [7, 4], "Eldenmere": region["town"]["tile_position"],
        "bridge_world_anchor": region["bridge"]["tile_position"],
        "bridge_deck_center": [-111, 29], "western_farm": [-36, 8],
        "relief_spur_join": [-70, 24], "relief_staging": [-68, 16],
        "east_approach": region["bridge"]["east_approach_tile"],
        "west_approach": region["bridge"]["west_approach_tile"]
    }
    return {
        "version": 1, "regional_source": REGION.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(REGION.read_bytes()),
        "projection": scenery.recipe["projection"],
        "canvas": list(scenery.size), "roads": visible, "fields": fields,
        "rivers": region["terrain"]["rivers"],
        "scorched": region["terrain"]["scorched"],
        "junction_arms": [
            {"road": "south_town_road", "direction": "N/slightly E", "toward": "Eldenmere"},
            {"road": "south_town_road", "direction": "WSW", "toward": "western bridge"},
            {"road": "southern_land_corridor", "direction": "SSE", "toward": "southern farms"}
        ],
        "anchors": {key: {"tile": tile, "pixel": list(project.point(tile))}
                    for key, tile in anchors.items()},
        "bridge": bridge_metadata,
          "mask_contract": "Native L-mode 0/255 masks retain exact projected source roads/fields/river/scorch before cosmetic feathering. actor_clearance and worn_verge_variation are explicitly nongeographic authoring reservations, not new roads or changes to region.json.",
        "masks": {key: {"file": f"masks/{key}.png", "mode": image.mode,
                    "canvas": list(image.size), "rgba_sha256": pixel_sha256(image),
                    "authority": "authoring reservation, not regional geometry" if key in
                             ("actor_clearance", "worn_verge_variation") else "region.json"}
                  for key, image in scenery.masks.items()},
        "route": scenery.route
    }


def review_images(panorama: Image.Image, scenery: Scenery, geometry: dict,
                  manifest: dict) -> dict[Path, Image.Image]:
    products = {}
    start = manifest["camera_junction"]
    finish = manifest["camera_bridge"]
    junction_rect = manifest["reference_scene"]["rect_pixels"]
    bridge_rect = manifest["bridge_reference"]["rect_pixels"]
    products[REVIEW / "crossroads_native.png"] = crop_rect(panorama, [*start, 480, 320])
    products[REVIEW / "crossroads_reference.png"] = crop_rect(panorama, junction_rect)
    products[REVIEW / "bridge_native.png"] = crop_rect(panorama, [*finish, 480, 320])
    products[REVIEW / "bridge_wide.png"] = crop_rect(panorama, bridge_rect)
    annotated = crop_rect(panorama, junction_rect)
    draw = ImageDraw.Draw(annotated)
    cx, cy = start[0] - junction_rect[0], start[1] - junction_rect[1]
    draw.rectangle((cx, cy, cx + 479, cy + 319), outline="#f8eab9", width=2)
    draw.rectangle((cx + 12, cy + 10, cx + 468, cy + 98), outline="#7acbd0", width=1)
    _label(draw, (16, 12), "NATIVE 960x480 CROP - exact three-arm junction; no actors baked")
    _label(draw, (cx + 18, cy + 16), "caption safe area", fill="#9cdee2", size=13)
    for key, position in manifest["actor_anchors"].items():
        x, y = position[0] - junction_rect[0], position[1] - junction_rect[1]
        width, height, anchor_y = (300, 144, 136) if key == "parked_caravan" else (80, 96, 92)
        draw.rectangle((x - width / 2, y - anchor_y, x + width / 2, y - anchor_y + height),
                       outline="#f3d28a", width=1)
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill="#fff2bd")
        _label(draw, (x - 30, y + 15), key, size=13)
    _label(draw, (20, 444), "Boxes/anchor dots are review annotations ONLY. Wagon is parked mostly outside the 480px shot.", size=14)
    products[REVIEW / "crossroads_staging.png"] = annotated

    geography = crop_rect(panorama, junction_rect)
    draw = ImageDraw.Draw(geography)
    for road_id, color in (("south_town_road", "#ffe2a5"), ("southern_land_corridor", "#d6ae81")):
        road = next(r for r in scenery.region["roads"] if r["id"] == road_id)
        points = [(scenery.project.point(p)[0] - junction_rect[0],
                   scenery.project.point(p)[1] - junction_rect[1]) for p in road["points"]]
        draw.line(points, fill=color, width=2)
    jx, jy = scenery.project.point((7, 4))
    jx, jy = jx - junction_rect[0], jy - junction_rect[1]
    draw.ellipse((jx - 7, jy - 7, jx + 7, jy + 7), outline="#fff0c2", width=2)
    _label(draw, (18, 12), "GEOGRAPHY AUDIT: junction (7,4); three arms, not four")
    _label(draw, (jx - 158, 52), "Stone N/slightly E to Eldenmere", size=14)
    _label(draw, (32, jy + 58), "Stone WSW to bridge | width 2.5 tiles", size=14)
    _label(draw, (jx + 104, jy + 78), "Rutted dirt SSE | width 1.9 tiles", size=14)
    _label(draw, (18, 444), "No river at this intersection. All centerlines are the region's existing densified points.", size=14)
    products[REVIEW / "geography_junction.png"] = geography

    audit = crop_rect(panorama, bridge_rect)
    draw = ImageDraw.Draw(audit)
    for parcel in scenery.region["terrain"]["scorched"]:
        points = [(scenery.project.point(p)[0] - bridge_rect[0],
                   scenery.project.point(p)[1] - bridge_rect[1]) for p in parcel["polygon"]]
        draw.line(points + points[:1], fill="#f2a68a", width=2)
    deck = geometry["bridge"]["deck_rect_pixels"]
    rect = (deck[0] - bridge_rect[0], deck[1] - bridge_rect[1],
            deck[2] - bridge_rect[0], deck[3] - bridge_rect[1])
    draw.rectangle(rect, outline="#f8e9b5", width=2)
    x, y = finish[0] - bridge_rect[0], finish[1] - bridge_rect[1]
    draw.rectangle((x, y, x + 479, y + 319), outline="#75d7df", width=2)
    _label(draw, (18, 12), "FIXED-SCALE BRIDGE: deck y=29, world anchor y=30; river runs N/S")
    _label(draw, (18, 42), "18 tiles x 28px = 504px span | 3 tiles x 24px = 72px clear deck", size=14)
    a, b = geometry["bridge"]["transparent_gap_sprite_columns"]
    _label(draw, (18, 69), f"New assembled art: 200px abutments | {b - a}px collapse | unchanged inner broken faces", size=14)
    _label(draw, (18, 427), "Peach: exact scorched parcels on BOTH banks. Cyan: native 480x320 endpoint (terminal approaches partly cropped).", size=13)
    _label(draw, (18, 451), "Retained outer masonry + staggered cobble columns; one stone pixel scale, no source repaint or camera zoom.", size=13)
    products[REVIEW / "geography_bridge.png"] = audit

    # This downsample is review-only and is never an illustration input.
    scale = 0.25
    overview = panorama.resize((round(panorama.width * scale), round(panorama.height * scale)),
                               Image.Resampling.LANCZOS)
    diagram = Image.new("RGB", (overview.width, overview.height + 112), "#233c36")
    diagram.paste(overview, (0, 66))
    draw = ImageDraw.Draw(diagram)
    _label(draw, (14, 10), "ELDEN VALE - native crossroads corridor geographic audit", size=20)
    _label(draw, (14, 39), "E right / S down | 28x24px per tile | one projection; original region unchanged", size=14)
    map_overlay = Image.new("RGBA", overview.size)
    map_draw = ImageDraw.Draw(map_overlay)
    for road in scenery.region["roads"]:
        points = [(scenery.project.point(p)[0] * scale, scenery.project.point(p)[1] * scale)
                  for p in road["points"]]
        map_draw.line(points, fill="#f1d6a0" if road["kind"] == "stone" else "#bf9d73", width=1)
    path = [(x * scale + 240 * scale, y * scale + 160 * scale)
            for x, y in manifest["camera_path"]]
    map_draw.line(path, fill="#83d7dd", width=2)
    for camera in (start, finish):
        x, y = camera[0] * scale, camera[1] * scale
        map_draw.rectangle((x, y, x + 480 * scale, y + 320 * scale), outline="#fbedc0", width=2)
    overview = overview.convert("RGBA")
    overview.alpha_composite(map_overlay)
    diagram.paste(overview.convert("RGB"), (0, 66))
    labels = [("junction", "(7,4) THREE-WAY", -90, -44),
              ("western_farm", "canonical western farm", -100, -58),
              ("relief_staging", "relief spur / loading yard", -100, -45),
              ("bridge_deck_center", "broken bridge (-111,29)", -95, 55)]
    for key, text, dx, dy in labels:
        p = geometry["anchors"][key]["pixel"]
        x, y = p[0] * scale, p[1] * scale + 66
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill="#fff0c0")
        _label(draw, (max(8, min(diagram.width - 255, x + dx)), y + dy), text, size=13)
    town = geometry["anchors"]["Eldenmere"]["pixel"]
    _label(draw, (town[0] * scale - 150, 73), "Eldenmere (12,-28): at north edge", size=13)
    _label(draw, (14, diagram.height - 30),
           f"Actual road arc: {manifest['route_length_tiles']:.3f} tiles. Blue: camera-center track. White: native endpoint viewports.", size=14)
    products[REVIEW / "geography_overview.png"] = diagram

    strip = Image.new("RGB", (1920, 516), "#233c36")
    draw = ImageDraw.Draw(strip)
    for column, (tile, title) in enumerate((([-36, 9], "Canonical western farm / field access"),
                                          ([-69, 20], "Relief staging spur, same physical scale"),
                                          ([-52, 29], "Western grain lower / stone-road curve"))):
        point = scenery.project.point(tile)
        rect = [round(point[0] - 320), round(point[1] - 240), 640, 480]
        strip.paste(crop_rect(panorama, rect), (column * 640, 36))
        _label(draw, (column * 640 + 10, 10), title, size=14)
    products[REVIEW / "geography_corridor.png"] = strip
    return products


def build_products(recipe: dict) -> tuple[dict[Path, bytes], dict]:
    sources = verified_inputs(recipe)
    region = json.loads(REGION.read_text())
    scenery = Scenery(recipe, region)
    panorama, bridge, bridge_metadata = scenery.render()
    route = scenery.route
    actors = scenery.actors
    manifest = {
        "version": 1, "id": "regent_crossroads", "scene": "crossroads",
        "canvas": recipe["canvas"], "viewport": recipe["viewport"],
        "background": "panorama.png", "opaque": True,
        "decoded_rgba_bytes": panorama.width * panorama.height * 4,
        "background_rgba_sha256": pixel_sha256(panorama),
        "regional_source": REGION.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(REGION.read_bytes()),
        "projection": {**recipe["projection"],
                       "equations": ["px=(tile_x-origin_x)*sx+offset_x", "py=(tile_y-origin_y)*sy+offset_y"],
                       "inverse": ["tile_x=(px-offset_x)/sx+origin_x", "tile_y=(py-offset_y)/sy+origin_y"],
                       "orientation": "east-right, south-down; no local projection/zoom overrides"},
        "junction_tile": recipe["junction_tile"], "bridge_tile": recipe["bridge_tile"],
        "bridge_world_anchor_tile": region["bridge"]["tile_position"],
        "bridge_tile_note": "bridge_tile is the actual road/deck center (-111,29); canonical prop/world anchor is (-111,30).",
        **route,
        "actor_anchors": actors,
        "actor_anchors_screen_junction": recipe["actors_screen"],
        "actor_tiles": {key: [round(v, 8) for v in scenery.project.inverse(point)] for key, point in actors.items()},
        "actor_anchor_semantics": "Absolute panorama foot anchors, native 80x96 humans with [40,92] registration; carrier maps to the parent's local actor. Parked caravan uses existing native 300x144 / [150,136] registration. No actor images were read or baked.",
        "actor_clearance_rect_pixels": [list(rect) for rect in scenery.clear_rects],
        "actor_foot_probes": {"human_relative_rect_pixels": [-11, -4, 22, 8],
                      "parked_caravan_relative_rect_pixels": [-145, -12, 290, 15],
                      "note": "All foot-probe corners remain outside canonical road widths; complete visible sprite rectangles are reserved against baked prop artwork. These are authoring clearances, not runtime collision overrides."},
        "caption_safe_rect_viewport": [12, 10, 456, 88],
        "parked_caravan_note": "Anchor [600,265] relative to start viewport; mostly offscreen on safe east verge. Full sprite starts at viewport x450, clear of the three conversation bodies. Optional, not a baked wagon.",
        "reference_scene": {"image": "reference_scene.png", "rect_pixels": reference_rect(route["camera_junction"]),
                            "canvas": [960, 480], "camera_junction": [240, 80],
                            "actor_anchors": {key: [point[0] - route["camera_junction"][0] + 240,
                                                     point[1] - route["camera_junction"][1] + 80]
                                              for key, point in actors.items()}},
        "bridge_reference": {"image": "bridge_reference.png", "rect_pixels": reference_rect(route["camera_bridge"]),
                             "canvas": [960, 480], "camera_bridge": [240, 80], "zoom": 1},
        "bridge": bridge_metadata,
        "depth_layers": [], "foreground": None,
        "source_recipe": RECIPE.relative_to(ROOT).as_posix(),
        "source_provenance": (SOURCE / "provenance.json").relative_to(ROOT).as_posix(),
        "geography_review": (REVIEW / "geography_overview.png").relative_to(ROOT).as_posix(),
        "authoring": "Offline retained-raw-source quilting, bounded transparent composition and exact regional masks. Only the new bridge is assembled with additional retained outer masonry/parapet/arch-front columns and staggered cobble courses after one uniform source reduction, not a simple crop export; original runtime bridge images are unchanged. Water uses a calm raw riverbank sample with recorded contrast/color treatment. No imagegen tool used; no atlas/map or tiny runtime tile enlargement.",
        "integration": "Parent must opt in to scene crossroads, this manifest background and camera track. Existing scene, renderer, actors, exporters and music are untouched.",
        "limitations": ["This fixed-scale oblique ground-plane illustration has no invented horizon or perspective vanishing point.",
                        "The native bridge shot partly crops terminal approaches; inspect bridge_reference for both complete bank-damage parcels and the full physical span.",
                        "Retained farm motifs are stylized; their registered source positions are canonical, but their decorative silhouettes are not collision footprints.",
                        "Static vegetation is baked into the opaque ground composition; no foreground/depth parallax is claimed."]
    }
    geometry = geographic_record(scenery, bridge_metadata)
    images = {
        OUTPUT / "panorama.png": panorama,
        OUTPUT / "reference_scene.png": crop_rect(panorama, manifest["reference_scene"]["rect_pixels"]),
        OUTPUT / "bridge_reference.png": crop_rect(panorama, manifest["bridge_reference"]["rect_pixels"]),
        SOURCE / "bridge_components.png": bridge,
        SOURCE / "water_sample.png": scenery.materials.source("water")
    }
    for key, mask in scenery.masks.items():
        images[SOURCE / "masks" / f"{key}.png"] = mask
    images.update(review_images(panorama, scenery, geometry, manifest))
    provenance = {
        "version": 1, "method": recipe["method"], "seed": recipe["seed"],
        "tool": "tools/build_regent_crossroads.py",
        "tool_sha256": sha256(Path(__file__).read_bytes()),
        "recipe_sha256": sha256(RECIPE.read_bytes()),
        "dependencies": {"Pillow": "13.0.0", "numpy": ">=2,<3"},
        "source_records": sources, "materials": recipe["materials"],
        "material_sampling": "Raw bounded crop, uniform nearest reduction (<=1), three-candidate minimum-error overlap quilting. Only water has the explicitly recorded per-channel mean-centered contrast reduction and RGB multiply before quilting. Source crop positions/flips are recorded in material_samples.json; no repeating 24px tile is loaded.",
        "material_samples": "material_samples.json", "prop_crops": scenery.prop_sources,
        "prop_placements": sorted(scenery.props, key=lambda p: p["id"]),
        "geography": "geometry.json", "bridge": bridge_metadata,
        "color_grade": {"rgb_multiply": [0.96, 0.97, 0.94], "rgb_add": [3, 2, 4]},
        "sample_anchors": {
            "stone_road": [[7, 4], [-15, 11], [-42, 17], [-70, 24], [-98, 28]],
            "dirt_sse": [[14, 12], [20, 21]],
            "western_river": [[-116, 8], [-111, 30], [-113, 40]],
            "grain_lower": [[-54, 29]],
            "bridge_banks": [[-122, 29], [-102, 29]]
        },
        "image_products": {p.relative_to(ROOT).as_posix(): {"canvas": list(image.size),
                            "mode": image.mode, "rgba_sha256": pixel_sha256(image)}
                           for p, image in images.items()},
        "checks": "Inputs are pinned by original SHA256. PNG --check accepts identical decoded RGBA when PNG compression differs; JSON must match exactly. Normal local builds use deterministic compression and retain already-identical files."
    }
    provenance["panorama_sample_probes"] = [
        {"surface": key, "tile": tile, "pixel": [round(v) for v in scenery.project.point(tile)],
         "rgb": list(panorama.getpixel(tuple(round(v) for v in scenery.project.point(tile))))}
        for key, tiles in provenance["sample_anchors"].items() for tile in tiles
    ]
    products = {path: png_bytes(image) for path, image in images.items()}
    products[OUTPUT / "manifest.json"] = json_bytes(manifest)
    products[SOURCE / "geometry.json"] = json_bytes(geometry)
    products[SOURCE / "material_samples.json"] = json_bytes(scenery.materials.samples)
    products[SOURCE / "provenance.json"] = json_bytes(provenance)
    return products, manifest


def allowed_product(path: Path) -> bool:
    if path.is_relative_to(SOURCE) or path.is_relative_to(OUTPUT):
        return True
    return (path.parent == REVIEW and path.suffix == ".png" and
            path.name.startswith(("geography", "crossroads", "bridge")))


def equivalent_png(existing: bytes, generated: bytes) -> bool:
    try:
        with Image.open(BytesIO(existing)) as a, Image.open(BytesIO(generated)) as b:
            return a.size == b.size and a.convert("RGBA").tobytes() == b.convert("RGBA").tobytes()
    except (OSError, ValueError):
        return False


def validate_contract(manifest: dict, recipe: dict, region: dict) -> None:
    width, height = manifest["canvas"]
    if width * height * 4 > 50_000_000:
        raise ValueError("Decoded RGBA panorama exceeds the 50MB bound")
    for point in manifest["camera_path"]:
        if not (0 <= point[0] <= width - 480 and 0 <= point[1] <= height - 320):
            raise ValueError("A native viewport leaves the panorama")
    if any(b[0] >= a[0] for a, b in zip(manifest["camera_path"], manifest["camera_path"][1:])):
        raise ValueError("Camera arc samples must move monotonically west")
    for key, point in manifest["actor_tiles"].items():
        for road in region["roads"]:
            if distance_to_polyline(tuple(point), road["points"]) < road["width"] / 2 + 0.18:
                raise ValueError(f"Actor anchor intrudes on canonical carriageway: {key}")
    if manifest["bridge"]["clear_deck_pixels"] != region["bridge"]["deck_width_tiles"] * recipe["projection"]["pixels_per_tile"][1]:
        raise ValueError("Bridge source deck and canonical projected width disagree")


def build(check: bool = False) -> dict:
    recipe = json.loads(RECIPE.read_text())
    products, manifest = build_products(recipe)
    validate_contract(manifest, recipe, json.loads(REGION.read_text()))
    stale = []
    same_pixels = []
    for path, content in products.items():
        if not allowed_product(path):
            raise ValueError(f"Write outside new scenery ownership: {path}")
        existing = path.read_bytes() if path.exists() else None
        equal_pixels = (existing is not None and path.suffix == ".png" and
                        existing != content and equivalent_png(existing, content))
        if check:
            if existing != content and not equal_pixels:
                stale.append(path.relative_to(ROOT).as_posix())
            elif equal_pixels:
                same_pixels.append(path.relative_to(ROOT).as_posix())
        elif existing != content and not equal_pixels:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if stale:
        raise SystemExit("Stale crossroads outputs: " + ", ".join(stale))
    if same_pixels:
        print(f"Accepted {len(same_pixels)} PNG compression-only differences (decoded RGBA identical).")
    print(f"{'Verified' if check else 'Built'} {len(products)} isolated scenery outputs; "
          f"{manifest['canvas'][0]}x{manifest['canvas'][1]}, {len(manifest['camera_path'])} native camera samples; "
          f"actual road arc {manifest['route_length_tiles']:.6f} tiles.")
    print(f"Junction camera {manifest['camera_junction']}; bridge camera {manifest['camera_bridge']}; "
          f"decoded RGBA {manifest['decoded_rgba_bytes']:,} bytes.")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only regeneration; compare decoded PNG pixels and exact JSON")
    build(parser.parse_args().check)