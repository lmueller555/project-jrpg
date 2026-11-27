"""Source timing and low-alpha cleanup must preserve substantive painted pixels."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from tools import export_prologue_faces as exporter


class FaceExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root/'source'
        self.output = self.root/'output'
        self.review = self.root/'review'
        folder = self.source/'lucan'
        folder.mkdir(parents=True)
        # Tiny colored diagnostics stand in for full drawings in this fixture.
        # Their purpose is pixel preservation and export, never motion quality.
        master = Image.new('RGBA', (4,4))
        master.putpixel((0,0), (255,0,255,8))
        master.putpixel((1,1), (180,80,160,180))
        master.putpixel((2,2), (100,120,130,255))
        self.master = folder/'master.png'
        master.save(self.master)
        self.profile = {
            'version':1, 'actor':'lucan', 'canvas':[768,1024], 'anchor':[384,960],
            'cycle_ms':800, 'alpha_floor':16,
            'contacts':[{'frame':0,'foot':'near'}, {'frame':4,'foot':'far'}],
            'source_sha256':{'master.png':sha256(self.master.read_bytes()).hexdigest()},
            'frames':[{'source':'master.png', 'cell':[0,0,4,4], 'scale':1,
                       'origin':[100,100], 'landmarks':{}} for _ in range(8)],
        }
        (folder/'source_art_48.json').write_text(json.dumps(self.profile))
        for name, value in (('ROOT',self.root), ('SOURCE',self.source),
                            ('OUTPUT',self.output), ('REVIEW',self.review)):
            owner = patch.object(exporter, name, value)
            owner.start()
            self.addCleanup(owner.stop)

    def test_export_uses_authored_duration_and_cleans_only_low_alpha_fringe(self):
        exporter.build_actor('lucan')
        manifest = json.loads((self.output/'lucan/animation.json').read_text())
        self.assertEqual(manifest['duration_ms'],800)
        self.assertEqual([frame['duration_ms'] for frame in manifest['frames']], [100]*8)
        self.assertEqual(manifest['fps'],10)
        with Image.open(self.output/'lucan/frame_00.png') as frame:
            self.assertEqual(frame.getpixel((100,100))[3],0)
            self.assertEqual(frame.getpixel((101,101))[3],180)
            self.assertEqual(frame.getpixel((102,102)),(100,120,130,255))
        exporter.build_actor('lucan', check=True)

    def test_modified_master_cannot_silently_replace_registered_art(self):
        Image.new('RGBA',(4,4),'red').save(self.master)
        with self.assertRaisesRegex(ValueError,'Authored source changed'):
            exporter.build_actor('lucan')

    def test_opaque_generated_card_cannot_be_exported_as_a_character(self):
        Image.new('RGBA',(4,4),'gray').save(self.master)
        self.profile['source_sha256']['master.png'] = sha256(self.master.read_bytes()).hexdigest()
        (self.source/'lucan/source_art_48.json').write_text(json.dumps(self.profile))
        with self.assertRaisesRegex(ValueError,'transparent background'):
            exporter.build_actor('lucan')


if __name__ == '__main__':
    unittest.main()
