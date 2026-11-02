"""Read-only geography, provenance and native-crop contract for offline scenery.

No game/actor/audio import and no mutation of the checked-in assets. Full
regeneration is independently exercised by build_regent_crossroads.py --check.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_regent_crossroads as builder


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def distance(point, a, b) -> float:
    """Independent continuous segment distance, in canonical world tiles."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    denominator = dx * dx + dy * dy
    t = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / denominator if denominator else 0
    t = min(1.0, max(0.0, t))
    return math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy)


def path_distance(point, points) -> float:
    return min(distance(point, a, b) for a, b in zip(points, points[1:]))


class RegentCrossroadsArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = load_json(builder.RECIPE)
        cls.manifest = load_json(builder.OUTPUT / "manifest.json")
        cls.geometry = load_json(builder.SOURCE / "geometry.json")
        cls.provenance = load_json(builder.SOURCE / "provenance.json")
        cls.region = load_json(builder.REGION)
        cls.project = builder.Projection(cls.manifest["projection"])
        cls.roads = {r["id"]: r for r in cls.region["roads"]}
        with Image.open(builder.OUTPUT / "panorama.png") as image:
            cls.panorama = image.convert("RGB")
        cls.size = tuple(cls.manifest["canvas"])
        cls.masks = {}
        for key, spec in cls.geometry["masks"].items():
            with Image.open(builder.SOURCE / spec["file"]) as image:
                cls.masks[key] = image.copy()

    @classmethod
    def tearDownClass(cls):
        cls.panorama.close()
        for image in cls.masks.values():
            image.close()

    def test_pinned_regional_source_is_unmodified(self):
        expected = "0ed0eeb8060f035ff2db89fc4f1ef20fc554f9651c9c46893e46613789577d88"
        self.assertEqual(builder.sha256(builder.REGION.read_bytes()), expected)
        self.assertEqual(self.manifest["source_sha256"], expected)
        self.assertEqual(self.geometry["source_sha256"], expected)
        self.assertEqual(self.manifest["regional_source"], "assets/maps/overworld/elden_vale/region.json")

    def test_every_original_art_input_retains_its_pinned_hash(self):
        self.assertEqual(self.provenance["source_records"], self.recipe["source_records"])
        self.assertEqual(len(builder.verified_inputs(self.recipe)), 10)
        for spec in self.provenance["source_records"]:
            with self.subTest(source=spec["file"]):
                self.assertEqual(builder.sha256((ROOT / spec["file"]).read_bytes()), spec["sha256"])

    def test_no_tiny_chart_runtime_texture_or_actor_image_input(self):
        images = [spec["file"] for spec in self.provenance["source_records"] if spec["file"].endswith(".png")]
        self.assertEqual(len(images), 7)
        for path in images:
            self.assertTrue(path.startswith("assets/source/"), path)
            self.assertNotIn("/actors/", path)
            self.assertNotIn("/cartography/", path)
            self.assertNotIn("/maps/", path)
            self.assertNotIn("region.png", path)
            with Image.open(ROOT / path) as image:
                self.assertGreaterEqual(min(image.size), 887)
        self.assertIn("no image generation", self.recipe["method"].lower())
        self.assertEqual(self.manifest["depth_layers"], [])
        self.assertIsNone(self.manifest["foreground"])

    def test_native_opaque_canvas_is_bounded_in_decoded_rgba(self):
        self.assertEqual(self.manifest["version"], 1)
        self.assertEqual(self.size, (4928, 1728))
        self.assertEqual(self.panorama.size, self.size)
        self.assertEqual(self.manifest["viewport"], [480, 320])
        self.assertEqual(self.panorama.convert("RGBA").getchannel("A").getextrema(), (255, 255))
        self.assertTrue(self.manifest["opaque"])
        self.assertEqual(self.manifest["decoded_rgba_bytes"], self.size[0] * self.size[1] * 4)
        self.assertLess(self.manifest["decoded_rgba_bytes"], 50_000_000)
        self.assertEqual(builder.pixel_sha256(self.panorama), self.manifest["background_rgba_sha256"])

    def test_projection_roundtrips_and_preserves_geographic_orientation(self):
        self.assertEqual(self.project.scale, (28, 24))
        self.assertEqual(self.project.origin, (-136, -28))
        for tile in ([7, 4], [-111, 29], [-111, 30], [-36, 8], [-70, 24], [12, -28], [-121.25, 30.75]):
            actual = self.project.inverse(self.project.point(tile))
            np.testing.assert_allclose(actual, tile, atol=1e-12)
        origin = self.project.point((0, 0))
        east, south = self.project.point((1, 0)), self.project.point((0, 1))
        self.assertGreater(east[0], origin[0])
        self.assertGreater(south[1], origin[1])
        self.assertEqual(east[1], origin[1])
        self.assertEqual(south[0], origin[0])

    def test_junction_has_exactly_three_real_arms(self):
        point = [7, 4]
        incident = [road for road in self.region["roads"] if point in road["points"]]
        self.assertEqual({r["id"] for r in incident}, {"south_town_road", "southern_land_corridor"})
        arms = []
        for road in incident:
            index = road["points"].index(point)
            if index:
                arms.append(road["points"][index - 1])
            if index + 1 < len(road["points"]):
                arms.append(road["points"][index + 1])
        self.assertEqual(len(arms), 3)
        self.assertEqual(sum(p[0] > 7 and p[1] < 4 for p in arms), 1)  # N/slightly E
        self.assertEqual(sum(p[0] < 7 and p[1] > 4 for p in arms), 1)  # WSW
        self.assertEqual(sum(p[0] > 7 and p[1] > 4 for p in arms), 1)  # SSE
        self.assertEqual(len(self.geometry["junction_arms"]), 3)

    def test_canonical_road_hierarchy_and_widths_are_not_reauthored(self):
        stone, dirt = self.roads["south_town_road"], self.roads["southern_land_corridor"]
        self.assertEqual((stone["kind"], stone["surface"], stone["width"], stone["ruts"]),
                         ("stone", "stone_road", 2.5, False))
        self.assertEqual((dirt["kind"], dirt["surface"], dirt["width"], dirt["ruts"]),
                         ("cart", "dirt", 1.9, True))
        for road in self.geometry["roads"]:
            self.assertEqual(road, self.roads[road["id"]])

    def test_all_visible_fields_and_spurs_use_original_geometry(self):
        fields = {field["id"]: field for field in self.region["terrain"]["fields"]}
        for field in self.geometry["fields"]:
            self.assertEqual(field, fields[field["id"]])
        ids = {road["id"] for road in self.geometry["roads"]}
        self.assertTrue({"western_farm_spur", "relief_staging_spur", "field_loop"} <= ids)
        self.assertEqual(self.roads["relief_staging_spur"]["points"][0], [-70, 24])
        self.assertEqual(self.roads["western_farm_spur"]["points"][0], [-42, 17])
        self.assertEqual(self.geometry["anchors"]["western_farm"]["tile"], [-36, 8])

    def test_no_building_or_gate_was_invented_at_the_junction(self):
        canonical = {p["id"]: p for s in self.region["setpieces"] for p in s.get("props", [])}
        building_keys = {"farm_house", "barn", "shed", "checkpoint_shelter"}
        for prop in self.provenance["prop_placements"]:
            if prop["key"] in building_keys:
                self.assertIn(prop["id"], canonical)
                self.assertEqual(prop["tile_position"], canonical[prop["id"]]["tile_position"])
                self.assertGreater(math.dist(prop["tile_position"], (7, 4)), 10)
            self.assertNotIn("gate", prop["key"])

    def test_every_geographic_mask_is_native_binary_and_fingerprinted(self):
        for key, mask in self.masks.items():
            with self.subTest(mask=key):
                self.assertEqual(mask.mode, "L")
                self.assertEqual(mask.size, self.size)
                self.assertLessEqual(set(mask.tobytes()), {0, 255})
                self.assertEqual(builder.pixel_sha256(mask), self.geometry["masks"][key]["rgba_sha256"])
        for key in ("stone_road", "dirt_road", "fields", "river", "scorch"):
            self.assertEqual(self.geometry["masks"][key]["authority"], "region.json")
        self.assertIn("not regional geometry", self.geometry["masks"]["worn_verge_variation"]["authority"])

    def test_stroke_measures_world_width_before_anisotropic_projection(self):
        # An independent axis-aligned probe catches drawing a 2.5*28 wide
        # horizontal path instead of the canonical 2.5*24 depth.
        project = builder.Projection({"origin_tiles": [0, 0], "pixels_per_tile": [28, 24]})
        horizontal = builder.polyline_mask((336, 240), [[2, 5], [10, 5]], 2.5, project)
        vertical = builder.polyline_mask((336, 240), [[6, 2], [6, 8]], 2.5, project)
        ys = np.flatnonzero(np.asarray(horizontal)[:, 168])
        xs = np.flatnonzero(np.asarray(vertical)[120])
        self.assertEqual(int(ys[-1] - ys[0]), 60)
        self.assertEqual(int(xs[-1] - xs[0]), 70)

    def test_native_masks_contain_actual_road_centerlines(self):
        for road in self.geometry["roads"]:
            mask = self.masks["stone_road" if road["kind"] == "stone" else "dirt_road"]
            for tile in road["points"]:
                x, y = [round(v) for v in self.project.point(tile)]
                if 0 <= x < self.size[0] and 0 <= y < self.size[1]:
                    self.assertEqual(mask.getpixel((x, y)), 255, (road["id"], tile))

    def test_junction_view_has_no_copied_or_invented_river(self):
        camera = self.manifest["camera_junction"]
        water = builder.crop_rect(self.masks["river"], [*camera, 480, 320])
        self.assertIsNone(water.getbbox())
        self.assertEqual(self.geometry["rivers"], self.region["terrain"]["rivers"])

    def test_river_is_the_canonical_north_south_western_watercourse(self):
        river = self.geometry["rivers"][0]
        self.assertEqual(river["id"], "western_boundary_river")
        self.assertEqual(river["width"], 10)
        self.assertIn([-111, 30], river["points"])
        self.assertGreater(max(p[1] for p in river["points"]) - min(p[1] for p in river["points"]),
                           max(p[0] for p in river["points"]) - min(p[0] for p in river["points"]))
        x, y = [round(v) for v in self.project.point((-111, 30))]
        self.assertEqual(self.masks["river"].getpixel((x, y)), 255)
        self.assertEqual(self.geometry["scorched"], self.region["terrain"]["scorched"])

    def test_camera_track_endpoints_and_native_projection_are_exact(self):
        self.assertEqual(self.manifest["camera_junction"], [3734, 623])
        self.assertEqual(self.manifest["camera_bridge"], [432, 1203])
        self.assertEqual(self.manifest["camera_path"][0], self.manifest["camera_junction"])
        self.assertEqual(self.manifest["camera_path"][-1], self.manifest["camera_bridge"])
        self.assertEqual(self.manifest["route_tile_points"][0], [7, 4])
        self.assertEqual(self.manifest["route_tile_points"][-1], [-111, 29])
        for camera, tile, screen in ((self.manifest["camera_junction"], [7, 4], [270, 145]),
                                     (self.manifest["camera_bridge"], [-111, 29], [268, 165])):
            np.testing.assert_allclose(np.add(camera, screen), self.project.point(tile), atol=0)

    def test_route_uses_already_densified_source_not_control_chords(self):
        road = self.roads["south_town_road"]
        first, last = self.manifest["source_point_indices"]
        self.assertEqual([first, last], [30, 90])
        self.assertEqual(self.manifest["road_source_tile_points"], road["points"][first:last + 1])
        self.assertGreater(len(self.manifest["road_source_tile_points"]), 50)
        self.assertIn([-98.4556, 28.7407], self.manifest["road_source_tile_points"])

    def test_actual_route_arc_length_and_pixel_arc_are_preserved(self):
        points = np.asarray(self.manifest["road_source_tile_points"])
        tile_arcs = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        pixel_points = np.asarray([self.project.point(p) for p in points])
        pixel_arcs = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pixel_points, axis=0), axis=1))]
        self.assertAlmostEqual(self.manifest["route_length_tiles"], float(tile_arcs[-1]), places=7)
        self.assertAlmostEqual(self.manifest["route_length_tiles"], 122.06790536, places=7)
        self.assertAlmostEqual(self.manifest["route_length_pixels"], float(pixel_arcs[-1]), places=5)
        distances = np.asarray(self.manifest["route_arc_distances_tiles"])
        np.testing.assert_allclose(self.manifest["route_arc_distances_pixels"],
                                   np.interp(distances, tile_arcs, pixel_arcs), atol=2e-6)
        self.assertEqual(distances[0], 0)
        self.assertAlmostEqual(float(distances[-1]), float(tile_arcs[-1]), places=7)
        self.assertTrue(np.all(np.diff(distances) > 0))
        self.assertLessEqual(float(np.diff(distances).max()), 1.00000001)

    def test_every_camera_arc_sample_is_on_the_actual_centerline(self):
        points = np.asarray(self.manifest["road_source_tile_points"])
        arcs = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        samples = np.asarray(self.manifest["route_arc_distances_tiles"])
        expected = np.stack([np.interp(samples, arcs, points[:, i]) for i in (0, 1)], axis=1)
        np.testing.assert_allclose(self.manifest["route_tile_points"], expected, atol=2e-8)
        for tile in self.manifest["route_tile_points"]:
            self.assertLess(path_distance(tile, points), 1e-7)

    def test_camera_is_monotonically_westward_with_declared_framing(self):
        camera = np.asarray(self.manifest["camera_path"])
        self.assertEqual(len(camera), 124)
        self.assertTrue(np.all(np.diff(camera[:, 0]) < 0))
        for tile, distance, point in zip(self.manifest["route_tile_points"],
                                         self.manifest["route_arc_distances_tiles"], camera):
            t = distance / self.manifest["route_length_tiles"]
            screen = np.asarray([270, 145]) * (1 - t) + np.asarray([268, 165]) * t
            np.testing.assert_allclose(np.asarray(self.project.point(tile)) - screen, point, atol=1e-6)

    def test_all_native_camera_windows_have_surrounding_source_art(self):
        for x, y in self.manifest["camera_path"]:
            self.assertGreaterEqual(x, 16)
            self.assertGreaterEqual(y, 16)
            self.assertLessEqual(x + 480, self.size[0] - 16)
            self.assertLessEqual(y + 320, self.size[1] - 16)
        builder.validate_contract(self.manifest, self.recipe, self.region)

    def test_actor_anchors_are_absolute_and_side_stage_is_below_caption(self):
        self.assertEqual(self.manifest["actor_anchors"], {
            "aldric": [4004, 863], "carrier": [3899, 863],
            "clerk": [4064, 879], "parked_caravan": [4334, 888]})
        for key, point in self.manifest["actor_anchors"].items():
            screen = np.subtract(point, self.manifest["camera_junction"])
            np.testing.assert_array_equal(screen, self.manifest["actor_anchors_screen_junction"][key])
            if key != "parked_caravan":
                self.assertGreater(screen[1] - 92, 98)  # whole human canvas below caption
        self.assertEqual(self.manifest["actor_anchors_screen_junction"]["parked_caravan"][0] - 150, 450)
        self.assertGreater(450, self.manifest["actor_anchors_screen_junction"]["clerk"][0] + 40)

    def test_entire_human_and_wagon_foot_probes_are_on_safe_verge(self):
        for key, point in self.manifest["actor_anchors"].items():
            x0, y0, w, h = ([-145, -12, 290, 15] if key == "parked_caravan" else [-11, -4, 22, 8])
            for dx in np.linspace(x0, x0 + w, 9):
                for dy in (y0, y0 + h / 2, y0 + h):
                    tile = self.project.inverse((point[0] + dx, point[1] + dy))
                    for road in self.region["roads"]:
                        self.assertGreater(path_distance(tile, road["points"]), road["width"] / 2 + 0.1,
                                           (key, tile, road["id"]))

    def test_no_prop_artwork_overlaps_the_reserved_actor_canvases(self):
        for prop in self.provenance["prop_placements"]:
            x, y = prop["anchor_pixels"]
            w, h = prop["size_pixels"]
            left, top = round(x - w / 2), round(y - h)
            for a, b, c, d in self.manifest["actor_clearance_rect_pixels"]:
                overlaps = left < c and left + w > a and top < d and top + h > b
                self.assertFalse(overlaps, prop["id"])

    def test_large_tree_canopies_do_not_hide_either_burned_bank(self):
        for prop in self.provenance["prop_placements"]:
            if prop["height_pixels"] < 65:
                continue
            x, y = prop["anchor_pixels"]
            w, h = prop["size_pixels"]
            left, top = round(x - w / 2), round(y - h)
            self.assertIsNone(self.masks["scorch"].crop((left - 7, top - 7, left + w + 7, top + h + 7)).getbbox(), prop["id"])

    def test_original_prop_crop_registration_and_human_scale_are_retained(self):
        original = load_json(builder.POLISH / "recipe.json")["props"]
        for key, crop in self.provenance["prop_crops"].items():
            self.assertEqual(crop["registered_crop"], original[key]["crop"])
            self.assertEqual(crop["file"], (builder.POLISH / original[key]["source"]).relative_to(ROOT).as_posix())
            self.assertEqual(crop["alpha_threshold"], 128)
            self.assertIn("nearest", crop["resampling"])
        trees = [p for p in self.provenance["prop_placements"] if p["key"] in ("oak_a", "oak_b", "oak_c")]
        self.assertGreater(len(trees), 20)
        self.assertTrue(all(130 <= p["height_pixels"] <= 200 for p in trees))
        self.assertTrue({"junction_frame:oak_a", "junction_frame:oak_b"} <= {p["id"] for p in trees})

    def test_raw_material_cells_are_reduced_not_tiny_tiles_enlarged(self):
        materials = builder.Materials(self.recipe)
        for key, spec in self.recipe["materials"].items():
            self.assertLessEqual(spec["scale"], 1)
            a, b, c, d = spec["crop"]
            image = materials.source(key)
            self.assertEqual(image.size, (round((c - a) * spec["scale"]), round((d - b) * spec["scale"])))
            self.assertGreater(min(image.size), 24)
            if "sheet" in spec:
                self.assertGreaterEqual(min(c - a, d - b), 300)
            if key == "water":
                self.assertEqual(spec["file"], "assets/source/cinematics/regent_arrival/scenery/riverbank_revised.png")
                self.assertEqual(spec["crop"], [565, 420, 685, 466])
                with Image.open(ROOT / spec["file"]) as raw:
                    retained = np.asarray(raw.convert("RGB").crop(spec["crop"])).astype(np.float32)
                mean = retained.mean(axis=(0, 1), keepdims=True)
                expected = np.clip((mean + (retained - mean) * 0.6) * [0.65, 0.72, 0.69], 0, 255).astype(np.uint8)
                np.testing.assert_array_equal(np.asarray(image), expected)
                self.assertLess(float(np.asarray(image).std(axis=(0, 1)).max()), 12)

    def test_actual_nonperiodic_material_crop_samples_are_recorded(self):
        samples = json.loads((builder.SOURCE / "material_samples.json").read_text())
        self.assertGreater(len(samples), 10)
        used = {sample["material"] for sample in samples}
        self.assertTrue({"meadow", "stone", "earth", "grain", "water"} <= used)
        materials = builder.Materials(self.recipe)
        for sample in samples:
            raw = materials.source(sample["material"])
            for _, _, rx, ry, flip in sample["placements"]:
                self.assertGreaterEqual(rx, 0)
                self.assertGreaterEqual(ry, 0)
                self.assertLessEqual(rx + sample["patch"], raw.width)
                self.assertLessEqual(ry + sample["patch"], raw.height)
                self.assertIn(flip, range(4))

    def test_quilting_is_deterministic_without_periodic_swatch_edges(self):
        for key in ("meadow", "water"):
            with self.subTest(material=key):
                a = builder.Materials(self.recipe).quilt((220, 160), key)
                b = builder.Materials(self.recipe).quilt((220, 160), key)
                self.assertEqual(a.tobytes(), b.tobytes())
                array = np.asarray(a).astype(np.int16)
                patch = min(96, min(builder.Materials(self.recipe).source(key).size) * 2 // 3)
                step = patch - max(8, patch // 4)
                self.assertFalse(np.array_equal(array[:, :-step], array[:, step:]))
                jumps = np.abs(np.diff(array, axis=1)).mean(axis=(0, 2))
                seams = jumps[step - 1::step]
                self.assertLess(float(seams.mean()), float(jumps.mean()) * 1.8)

    def test_bridge_distinguishes_world_anchor_from_roaddeck_center(self):
        bridge = self.manifest["bridge"]
        self.assertEqual(self.manifest["bridge_tile"], [-111, 29])
        self.assertEqual(self.manifest["bridge_world_anchor_tile"], [-111, 30])
        self.assertEqual(bridge["world_anchor_tile"], self.region["bridge"]["tile_position"])
        self.assertEqual(bridge["deck_rect_tiles"], self.region["bridge"]["deck_rect_tiles"])
        self.assertEqual(bridge["deck_rect_pixels"], [448, 1332, 952, 1404])
        self.assertEqual(bridge["clear_deck_pixels"], 72)
        self.assertEqual(bridge["physical_span_pixels"], 18 * 28)
        self.assertEqual(bridge["camera_zoom"], 1)

    def test_bridge_actual_pixels_have_a_readable_central_gap_and_72px_deck(self):
        # Measure the exported pixels, not a recipe/manifest gap assertion.
        with Image.open(builder.SOURCE / "bridge_components.png") as image:
            pixels = np.asarray(image.convert("RGBA"))
        self.assertEqual(pixels.shape, (116, 504, 4))
        occupied = np.any(pixels[..., 3] != 0, axis=0)
        center = 504 // 2
        west = np.flatnonzero(occupied[:center])
        east = np.flatnonzero(occupied[center:]) + center
        a, b = int(west[-1] + 1), int(east[0])
        self.assertGreaterEqual(b - a, 120)
        self.assertLessEqual(b - a, 150)
        self.assertGreaterEqual(len(west), 190)
        self.assertGreaterEqual(len(east), 190)
        self.assertFalse(np.any(pixels[:, a:b, 3]))
        bridge = self.manifest["bridge"]
        self.assertEqual(bridge["transparent_gap_sprite_columns"], [a, b])
        self.assertEqual(self.geometry["bridge"]["transparent_gap_sprite_columns"], [a, b])
        origin = np.asarray(bridge["sprite_origin_pixels"])
        screen_offset = origin - self.manifest["camera_bridge"]
        screen_center = self.project.point((-111, 29))[0] - self.manifest["camera_bridge"][0]
        for face in (a - 1, b):
            screen_x = int(face + screen_offset[0])
            self.assertGreaterEqual(screen_x, 100)
            self.assertLessEqual(screen_x, 380)
            self.assertLessEqual(abs(screen_x - screen_center), 75)
        native_columns = np.flatnonzero(occupied) + screen_offset[0]
        native_columns = native_columns[(native_columns >= 0) & (native_columns < 480)]
        self.assertLessEqual(int(native_columns[0]), 20)
        self.assertEqual(int(native_columns[-1]), 479)

        # Independent approved-source registration: two 72-row deck samples
        # must survive at the one original pixel scale, including in panorama.
        approved = load_json(ROOT / "assets/source/terrain/overworld/elden_vale/composition/recipe.json")["props"]["broken_bridge_wide"]
        top = approved["deck_top_px"] - approved["components"][0]["position"][1]
        bottom = approved["deck_bottom_px"] - approved["components"][0]["position"][1]
        self.assertEqual((top, bottom, bottom - top), (20, 92, 72))
        with Image.open(ROOT / "assets/source/terrain/overworld/elden_vale/composition/wide_bridge_generation.png") as raw:
            uniform = np.asarray(raw.convert("RGBA").resize((232, 116), Image.Resampling.NEAREST))
        for source_x, output_x in ((56, 140), (176, 364)):
            retained = uniform[top:bottom, source_x:source_x + 4, :3]
            np.testing.assert_array_equal(pixels[top:bottom, output_x:output_x + 4, :3], retained)
            self.assertTrue(np.all(pixels[top:bottom, output_x:output_x + 4, 3] == 255))
            x, y = origin + (output_x, top)
            actual = np.asarray(self.panorama.crop((int(x), int(y), int(x + 4), int(y + 72))))
            graded = np.clip(retained * np.asarray([0.96, 0.97, 0.94]) + [3, 2, 4], 0, 255).astype(np.uint8)
            np.testing.assert_array_equal(actual, graded)
        self.assertEqual([int(origin[1] + top), int(origin[1] + bottom)], [1332, 1404])

    def test_bridge_uses_one_uniform_raw_scale_then_explicit_outer_column_extension(self):
        spec = self.recipe["bridge"]
        with Image.open(ROOT / "assets/source/terrain/overworld/elden_vale/composition/wide_bridge_generation.png") as raw:
            image = raw.convert("RGBA")
        self.assertEqual(image.size, (1774, 887))
        self.assertEqual(spec["uniform_resize"], [232, 116])
        self.assertEqual(232 / image.width, 116 / image.height)
        self.assertEqual(spec["component_crops"], [[0, 0, 116, 116], [116, 0, 232, 116]])
        self.assertEqual(spec["component_positions_pixels"], [[84, 0], [304, 0]])
        self.assertEqual(spec["assembled_abutment_width_pixels"], 200)
        self.assertEqual(spec["outer_extension_pixels"], 84)
        image.putalpha(image.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
        image = image.resize((232, 116), Image.Resampling.NEAREST)
        expected = Image.new("RGBA", (504, 116))
        for crop, position in zip(spec["component_crops"], spec["component_positions_pixels"]):
            expected.alpha_composite(image.crop(crop), tuple(position))
        seams = {"west": set(), "east": set()}
        for column in spec["retained_outer_columns"]:
            a, b, c, d = column["crop"]
            x, y = column["position"]
            with self.subTest(column=column):
                self.assertEqual(y, b)  # retained deck/face rows never change scale/depth
                self.assertGreater(c - a, 0)
                self.assertGreater(d - b, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(y + d - b, 116)
                self.assertGreaterEqual(x, 0)
                self.assertLessEqual(x + c - a, 504)
                if column["side"] == "west":
                    self.assertGreaterEqual(a, 0)
                    self.assertLessEqual(c, 84)  # no copied jagged inner face
                    self.assertLessEqual(x + c - a, 108)
                else:
                    self.assertEqual(column["side"], "east")
                    self.assertGreaterEqual(a, 148)
                    self.assertLessEqual(c, 232)
                    self.assertGreaterEqual(x, 396)
                if column["part"] == "staggered_cobble_course":
                    self.assertIn((b, d), ((20, 44), (44, 68), (68, 92)))
                    seams[column["side"]].add(x)
                # There is deliberately no resize/repaint in this independent
                # assembly oracle: output columns are native reduced pixels.
                expected.alpha_composite(image.crop((a, b, c, d)), (x, y))
        for side in seams:
            self.assertGreaterEqual(len(seams[side]), 3)
        with Image.open(builder.SOURCE / "bridge_components.png") as actual:
            self.assertEqual(actual.convert("RGBA").tobytes(), expected.tobytes())
        pixels = np.asarray(expected)
        uniform = np.asarray(image).copy()
        # Alpha compositing clears source RGB hidden under A=0. Normalize only
        # those invisible pixels; every visible stone color and alpha is exact.
        uniform[uniform[..., 3] == 0] = 0
        np.testing.assert_array_equal(pixels[:, 108:200], uniform[:, 24:116])
        np.testing.assert_array_equal(pixels[:, 304:396], uniform[:, 116:208])
        self.assertIn("not a simple crop export", self.manifest["bridge"]["assembly_method"])
        self.assertEqual(self.manifest["bridge"]["retained_outer_columns_after_uniform_scale"], spec["retained_outer_columns"])

    def test_central_collapse_shows_actual_river_not_a_painted_bridge(self):
        bridge = self.manifest["bridge"]
        a, b = bridge["transparent_gap_panorama_columns"]
        deck = bridge["deck_rect_pixels"]
        gap = np.asarray(self.panorama.crop((a + 7, deck[1] + 7, b - 7, deck[3] - 7)))
        self.assertGreater(float(np.mean(gap[..., 2] > gap[..., 0] * 1.2)), 0.75)
        water = self.masks["river"].crop((a + 10, deck[1] + 10, b - 10, deck[3] - 10))
        self.assertGreater(float(np.asarray(water).mean()), 250)

    def test_both_banks_have_visible_damage_in_the_native_endpoint(self):
        x, y = self.manifest["camera_bridge"]
        rect = [x, y, 480, 320]
        image = np.asarray(builder.crop_rect(self.panorama, rect))
        water = np.asarray(builder.crop_rect(self.masks["river"], rect))
        bridge_alpha = Image.new("L", self.size)
        with Image.open(builder.SOURCE / "bridge_components.png") as components:
            bridge_alpha.paste(components.getchannel("A"), tuple(self.manifest["bridge"]["sprite_origin_pixels"]))
        alpha = np.asarray(builder.crop_rect(bridge_alpha, rect))
        for feature in self.region["terrain"]["scorched"]:
            native_mask = np.asarray(builder.crop_rect(builder.polygon_mask(self.size, feature["polygon"], self.project), rect))
            visible = (native_mask > 0) & (water == 0) & (alpha == 0)
            self.assertGreater(int(visible.sum()), 1000, feature["id"])
            self.assertLess(float(np.median(image[visible].mean(axis=1))), 65, feature["id"])

    def test_native_previews_are_exact_unscaled_panorama_crops(self):
        for filename, camera in (("crossroads_native.png", self.manifest["camera_junction"]),
                                  ("bridge_native.png", self.manifest["camera_bridge"])):
            expected = builder.crop_rect(self.panorama, [*camera, 480, 320])
            with Image.open(builder.REVIEW / filename) as image:
                self.assertEqual(image.size, (480, 320))
                self.assertEqual(image.convert("RGB").tobytes(), expected.tobytes())

    def test_local_960x480_scene_and_bridge_reference_are_exact_crops(self):
        for key, review in (("reference_scene", "crossroads_reference.png"),
                            ("bridge_reference", "bridge_wide.png")):
            spec = self.manifest[key]
            expected = builder.crop_rect(self.panorama, spec["rect_pixels"])
            for path in (builder.OUTPUT / spec["image"], builder.REVIEW / review):
                with Image.open(path) as image:
                    self.assertEqual(image.size, (960, 480))
                    self.assertEqual(image.convert("RGB").tobytes(), expected.tobytes())
        self.assertEqual(self.manifest["reference_scene"]["camera_junction"], [240, 80])

    def test_full_fixed_scale_bridge_reference_contains_complete_damage_parcels(self):
        x, y, w, h = self.manifest["bridge_reference"]["rect_pixels"]
        for feature in self.region["terrain"]["scorched"]:
            for tile in feature["polygon"]:
                point = self.project.point(tile)
                self.assertGreater(point[0], x)
                self.assertGreater(point[1], y)
                self.assertLess(point[0], x + w)
                self.assertLess(point[1], y + h)
        self.assertIn("partly cropped", self.manifest["bridge"]["framing_limitation"])

    def test_background_sample_pixels_and_product_hashes_match_provenance(self):
        for sample in self.provenance["panorama_sample_probes"]:
            self.assertEqual(self.panorama.getpixel(tuple(sample["pixel"])), tuple(sample["rgb"]))
            np.testing.assert_allclose(sample["pixel"], self.project.point(sample["tile"]), atol=0.5)
        for path, spec in self.provenance["image_products"].items():
            with self.subTest(product=path), Image.open(ROOT / path) as image:
                self.assertEqual(list(image.size), spec["canvas"])
                self.assertEqual(builder.pixel_sha256(image), spec["rgba_sha256"])
        self.assertEqual(self.provenance["tool_sha256"], builder.sha256((ROOT / "tools/build_regent_crossroads.py").read_bytes()))
        self.assertEqual(self.provenance["recipe_sha256"], builder.sha256(builder.RECIPE.read_bytes()))

    def test_output_allowlist_rejects_all_existing_scene_assets_and_clerk_reviews(self):
        for path in (ROOT / "assets/story/regent_arrival/scene.json", ROOT / "regent_arrival.py",
                     ROOT / "regent_aerial.py", builder.POLISH / "texture_sheet.png",
                     builder.REVIEW / "clerk_reference.png", ROOT / "assets/music/test.png"):
            self.assertFalse(builder.allowed_product(path), path)
        self.assertTrue(builder.allowed_product(builder.OUTPUT / "panorama.png"))
        self.assertTrue(builder.allowed_product(builder.SOURCE / "masks/stone_road.png"))
        self.assertTrue(builder.allowed_product(builder.REVIEW / "geography_junction.png"))

    def test_png_compression_fallback_accepts_only_identical_decoded_pixels(self):
        image = self.panorama.crop((100, 100, 150, 145)).convert("RGBA")
        a, b = BytesIO(), BytesIO()
        image.save(a, format="PNG", compress_level=0)
        image.save(b, format="PNG", compress_level=9)
        self.assertNotEqual(a.getvalue(), b.getvalue())
        self.assertTrue(builder.equivalent_png(a.getvalue(), b.getvalue()))
        changed = image.copy()
        changed.putpixel((1, 1), (255, 0, 255, 255))
        self.assertFalse(builder.equivalent_png(a.getvalue(), builder.png_bytes(changed)))
        changed = image.copy()
        changed.putalpha(254)
        self.assertFalse(builder.equivalent_png(a.getvalue(), builder.png_bytes(changed)))

    def test_check_path_is_read_only_even_with_compression_differences(self):
        path = builder.OUTPUT / "reference_scene.png"
        with Image.open(path) as image:
            alternative = BytesIO()
            image.save(alternative, format="PNG", compress_level=0)
        products = {path: alternative.getvalue(), builder.OUTPUT / "manifest.json":
                    (builder.OUTPUT / "manifest.json").read_bytes()}
        with patch.object(builder, "build_products", return_value=(products, self.manifest)), \
             patch.object(Path, "write_bytes", side_effect=AssertionError("--check attempted a write")), \
             redirect_stdout(StringIO()):
            self.assertEqual(builder.build(check=True), self.manifest)


if __name__ == "__main__":
    unittest.main()