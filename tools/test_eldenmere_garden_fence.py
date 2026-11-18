"""Validate modular seams, hinged gate behavior, dry access and review delivery."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'assets/terrain/eldenmere/garden_fence'
SOURCE = ROOT / 'assets/source/terrain/eldenmere/garden_fence'
PREVIOUS = PACK.parent / 'reeds'


def load(path): return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as im: return im.convert('RGBA')


class GardenFenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = load(SOURCE / 'recipe.json')
        cls.fence = load(PACK / 'fence.json')
        cls.gate = load(PACK / 'gate/gate.json')
        cls.scene = load(PACK / 'review_scene.json')
        cls.modules = {m['id']: m for m in cls.fence['modules']}
        cls.frames = [opened(PACK / 'gate' / p['image']) for p in cls.gate['poses']]
        cls.leaves = [opened(PACK / 'gate' / p['leaf']) for p in cls.gate['poses']]

    def test_native_materials_alpha_source_parts_and_scale(self):
        materials = load(PACK / 'palette.json')['materials']
        cottage = load(PACK.parent / 'cottage/palette.json')['materials']
        self.assertEqual(materials['wood'], cottage['wood'])
        self.assertEqual(materials['iron'], cottage['iron'])
        colors = {tuple(bytes.fromhex(c[1:])) for ramp in materials.values() for c in ramp.values()}
        for path in list((PACK / 'parts').glob('*.png')) + list((PACK / 'modules').rglob('*.png')) + list((PACK / 'gate').rglob('*.png')):
            im = opened(path)
            self.assertLessEqual(set(im.getchannel('A').get_flattened_data()), {0, 255})
            self.assertTrue(all(not p[3] or p[:3] in colors for p in im.get_flattened_data()), path)
        for sample in self.recipe['samples']:
            path = f"parts/{sample['id']}.png"
            self.assertEqual(opened(PACK / path).size, tuple(sample['size']))
            self.assertEqual(opened(PACK / path).tobytes(), opened(SOURCE / path).tobytes())
        self.assertEqual(opened(PACK / 'parts/post.png').size, (4, 18))
        self.assertFalse(self.fence['cloth_details'])
        self.assertFalse(self.fence['ambient_motion'])
        self.assertFalse(self.fence['collision_implemented'])

    def test_complete_connection_set_exact_layers_sheet_and_rail_seams(self):
        self.assertEqual(self.fence['frame_size'], [24, 48])
        self.assertEqual(self.fence['ground_rect'], [0, 20, 24, 24])
        self.assertEqual(len(self.modules), 30)
        for wear in ('a', 'b'):
            self.assertEqual({m['mask'] for m in self.modules.values() if m['wear_variant'] == wear}, set(range(1, 16)))
        self.assertNotEqual(opened(PACK / 'parts/upper_a.png').tobytes(), opened(PACK / 'parts/upper_b.png').tobytes())
        sheet = opened(PACK / 'modules.png')
        self.assertEqual(sheet.size, (240, 144))
        post = opened(PACK / 'modules/ew_a/post.png')
        for name, record in self.modules.items():
            expected = Image.new('RGBA', (24, 48))
            for layer in ('shadow', 'rails', 'post'): expected.alpha_composite(opened(PACK / 'modules' / name / f'{layer}.png'))
            self.assertEqual(expected.tobytes(), opened(PACK / record['image']).tobytes())
            self.assertEqual(opened(PACK / 'modules' / name / 'post.png').tobytes(), post.tobytes())
            x, y, w, h = record['sheet_rect']
            self.assertEqual(sheet.crop((x, y, x + w, y + h)).tobytes(), expected.tobytes())
            rails = opened(PACK / 'modules' / name / 'rails.png')
            for direction in record['connections']:
                if direction in ('E', 'W'):
                    x = 23 if direction == 'E' else 0
                    self.assertTrue(all(rails.getpixel((x, y))[3] == 255 for y in (16, 17, 18, 26, 27, 28)))
                else:
                    upper, lower = (4, 14) if direction == 'N' else (27, 37)
                    self.assertTrue(all(rails.getpixel((x, upper))[3] for x in (10, 11, 12)))
                    self.assertTrue(all(rails.getpixel((x, lower))[3] for x in (12, 13, 14)))
        ports = self.fence['ports']
        self.assertEqual(ports['E'], [ports['W'][0] + 24, ports['W'][1]])
        self.assertEqual(ports['S'], [ports['N'][0], ports['N'][1] + 24])

    def test_fixed_hinges_latch_release_swing_settling_and_full_opening(self):
        meta = self.gate
        self.assertEqual(meta['clear_opening_width_pixels'], 24)
        self.assertEqual(meta['hinge_axis_x'], 11)
        self.assertEqual(meta['opens_toward'], 'north')
        self.assertFalse(meta['autonomous_open_close'])
        self.assertFalse(meta['animations']['opening']['loop'])
        self.assertFalse(meta['animations']['closing']['loop'])
        self.assertEqual(meta['animations']['opening']['frames'], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(meta['animations']['closing']['frames'], [4, 3, 2, 1, 0])
        self.assertEqual([p['angle_degrees'] for p in meta['poses']], [0, 0, 20, 45, 70, 90, 88, 90])
        post = opened(PACK / 'gate/posts_hinges.png')
        shadow = opened(PACK / 'gate/shadow.png')
        sheet = opened(PACK / 'gate/sheet.png')
        self.assertEqual(sheet.size, (384, 48))
        for index, (frame, leaf) in enumerate(zip(self.frames, self.leaves, strict=True)):
            expected = shadow.copy(); expected.alpha_composite(leaf); expected.alpha_composite(post)
            self.assertEqual(frame.tobytes(), expected.tobytes())
            self.assertEqual(sheet.crop((index * 48, 0, (index + 1) * 48, 48)).tobytes(), frame.tobytes())
            self.assertIsNone(ImageChops.multiply(ImageChops.difference(frame.convert('RGB'), self.frames[0].convert('RGB')),
                                                 post.getchannel('A').convert('RGB')).getbbox())
        panel = opened(PACK / 'gate/panel.png'); latch = opened(PACK / 'gate/latch.png')
        self.assertIsNotNone(latch.getbbox())
        for phase, lift in ((0, 0), (1, 1)):
            whole = panel.copy(); whole.alpha_composite(latch, (0, -lift))
            expected = Image.new('RGBA', (48, 48)); expected.alpha_composite(whole, (12, 24))
            self.assertEqual(expected.tobytes(), self.leaves[phase].tobytes())
        rights = [self.leaves[i].getbbox()[2] for i in (1, 2, 3, 4, 5)]
        self.assertTrue(all(a > b for a, b in zip(rights, rights[1:])))
        self.assertLess(self.leaves[7].getbbox()[1], self.leaves[0].getbbox()[1] - 16)
        self.assertEqual(self.frames[5].tobytes(), self.frames[7].tobytes())
        self.assertNotEqual(self.frames[6].tobytes(), self.frames[7].tobytes())
        self.assertIsNone(self.frames[7].crop((12, 0, 36, 40)).getbbox())

    def test_enclosure_connections_clear_gate_and_level_connected_approach(self):
        scene = self.scene
        by_cell = {tuple(i['cell']): i for i in scene['instances']}
        gate_cell = tuple(scene['gate_cell'])
        self.assertNotIn(gate_cell, by_cell)
        self.assertEqual(len(by_cell), 17)
        offsets = {'N': (0, -1), 'E': (1, 0), 'S': (0, 1), 'W': (-1, 0)}
        opposite = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
        for cell, instance in by_cell.items():
            self.assertEqual(instance['ground_elevation_pixels'], 0)
            self.assertEqual(instance['position'], [cell[0] * 24, cell[1] * 24 - 20])
            for direction in self.modules[instance['module']]['connections']:
                dx, dy = offsets[direction]; neighbor = cell[0] + dx, cell[1] + dy
                self.assertIn(neighbor, set(by_cell) | {gate_cell})
                if neighbor != gate_cell:
                    self.assertIn(opposite[direction], self.modules[by_cell[neighbor]['module']]['connections'])
        old = load(PACK.parent / 'cottage_shapes/review_scene.json')
        cells = {tuple(c) for c in old['path_cells']} | {tuple(c) for c in scene['path_cells_added']}
        start = tuple(scene['path_join_cell']); reached = {start}; todo = [start]
        while todo:
            x, y = todo.pop()
            for dx, dy in offsets.values():
                q = x + dx, y + dy
                if q in cells and q not in reached: reached.add(q); todo.append(q)
        self.assertIn(gate_cell, reached)
        self.assertIn((gate_cell[0], gate_cell[1] - 1), reached)
        self.assertIn((26, 42), reached)  # Existing cottage's dry doorstep apron.
        path = opened(PACK / 'review_path.png'); gm = load(PACK.parent / 'grass_dirt/tileset.json')
        neighbors = ((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
        for x, y in {tuple(c) for c in scene['path_cells_added']} | {start}:
            raw = sum(1 << i for i, (dx, dy) in enumerate(neighbors) if (x + dx, y + dy) in cells)
            tile = opened(PACK.parent / 'grass_dirt' / gm['tiles'][gm['lookup_256'][raw]]['image'])
            self.assertEqual(tile.tobytes(), path.crop((x*24,y*24,x*24+24,y*24+24)).tobytes())

    def test_exact_scene_reconstruction_local_changes_and_parent_timing(self):
        self.assertEqual(self.scene['grid_size'], [40, 54])
        self.assertEqual(len(self.scene['frames']), 108)
        self.assertEqual(self.scene['cycle_duration_ms'], 10800)
        self.assertTrue(self.scene['gate_use_is_demonstration_only'])
        ground = opened(PACK / 'review_ground.png'); paths = opened(PACK / 'review_path.png')
        static = Image.new('RGBA', ground.size)
        for layer in ('shadow', 'rails'):
            for instance in self.scene['instances']:
                static.alpha_composite(opened(PACK / 'modules' / instance['module'] / f'{layer}.png'), tuple(instance['position']))
        posts = Image.new('RGBA', ground.size)
        for instance in self.scene['instances']:
            posts.alpha_composite(opened(PACK / 'modules' / instance['module'] / 'post.png'), tuple(instance['position']))
        gate_position = tuple(self.scene['gate_position'])
        for tick, record in enumerate(self.scene['frames']):
            self.assertEqual(record['parent_frame'], tick // 2)
            self.assertEqual(record['duration_ms'], 100)
            expected = ground.copy(); previous = opened(PREVIOUS / f'scene_frames/frame_{tick//2+1:02}.png'); expected.paste(previous, (0,0))
            allowed = paths.getchannel('A').copy(); expected.alpha_composite(paths)
            for p in self.scene['garden_plants']:
                phase = (tick // 6 + p['phase_offset']) % 9
                plant = opened(PACK.parent / p['pack'] / p['plant'] / f'frames/frame_{phase+1:02}.png')
                expected.alpha_composite(plant, tuple(p['position'])); allowed.paste(plant.getchannel('A'), tuple(p['position']))
            expected.alpha_composite(static); allowed = ImageChops.lighter(allowed, static.getchannel('A'))
            expected.alpha_composite(opened(PACK / 'gate/shadow.png'), gate_position)
            expected.alpha_composite(self.leaves[record['gate_pose']], gate_position)
            expected.alpha_composite(posts)
            expected.alpha_composite(opened(PACK / 'gate/posts_hinges.png'), gate_position)
            actual = opened(PACK / record['image']); self.assertEqual(actual.size, (960,1296)); self.assertEqual(expected.tobytes(), actual.tobytes())
            allowed = ImageChops.lighter(allowed, posts.getchannel('A'))
            g = Image.new('L', ground.size); g.paste(self.frames[record['gate_pose']].getchannel('A'), gate_position); allowed = ImageChops.lighter(allowed, g)
            difference = ImageChops.difference(actual.crop((0,0,768,1296)).convert('RGB'), previous.convert('RGB'))
            outside = ImageChops.invert(allowed.crop((0,0,768,1296))).convert('RGB')
            self.assertIsNone(ImageChops.multiply(difference, outside).getbbox())
        poses = [r['gate_pose'] for r in self.scene['frames']]
        self.assertEqual(poses[:54], poses[54:])
        self.assertEqual(poses[8:15], list(range(1,8)))
        self.assertEqual(poses[33:38], [4,3,2,1,0])

    def test_scene_gifs_lossless_pixels_durations_and_loops(self):
        for name, crop, scale in (('review_scene', None, 2), ('garden_closeup', self.scene['review']['closeup_rect'], 4)):
            tick = 0
            with Image.open(PACK / f'{name}.gif') as gif:
                self.assertEqual(gif.info['loop'], 0)
                for encoded in range(gif.n_frames):
                    gif.seek(encoded); duration = gif.info['duration']; self.assertEqual(duration % 100, 0)
                    actual = gif.convert('RGB')
                    for i in range(tick, tick + duration // 100):
                        expected = opened(PACK / self.scene['frames'][i]['image']).convert('RGB')
                        if crop: expected = expected.crop(crop)
                        expected = expected.resize((expected.width*scale,expected.height*scale),Image.Resampling.NEAREST)
                        self.assertEqual(actual.tobytes(), expected.tobytes())
                    tick += duration // 100
                self.assertEqual(tick, 108)
                gif.seek(0); self.assertEqual(gif.convert('RGB').tobytes(), opened(PACK / f'{name}.png').convert('RGB').tobytes())

    def test_module_board_exact_pixels_and_matching_character_scale(self):
        tick = 0
        names = ('ew_a','ew_b','ns_a','ne_a','nes_a','nesw_a','e_a')
        with Image.open(PACK / 'modules_review.gif') as gif:
            self.assertEqual(gif.info['loop'], 0)
            for encoded in range(gif.n_frames):
                gif.seek(encoded); duration = gif.info['duration']; self.assertEqual(duration % 100, 0); board = gif.convert('RGB')
                for t in range(tick, tick + duration // 100):
                    pose = self.scene['frames'][t]['gate_pose']
                    for index, name in enumerate(names):
                        tile = Image.new('RGBA',(24,48),'#70935a'); tile.alpha_composite(opened(PACK / 'modules' / name / 'module.png'))
                        expected = tile.convert('RGB').resize((144,288),Image.Resampling.NEAREST); x=20+index%4*310; y=88+index//4*334
                        self.assertEqual(expected.tobytes(),board.crop((x,y,x+144,y+288)).tobytes())
                    tile=Image.new('RGBA',(48,48),'#70935a');tile.alpha_composite(self.frames[pose])
                    self.assertEqual(tile.convert('RGB').resize((288,288),Image.Resampling.NEAREST).tobytes(),board.crop((720,772,1008,1060)).tobytes())
                    tile=Image.new('RGBA',(72,48),'#70935a');tile.alpha_composite(opened(ROOT/'assets/characters/caelan/idle_front.png'),(2,4));tile.alpha_composite(self.frames[pose],(24,0))
                    self.assertEqual(tile.convert('RGB').resize((216,144),Image.Resampling.NEAREST).tobytes(),board.crop((20,856,236,1000)).tobytes())
                tick += duration // 100
            self.assertEqual(tick,54)


if __name__ == '__main__': unittest.main()
