"""Authored eagle export preserves anatomy, registration and source provenance."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from tools.build_prologue_eagle import ANCHOR, CANVAS, SOURCE, TARGET, build, products


def pixels(image):
    reader = getattr(image, 'get_flattened_data', None)
    return list(reader() if reader is not None else image.getdata())


class PrologueEagleExportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.source = self.folder/'source';self.source.mkdir()
        self.target = self.folder/'runtime'
        self.recipe = {'version':1, 'canvas':list(CANVAS), 'anchor':list(ANCHOR),
            'density':2, 'alpha_threshold':128, 'palette_colors':128, 'sources':{},
            'sequences':{
                'flap':{'loop':True, 'durations_ms':[47]*14+[46,46],
                        'cells':list(range(16)), 'source':'flap'},
                'bank':{'loop':False, 'duration_ms':375,
                        'cells':list(range(8)), 'source':'bank'},
                'glide':{'loop':True, 'duration_ms':250,
                         'cells':[6,7], 'source':'bank'}},
            'timing':{'period_ms':750, 'first_phase_ms':391,
                      'second_phase_ms':141, 'downstroke_phase':.25}}
        self.raw_sources = {}
        for name, columns, rows, width, height, scale, chest in (
                ('flap',4,4,197,189,1,[24,24]),
                ('bank',4,2,245,127,.8,[30.5,32])):
            sheet = Image.new('RGBA',(width,height))
            for cell in range(columns*rows):
                column, row = cell % columns, cell // columns
                left, top = round(column*width/columns), round(row*height/rows)
                right, bottom = round((column+1)*width/columns), round((row+1)*height/rows)
                pose = Image.new('RGBA',(right-left,bottom-top))
                draw = ImageDraw.Draw(pose)
                cx, cy = map(round,chest)
                # A connected reddish-brown torso and gold head must survive.
                draw.rectangle((cx-4,cy-5,cx+4,cy+9),fill=(90,40,25,255))
                draw.rectangle((cx-2,cy-11,cx+2,cy-5),fill=(180,140,60,255))
                reach = 10+cell % 4
                draw.rectangle((cx-reach,cy-3+cell//4,cx+reach,cy+cell//4),
                               fill=(110,70,40,255))
                for x in range(15):
                    for y in range(7):
                        grey = (cell*17+x*11+y*9) % 256
                        pose.putpixel((x+2,y+3),(grey,grey,grey,255))
                pose.putpixel((0,0),(255,0,0,255))
                pose.putpixel((1,0),(0,255,0,255))
                pose.putpixel((2,0),(30,40,70,127))
                pose.putpixel((3,0),(30,40,70,128))
                sheet.paste(pose,(left,top))
            path = self.source/(name+'_generated.png')
            sheet.save(path)
            raw = path.read_bytes()
            self.raw_sources[path.name] = raw
            self.recipe['sources'][name] = {'file':path.name,'sha256':sha256(raw).hexdigest(),
                'grid':[columns,rows],'scale':scale,'chest_anchor':chest}
        self.write_recipe()

    def write_recipe(self):
        (self.source/'recipe.json').write_text(json.dumps(self.recipe))

    def export(self):
        return products(self.source,self.target)

    def test_common_palette_binary_alpha_and_full_frames(self):
        output = self.export()
        colors = set()
        files = [path for path in output if path.suffix == '.png']
        self.assertEqual(len(files),24)
        for path in files:
            image = Image.open(BytesIO(output[path])).convert('RGBA')
            self.assertEqual(image.size,CANVAS)
            self.assertEqual(set(image.getchannel('A').getextrema()),{0,255})
            self.assertLessEqual(set(pixels(image.getchannel('A'))),{0,255})
            colors.update(pixel[:3] for pixel in pixels(image) if pixel[3])
        self.assertLessEqual(len(colors),128)
        provenance = json.loads(output[self.target/'export_provenance.json'])
        palette = provenance['palette_rgb']
        self.assertEqual(sha256(bytes(palette)).hexdigest(),provenance['palette_sha256'])
        self.assertTrue(colors <= {tuple(palette[index:index+3]) for index in range(0,len(palette),3)})

    def test_dark_brown_torso_and_head_remain_solid_while_matte_disappears(self):
        output = self.export()
        frame = Image.open(BytesIO(output[self.target/'flap_01.png'])).convert('RGBA')
        dx, dy = ANCHOR[0]-24, ANCHOR[1]-24
        for x in range(20,29):
            for y in range(19,34):
                self.assertEqual(frame.getpixel((x+dx,y+dy))[3],255,(x,y))
        for y in range(13,24):
            self.assertEqual(frame.getpixel((24+dx,y+dy))[3],255,y)
        for x in (0,1,2):self.assertEqual(frame.getpixel((x+dx,dy))[3],0,x)
        self.assertEqual(frame.getpixel((3+dx,dy))[3],255)

    def test_chest_registration_is_fixed_as_wing_bounds_and_cell_sizes_change(self):
        output = self.export()
        provenance = json.loads(output[self.target/'export_provenance.json'])
        flap = [provenance['frames'][f'flap_{index:02}.png'] for index in range(1,17)]
        self.assertEqual({tuple(record['offset']) for record in flap},{(104,120)})
        self.assertGreater(len({tuple(record['source_occupied_bounds']) for record in flap}),1)
        self.assertEqual(flap[0]['crop'],[0,0,49,47])
        self.assertEqual(flap[1]['crop'],[49,0,98,47])
        self.assertEqual(flap[-1]['crop'],[148,142,197,189])
        for source in ('flap','bank'):
            sizes = {tuple(record['scaled_canvas']) for record in provenance['frames'].values()
                     if record['source'] == source}
            self.assertEqual(len(sizes),1,source)
        for name, record in provenance['frames'].items():
            spec = self.recipe['sources'][record['source']]
            expected = [round(coordinate*spec['scale']) for coordinate in spec['chest_anchor']]
            self.assertEqual(record['scaled_chest_anchor'],expected,name)
            self.assertEqual([record['offset'][axis]+expected[axis] for axis in range(2)],list(ANCHOR),name)
            self.assertTrue(0 <= record['occupied_bounds'][0] < record['occupied_bounds'][2] <= CANVAS[0])
            self.assertTrue(0 <= record['occupied_bounds'][1] < record['occupied_bounds'][3] <= CANVAS[1])

    def test_timing_and_authored_handoffs_reuse_complete_frames(self):
        self.recipe['sequences']['bank']['frame_files'] = ['flap_04.png']+[
            f'bank_{index:02}.png' for index in range(2,8)]+['flap_04.png']
        self.recipe['sequences']['glide']['frame_files'] = ['flap_04.png','flap_13.png']
        self.write_recipe()
        manifest = json.loads(self.export()[self.target/'animation.json'])
        self.assertEqual(manifest['timing'],self.recipe['timing'])
        sequences = manifest['sequences']
        self.assertEqual([len(sequences[name]['frames']) for name in ('flap','bank','glide')],[16,8,2])
        self.assertEqual([sum(frame['duration_ms'] for frame in sequences[name]['frames'])
                          for name in ('flap','bank','glide')],[750,3000,500])
        self.assertTrue(sequences['flap']['loop'])
        self.assertFalse(sequences['bank']['loop'])
        self.assertTrue(sequences['glide']['loop'])
        self.assertEqual(sequences['bank']['frames'][0]['file'],sequences['bank']['frames'][-1]['file'])
        self.assertEqual([frame['file'] for frame in sequences['glide']['frames']],['flap_04.png','flap_13.png'])

    def test_default_glide_references_bank_frames_without_duplicate_exports(self):
        output = self.export()
        manifest = json.loads(output[self.target/'animation.json'])
        self.assertEqual([frame['file'] for frame in manifest['sequences']['glide']['frames']],
                         ['bank_07.png','bank_08.png'])
        self.assertFalse(any(path.name.startswith('glide_') for path in output))

    def test_reproduction_and_check_preserve_sources_and_detect_stale_output(self):
        first = build(source=self.source,target=self.target)
        second = products(self.source,self.folder/'other')
        self.assertEqual({path.name:data for path,data in first.items()},
                         {path.name:data for path,data in second.items()})
        build(check=True,source=self.source,target=self.target)
        for name,raw in self.raw_sources.items():self.assertEqual((self.source/name).read_bytes(),raw)
        (self.target/'flap_01.png').write_bytes(b'stale')
        with self.assertRaisesRegex(ValueError,'flap_01.png'):
            build(check=True,source=self.source,target=self.target)
        self.assertEqual((self.target/'flap_01.png').read_bytes(),b'stale')

    def test_changed_source_fails_before_any_runtime_write(self):
        path = self.source/'flap_generated.png'
        path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'source changed'):
            build(source=self.source,target=self.target)
        self.assertFalse(self.target.exists())

    def test_export_rejects_clipped_pose_instead_of_resizing_its_anatomy(self):
        self.recipe['sources']['flap']['scale'] = 20;self.write_recipe()
        with self.assertRaisesRegex(ValueError,'clips the authored pose'):self.export()

    def test_sequence_cannot_escape_to_an_unexported_image(self):
        self.recipe['sequences']['glide']['frame_files'] = ['../missing.png','flap_13.png']
        self.write_recipe()
        with self.assertRaisesRegex(ValueError,'complete poses'):self.export()


class PrologueEagleProductionAssetsTests(unittest.TestCase):
    def test_preserved_art_exports_are_current_distinct_and_registered(self):
        recipe = json.loads((SOURCE/'recipe.json').read_text())
        before = {spec['file']:(SOURCE/spec['file']).read_bytes() for spec in recipe['sources'].values()}
        output = build(check=True)
        manifest = json.loads(output[TARGET/'animation.json'])
        self.assertEqual(manifest['canvas'],[256,256])
        self.assertEqual(manifest['anchor'],[128,144])
        self.assertEqual(manifest['density'],2)
        for prefix,count in (('flap',16),('bank',8)):
            frames = [output[TARGET/f'{prefix}_{index:02}.png'] for index in range(1,count+1)]
            self.assertEqual(len(set(frames)),count,prefix)
        colors = set()
        for path,data in output.items():
            if path.suffix != '.png':continue
            frame = Image.open(BytesIO(data)).convert('RGBA')
            self.assertEqual(frame.size,(256,256))
            self.assertLessEqual(set(pixels(frame.getchannel('A'))),{0,255})
            colors.update(pixel[:3] for pixel in pixels(frame) if pixel[3])
        self.assertLessEqual(len(colors),128)
        for name,raw in before.items():self.assertEqual((SOURCE/name).read_bytes(),raw)


if __name__ == '__main__':unittest.main()
