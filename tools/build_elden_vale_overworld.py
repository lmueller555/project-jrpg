"""Build the vector region manifest and a separate atlas survey reference.

The approved classroom map is read-only. This tool exports no runtime terrain
PNG, chunk image, collision mask, town link, or change to existing game assets.
Geometry remains in tiles; normalized atlas anchors are provenance, not scale.
"""
from __future__ import annotations

import argparse
from collections import deque
from copy import deepcopy
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/maps/overworld/elden_vale/recipe.json"
OUTPUT = ROOT / "assets/maps/overworld/elden_vale/region.json"
REFERENCE = ROOT / "docs/reviews/elden_vale_composition/atlas_reference.png"


def smooth_road(points, steps=6):
    """Densify a hand-authored route, retaining each purposeful junction.

    The cubic Hermite interpolation uses short tangents to avoid loops
    around tight bends. Its output is the single source for paint, clearances,
    the regional map and walking-time validation, rather than a visual-only
    curve that would disagree with collision or travel measurements.
    """
    if len(points) < 3 or steps < 2:
        return deepcopy(points)
    result = [list(points[0])]
    for index, (a, b) in enumerate(zip(points, points[1:])):
        previous = points[max(0, index-1)]
        following = points[min(len(points)-1, index+2)]
        for sample in range(1, steps+1):
            t = sample/steps
            h00 = 2*t**3-3*t**2+1
            h10 = t**3-2*t**2+t
            h01 = -2*t**3+3*t**2
            h11 = t**3-t**2
            # A shortened tangent gives broad countryside curves and keeps
            # bridge approaches from overshooting the authored crossing.
            point = [h00*a[axis]+h10*(b[axis]-previous[axis])*.35+
                     h01*b[axis]+h11*(following[axis]-a[axis])*.35
                     for axis in (0, 1)]
            result.append([round(value, 4) for value in point])
    return result


def _distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length2 = dx * dx + dy * dy
    t = 0 if not length2 else max(0, min(1, ((point[0] - start[0]) * dx +
                                           (point[1] - start[1]) * dy) / length2))
    return math.hypot(point[0] - start[0] - t * dx,
                      point[1] - start[1] - t * dy), t


def _inside(point, rect):
    x, y, width, height = rect
    return x <= point[0] < x + width and y <= point[1] < y + height


def _road_distance(road, target):
    best = (math.inf, 0.0)
    travelled = 0.0
    for start, end in zip(road["points"], road["points"][1:]):
        distance, ratio = _distance(target, start, end)
        length = math.dist(start, end)
        if distance < best[0]:
            best = distance, travelled + ratio * length
        travelled += length
    if best[0] > road["width"] / 2:
        raise ValueError("Bridge approach target does not lie on its authored road")
    return best[1]


def _blocked(data, point, repaired=False):
    bridge = data["bridge"]
    on_deck = repaired and _inside(point, bridge["deck_rect_tiles"])
    if not on_deck:
        for river in data["terrain"]["rivers"]:
            if any(_distance(point, a, b)[0] <= river["width"] / 2
                   for a, b in zip(river["points"], river["points"][1:])):
                return True
    if not repaired and _inside(point, bridge["damage_rect_tiles"]):
        return True
    for wall in data["walls"]:
        if abs(point[1] - wall["y"]) <= 1 and wall["x0"] <= point[0] <= wall["x1"]:
            if not wall["gate_x"] - wall["gate_width"] / 2 <= point[0] < wall["gate_x"] + wall["gate_width"] / 2:
                return True
    # A clearance flag alone never releases an unauthored destination.
    return any(_inside(point, gate["rect_tiles"]) for gate in data["gates"])


def _flood(data, repaired=False):
    bounds = data["bounds_tiles"]
    spawn = tuple(data["spawn_tile"])
    if _blocked(data, spawn, repaired):
        raise ValueError("Spawn is blocked by authored vector geometry")
    reached = {spawn}
    pending = deque([spawn])
    tested = {spawn}
    while pending:
        x, y = pending.popleft()
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if point in tested or not _inside(point, bounds):
                continue
            tested.add(point)
            if not _blocked(data, point, repaired):
                reached.add(point)
                pending.append(point)
    return reached


