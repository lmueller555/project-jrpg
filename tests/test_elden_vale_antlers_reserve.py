"""Pale Antlers: native registration, geometry-safe contact, actor readability."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from PIL import Image,ImageDraw,ImageChops
from main import Game
from rendering import WorldCanvas
ROOT=Path(__file__).resolve().parents[1]

def read(p):return json.loads((ROOT/p).read_text())

class AntlerReserveContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=read('assets/maps/elden_vale_sanctuary/map.json')
        cls.spec=read('assets/source/maps/sanctuary_reserve_hd/recipe.json')['pale_antlers']
        cls.records=cls.scene['landmark_layers']

    def test_native_density_and_explicit_nonblocking_layers(self):
        for r in self.records:
            with Image.open(ROOT/r['image']) as im:
                self.assertEqual(im.size,tuple(int(v*2) for v in r['logical_size']))
                self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255})
                self.assertEqual(r['collision'],'none')
                if r['layer']=='overhead':
                    self.assertEqual(Image.open(ROOT/r['occlusion_mask']).tobytes(),im.getchannel('A').tobytes())
        self.assertEqual(sum(r['layer']=='overhead' for r in self.records),4)

    def test_registered_parts_reconstruct_all_raised_anatomy(self):
        spec=self.spec;whole=Image.open(ROOT/read(spec['manifest'])['assets']['antlers_complete']['image']).convert('RGBA')
        whole=whole.resize(tuple(spec['projection_artwork']),Image.Resampling.NEAREST)
        assembled=Image.new('RGBA',whole.size)
        for r in self.records:
            if 'assembly_position_artwork' in r or r['id'].endswith('skull_contact'):
                position=r.get('assembly_position_artwork',[0,spec['split_y_artwork']])
                assembled.alpha_composite(Image.open(ROOT/r['image']).convert('RGBA'),tuple(position))
        # RGB in transparent cells is irrelevant. Every source pixel above the
        # reviewed contact fringe and within the anatomical enclosure survives.
        protected=Image.new('L',whole.size);d=ImageDraw.Draw(protected)
        d.rectangle((0,0,whole.width,min(p[1] for p in spec['fringe_contour_artwork'])-1),fill=255)
        d.polygon([tuple(p) for p in spec['bone_polygon_artwork']],fill=255)
        for background in ('black','white'):
            a=Image.new('RGBA',whole.size,background);a.alpha_composite(whole)
            b=Image.new('RGBA',whole.size,background);b.alpha_composite(assembled)
            diff=ImageChops.difference(a.convert('RGB'),b.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(diff,protected.convert('RGB')).getbbox())

    def test_contact_pixels_are_only_on_existing_ridge(self):
        r=next(r for r in self.records if r['id'].endswith('skull_contact'))
        alpha=Image.open(ROOT/r['image']).getchannel('A');collision=Image.open(ROOT/self.scene['collision']).convert('L')
        supports=[f['rect'] for f in self.scene['collision_footprints'] if f['id'] in self.spec['ridge_footprints']]
        count=0
        for y in range(alpha.height):
            for x in range(alpha.width):
                if not alpha.getpixel((x,y)):continue
                wx=int(r['position'][0]+x/2);wy=int(r['position'][1]+y/2)
                self.assertTrue(any(rx<=wx<rx+rw and ry<=wy<ry+rh for rx,ry,rw,rh in supports))
                self.assertEqual(collision.getpixel((wx,wy)),255);count+=1
        self.assertGreater(count,0)

    def test_no_new_ordinary_entities_or_gameplay_contracts(self):
        baseline=read('assets/source/maps/sanctuary_reserve_hd/baseline_maps.json')['elden_vale_sanctuary']
        self.assertEqual([e['id'] for e in self.scene['entities']],[e['id'] for e in baseline['entities']])
        for key in ('public_approaches','loop_waypoints','collision_footprints','cave_barrier','world_links','player_probe_size'):
            self.assertEqual(self.scene[key],baseline[key])

class AntlerReserveGame(unittest.TestCase):
    def test_actual_game_cutaway_and_north_loop_motion(self):
        with TemporaryDirectory() as tmp:
            g=Game(fullscreen=False,start_on_title=True,save_path=Path(tmp)/'save.json',settings_path=Path(tmp)/'settings.json')
            try:
                g.on_title=False;g.opening.stage='disabled';g.opening_fade=g.transfer_cooldown=0
                g.world=g._scene_by_id('elden_vale_sanctuary');g.player.position.update(1100,270)
                g.update(0,(0,0),False)
                camera=(672,110)
                def draw(actors):
                    target=WorldCanvas((480,320),pygame.SRCALPHA);target.fill((0,0,0,0))
                    g.world.landmarks.draw(target,camera,'overhead',actors=actors)
                    return pygame.image.tobytes(target.native,'RGBA')
                normal=draw([g.player]);self.assertNotEqual(normal,draw([]))
                g.audio.set_reduced_motion(True);g.update(0,(0,0),False)
                self.assertEqual(normal,draw([g.player]))
                for running,direction in [(False,(0,1)),(True,(0,-1))]:
                    before=g.player.position.copy()
                    for _ in range(15):g.update(1/30,direction,running)
                    self.assertGreater(g.player.position.distance_to(before),10)
            finally:g.music.stop();pygame.quit()
