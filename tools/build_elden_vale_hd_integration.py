#!/usr/bin/env python3
"""Build explicit regional HD bindings without changing active map geometry.

The staged foundation remains immutable. Selected vegetation is uniformly sampled
from one union crop shared by its idle, moving frames and fixed layers. Logical
canvases, feet and collision ownership stay with the existing regional consumers.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from io import BytesIO
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.elden_vale_landmark_bindings import regional_bindings
FOUNDATION = ROOT / "assets/terrain/overworld/elden_vale/hd/art.json"
OUTPUT = ROOT / "assets/maps/overworld/elden_vale/hd_integration"
SOURCE = ROOT / "assets/source/maps/overworld/elden_vale/hd_integration"

PLANT_ALIASES = {
    "tree_broadleaf": "broadleaf_full",
    "oak_a": "broadleaf_full",
    "oak_b": "broadleaf_spreading",
    "oak_c": "broadleaf_weathered",
    "tree_conifer": "conifer_spruce",
    "conifer_a": "conifer_spruce",
    "conifer_b": "conifer_fir",
    "orchard_tree": "orchard_red_fruit",
    "sapling": "woodland_sparse",
    "shrub": "shrub_rounded",
    "fern": "fern_splayed",
    "log": "fallen_log_weathered",
    "stump": "stump_mossy",
    "flowers_a": "flowers_white",
    "flowers_b": "flowers_violet",
    "grass_tuft": "grass_sparse",
    "reeds": "tall_reeds_splayed",
    "rock": "boulder_rounded",
    "river_rocks": "boulder_mossy",
}

MATERIAL_ALIASES = {
    "grass": "lawn_00",
    "grass_lush": "lawn_01",
    "grass_meadow": "meadow_00",
    "pasture": "meadow_00",
    "orchard_grass": "sheltered_00",
    "forest_floor": "sheltered_00",
    "dirt": "dirt_00",
    "cart_earth": "dirt_01",
}


def json_bytes(value):
    return (json.dumps(value, indent=2) + "\n").encode()


def png_bytes(image):
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def read_rgba(path):
    with Image.open(path) as original:
        image = original.convert("RGBA")
    if set(image.getchannel("A").tobytes()) - {0, 255}:
        raise ValueError(f"Donor alpha is not binary: {path}")
    return image


def union_bounds(images):
    boxes = [image.getbbox() for image in images]
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        raise ValueError("Vegetation donor is empty")
    return (min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes))


def registered_frames(donor_images, logical_size):
    """Use one occupied envelope, scale and registration for every donor state."""
    target = tuple(2 * value for value in logical_size)
    union = union_bounds(donor_images)
    width, height = union[2] - union[0], union[3] - union[1]
    # Two artwork pixels retain contour room while keeping the supporting roots
    # at one logical unit inside the consumer's original bounding canvas.
    scale = min((target[0] - 4) / width, (target[1] - 4) / height)
    sampled = (max(1, round(width * scale)), max(1, round(height * scale)))
    origin = ((target[0] - sampled[0]) // 2, target[1] - 2 - sampled[1])
    result = []
    for source in donor_images:
        image = source.crop(union).resize(sampled, Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", target)
        canvas.alpha_composite(image, origin)
        result.append(canvas)
    return result, {"union_crop_artwork": list(union), "uniform_scale": scale,
                    "sampled_size_artwork": list(sampled),
                    "origin_artwork": list(origin), "contour_padding_artwork": 2}


def layout_reservations():
    return {
        "status": "foundation layout recommendations; no active map mutation",
        "coordinate_space": "regional logical tiles except explicit detailed-scene support",
        "six_area_roles": [
            {"id": "home_meadows", "anchor_tile": [12, -28],
             "preserve": ["town entry and exit", "familiar inhabited meadows"]},
            {"id": "southern_farms", "anchor_tile": [-15, 51],
             "preserve": ["farmyards", "orchard aisles", "work stations", "southern caravan road"]},
            {"id": "western_bridge_road", "anchor_tile": [-98, 28],
             "preserve": ["destroyed crossing", "crew work", "independent bridge repair flag"]},
            {"id": "central_causeway", "anchor_tile": [-3, 8],
             "preserve": ["existing main stone-road alignment", "no boundary crossing"]},
            {"id": "northern_woodland", "anchor_tile": [8, -64],
             "preserve": ["millrace relationship", "woodland loop", "checkpoint route"]},
            {"id": "sanctuary_ridge", "anchor_tile": [90, -66],
             "preserve": ["existing spur", "automatic reserve contact", "return landing", "grove"]},
        ],
        "causeway": {
            "existing_road": "south_town_road",
            "alignment_tiles": [[10, -1], [7, 4], [-3, 8], [-15, 11], [-28, 14]],
            "suggested_clearance_width_tiles": 4,
            "optional_meadow_clearing_tiles": [-8, 2, 20, 14],
            "collision": "none added; signature ruins belong to the landmark integration",
        },
        "pale_antlers": {
            "overhead_envelope_tiles": [44, -86, 64, 43],
            "collision": "none for overhead envelope; preserve intended walkable ground",
            "regional_support_candidate_prop_ids": ["sanctuary_ledge_5", "sanctuary_upper_outcrop"],
            "regional_support_policy": "Existing solid contacts only; do not turn the walkable hill into a solid zone.",
            "viewpoints_tiles": [[12, -25], [42, -45], [69, -55], [90, -62]],
            "distant_presentation": "Separate later distant layer; do not clear a town-to-ridge forest corridor.",
            "detailed_support_reference": {
                "file": "assets/source/terrain/overworld/elden_vale/signature_landscape_hd/layout_plan.json",
                "space": "detailed Sanctuary logical coordinates, not regional tiles",
            },
        },
        "boundaries": "Keep both unnamed rivers, walls, closed gates and ruined western bridge; no new crossing.",
    }


def build(check=False):
    foundation = json.loads(FOUNDATION.read_text())
    products = {}
    dependencies = {}

    def depend(path):
        dependencies[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()

    depend(FOUNDATION)
    depend(Path(__file__))
    plants = {record["id"]: record for record in foundation["vegetation"]}
    manifest = {
        "version": 1,
        "id": "elden_vale.hd.foundation.integration",
        "integration_status": "integrated",
        "integration_scope": "Selected regional terrain and scenery bindings; other banks retain their own migration state.",
        "artwork_pixels_per_world_pixel": 2,
        "logical_tile_size": [24, 24],
        "path_space": "repository_relative",
        "anchor_space": "logical",
        "visual_approval": foundation["visual_approval"],
        "source_pack": FOUNDATION.relative_to(ROOT).as_posix(),
        "source_pack_integration_status": foundation["integration_status"],
        "geometry_owner": "assets/maps/overworld/elden_vale/region.json",
        "tiles": deepcopy(foundation["tiles"]),
        "props": deepcopy(foundation["props"]),
    }
    for kind in ("tiles", "props"):
        for record in manifest[kind].values():
            depend(ROOT / record["image"])
            record["collision"] = "existing regional geometry; never derived from image alpha"

    shared_materials = ROOT / "assets/terrain/eldenmere/grass_dirt_hd/materials"
    for alias, material in MATERIAL_ALIASES.items():
        path = shared_materials / f"{material}.png"
        depend(path)
        manifest["tiles"][alias] = {
            **manifest["tiles"][alias],
            "image": path.relative_to(ROOT).as_posix(),
            "source_material": material,
            "logical_size": [24, 24],
            "artwork_pixels_per_world_pixel": 2,
        }

    registrations = {}
    for alias, donor_id in PLANT_ALIASES.items():
        legacy = foundation["props"][alias]
        donor = plants[donor_id]
        source_paths = [ROOT / donor["idle"]]
        source_paths.extend(ROOT / frame["file"] for frame in donor["frames"])
        layer_names = [layer for layer in ("fixed", "backing") if donor.get(layer)]
        source_paths.extend(ROOT / donor[layer] for layer in layer_names)
        for path in source_paths:
            depend(path)
        source_images = [read_rgba(path) for path in source_paths]
        if len({image.size for image in source_images}) != 1:
            raise ValueError(f"Donor states do not share a canvas: {donor_id}")
        frames, registration = registered_frames(source_images, legacy["logical_size"])
        folder = OUTPUT / "vegetation" / alias
        idle_path = folder / "idle.png"
        products[idle_path] = png_bytes(frames[0])
        paths = []
        for index in range(len(donor["frames"])):
            path = folder / f"frame_{index:02}.png"
            products[path] = png_bytes(frames[index + 1])
            paths.append(path.relative_to(ROOT).as_posix())
        layer_paths = {}
        for index, layer in enumerate(layer_names, 1 + len(donor["frames"])):
            path = folder / f"{layer}.png"
            products[path] = png_bytes(frames[index])
            layer_paths[layer] = path.relative_to(ROOT).as_posix()
        record = {
            **legacy,
            "image": idle_path.relative_to(ROOT).as_posix(),
            "frames": paths,
            "frame_duration_ms": 600,
            "reduced_motion_frame": 0,
            "reduced_motion_image": idle_path.relative_to(ROOT).as_posix(),
            "artwork_pixels_per_world_pixel": 2,
            "foot_anchor": deepcopy(legacy["foot_anchor"]),
            "source_plant": donor_id,
            "source_manifest": FOUNDATION.relative_to(ROOT).as_posix(),
            "animation_kind": donor.get("animation_kind", "static"),
            "interaction_cues": False,
            "collision": "existing regional geometry; never derived from image alpha",
            **layer_paths,
        }
        manifest["props"][alias] = record
        registrations[alias] = {
            "source_plant": donor_id,
            "logical_size": legacy["logical_size"],
            "foot_anchor": legacy["foot_anchor"],
            "source_paths": [path.relative_to(ROOT).as_posix() for path in source_paths],
            "animation_frames": len(paths),
            **registration,
        }

    landmarks,signature_props=regional_bindings(products,depend,png_bytes)
    manifest['landmarks']=landmarks
    manifest['props'].update(signature_props)
    manifest['signature_integration']='Pale Antlers and Sanctuary miniature; original staged bank retained'
    # This registry cannot replace actors/effects or the separately owned reserve icon.
    forbidden = {"guard_front", "guard_back", "bird_1", "bird_2", "sheep_1", "sheep_2",
                 "butterfly_1", "butterfly_2", "smoke_1", "smoke_2"}
    if forbidden.intersection(manifest["props"]):
        raise ValueError("Integration bindings resurrect a separately owned actor/effect")
    products[OUTPUT / "manifest.json"] = json_bytes(manifest)
    products[SOURCE / "layout_reservations.json"] = json_bytes(layout_reservations())
    products[SOURCE / "recipe.json"] = json_bytes({
        "id": manifest["id"],
        "dependencies_sha256": dependencies,
        "selected_bindings": {"tiles": len(manifest["tiles"]), "props": len(manifest["props"])},
        "method": "Immutable staged foundation plus shared HD materials and common-union vegetation registration",
        "density": 2,
        "registrations": registrations,
        "material_aliases": MATERIAL_ALIASES,
        "geometry": "Existing logical canvases/foot anchors retained; no map or collision mutation by this builder.",
        "exclusions": sorted(forbidden),
    })
    stale = []
    for path, data in products.items():
        if check:
            if not path.exists() or path.read_bytes() != data:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if stale:
        raise SystemExit("Stale HD integration exports: " + ", ".join(stale))
    print(f"{'Verified' if check else 'Exported'} {len(products)} integration products; "
          f"{len(manifest['tiles'])} tiles, {len(manifest['props'])} props, "
          f"{len(registrations)} adapted plant aliases")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    build(parser.parse_args().check)