def validate(data):
    if data["version"] != 1 or data["kind"] != "overworld":
        raise ValueError("Unsupported Elden Vale manifest version/kind")
    if data["tile_size"] != 24 or data["chunk_size"] != 16:
        raise ValueError("The authored layout requires 24px tiles and 16-tile chunks")
    if data["bounds_tiles"] != [-256, -192, 512, 384]:
        raise ValueError("Stable global tile bounds changed")
    for category in (data["terrain"]["rivers"], data["roads"], data["walls"],
                     data["gates"], data["landmarks"]):
        ids = [record["id"] for record in category]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate geometry identity")
    for river in data["terrain"]["rivers"]:
        if river["width"] <= 0 or len(river["points"]) < 2:
            raise ValueError("River requires positive width and a continuous polyline")
    crops = {"grain", "vegetables", "fallow", "pasture", "orchard"}
    for field in data["terrain"].get("fields", []):
        if field.get("crop") not in crops or len(field["polygon"]) < 3:
            raise ValueError("A field needs an explicit crop and parcel outline")
    if not {"stone", "cart", "foot"} <= {road.get("kind") for road in data["roads"]}:
        raise ValueError("Regional roads require a readable surface hierarchy")
    if any(road["width"] < 1.15 or len(road["points"]) < 2 for road in data["roads"]):
        raise ValueError("A route is too narrow for the regional player probe")
    setpieces = data.get("setpieces", [])
    if sum(piece.get("kind") == "farmstead" for piece in setpieces) < 3:
        raise ValueError("The environment pass requires three composed farmsteads")
    identifiers = [prop["id"] for piece in setpieces for prop in piece.get("props", [])]
    identifiers.extend(prop["id"] for prop in data.get("decorations", []))
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Authored props must have unique identities")
    for piece in setpieces:
        if not piece.get("approach_tile") or not piece.get("review"):
            raise ValueError("A composed scene needs a walkable approach and review camera")
    for wall in data["walls"]:
        for endpoint in ((wall["x0"], wall["y"]), (wall["x1"], wall["y"])):
            if not any(any(_distance(endpoint, a, b)[0] < river["width"] / 2 - 1
                           for a, b in zip(river["points"], river["points"][1:]))
                       for river in data["terrain"]["rivers"]):
                raise ValueError("A wall endpoint does not overlap a river bank")
    if _inside(data["town"]["exit_tile"], data["town"]["entry_rect_tiles"]):
        raise ValueError("Town exit would immediately re-enter the town footprint")
    if any(gate["clearance_flag"] != "CH01_OPENING_REGION_RELEASED" or gate["destination_ready"]
           for gate in data["gates"]):
        raise ValueError("Opening checkpoints must retain their pending destinations")
    if data["bridge"]["repair_flag"] != "ELDEN_VALE_WEST_BRIDGE_REPAIRED":
        raise ValueError("Bridge repair must remain independent of checkpoint release")
    bridge = data["bridge"]
    if (bridge.get("deck_width_tiles") != 3 or bridge["deck_rect_tiles"][3] != 3
            or bridge["deck_rect_tiles"][1]+1.5 != bridge.get("deck_center_tile_y")):
        raise ValueError("The bridge roadway must span exactly three tiles north-south")
    if bridge.get("broken_art_key") != "broken_bridge_wide":
        raise ValueError("The widened roadway requires its matching broken bridge artwork")
    for piece in setpieces:
        if piece.get("kind") == "farmstead" and len(piece.get("door_approaches", [])) < 3:
            raise ValueError("A farm needs clear fronts for its home, barn and shed")
    for shore in data["terrain"].get("shore_conditions", []):
        if shore.get("kind") not in {"gravel", "damp", "reeds", "rocky"} or len(shore.get("polygon", [])) < 3:
            raise ValueError("A shoreline condition requires a known material and landward outline")
    validation = data["route_validation"]
    road = next(road for road in data["roads"] if road["id"] == validation["bridge_approach_road"])
    start_distance = _road_distance(road, validation.get("bridge_approach_start_tile", data["spawn_tile"]))
    end_distance = _road_distance(road, validation["bridge_approach_end_tile"])
    if end_distance < start_distance:
        raise ValueError("Bridge approach reverses its authored road direction")
    seconds = (end_distance - start_distance) * data["tile_size"] / validation["walking_speed_px_per_second"]
    low, high = validation["bridge_approach_target_seconds"]
    if not low <= seconds <= high:
        raise ValueError(f"Authored bridge approach {seconds:.2f}s is outside {low}-{high}s")
    validation["measured_bridge_approach_seconds"] = round(seconds, 2)
    reached = _flood(data)
    required = [data["town"]["exit_tile"], data["bridge"]["east_approach_tile"]]
    required.extend(mark["tile_position"] for mark in data["landmarks"]
                    if mark["id"] in validation["reachable_landmark_ids"])
    required.extend(point for gate in data["gates"] for point in gate["guard_tiles"])
    required.extend(piece["approach_tile"] for piece in setpieces)
    if any(tuple(point) not in reached for point in required):
        raise ValueError("An authored spawn, landmark, guard or bridge approach is unreachable")
    north = min(wall["y"] for wall in data["walls"])
    south = max(wall["y"] for wall in data["walls"])
    if any(y <= north or y >= south for _, y in reached):
        raise ValueError("The opening enclosure has a wall/river/checkpoint bypass")
    if tuple(data["bridge"]["west_approach_tile"]) in reached:
        raise ValueError("The destroyed bridge can be crossed without repair")
    repaired = _flood(data, repaired=True)
    if tuple(data["bridge"]["west_approach_tile"]) not in repaired:
        raise ValueError("The independent repaired deck does not join both banks")
    validation["geometry_checks"] = {
        "opening_reachable_tiles": len(reached),
        "required_points_reachable": len(required),
        "closed_perimeter": True,
        "broken_bridge_blocks_crossing": True,
        "repaired_bridge_connects_banks": True,
        "scope": "Offline four-neighbour tile sampling of continuous vector barriers and authored approaches; runtime actor/decoration probes have separate engine checks."
    }


