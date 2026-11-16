"""Native density, reproducible sources and explicit scene-bank retirement."""
from pathlib import Path
import hashlib,json,unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/caelan/scene_actions_hd'
class CaelanSceneActionsHDTests(unittest.TestCase):
    def test_registered_art_is_native_two_density_and_has_hard_alpha(self):
        data=json.loads((ROOT/'assets/characters/caelan/scene_actions.json').read_text())
        self.assertGreaterEqual(len(data['outputs']),130)
        for rec in data['outputs']:
            with self.subTest(file=rec['file']):
                path=ROOT/rec['file']
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),rec['output_sha256'])
                with Image.open(path) as im:
                    self.assertEqual(list(im.size),[v*2 for v in rec['logical_size']])
                    self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255})
                self.assertEqual(rec['anchor_space'],'logical')
        for rec in data['sources']:
            self.assertEqual(hashlib.sha256((ROOT/rec['file']).read_bytes()).hexdigest(),rec['sha256'])
    def test_retired_inputs_and_builders_have_no_remaining_files(self):
        ledger=json.loads((SOURCE/'retired.json').read_text())
        for rec in ledger['removed_files']:
            self.assertFalse((ROOT/rec['path']).exists(),rec['path'])
    def test_export_is_reproducible(self):
        from tools.export_caelan_scene_actions_hd import build
        build(check=True)
    def test_approved_travel_is_unchanged(self):
        protected=json.loads((SOURCE/'protected_travel.json').read_text())
        for name,digest in protected.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
