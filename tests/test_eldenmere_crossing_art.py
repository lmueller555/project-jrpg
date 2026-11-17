"""Crossing drawing coverage, cardinal construction and bank/door contracts.

These tests deliberately measure opaque walking pixels and occupied rail lengths,
not only their transparent PNG canvases. Game travel/layer tests live with the
integration owner and are not replaced by these source tests.
"""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from PIL import Image, ImageChops

from tools import eldenmere_crossing_art as art

ROOT = Path(__file__).resolve().parents[1]


def crop_logical(im, rect):
    x, y, w, h = rect
    return im.crop((x * 2, y * 2, (x + w) * 2, (y + h) * 2))


class CrossingArtwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assemblies = art.crossing_assemblies()

    def test_origins_and_logical_dimensions_keep_both_existing_bridges(self):
        expected = {'upper_bridge': ((768, 444), (144, 72)),
                    'main_bridge': ((744, 996), (168, 72)),
                    'mill_landing': ((948, 318), (48, 72))}
        self.assertEqual(set(self.assemblies), set(expected))
        for name, (pos, size) in expected.items():
            a = self.assemblies[name]
            self.assertEqual((a.position, a.logical_size), (pos, size))
            for im in (a.deck, a.far_rail, a.near_rail, a.contact_shadow, a.ground):
                self.assertEqual(im.size, tuple(v * 2 for v in size))

    def test_every_walking_pixel_is_dry_and_opaque_including_both_bank_ends(self):
        for name, a in self.assemblies.items():
            alpha = crop_logical(a.deck, a.metadata['walk_surface']).getchannel('A')
            self.assertEqual(alpha.getextrema(), (255, 255), name)
            self.assertEqual(a.metadata['walking_surface_opaque_coverage'], 1, name)
            # Every complete row spans the exact width. No perspective taper.
            for y in range(alpha.height):
                self.assertEqual(alpha.crop((0, y, alpha.width, y + 1)).getbbox(),
                                 (0, 0, alpha.width, 1), (name, y))

    def test_longer_bridge_has_genuinely_longer_occupied_deck_and_rails(self):
        upper, main = self.assemblies['upper_bridge'], self.assemblies['main_bridge']
        for role in ('deck', 'far_rail', 'near_rail'):
            u = getattr(upper, role).getchannel('A').getbbox()
            m = getattr(main, role).getchannel('A').getbbox()
            self.assertEqual((m[2] - m[0]) - (u[2] - u[0]), 48, role)
            # Nearly all of each span must actually contain rail artwork.
            if role != 'deck':
                self.assertGreaterEqual((u[2] - u[0]) / upper.deck.width, .97)
                self.assertGreaterEqual((m[2] - m[0]) / main.deck.width, .97)

    def test_same_board_and_post_scale_across_spans_without_resizing(self):
        upper, main = self.assemblies['upper_bridge'], self.assemblies['main_bridge']
        # A corresponding native board and standard rail bay are byte-identical.
        for role, box in (('deck', (24, 25, 48, 118)),
                          ('far_rail', (3, 2, 53, 26)),
                          ('near_rail', (3, 98, 53, 122))):
            self.assertEqual(getattr(upper, role).crop(box).tobytes(),
                             getattr(main, role).crop(box).tobytes(), role)
        self.assertEqual(art.board_section().size, (24, 96))
        self.assertEqual(art.post_section().size, (6, 26))
        self.assertEqual(art.rail_section().size, (48, 26))

    def test_whole_standard_bays_and_explicit_ends_not_centered_small_donor(self):
        for name in ('upper_bridge', 'main_bridge'):
            a = self.assemblies[name]; centers = a.metadata['rails_logical']['post_centers_x']
            self.assertEqual(centers[0], 3)
            self.assertEqual(centers[-1], a.logical_size[0] - 3)
            self.assertEqual([b - x for x, b in zip(centers, centers[1:-1])],
                             [24] * (len(centers) - 2))
            self.assertEqual(centers[-1] - centers[-2], 18)
            # At both timber beam heights the line bridges end-to-end.
            for role, y in (('far_rail', 7), ('near_rail', 103)):
                alpha = getattr(a, role).getchannel('A')
                self.assertEqual(alpha.crop((6, y, alpha.width - 6, y + 1)).getextrema(), (255, 255))

    def test_near_rail_has_matched_height_and_only_lower_body_overlap(self):
        for name in ('upper_bridge', 'main_bridge'):
            a = self.assemblies[name]
            far = a.far_rail.getchannel('A').getbbox()
            near = a.near_rail.getchannel('A').getbbox()
            self.assertEqual(far[3] - far[1], near[3] - near[1])
            self.assertEqual(near[1], 98)  # local y49, not whole-body y24
            self.assertEqual(near[3], 124)
            self.assertLess(near[3] - near[1], 72 // 2)
            self.assertEqual(a.metadata['rails_logical']['rise'], 11)

    def test_mill_dry_apron_and_open_door_lane_are_explicit(self):
        a = self.assemblies['mill_landing']; m = a.metadata
        self.assertEqual(m['exterior_interface']['deck_world'], [948, 330, 48, 48])
        self.assertEqual(m['door_anchor_world'], [971, 342])
        self.assertEqual(m['road_connection_world'], [972, 384])
        self.assertEqual(m['clear_approach_world'], [960, 330, 24, 54])
        # Neither side rail puts a crossbar through the road-to-door corridor.
        for im in (a.far_rail, a.near_rail):
            self.assertIsNone(crop_logical(im, (12, 0, 24, 72)).getchannel('A').getbbox())
        self.assertLess(a.position[0] + a.logical_size[0], m['exterior_interface']['wheel_west_world'])

    def test_mill_service_surface_overlays_every_water_phase_and_reduced_motion(self):
        for name, a in self.assemblies.items():
            first = None
            # Six different underlying water states, including a held phase0.
            for phase in (0, 1, 2, 3, 4, 5, 0):
                water = Image.new('RGBA', a.deck.size, (45 + phase * 3, 88 + phase * 5, 97, 255))
                water.alpha_composite(a.ground)
                actual = crop_logical(water, a.metadata['walk_surface'])
                if first is None: first = actual.tobytes()
                self.assertEqual(first, actual.tobytes(), (name, phase))

    def test_water_can_remain_visible_beside_each_assembly(self):
        for name, a in self.assemblies.items():
            # All source canvases retain transparent spaces, rather than a water
            # colored opaque background painted into a rectangular asset.
            self.assertEqual(a.ground.getpixel((a.deck.width // 2, 140))[3], 0, name)
            self.assertNotEqual(a.metadata['water_beside_samples_world'][0],
                                a.metadata['water_beside_samples_world'][1])

    def test_decks_and_rails_have_hard_alpha_shadow_is_separately_named(self):
        for name, a in self.assemblies.items():
            for im in (a.deck, a.far_rail, a.near_rail):
                values = {i for i, count in enumerate(im.getchannel('A').histogram()) if count}
                self.assertEqual(values, {0, 255}, name)
            values = {i for i, count in enumerate(a.contact_shadow.getchannel('A').histogram()) if count}
            self.assertEqual(values, {0, 72})

    def test_existing_collision_rows_match_the_full_48_unit_walking_surface(self):
        c = Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png').convert('L')
        for name in ('upper_bridge', 'main_bridge'):
            a = self.assemblies[name]; lo, hi = a.metadata['preserved_clear_rows_world']
            self.assertEqual(hi - lo, 48)
            self.assertEqual(c.crop((850, lo, 851, hi)).getextrema(), (0, 0))
            self.assertNotEqual(c.getpixel((850, lo - 1)), 0)
            self.assertNotEqual(c.getpixel((850, hi)), 0)
        self.assertEqual(c.crop((967, 336, 975, 384)).getextrema(), (0, 0))

    def test_plan_endpoint_and_dry_bank_envelopes_match_actual_stream_cells(self):
        from tools.build_eldenmere_blockout import geometry
        plan = json.loads((ROOT/'assets/maps/eldenmere/terrain_foundation/adapted_plan.json').read_text())
        geom = geometry(plan)
        for r in plan['crossings']:
            if r['kind'] != 'stream_bridge': continue
            a = self.assemblies[r['id']]; x, y, w, h = r['rect']
            self.assertEqual(a.position, (x * 24, y * 24 - 12))
            self.assertEqual(a.logical_size, (w * 24, 72))
            centers = [row[0] for row in geom['stream'] if row[1] == y]
            self.assertEqual(len(centers), 1)
            left, right = (centers[0] - 1) * 24, (centers[0] + 2) * 24
            self.assertEqual(a.metadata['bank_overlap_world'],
                             [[x * 24, y * 24, left - x * 24, h * 24],
                              [right, y * 24, (x + w) * 24 - right, h * 24]])

    def test_pure_generator_returns_independent_images_and_deterministic_metrics(self):
        again = art.crossing_assemblies()
        for name, a in self.assemblies.items():
            self.assertEqual(a.metadata, again[name].metadata)
            self.assertEqual(a.ground.tobytes(), again[name].ground.tobytes())
            again[name].deck.putpixel((0, 0), (255, 0, 0, 255))
            self.assertNotEqual(a.deck.getpixel((0, 0)), again[name].deck.getpixel((0, 0)))

    def test_source_exports_recipe_hashes_and_native_diagrams_are_reproducible(self):
        products = art.products()
        for path, data in products.items():
            self.assertEqual((ROOT/path).read_bytes(), data, str(path))
            self.assertTrue(str(path).startswith(str(art.SOURCE)))
        recipe = json.loads(products[art.SOURCE/'recipe.json'])
        for r in recipe['exports']:
            self.assertEqual(sha256(products[art.SOURCE/r['file']]).hexdigest(), r['sha256'])
        self.assertIn('not gameplay', recipe['review']['diagrams'])
        for name in self.assemblies:
            with Image.open(ROOT/art.SOURCE/name/'construction_diagram.png') as im:
                self.assertEqual(im.size, (960, 640))


if __name__ == '__main__':
    unittest.main()