def prepare():
    data = deepcopy(json.loads(SOURCE.read_text(encoding="utf-8")))
    for road in data.get("roads", []):
        if road.get("control_points"):
            road["points"] = smooth_road(road["control_points"], road.get("smooth_steps", 6))
    geography = data["geography"]
    atlas = ROOT / geography["atlas_source"]
    digest = hashlib.sha256(atlas.read_bytes()).hexdigest()
    if digest != geography["atlas_sha256"]:
        raise ValueError("Approved atlas hash differs from the pinned survey source")
    with Image.open(atlas) as image:
        if list(image.size) != geography["atlas_source_size"]:
            raise ValueError("Approved atlas dimensions differ from the survey")
    width, height = geography["atlas_source_size"]
    normalize = lambda point: [round(point[0] / width, 8), round(point[1] / height, 8)]
    for anchor in geography["anchors"]:
        anchor["atlas_normalized"] = normalize(anchor["atlas_pixel"])
    for trace in geography["atlas_traces"]:
        trace["atlas_normalized_points"] = [normalize(point) for point in trace["atlas_points"]]
    geography["opening_corridor_normalized_polygon"] = [normalize(point) for point in geography["opening_corridor_reference_polygon"]]
    data["build"] = {
        "tool": Path(__file__).relative_to(ROOT).as_posix(),
        "source_recipe": SOURCE.relative_to(ROOT).as_posix(),
        "source_recipe_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "atlas_reference": REFERENCE.relative_to(ROOT).as_posix(),
        "exports": [OUTPUT.relative_to(ROOT).as_posix(), REFERENCE.relative_to(ROOT).as_posix()]
    }
    validate(data)
    return data


