"""The emergency worker remains a grounded native derivative after rebuilding."""
from hashlib import sha256
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from tools.build_regent_emergency_assets import products


ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets/story/regent_emergency'


class RegentEmergencyAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.animation=json.loads((ASSETS/'animation.json').read_text())
        cls.recipe=json.loads((ROOT/cls.animation['source_recipe']).read_text())

    def test_original_inputs_and_every_export_match_the_retained_source(self):
        for record in self.recipe['sources']:
            with self.subTest(source=record['path']):
                self.assertEqual(sha256((ROOT/record['path']).read_bytes()).hexdigest(),record['sha256'])
        for path,body in products().items():
            with self.subTest(export=path.relative_to(ROOT)):
                self.assertEqual(path.read_bytes(),body)

    def test_injured_walking_retains_native_boot_contact_and_unequal_limp_cadence(self):
        self.assertEqual(self.animation['frame_size'],[24,36])
        self.assertEqual(self.animation['draw_anchor'],[12,30])
        self.assertEqual(self.animation['probe_size'],[8,4])
        for direction in ('front','back','left','right'):
            frames=self.animation['walks'][direction]
            self.assertEqual(len(frames),6)
            self.assertEqual(len(set(frames)),4)
            self.assertEqual(frames[2],frames[3])
            self.assertEqual(frames[4],frames[5])
            for index in range(4):
                path=ASSETS/f'walk_{direction}/frame_{index:02}.png'
                source=ROOT/self.recipe['source_sprite_root']/f'walk_{direction}/frame_{index+1:02}.png'
                with self.subTest(direction=direction,pose=index),Image.open(path) as actual,Image.open(source) as original:
                    actual=actual.convert('RGBA');original=original.convert('RGBA')
                    self.assertEqual(actual.size,(24,36))
                    self.assertLessEqual(set(actual.getchannel('A').get_flattened_data()),{0,255})
                    self.assertEqual(actual.crop((0,29,24,36)).tobytes(),
                                     original.crop((0,29,24,36)).tobytes())
                    self.assertNotEqual(actual.tobytes(),original.tobytes())

    def test_actor_and_portrait_registration_use_the_new_derivative_without_replacing_sources(self):
        art=json.loads((ROOT/'assets/story/regent/art.json').read_text())
        worker=next(record for record in art['actors'] if record['id']=='regent_survivor')
        self.assertEqual(worker['art'],'assets/story/regent_emergency/animation.json')
        self.assertEqual(worker['draw_anchor'],self.animation['draw_anchor'])
        self.assertEqual(worker['probe_size'],self.animation['probe_size'])
        self.assertEqual(next(record for record in art['actors'] if record['id']=='regent_clerk')['name'],'Page')
        portraits=json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())['portraits']
        target=ROOT/'assets/portraits/eldenmere'/portraits['regent_survivor']['file']
        self.assertEqual(target.read_bytes(),(ASSETS/'portrait.png').read_bytes())
        with Image.open(target) as derived,Image.open(ROOT/self.recipe['source_portrait']) as original:
            self.assertEqual(derived.size,(72,72))
            self.assertNotEqual(derived.tobytes(),original.tobytes())

    def test_existing_visit_builder_retains_emergency_actor_and_modern_room_stations(self):
        builder=importlib.import_module('tools.build_regent_quest')
        # The historical builder records repository-relative Lucan paths.
        # Keep its disposable output inside the repository without touching
        # any checked-in asset or depending on a patched image loader.
        with tempfile.TemporaryDirectory(prefix='.regent-rebuild-',dir=ROOT) as directory:
            output=Path(directory)
            for name in ('art.json','layout.json'):
                (output/name).write_bytes((ROOT/'assets/story/regent'/name).read_bytes())
            before=json.loads((output/'layout.json').read_text())
            with patch.object(builder,'OUT',output):builder.build()
            rebuilt=json.loads((output/'art.json').read_text())
            self.assertEqual(sum(record['id']=='regent_survivor' for record in rebuilt['actors']),1)
            self.assertEqual(next(record for record in rebuilt['actors'] if record['id']=='regent_clerk')['name'],'Page')
            layout=json.loads((output/'layout.json').read_text())
            for key in ('survivor_start','survivor_entry','survivor_rest','survivor_seat',
                        'serene_aid','tomas_aid','driver_aid'):
                self.assertEqual(layout[key],before[key])


if __name__=='__main__':unittest.main()
