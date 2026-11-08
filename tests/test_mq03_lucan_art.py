"""MQ03 references Lucan's approved art and retires only dispute staging."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def read(path):return json.loads((ROOT/path).read_text())


class LucanVisitArtTests(unittest.TestCase):
    def test_registered_guard_reuses_every_approved_direction_without_body_changes(self):
        art = read('assets/story/regent/art.json')
        actors = {actor['id']: actor for actor in art['actors']}
        self.assertEqual(set(actors), {'aldric', 'lucan', 'regent_clerk', 'regent_driver',
                                       'regent_survivor'})
        lucan = actors['lucan']
        self.assertEqual(lucan['draw_anchor'], [12, 30])
        animation = read(lucan['art'])
        self.assertEqual(animation['foot_anchor'], [12, 34])
        for direction in ('front', 'left', 'right', 'back'):
            idle = f'assets/characters/lucan/idle_{direction}.png'
            self.assertEqual(animation['idles'][direction], idle)
            metadata = read(f'assets/characters/lucan/walk_{direction}/animation.json')
            expected = [f"assets/characters/lucan/walk_{direction}/{frame['file']}"
                        for frame in metadata['frames']]
            self.assertEqual(animation['walks'][direction], expected)
            self.assertEqual(len(expected), 4)
            for path in (idle, *expected):
                with Image.open(ROOT/path) as image:self.assertEqual(image.size, (24, 36))

    def test_meal_stations_and_original_household_are_preserved_without_dispute_props(self):
        art = read('assets/story/regent/art.json')
        self.assertNotIn('existing_actors', art)
        ids = {prop['id'] for prop in art['props']}
        self.assertNotIn('venn_cart', ids);self.assertNotIn('road_stone', ids)
        self.assertIn('regent_wagon', ids)
        self.assertEqual(sum(name.startswith('dining_guest_chair_') for name in ids), 4)
        layout = read('assets/story/regent/layout.json')
        self.assertIn('lucan_courtyard', layout['dining_stations'])
        for key in layout:
            self.assertFalse(key.startswith(('venn_', 'cart_', 'foreman', 'attendant_')), key)
        for direction in ('front', 'left', 'right', 'back'):
            self.assertTrue((ROOT/f'assets/story/venn/father/idle_{direction}.png').is_file())

    def test_dialogue_portrait_resolves_to_the_existing_approved_lucan_portrait(self):
        dialogue = read('assets/dialogue/eldenmere.json')
        speaker = dialogue['speakers']['lucan']
        self.assertEqual(speaker['actor_id'], 'lucan')
        self.assertIn('lucan', dialogue['characters'])
        self.assertNotIn('road_foreman', dialogue['characters'])
        manifest = read('assets/portraits/eldenmere/portraits.json')
        portrait = manifest['portraits'][speaker['portrait']]
        resolved = (ROOT/'assets/portraits/eldenmere'/portrait['file']).resolve()
        self.assertEqual(resolved, ROOT/'assets/story/ice_reaper_opening/portraits/lucan.png')
        with Image.open(resolved) as image:self.assertEqual(image.size, (96, 96))

    def test_shared_meal_has_six_registered_seated_bodies_and_seven_chairs(self):
        layout = read('assets/story/regent/layout.json')
        seats = layout['meal_seats']
        self.assertEqual(set(seats), {'aldric', 'lucan', 'regent_clerk', 'regent_driver',
                                     'mother_serene', 'tomas'})
        self.assertEqual(seats['lucan']['facing'], 'front')
        self.assertEqual(seats['regent_driver']['facing'], 'back')
        room = read('assets/maps/eldenmere/building_interiors/rooms/sanctuary_dining/map.json')
        fixed_chairs = [entity for entity in room['entities'] if entity['id'].startswith('chair_')]
        guest_chairs = [prop for prop in read('assets/story/regent/art.json')['props']
                        if prop['id'].startswith('dining_guest_chair_')]
        self.assertEqual(len(fixed_chairs)+len(guest_chairs), 7)
        for record in seats.values():
            self.assertEqual(record['anchor'], room['player_draw_anchor'])
            with Image.open(ROOT/record['image']) as image:
                self.assertEqual(image.size, (24, 36))
                self.assertEqual(image.mode, 'RGBA')
                self.assertTrue(set(image.getchannel('A').tobytes()) <= {0, 255})

    def test_builder_preserves_approved_exports_and_custom_room_edits(self):
        spec = importlib.util.spec_from_file_location('mq03_art_builder', ROOT/'tools/build_regent_quest.py')
        builder = importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);out = root/'assets/story/regent';out.mkdir(parents=True)
            art = read('assets/story/regent/art.json')
            art['actors'][0]['approved_export_marker'] = 'keep'
            (out/'art.json').write_text(json.dumps(art))
            layout = read('assets/story/regent/layout.json')
            layout.update(serene=[302, 118], future_room_note='retain this authored extension',
                          venn_road=[1, 2], cart_route=[[1, 2]])
            (out/'layout.json').write_text(json.dumps(layout))
            for direction in ('front', 'left', 'right', 'back'):
                path = Path(f'assets/characters/lucan/walk_{direction}/animation.json')
                (root/path).parent.mkdir(parents=True);shutil.copyfile(ROOT/path, root/path)
            with patch.object(builder, 'ROOT', root), patch.object(builder, 'OUT', out):
                with contextlib.redirect_stdout(io.StringIO()):builder.build()
            updated = json.loads((out/'layout.json').read_text())
            self.assertEqual(updated['serene'], [302, 118])
            self.assertEqual(updated['future_room_note'], 'retain this authored extension')
            self.assertNotIn('venn_road', updated);self.assertNotIn('cart_route', updated)
            self.assertEqual(json.loads((out/'art.json').read_text())['actors'][0]['approved_export_marker'], 'keep')
            for name in ('venn_father', 'road_foreman', 'regent_attendant'):
                self.assertFalse((out/'actors'/name).exists())
            self.assertFalse((out/'props/venn_cart.png').exists())


if __name__ == '__main__':unittest.main()
