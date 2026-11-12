"""The story-boss stage is native, animated, reproducible and separate from random pools."""
from hashlib import sha256
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from cave_battlefield import CAVE_BATTLEFIELDS, CaveBattlefield
from cave_random_encounters import BATTLEFIELDS as RANDOM_BATTLEFIELDS


ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = 'cave_echo_chamber'
LEGACY_PNG_HASHES = {
    'cave_outer': 'fce3e855cd4ab55ea30e6971c66cbd98075ab6d1b0909574eab89964f79c9e9d',
    'cave_grotto': '6eb7bf2a10c33de1d69e3535e2b36d31f68c472bca81246dd53290854a63345a',
    'cave_hollow': '991a88025ec97cdc6a049756954d4a3ba124d14316efbd7b5034ac9e9cd8282e',
    'cave_depths': '99e3a25c53488341d23c4f897375d27305b7051f5ae89012bcb9dfdaab721be9',
}


class EchoChamberBattlefieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_all_exports_are_reproducible_from_a_different_working_directory(self):
        with tempfile.TemporaryDirectory(prefix='echo-field-check-') as directory:
            result = subprocess.run([sys.executable, str(ROOT/'tools/build_cave_battlefields.py'),
                                     '--check'], cwd=directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_echo_room_identity_and_approved_embedded_crystal_sources(self):
        field = CaveBattlefield(IDENTIFIER)
        data = field.data
        self.assertEqual(data['name'], 'Echo Chamber')
        self.assertEqual(data['size'], [480, 320])
        self.assertEqual(data['source_scene'], 'sanctuary_cave')
        self.assertEqual(data['source_rooms'], ['echo_chamber'])
        self.assertEqual(data['source_room_names'], ['Echo Chamber'])
        self.assertEqual(data['source_position'], [2060, 360])
        self.assertEqual(data['animation']['period_ms'], 12000)
        self.assertEqual(set(data['animation']['crystal_colors']),
                         {'red', 'blue', 'white'})
        self.assertEqual(data['animation']['microcrystal_count'], 0)
        self.assertEqual([c['element'] for c in data['elemental_crystals']],['fire','ice','water'])
        self.assertTrue(all(c['size']==[64,76] for c in data['elemental_crystals']))
        self.assertEqual(data['animation']['water_tiles'], 0)
        self.assertTrue(data['animation']['pulse'])
        self.assertEqual(data['clear_actor_stage'], [24, 145, 432, 77])
        self.assertTrue(all(max(size) <= 5 for crystal in data['crystals']
                            for size in crystal['crystal_sizes']))
        sources = data['build']['source_sha256']
        self.assertIn('assets/maps/sanctuary_cave/map.json', sources)
        self.assertIn('assets/source/combat/cave_battlefields/recipe.json', sources)
        for name, digest in sources.items():
            with self.subTest(source=name):
                self.assertEqual(sha256((ROOT/name).read_bytes()).hexdigest(), digest)

    def test_animation_is_cached_varied_looping_and_reduced_motion_is_static(self):
        with patch.object(pygame.image, 'load', wraps=pygame.image.load) as load:
            field = CaveBattlefield(IDENTIFIER)
            self.assertEqual(load.call_count, 48+3*8)
            original_loads = load.call_count
            frames = [pygame.image.tobytes(field.frame(index*250), 'RGB') for index in range(48)]
            self.assertGreaterEqual(len(set(frames)), 20)
            self.assertIs(field.frame(0), field.frame(12000))
            self.assertIs(field.frame(-100), field.frame(0))
            self.assertIs(field.frame(249), field.frames[0])
            self.assertIs(field.frame(250), field.frames[1])
            for elapsed in (0, 250, 2750, 6000, 60000):
                self.assertIs(field.frame(elapsed, reduced_motion=True), field.frames[8])
            target = pygame.Surface((480, 320))
            for offset in (0, 40, 160, 900):
                field.draw(target, 1000, vertical_offset=offset)
                self.assertEqual(target.get_size(), (480, 320))
            self.assertEqual(load.call_count, original_loads)

    def test_story_stage_does_not_change_the_four_random_battlefields(self):
        self.assertIn(IDENTIFIER, CAVE_BATTLEFIELDS)
        self.assertNotIn(IDENTIFIER, RANDOM_BATTLEFIELDS)
        self.assertEqual(set(RANDOM_BATTLEFIELDS), set(LEGACY_PNG_HASHES))
        for identifier, expected in LEGACY_PNG_HASHES.items():
            with self.subTest(field=identifier):
                paths = sorted((ROOT/'assets/combat'/identifier).glob('*.png'))
                self.assertEqual(sha256(b''.join(path.read_bytes() for path in paths)).hexdigest(), expected)

    def test_channel_lighting_tracks_the_active_form_and_preserves_large_hud_framing(self):
        field=CaveBattlefield(IDENTIFIER)
        from vespermaw_crystals import ElementalCrystals
        before=ElementalCrystals.strengths(0,{'element':'fire','from':'fire','to':'ice','progress':0,'commit':.66})
        after=ElementalCrystals.strengths(0,{'element':'ice','from':'fire','to':'ice','progress':.66,'commit':.66})
        self.assertGreater(before['fire'],before['ice'])
        self.assertGreater(after['ice'],after['fire'])
        self.assertEqual(after['water'],0)
        quiet=ElementalCrystals.strengths(100,{'element':'water'},True)
        self.assertEqual(quiet,ElementalCrystals.strengths(5000,{'element':'water'},True))
        first=pygame.Surface((480,320));second=pygame.Surface((480,320))
        field.draw(first,1000,vertical_offset=0,elemental_state={'element':'ice'})
        field.draw(second,1000,vertical_offset=40,elemental_state={'element':'ice'})
        self.assertEqual(pygame.image.tobytes(first,'RGB'),pygame.image.tobytes(second,'RGB'))
        self.assertEqual(field.crystal_origin('ice',40),field.crystal_origin('ice',0))

    def test_new_field_retains_strict_identity_dimensions_and_frame_path_validation(self):
        valid = CaveBattlefield(IDENTIFIER).data
        with tempfile.TemporaryDirectory(prefix='echo-field-invalid-') as directory:
            destination = Path(directory)/'assets/combat'/IDENTIFIER/'battlefield.json'
            destination.parent.mkdir(parents=True)
            for field, value in (('id', 'cave_depths'), ('size', [240, 160]),
                                 ('frame_duration_ms', True),
                                 ('background_frames', ['../escape.png']),
                                 ('background_frames', ['/tmp/escape.png'])):
                with self.subTest(field=field, value=value):
                    data = deepcopy(valid)
                    data[field] = value
                    destination.write_text(json.dumps(data))
                    with self.assertRaises(ValueError):CaveBattlefield(IDENTIFIER, root=directory)


if __name__ == '__main__':unittest.main()
