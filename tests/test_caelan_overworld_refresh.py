"""Authored travel registration, safe exports and actual Player playback.

These checks establish content provenance and runtime contracts. They do not
certify anatomy or visual quality; those require the native-scale scene review.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/caelan/overworld_refresh'
BASE=ROOT/'assets/characters/caelan'
DIRECTIONS=('front','back','left','right')


def read(path):return json.loads(path.read_text())


def travel_paths():
    return {f'assets/characters/caelan/idle_{direction}.png'
            for direction in DIRECTIONS} | {
        f'assets/characters/caelan/{gait}_{direction}/frame_{phase:02}.png'
        for gait in ('walk','run') for direction in DIRECTIONS for phase in range(1,5)}


class CaelanOverworldRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration=read(SOURCE/'registration.json')
        cls.records=cls.registration['source_cells']

    def test_source_and_all_thirty_six_individual_runtime_drawings_are_registered(self):
        self.assertEqual(len(self.records),36)
        self.assertEqual({record['file'] for record in self.records},travel_paths())
        atlas=SOURCE/'travel_authored.png'
        self.assertEqual(self.registration['source'],atlas.relative_to(ROOT).as_posix())
        self.assertEqual(self.registration['source_sha256'],hashlib.sha256(atlas.read_bytes()).hexdigest())
        self.assertEqual({record['index'] for record in self.records},set(range(36)))
        with Image.open(atlas) as image:
            width,height=image.size
        rectangles=set()
        for record in self.records:
            with self.subTest(file=record['file']):
                x,y,w,h=record['source_rect']
                self.assertGreater(w,0);self.assertGreater(h,0)
                self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
                self.assertLessEqual(x+w,width);self.assertLessEqual(y+h,height)
                rectangles.add(tuple(record['source_rect']))
                self.assertIn(record['direction'],DIRECTIONS)
                if '/idle_' in record['file']:
                    self.assertEqual(record['gait'],'idle')
                    self.assertEqual(record['phase'],0)
                else:
                    self.assertEqual(record['gait'],Path(record['file']).parent.name.split('_')[0])
                    self.assertEqual(record['phase'],int(Path(record['file']).stem.rsplit('_',1)[1])-1)
                self.assertEqual(record['canvas'],[24,36])
                self.assertEqual(record['foot_anchor'],[12,34])
                self.assertGreater(record['scale'],0)
                self.assertEqual(len(record['source_bounds']),4)
                self.assertEqual(len(record['destination']),2)
        self.assertEqual(len(rectangles),36)
        # One authored scale avoids making the torso or head breathe between poses.
        self.assertEqual(len({record['scale'] for record in self.records}),1)

    def test_rebuilding_products_matches_the_committed_exports_without_writing(self):
        from tools.build_caelan_overworld import products
        files=products()
        self.assertTrue(travel_paths()<=set(files))
        for relative,raw in files.items():
            with self.subTest(file=relative):
                path=Path(relative)
                self.assertFalse(path.is_absolute())
                self.assertNotIn('..',path.parts)
                if relative.startswith('assets/characters/'):
                    self.assertTrue(relative.startswith('assets/characters/caelan/'))
                if relative.startswith('assets/source/characters/'):
                    self.assertTrue(relative.startswith('assets/source/characters/caelan/'))
                self.assertEqual((ROOT/path).read_bytes(),raw)

    def test_native_frames_have_hard_alpha_clear_margins_and_grounded_or_flight_feet(self):
        for relative in sorted(travel_paths()):
            with self.subTest(file=relative):
                image=Image.open(ROOT/relative).convert('RGBA')
                self.assertEqual(image.size,(24,36))
                self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
                left,top,right,bottom=image.getbbox()
                self.assertGreater(left,0)
                self.assertLess(right,24)
                self.assertGreaterEqual(top,0)
                self.assertLessEqual(bottom,35)
                if '/run_' in relative:
                    phase=int(Path(relative).stem.rsplit('_',1)[1])
                    self.assertEqual(bottom,32 if phase in (2,4) else 35)
                else:self.assertEqual(bottom,35)
        front=Image.open(BASE/'idle_front.png').convert('RGBA').getbbox()
        self.assertEqual(front[3]-front[1],34)

    def test_facing_gait_identity_and_original_cadence_remain_explicit(self):
        idles=read(BASE/'idle_directions.json')
        idle_strip=Image.open(BASE/'idle_directions.png').convert('RGBA')
        self.assertEqual(idles['foot_anchor'],[12,34])
        for record in idles['frames']:
            self.assertEqual(record['status'],'review')
            direction=record['id'].split('.')[-1]
            x,y,w,h=record['rect']
            self.assertEqual(idle_strip.crop((x,y,x+w,y+h)).tobytes(),
                             Image.open(BASE/f'idle_{direction}.png').convert('RGBA').tobytes())
        walking=read(BASE/'walk_directions.json')
        walk_strip=Image.open(BASE/'walk_directions.png').convert('RGBA')
        for record in walking['directions']:
            self.assertEqual(record['status'],'review')
            for index,frame in enumerate(record['frames']):
                x,y,w,h=frame['rect']
                self.assertEqual(walk_strip.crop((x,y,x+w,y+h)).tobytes(),
                    Image.open(BASE/f"walk_{record['direction']}/frame_{index+1:02}.png").convert('RGBA').tobytes())
        for gait,duration in (('walk',140),('run',100)):
            drawings=[]
            for direction in DIRECTIONS:
                folder=BASE/f'{gait}_{direction}'
                data=read(folder/'animation.json')
                self.assertEqual(data['status'],'review')
                self.assertEqual(data['frame_size'],[24,36])
                self.assertEqual(data['foot_anchor'],[12,34])
                self.assertEqual(len(data['frames']),4)
                self.assertEqual([frame['duration_ms'] for frame in data['frames']],[duration]*4)
                strip=Image.open(folder/'spritesheet.png').convert('RGBA')
                self.assertEqual(strip.size,(96,36))
                for index,frame in enumerate(data['frames']):
                    image=Image.open(folder/frame['file']).convert('RGBA')
                    self.assertEqual(strip.crop((index*24,0,(index+1)*24,36)).tobytes(),image.tobytes())
                    drawings.append(image.tobytes())
                if gait=='run':
                    self.assertEqual([frame['airborne'] for frame in data['frames']],[False,True,False,True])
            self.assertEqual(len(set(drawings)),16)
        # Separate profiles retain asymmetry instead of mirroring the pouch side.
        left=Image.open(BASE/'idle_left.png').convert('RGBA')
        right=Image.open(BASE/'idle_right.png').convert('RGBA')
        self.assertNotEqual(left.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes(),right.tobytes())
        # A changed file alone cannot prove an alternating stride. In the
        # reviewed frontal contacts, the grounded boot crosses from one side
        # of the head to the other; the earlier drawing planted the
        # same leg on both contacts. Compare silhouette centres, allowing the
        # whole body to sway rather than assuming a fixed screen centre.
        def centre_x(image,top,bottom):
            xs=[x for y in range(top,bottom) for x in range(image.width)
                if image.getpixel((x,y))[3]]
            self.assertTrue(xs)
            return sum(xs)/len(xs)
        for direction in ('front','back'):
            contacts=[Image.open(BASE/f'run_{direction}/frame_{phase:02}.png').convert('RGBA')
                      for phase in (1,3)]
            with self.subTest(direction=direction):
                leads=[centre_x(image,31,35)-centre_x(image,2,10) for image in contacts]
                self.assertTrue(all(abs(lead)>.25 for lead in leads))
                self.assertLess(leads[0]*leads[1],0)

    def test_player_loads_and_selects_every_export_at_the_authored_phase_boundary(self):
        import pygame
        from main import Player
        world=SimpleNamespace(data={'spawn':[100,100]},
                              image=lambda name:pygame.image.load(str(ROOT/name)),
                              can_stand=lambda point:True)
        player=Player(world)
        for direction in DIRECTIONS:
            player.facing=direction
            player.moving=False
            self.assertIs(player.sprite(),player.idles[direction])
            for running,gait,duration in ((False,'walk',140),(True,'run',100)):
                player.moving=True;player.running=running
                bank=(player.runs if running else player.walks)[direction]
                self.assertEqual([entry[1] for entry in bank],[duration]*4)
                for phase in range(4):
                    player.walk_ms=(phase+.5)*duration
                    self.assertIs(player.sprite(),bank[phase][0])
        # Sprite canvas changes must not silently change movement speed.
        player.position.update(100,100)
        player.update((1,0),1.,world,False)
        self.assertAlmostEqual(player.position.x,172.)
        player.position.update(100,100)
        player.update((1,0),1.,world,True)
        self.assertAlmostEqual(player.position.x,208.)
        player.update((0,0),.5,world)
        self.assertFalse(player.moving)
        self.assertIs(player.sprite(),player.idles[player.facing])


if __name__=='__main__':unittest.main()
