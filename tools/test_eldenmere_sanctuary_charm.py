"""Verify native charm assets, fixed structures, actor access and review delivery."""
from collections import deque
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/sanctuary_charm'
TERRAIN=PACK.parent
BASE=ROOT/'assets/maps/eldenmere/terrain_foundation'
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary_charm'


def load(path):return json.loads(path.read_text())


def opened(path,mode='RGBA'):
    with Image.open(path) as image:return image.convert(mode)


def box(rect):
    x,y,w,h=rect;return x,y,x+w,y+h


class SanctuaryCharmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'charm.json');cls.recipe=load(SOURCE/'recipe.json')
        cls.original=opened(TERRAIN/'sanctuary/closed.png')

    def test_native_props_materials_alpha_and_fixed_containers_stems(self):
        palette=load(PACK/'palette.json')['materials']
        colors={(*bytes.fromhex(c[1:]),255) for ramp in palette.values() for c in ramp.values()}
        leaves={(*bytes.fromhex(c[1:]),255) for c in palette['leaves'].values()}
        for p in self.recipe['props']:
            native=opened(PACK/f"props/{p['id']}.png")
            self.assertEqual(list(native.size),p['size'])
            self.assertEqual(set(native.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(c in colors for c in native.get_flattened_data() if c[3]))
            self.assertEqual(native.tobytes(),opened(SOURCE/f"parts/{p['id']}_native.png").tobytes())
            if p['id'] not in ('herb_planter','corner_vine'):continue
            poses=[opened(PACK/f"props/{p['id']}_frames/frame_{i:02}.png") for i in range(1,10)]
            self.assertEqual(poses[0].tobytes(),native.tobytes())
            self.assertGreater(len({im.tobytes() for im in poses}),1)
            for pose in poses:
                for y in range(native.height):
                    for x in range(native.width):
                        original=native.getpixel((x,y))
                        if original[3] and original not in leaves:self.assertEqual(pose.getpixel((x,y)),original)
                if p['id']=='herb_planter':
                    self.assertEqual(pose.crop((0,12,24,18)).tobytes(),native.crop((0,12,24,18)).tobytes())
        self.assertEqual(self.meta['wind']['cycle_duration_ms'],5400)
        self.assertEqual(self.meta['wind']['direction'],'E')

    def test_lantern_rest_reconstruction_local_motion_fixed_bracket_and_lit_insert(self):
        structure=opened(PACK/'layers/structure.png');x,y,w,h=self.recipe['lantern_rect']
        rest=structure.copy();rest.alpha_composite(opened(PACK/'layers/lantern/frame_01.png'))
        self.assertEqual(rest.tobytes(),self.original.tobytes())
        allowed=Image.new('L',rest.size)
        ImageDraw.Draw(allowed).rectangle((x-1,y,x+w,y+h-1),fill=255)
        panes=set();offsets=[]
        for phase,dx in enumerate(self.recipe['lantern_offsets'],1):
            layer=opened(PACK/f'layers/lantern/frame_{phase:02}.png')
            expected=Image.new('RGBA',rest.size)
            expected.alpha_composite(self.original.crop((x,y,x+w,y+h)),(x+dx,y))
            self.assertEqual(layer.tobytes(),expected.tobytes());offsets.append(dx)
            frame=structure.copy();frame.alpha_composite(layer)
            diff=ImageChops.difference(frame.convert('RGB'),self.original.convert('RGB'))
            diff.paste((0,0,0),(0,0),allowed);self.assertIsNone(diff.getbbox())
            self.assertEqual(frame.crop((102,157,113,164)).tobytes(),self.original.crop((102,157,113,164)).tobytes())
            self.assertEqual(frame.crop((118,156,150,198)).tobytes(),self.original.crop((118,156,150,198)).tobytes())
            self.assertEqual(frame.crop((34,51,65,84)).tobytes(),self.original.crop((34,51,65,84)).tobytes())
            lit=opened(PACK/f'layers/lantern_lit/frame_{phase:02}.png')
            panes.update(lit.get_flattened_data())
            self.assertEqual(lit.getchannel('A').tobytes(),layer.getchannel('A').tobytes())
        self.assertEqual(set(offsets),{-1,0,1})
        self.assertIn((245,217,154,255),panes)

    def test_smoke_exact_reuse_registration_no_clipped_opaque_pixels(self):
        ox,oy=self.recipe['smoke_origin'];dx,dy=ox-90,oy-47
        self.assertEqual(self.meta['smoke']['cycle_duration_ms'],3600)
        for phase in range(1,19):
            source=opened(TERRAIN/f'cottage/smoke/frame_{phase:02}.png')
            actual=opened(PACK/f'layers/smoke/frame_{phase:02}.png')
            expected=Image.new('RGBA',(216,216));expected.alpha_composite(source,(dx,dy))
            self.assertEqual(actual.tobytes(),expected.tobytes())
            for y in range(source.height):
                for x in range(source.width):
                    p=source.getpixel((x,y))
                    if p[3]:
                        self.assertTrue(0<=x+dx<216 and 0<=y+dy<216)
                        self.assertEqual(actual.getpixel((x+dx,y+dy)),p)
            left,top,right,bottom=actual.getbbox()
            self.assertGreaterEqual(left,ox-3);self.assertLessEqual(bottom,oy+2)

    def test_event_bell_is_separate_nonlooping_and_preserves_supports(self):
        meta=self.meta['bell'];self.assertEqual(meta['ambient'],'still');self.assertFalse(meta['cue_loop'])
        fixed=opened(PACK/'layers/bell_fixed_structure.png');frames=[]
        for phase in range(1,10):
            layer=opened(PACK/f'layers/bell_cue/frame_{phase:02}.png')
            frame=fixed.copy();frame.alpha_composite(layer);frames.append(frame)
            diff=ImageChops.difference(frame.convert('RGB'),self.original.convert('RGB')).getbbox()
            if diff:
                self.assertGreaterEqual(diff[0],40);self.assertLessEqual(diff[2],58)
                self.assertGreaterEqual(diff[1],60);self.assertLessEqual(diff[3],76)
            self.assertEqual(frame.crop((30,24,68,60)).tobytes(),self.original.crop((30,24,68,60)).tobytes())
        self.assertEqual(frames[0].tobytes(),self.original.tobytes())
        self.assertEqual(frames[-1].tobytes(),self.original.tobytes())
        self.assertGreater(len({im.tobytes() for im in frames}),3)
        with Image.open(PACK/'bell_cue.gif') as gif:
            self.assertEqual(gif.n_frames,9)
            for i,frame in enumerate(frames):
                gif.seek(i)
                self.assertEqual(gif.info['duration'],100 if i<8 else 1000)
                cell=Image.new('RGBA',(64,88),'#70935a');cell.alpha_composite(frame,(-18,-12))
                expected=cell.convert('RGB').resize((512,704),Image.Resampling.NEAREST)
                self.assertEqual(gif.convert('RGB').crop((0,84,512,788)).tobytes(),expected.tobytes())

    def test_scene_uses_approved_wind_phases_with_fixed_tree_and_grass_roots(self):
        cx,cy,_,_=self.meta['review_crop']
        tree=next(p for p in self.recipe['foliage'] if p['id']=='shade_tree')
        tx,ty=tree['position'];path=TERRAIN/tree['pack']
        trunk=opened(path/'trunk.png')
        grass=next(p for p in self.recipe['foliage'] if p['id']=='east_grass')
        gx,gy=grass['position'];base=opened(TERRAIN/grass['pack']/'base.png')
        poses=set()
        for tick,record in enumerate(self.meta['frames']):
            actual=opened(PACK/record['image'],'RGB')
            phase=tick//3%9
            canopy=opened(path/f'frames/frame_{phase+1:02}.png')
            poses.add(actual.crop((tx-cx,ty+20-cy,tx+96-cx,ty+90-cy)).tobytes())
            for y in range(90):
                for x in range(96):
                    p=canopy.getpixel((x,y))
                    if p[3]:self.assertEqual(actual.getpixel((tx-cx+x,ty-cy+y)),p[:3])
            for y in range(min(trunk.height,318-ty)):
                for x in range(trunk.width):
                    p=trunk.getpixel((x,y))
                    if p[3]:self.assertEqual(actual.getpixel((tx-cx+x,ty-cy+y)),p[:3])
            for y in range(20,24):
                for x in range(24):
                    p=base.getpixel((x,y))
                    if p[3]:self.assertEqual(actual.getpixel((gx-cx+x,gy-cy+y)),p[:3])
        self.assertGreater(len(poses),3)

    def test_full_width_actor_access_independent_of_exported_reach_count(self):
        blocked=opened(PACK/'navigation/blocking.png','L')
        expected=opened(BASE/'navigation/blocking.png','L');access=load(PACK/'navigation/access.json')
        for p in access['blockers']:expected.paste(255,box(p['rect']))
        self.assertEqual(expected.tobytes(),blocked.tobytes())
        allowed=opened(BASE/'navigation/allowed_routes.png','L')
        start=tuple(access['start']);visited={start};queue=deque([start])
        while queue:
            x,y=queue.popleft()
            for p in ((x+2,y),(x-2,y),(x,y+2),(x,y-2)):
                xx,yy=p
                if not(228<=xx<494 and 288<=yy<420) or p in visited:continue
                if allowed.getpixel(p) and not blocked.crop((xx-12,yy-6,xx+12,yy+6)).getbbox():
                    visited.add(p);queue.append(p)
        for name,p in access['destinations'].items():self.assertIn(tuple(p),visited,name)
        for yy in range(304,404,2):
            self.assertIsNone(blocked.crop((372,yy-6,396,yy+6)).getbbox(),f'Centre approach obstructed at {yy}')
        self.assertFalse(access['engine_collision_implemented'])

    def test_town_preservation_character_pixels_and_lossless_review_loop(self):
        before=opened(TERRAIN/'sanctuary/town_native.png','RGB');after=opened(PACK/'town_native.png','RGB')
        permitted=Image.new('L',before.size)
        permitted.paste(255,(252,84,468,300))
        for p in self.recipe['props']:
            for pos in p.get('positions',[p.get('position')]):
                x,y=pos;w,h=p['size'];permitted.paste(255,(x,y,x+w,y+h))
        for p in self.recipe['foliage']:
            sample=opened(TERRAIN/p['pack']/'idle.png');x,y=p['position']
            permitted.paste(255,(x,y,x+sample.width,y+sample.height))
        diff=ImageChops.difference(before,after);self.assertIsNotNone(diff.getbbox())
        diff.paste((0,0,0),(0,0),permitted);self.assertIsNone(diff.getbbox())
        hero=opened(ROOT/'assets/characters/caelan/idle_front.png')
        cx,cy,cw,ch=self.meta['review_crop'];hx,hy=self.meta['hero_foot'];scale=self.meta['review_scale']
        with Image.open(PACK/'sanctuary_review.gif') as gif:
            self.assertEqual(gif.n_frames,54);self.assertEqual(gif.info['loop'],0)
            total=0
            for i,r in enumerate(self.meta['frames']):
                native=opened(PACK/r['image'],'RGB');self.assertEqual(native.size,(cw,ch))
                for y in range(hero.height):
                    for x in range(hero.width):
                        p=hero.getpixel((x,y))
                        if p[3]:self.assertEqual(native.getpixel((hx-12-cx+x,hy-30-cy+y)),p[:3])
                gif.seek(i);self.assertEqual(gif.info['duration'],200);total+=gif.info['duration']
                actual=gif.convert('RGB').crop((0,84,cw*scale,84+ch*scale))
                expected=native.resize((cw*scale,ch*scale),Image.Resampling.NEAREST)
                self.assertEqual(actual.tobytes(),expected.tobytes())
            self.assertEqual(total,10800)
            gif.seek(0)
            self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'sanctuary_review.png','RGB').tobytes())
        for name in ('sanctuary_review.png','town_review.png','lantern_variants.png'):
            with Image.open(PACK/name) as image:self.assertEqual(image.mode,'RGB')


if __name__=='__main__':unittest.main()