def _label(image, position, text, scale=2, fill=(31, 32, 37, 255)):
    font = ImageFont.load_default()
    box = font.getbbox(text)
    label = Image.new("RGBA", (box[2] - min(0, box[0]) + 2, box[3] - min(0, box[1]) + 2))
    ImageDraw.Draw(label).text((1 - min(0, box[0]), 1 - min(0, box[1])), text, font=font, fill=fill)
    label = label.resize((label.width * scale, label.height * scale), Image.Resampling.NEAREST)
    image.alpha_composite(label, position)


def reference_png(data):
    geography = data["geography"]
    with Image.open(ROOT / geography["atlas_source"]) as source:
        annotated = source.convert("RGBA")
    overlay = Image.new("RGBA", annotated.size)
    draw = ImageDraw.Draw(overlay)
    polygon = [tuple(point) for point in geography["opening_corridor_reference_polygon"]]
    draw.polygon(polygon, fill=(255, 213, 50, 35))
    draw.line(polygon + [polygon[0]], fill=(255, 217, 57, 235), width=2)
    for trace, color in zip(geography["atlas_traces"], ((30, 235, 255, 240), (216, 129, 255, 240))):
        draw.line([tuple(point) for point in trace["atlas_points"]], fill=color, width=2)
    for number, anchor in enumerate(geography["anchors"], 1):
        x, y = anchor["atlas_pixel"]
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
        draw.text((x + 5, y - 9), str(number), fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 255))
    annotated.alpha_composite(overlay)
    canvas = Image.new("RGBA", (1448, 1556), (242, 237, 218, 255))
    canvas.alpha_composite(annotated)
    # An enlarged reference crop improves inspection; it is not runtime art.
    inset = annotated.crop((130, 310, 360, 530)).resize((460, 440), Image.Resampling.NEAREST)
    canvas.alpha_composite(inset, (16, 1100))
    lines = [
        "ELDEN VALE - ATLAS SURVEY REFERENCE",
        "Approved source PNG is unchanged (1448 x 1086).",
        "Left: enlarged reference crop; top: complete source.",
        "Cyan: western watercourse. Violet: eastern watercourse.",
        "Gold: indicative starting corridor, not existing walls.",
        "1 Eldenmere     2 Northern woodland context",
        "3 Western crossing context     4 Greyfold foothills",
        "5 Unnamed settlement illustration (no new town identity)",
        "Anchors follow the map; gameplay space is authored separately.",
        "No physical scale, exact confluences or temple site assigned.",
        "Walls, gates and bridge damage are runtime interpretation.",
        "Builder: tools/build_elden_vale_overworld.py",
        "Source SHA-256: " + geography["atlas_sha256"][:32],
        "                " + geography["atlas_sha256"][32:],
    ]
    for index, line in enumerate(lines):
        _label(canvas, (496, 1102 + index * 29), line)
    result = BytesIO()
    canvas.convert("RGB").save(result, format="PNG", optimize=False)
    return result.getvalue()


def build(check=False):
    data = prepare()
    outputs = {
        OUTPUT: (json.dumps(data, indent=2) + "\n").encode("utf-8"),
        REFERENCE: reference_png(data),
    }
    for path, content in outputs.items():
        if check:
            if not path.exists() or path.read_bytes() != content:
                raise ValueError(f"Generated output is stale: {path.relative_to(ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    verb = "Verified" if check else "Built"
    timing = data["route_validation"]["measured_bridge_approach_seconds"]
    count = data["route_validation"]["geometry_checks"]["opening_reachable_tiles"]
    print(f"{verb} Elden Vale vector manifest and atlas reference; bridge walk {timing}s; {count} opening tiles reachable.")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate geometry and compare both generated outputs without writing")
    build(check=parser.parse_args().check)
