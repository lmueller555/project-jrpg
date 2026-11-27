"""Native environment export retains pixels and catches lost source provenance."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools.build_prologue_mountains import LAYERS, build, products


class PrologueMountainExportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.source = self.folder/'source';self.source.mkdir()
        self.target = self.folder/'runtime'
        image = Image.new('RGBA', (4, 3))
        image.putdata([(x*50, y*60, 30, 96 if x == 1 else 255)
                       for y in range(3) for x in range(4)])
        image.save(self.source/'preserved.png')
        self.raw = (self.source/'preserved.png').read_bytes()
        self.recipe = {'version':1, 'density':2,
            'source_records':[{'file':'preserved.png','sha256':sha256(self.raw).hexdigest(),
                               'prompt':'Synthetic export fixture; no runtime artwork.', 'generation_id':'fixture'}],
            'layers':{name:{'source':'preserved.png'} for name in LAYERS}}
        self.write_recipe()

    def write_recipe(self):
        (self.source/'recipe.json').write_text(json.dumps(self.recipe))

    def test_native_crop_alpha_and_padding_preserve_source_pixels_without_scaling(self):
        self.recipe['layers']['crest'].update(crop=[1, 0, 4, 3], canvas=[7, 5],
                                               offset=[2, 1], alpha_threshold=128, anchor=[3, 4])
        self.write_recipe()
        output = products(self.source, self.target)
        original = Image.open(BytesIO(self.raw)).convert('RGBA')
        sky = Image.open(BytesIO(output[self.target/'sky.png']))
        self.assertEqual(sky.size, original.size)
        self.assertEqual(sky.tobytes(), original.tobytes())
        crest = Image.open(BytesIO(output[self.target/'crest.png']))
        self.assertEqual(crest.size, (7, 5))
        self.assertEqual(crest.getpixel((2, 1)), (50, 0, 30, 0))
        self.assertEqual(crest.getpixel((3, 1)), original.getpixel((2, 0)))
        self.assertEqual(crest.getpixel((1, 1)), (0, 0, 0, 0))
        manifest = json.loads(output[self.target/'art.json'])
        self.assertEqual(manifest['density'], 2)
        self.assertEqual(manifest['layers']['crest']['anchor'], [3, 4])
        self.assertEqual((self.source/'preserved.png').read_bytes(), self.raw)

    def test_changed_source_fails_before_any_export_write(self):
        (self.source/'preserved.png').write_bytes(self.raw+b'changed')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            build(source=self.source, target=self.target)
        self.assertFalse(self.target.exists())

    def test_check_detects_stale_exports_without_rewriting_them(self):
        build(source=self.source, target=self.target)
        build(check=True, source=self.source, target=self.target)
        (self.target/'mid.png').write_bytes(b'stale')
        with self.assertRaisesRegex(ValueError, 'mid.png'):
            build(check=True, source=self.source, target=self.target)
        self.assertEqual((self.target/'mid.png').read_bytes(), b'stale')

    def test_registration_cannot_crop_or_resize_away_preserved_pixels(self):
        self.recipe['layers']['mid']['canvas'] = [3, 2]
        self.write_recipe()
        with self.assertRaisesRegex(ValueError, 'complete native crop'):
            products(self.source, self.target)

    def test_missing_layer_is_rejected(self):
        self.recipe['layers'].pop('distant');self.write_recipe()
        with self.assertRaisesRegex(ValueError, 'six named'):
            products(self.source, self.target)


if __name__ == '__main__':unittest.main()
