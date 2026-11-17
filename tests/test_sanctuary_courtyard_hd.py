"""Scoped courtyard art preserves the assembled town and actual exploration."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
import pygame
from rendering import WorldCanvas

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/maps/eldenmere/courtyard_hd'
def read(path):return json.loads(Path(path).read_text())

class CourtyardAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe=read(SOURCE/'recipe.json');cls.old=read(SOURCE/'baseline_map.json');cls.data=read(ROOT/cls.recipe['map'])

    def test_courtyard_registration_survives_the_composed_town_migration(self):
        current={r['id']:r for r in self.data['entities']}
        previous={r['id']:r for r in self.old['entities']}
        for name in self.recipe['entity_ids']:
            for key in ('position','sort_y','phase_offset'):
                self.assertEqual(current[name][key],previous[name][key],(name,key))
        door=next(r for r in self.data['doors'] if r['id']=='sanctuary')
        old=next(r for r in self.old['doors'] if r['id']=='sanctuary')
        for key,value in old.items():
            if key!='frames':self.assertEqual(door[key],value)
        self.assertTrue(self.data['pause_on_focus_loss'])
        before=Image.open(ROOT/self.old['collision']).convert('L')
        after=Image.open(ROOT/self.data['collision']).convert('L')
        # New courtyard objects add only their declared ground supports. The
        # prior building, stair and circulation geometry remains authoritative.
        expected=before.copy();draw=ImageDraw.Draw(expected)
        for key in ('settlement_dressing','settlement_workyards'):
            for support in self.data.get(key,{}).get('solid_footprints',[]):
                x,y,w,h=support['rect'];draw.rectangle((x,y,x+w-1,y+h-1),fill=255)
        self.assertEqual(expected.tobytes(),after.crop((0,0,*before.size)).tobytes())

    def test_assets_keep_physical_canvases_and_actual_new_detail(self):
        previous={r['id']:r for r in self.old['entities']}
        for r in self.data['entities']:
            if r['id'] not in self.recipe['entity_ids']:continue
            with self.subTest(r['id']):
                old=Image.open(ROOT/previous[r['id']]['frames'][0]);new=Image.open(ROOT/r['frames'][0]).convert('RGBA')
                self.assertEqual(new.size,tuple(v*2 for v in old.size));self.assertEqual(r['logical_size'],list(old.size))
                self.assertLessEqual(set(new.getchannel('A').getdata()),{0,255})
                self.assertTrue(any(len({new.getpixel((x+i,y+j)) for i in (0,1) for j in (0,1)})>1 for y in range(0,new.height,2) for x in range(0,new.width,2)))
        self.assertTrue(all(r['artwork_pixels_per_world_pixel']==2 for r in self.data['ground_overlays']))
        self.assertEqual(Image.open(ROOT/self.data['overview']).size,tuple(self.data['size_pixels']))

    def test_scoped_grass_keeps_legacy_variants_and_fixed_roots_for_all_poses(self):
        live=read(ROOT/self.data['grass']['manifest'])['tall_grass'];old=read(ROOT/self.recipe['legacy_grass_manifest'])['tall_grass']
        for key in ('anchor','frame_size','contact_rect'):self.assertEqual(live[key],old[key])
        self.assertEqual(set(live['variants']),{'sparse_hd','splayed_hd','dense_hd'})
        for name in ('sparse_hd','splayed_hd','dense_hd'):
            v=live['variants'][name];self.assertEqual(sum(f['duration_ms'] for f in v['idle']),4800)
            poses=[*v['idle'],*[p for seq in v['parted'].values() for p in seq]];roots=None
            for p in poses:
                rear=Image.open(ROOT/p['rear']).convert('RGBA');front=Image.open(ROOT/p['front']).convert('RGBA');rear.alpha_composite(front)
                self.assertEqual(rear.size,(48,64));self.assertLessEqual(rear.getbbox()[3],56)
                self.assertGreaterEqual(rear.getbbox()[1],22)
                root=rear.crop((0,52,48,64)).tobytes()
                if roots is None:roots=root
                self.assertEqual(root,roots)

    def test_overview_covers_the_current_composed_town(self):
        overview=Image.open(ROOT/self.data['overview'])
        self.assertEqual(overview.size,tuple(self.data['size_pixels']))
        self.assertIn('town_hd',self.data['art_integrations'])


class CourtyardGameplay(unittest.TestCase):
    def setUp(self):
        from main import Game
        self.temp=tempfile.TemporaryDirectory();p=Path(self.temp.name)
        self.g=Game(fullscreen=False,start_on_title=True,save_path=p/'save.json',settings_path=p/'settings.json')
        g=self.g;g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'});g.opening_fade=0;g.world=g.town;g.transfer_cooldown=0;g.player.position.update(384,400)

    def tearDown(self):self.g.music.stop();pygame.quit();self.temp.cleanup()

    def test_walk_and_run_stairs_keep_speed_and_arrive_at_door(self):
        g=self.g
        for running in (False,True):
            g.player.position.update(384,400);start=g.player.position.y
            g.update(.1,(0,-1),running);distance=start-g.player.position.y
            self.assertGreater(distance,0);self.assertTrue(g.world.can_stand(g.player.position))
            if not running:walk=distance
            else:self.assertGreater(distance,walk)
            for _ in range(160):
                if g.player.position.y<=310:break
                g.update(1/60,(0,-1),running)
                self.assertTrue(g.world.can_stand(g.player.position))
            self.assertLessEqual(g.player.position.y,310)

    def test_native_door_reverses_and_actual_transfer_returns_to_safe_courtyard(self):
        g=self.g;door=next(d for d in g.world.doors if d.data['id']=='sanctuary')
        self.assertEqual(door.frames[0].get_size(),(32,42));self.assertEqual(door.frames[0].native.get_size(),(64,84))
        door.update((386,306),.2);progress=door.progress;door.update(None,.1);self.assertLess(door.progress,progress);door.update((386,306),.1);self.assertGreater(door.progress,0)
        def enter(d):
            before=g.world;direction=-1 if d.data['entry_side']=='north' else 1;g.transfer_cooldown=0;g.player.position.update(pygame.Vector2(d.data['anchor'])+(0,-direction*12));g.update(.5,(0,0),False)
            for _ in range(90):
                g.update(1/60,(0,direction),False)
                if g.world is not before:return
            self.fail('No doorway transfer')
        enter(door);self.assertEqual(g.world.data['id'],'sanctuary_hall');enter(next(d for d in g.world.doors if d.data['id']=='courtyard'));self.assertIs(g.world,g.town);self.assertEqual(g.player.facing,'front');self.assertTrue(g.world.can_stand(g.player.position))

    def test_scoped_native_grass_responds_to_actual_walk_run_and_recovers(self):
        g=self.g;field=g.world.grass;c=next(c for c in field.clumps if c.variant=='splayed_hd');x,y=c.position
        for running in (False,True):
            field.reset();g.player.position.update(x-26,y);g.update(.01,(0,0),running)
            peak=0
            for _ in range(30):
                g.update(1/60,(1,0),running);peak=max(peak,c.strength)
            self.assertGreater(c.activations,0);self.assertGreater(peak,0)
            if running:self.assertGreater(peak,1)
            rear=field._records[c.identifier][0]['surfaces'][0];self.assertEqual(rear.get_size(),(24,32));self.assertEqual(rear.native.get_size(),(48,64))
            g.player.position.update(384,320);g.update(0,(0,0),False);g.update(1,(0,0),False);self.assertEqual(c.strength,0)

    def test_focus_and_pause_freeze_exploration_and_ambient_clocks(self):
        g=self.g;g.update(.1,(0,0),False);before=(g.elapsed_ms,g.world.grass.elapsed_ms,tuple(g.player.position));g._music_focused=False
        g.update(.5,(1,0),True);self.assertEqual((g.elapsed_ms,g.world.grass.elapsed_ms,tuple(g.player.position)),before)
        g._music_focused=True;g.pause.is_open=True;g.update(.5,(1,0),True);self.assertEqual((g.elapsed_ms,g.world.grass.elapsed_ms,tuple(g.player.position)),before)
        g.pause.is_open=False;g.update(.1,(1,0),False);self.assertGreater(g.elapsed_ms,before[0])

    def test_reduced_motion_stills_native_scenery_but_keeps_door_functional(self):
        g=self.g;g.audio.set_reduced_motion(True);g.player.story_visible=False
        # Isolate the migrated scenery from independently animated NPC routines.
        g.world.npcs=[];g.world.routine_props=[];g.world.work_fittings=[]
        g.world.update_grass(0,reduced_motion=True)
        def render(t):
            c=WorldCanvas((480,320));g.world.draw(c,(120,72),g.player,t,False);return pygame.image.tobytes(c.native,'RGBA')
        self.assertEqual(render(0),render(1800))
        closed=render(0);door=next(d for d in g.world.doors if d.data['id']=='sanctuary')
        door.update((386,306),.5);self.assertEqual(door.state,'open')
        self.assertNotEqual(render(0),closed)

if __name__=='__main__':unittest.main()
