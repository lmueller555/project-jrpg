"""Check native quest states, access, preserved artwork and delivered GIF pixels."""
from collections import deque
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT/'assets/terrain/eldenmere/elira_interior'


def load(path):
    return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as image:
        return image.convert('RGBA')


class EliraInteriorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.room = load(PACK/'room.json')
        cls.base = ROOT/Path(cls.room['base_room']).parent
        cls.recipe = load(ROOT/'assets/source/terrain/eldenmere/elira_interior/recipe.json')

    def test_native_props_and_exact_shelf_states(self):
        lantern = opened(PACK/'sprites/lantern_unlit.png')
        stool = opened(PACK/'sprites/step_stool.png')
        self.assertEqual(lantern.size, (12,24))
        self.assertEqual(stool.size, (24,24))
        for sprite in (lantern, stool):
            self.assertEqual(set(sprite.getchannel('A').get_flattened_data()), {0,255})
            self.assertGreater(sum(a>0 for a in sprite.getchannel('A').get_flattened_data()), 70)
        expected = Image.new('RGBA', (48,40))
        expected.alpha_composite(opened(ROOT/'assets/terrain/eldenmere/cottage_storage/sprites/shelf.png'), (0,16))
        empty = opened(PACK/'sprites/shelf_empty.png')
        self.assertEqual(empty.tobytes(), expected.tobytes())
        expected.alpha_composite(lantern, tuple(self.recipe['lantern_on_shelf']))
        self.assertEqual(opened(PACK/'sprites/shelf_with_lantern.png').tobytes(), expected.tobytes())
        # The lantern ends directly above the central shelf board, without covering it.
        self.assertEqual(self.recipe['lantern_on_shelf'][1]+lantern.getbbox()[3], 27)
        self.assertFalse(self.room['lantern']['lit'])

    def test_actor_can_reach_stool_and_existing_furnishings(self):
        blocked = Image.open(PACK/'blocking.png').convert('L')
        x0,y0,w,h = self.room['floor_rect']
        pw,ph = self.room['actor_probe_size']
        self.assertEqual((pw,ph), (24,12))
        stool = self.room['step_stool']['floor_rect']
        base_blocked = Image.open(self.base/'blocking.png').convert('L')
        sx,sy,sw,sh = stool
        self.assertIsNone(base_blocked.crop((sx,sy,sx+sw,sy+sh)).getbbox())
        base_blocked.paste(255,(sx,sy,sx+sw,sy+sh))
        self.assertEqual(blocked.tobytes(), base_blocked.tobytes())
        def free(x,y):
            return (x0+pw//2<=x<=x0+w-pw//2 and y0+ph//2<=y<=y0+h-ph//2
                    and not blocked.crop((x-pw//2,y-ph//2,x+pw//2,y+ph//2)).getbbox())
        reached=set()
        queue=deque([tuple(self.room['navigation_start'])])
        while queue:
            x,y=queue.popleft()
            if (x,y) in reached or not free(x,y):
                continue
            reached.add((x,y))
            queue.extend(((x-2,y),(x+2,y),(x,y-2),(x,y+2)))
        for record in self.room['objects']:
            self.assertIn(tuple(record['access']),reached,record['id'])
        self.assertIn(tuple(self.room['interaction_approach']),reached)
        self.assertEqual(self.room['floor_tiles'], [10,10])
        self.assertFalse(self.room['quest_interaction_implemented'])

    def test_frames_preserve_entire_base_outside_new_props(self):
        base_room=load(self.base/'room.json')
        stool=opened(PACK/'sprites/step_stool.png')
        self.assertEqual(self.room['hero_position'],base_room['hero_position'])
        for key in ('floor_rect','entry_rect','room_size'):
            self.assertEqual(self.room[key],base_room[key])
        for index,record in enumerate(self.room['frames']):
            base=opened(self.base/base_room['frames'][index]['image'])
            self.assertEqual((record['duration_ms'],record['fire_phase'],record['daylight_phase']),
                             (300,index%4,index//2%9))
            rendered=[]
            for state in ('before','after'):
                expected=base.copy()
                expected.alpha_composite(opened(PACK/self.room['shelf_states'][state]),tuple(self.room['shelf_position']))
                expected.alpha_composite(stool,tuple(self.room['step_stool']['position']))
                actual=opened(PACK/record[state])
                self.assertEqual(actual.tobytes(),expected.tobytes())
                rendered.append(actual.convert('RGB'))
            diff=ImageChops.difference(*rendered).getbbox()
            self.assertIsNotNone(diff)
            x,y=self.room['shelf_position']
            lx,ly=self.recipe['lantern_on_shelf']
            self.assertGreaterEqual(diff[0],x+lx)
            self.assertGreaterEqual(diff[1],y+ly)
            self.assertLessEqual(diff[2],x+lx+12)
            self.assertLessEqual(diff[3],y+ly+24)

    def test_review_gif_exact_native_pixels_timing_and_loop(self):
        with Image.open(PACK/'room_states_review.gif') as gif:
            self.assertEqual(gif.size,(1800,1110))
            self.assertEqual(gif.info['loop'],0)
            self.assertEqual(gif.n_frames,36)
            total=0
            for tick in range(gif.n_frames):
                gif.seek(tick)
                self.assertEqual(gif.info['duration'],300)
                total+=gif.info['duration']
                decoded=gif.convert('RGB')
                if tick==0:
                    self.assertEqual(decoded.tobytes(),opened(PACK/'room_states_review.png').convert('RGB').tobytes())
                for state,(x,y) in zip(('before','after'),self.room['review']['panel_positions'],strict=True):
                    native=opened(PACK/self.room['frames'][tick][state]).convert('RGB')
                    expected=native.resize((864,1008),Image.Resampling.NEAREST)
                    self.assertEqual(decoded.crop((x,y,x+864,y+1008)).tobytes(),expected.tobytes())
            self.assertEqual(total,10800)


if __name__ == '__main__':
    unittest.main()
