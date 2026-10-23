"""Validate cottage-size alignment, furniture access, preserved sprites and previews."""
from collections import deque
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/cottage_layouts'
TERRAIN=PACK.parent


def load(path):return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as image:return image.convert('RGBA')


class CottageLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=load(PACK/'layouts.json')
        cls.rooms=[load(PACK/r['room']) for r in cls.index['layouts']]

    def test_exact_floor_envelopes_and_exterior_door_chimney_registration(self):
        self.assertEqual([r['floor_tiles'] for r in self.rooms],[[6,6],[8,6],[10,6]])
        self.assertEqual([r['entry_rect'][0]+12 for r in self.rooms],[72,120,168])
        base=load(TERRAIN/'cottage/cottage.json')
        chimney=next(r for r in base['components'] if r['id']=='chimney')
        for room in self.rooms:
            pack=PACK/room['id'];ext=load(TERRAIN/room['exterior']/'cottage.json')
            x,y,w,h=room['floor_rect'];self.assertEqual((x,y,h),(24,72,144))
            self.assertEqual(room['room_size'],[w+48,240])
            self.assertEqual([w,h],[ext['ground_rect'][2]*2,ext['ground_rect'][3]*2])
            floor=opened(pack/'floor.png')
            self.assertEqual(sum(p>0 for p in floor.getchannel('A').get_flattened_data()),w*h)
            gx=ext['ground_rect'][0];width=ext['ground_rect'][2]
            desired=24+(ext['door']['position'][0]+ext['door']['size'][0]/2-gx)/width*w
            self.assertLessEqual(abs(room['entry_rect'][0]+12-desired),1)
            cx=chimney['position'][0]+(chimney['rect'][2]-chimney['rect'][0])/2
            desired_chimney=24+(cx+ext.get('animation_offset_from_source',[0,0])[0]-gx)/width*w
            hearth=next(r for r in room['objects'] if r['id']=='hearth')
            self.assertEqual(hearth['position'][0]+24,desired_chimney)
            ex,ey,ew,eh=room['entry_rect']
            self.assertEqual(opened(pack/'walls.png').crop((ex,ey,ex+ew,ey+eh)).tobytes(),opened(TERRAIN/'cottage_interior/tiles/entry_threshold.png').tobytes())

    def test_source_sprite_sizes_ground_containment_and_no_blocker_overlap(self):
        expected_hearth_alpha=opened(TERRAIN/'cottage_hearth/structure.png').getchannel('A')
        for room in self.rooms:
            pack=PACK/room['id'];floor=opened(pack/'floor.png').getchannel('A')
            occupied=Image.new('L',tuple(room['room_size']))
            for r in room['objects']:
                if r['id']!='hearth':
                    sprite=opened(ROOT/r['image_from_repo_root']);self.assertEqual(sprite.size,tuple(r['frame_size']))
                else:
                    mask=Image.new('L',occupied.size);mask.paste(expected_hearth_alpha,tuple(r['position']))
                    self.assertIsNone(ImageChops.multiply(mask,opened(pack/'fixtures.png').getchannel('A')).getbbox())
                if r['floor_rect']:
                    x,y,w,h=r['floor_rect'];bounds=(x,y,x+w,y+h)
                    self.assertEqual(set(floor.crop(bounds).get_flattened_data()),{255})
                    self.assertIsNone(occupied.crop(bounds).getbbox(),(room['id'],r['id']))
                    occupied.paste(255,bounds)
            if room['partition_rect']:
                x,y,w,h=room['partition_rect'];bounds=(x,y,x+w,y+h)
                self.assertIsNone(occupied.crop(bounds).getbbox());occupied.paste(255,bounds)
                self.assertEqual((w,h),(12,72))
                self.assertEqual(216-(y+h),72)
            self.assertEqual(occupied.tobytes(),Image.open(pack/'blocking.png').convert('L').tobytes())

    def test_full_width_character_probe_reaches_all_furniture_and_hero(self):
        for room in self.rooms:
            blocked=Image.open(PACK/room['id']/'blocking.png').convert('L')
            x0,y0,w,h=room['floor_rect'];pw,ph=room['actor_probe_size']
            self.assertEqual((pw,ph),(24,12))
            def free(x,y):
                return (x0+pw//2<=x<=x0+w-pw//2 and y0+ph//2<=y<=y0+h-ph//2
                        and not blocked.crop((x-pw//2,y-ph//2,x+pw//2,y+ph//2)).getbbox())
            reached=set();queue=deque([tuple(room['navigation_start'])])
            while queue:
                x,y=queue.popleft()
                if (x,y) in reached or not free(x,y):continue
                reached.add((x,y));queue.extend(((x-2,y),(x+2,y),(x,y-2),(x,y+2)))
            self.assertEqual(len(reached),room['reachable_probe_positions'])
            for r in room['objects']:self.assertIn(tuple(r['access']),reached,(room['id'],r['id']))
            hx,hy=room['hero_position'];ax,ay=room['hero_foot_anchor']
            self.assertIn((hx+ax,hy+ay),reached)
            self.assertFalse(room['engine_collision_implemented'])

    def test_character_pixels_and_animation_changes_remain_local(self):
        hero=opened(ROOT/'assets/characters/caelan/idle_front.png');self.assertEqual(hero.size,(24,36))
        native_masks=[Image.open(TERRAIN/'cottage_hearth/masks'/f'{name}.png').convert('L') for name in ('fire','embers','rim')]
        for room in self.rooms:
            pack=PACK/room['id'];hearth=next(r for r in room['objects'] if r['id']=='hearth')
            allowed=Image.new('L',tuple(room['room_size']))
            for mask in native_masks:
                expanded=Image.new('L',allowed.size);expanded.paste(mask,tuple(hearth['position']));allowed=ImageChops.lighter(allowed,expanded)
            for name in ('daylight_mask','floor_glow_mask'):
                mask=Image.open(pack/f'{name}.png').convert('L').point(lambda p:255 if p else 0)
                allowed=ImageChops.lighter(allowed,mask)
            first=opened(pack/room['frames'][0]['image']).convert('RGB')
            px,py=room['hero_position']
            self.assertEqual(len(room['frames']),36)
            for tick,r in enumerate(room['frames']):
                self.assertEqual((r['duration_ms'],r['fire_phase'],r['daylight_phase']),(300,tick%4,tick//2%9))
                actual=opened(pack/r['image'])
                diff=ImageChops.difference(first,actual.convert('RGB'))
                self.assertIsNone(ImageChops.multiply(diff,ImageChops.invert(allowed).convert('RGB')).getbbox())
                for yy in range(36):
                    for xx in range(24):
                        color=hero.getpixel((xx,yy))
                        if color[3]:self.assertEqual(actual.getpixel((px+xx,py+yy)),color)

    def test_individual_gifs_lossless_nearest_pixels_and_complete_loop(self):
        for room in self.rooms:
            pack=PACK/room['id'];tick=0
            with Image.open(pack/'room_review.gif') as gif:
                self.assertEqual(gif.info['loop'],0)
                for index in range(gif.n_frames):
                    gif.seek(index);duration=gif.info['duration'];self.assertEqual(duration%300,0)
                    for phase in range(tick,tick+duration//300):
                        expected=opened(pack/room['frames'][phase]['image']).convert('RGB')
                        expected=expected.resize((expected.width*4,expected.height*4),Image.Resampling.NEAREST)
                        self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes())
                    tick+=duration//300
                self.assertEqual(tick*300,10800)
                gif.seek(0);self.assertEqual(gif.convert('RGB').tobytes(),opened(pack/'room_review.png').convert('RGB').tobytes())

    def test_comparison_preserves_same_pixel_scale_and_exterior_pairing(self):
        tick=0
        with Image.open(PACK/'layouts_review.gif') as gif:
            self.assertEqual(gif.info['loop'],0);self.assertEqual(gif.size,(2256,1320))
            for index in range(gif.n_frames):
                gif.seek(index);duration=gif.info['duration'];self.assertEqual(duration%300,0)
                for phase in range(tick,tick+duration//300):
                    x=24
                    for room in self.rooms:
                        frame=opened(PACK/room['id']/room['frames'][phase]['image']).convert('RGB')
                        expected=frame.resize((frame.width*3,frame.height*3),Image.Resampling.NEAREST)
                        self.assertEqual(gif.convert('RGB').crop((x,594,x+expected.width,594+expected.height)).tobytes(),expected.tobytes())
                        x+=expected.width+24
                tick+=duration//300
            self.assertEqual(tick*300,10800)
            gif.seek(0);self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'layouts_review.png').convert('RGB').tobytes())


if __name__=='__main__':unittest.main()
