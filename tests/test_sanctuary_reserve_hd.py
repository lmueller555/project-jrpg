"""Native reserve assembly preserves gameplay independently of new silhouettes."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from PIL import Image
from main import Game,World
from rendering import WorldCanvas
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'assets/source/maps/sanctuary_reserve_hd'
def read(path):return json.loads(Path(path).read_text())

class ReserveHDContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=read(SRC/'baseline_maps.json');cls.recipe=read(SRC/'recipe.json')
        cls.maps={key:read(ROOT/path) for key,path in cls.recipe['scenes'].items()}

    def test_original_collision_routes_stations_and_portal_contracts_are_identical(self):
        for name,data in self.maps.items():
            old=self.old[name]
            self.assertEqual(sha256((ROOT/data['collision']).read_bytes()).hexdigest(),self.recipe['collision_sha256'][name])
            for key in ('size_pixels','player_probe_size','player_draw_anchor','spawn','destinations','public_approaches','inspection_points','object_footprints','walkable_floor','exit_clearance','relief_clearance','collision_footprints','reserve_exit','cave_barrier','loop_waypoints','depth_samples','landmarks','fantasy_review_points','npcs','quests','world_links'):
                self.assertEqual(data.get(key),old.get(key),(name,key))
            for now,before in zip(data['doors'],old['doors']):
                for key,val in before.items():
                    if key not in ('frames','artwork_pixels_per_world_pixel','logical_size'):self.assertEqual(now[key],val,(name,key))
            self.assertEqual(len(data['doors']),len(old['doors']))

    def test_every_environment_entity_retains_logical_canvas_and_native_density(self):
        for name,data in self.maps.items():
            prior={e['id']:e for e in self.old[name]['entities']}
            self.assertEqual(len(prior),len(data['entities']))
            for e in data['entities']:
                before=prior[e['id']];self.assertEqual(e['position'],before['position']);self.assertEqual(e['sort_y'],before['sort_y'])
                size=Image.open(ROOT/before['frames'][0]).size
                self.assertEqual(e['logical_size'],list(size));self.assertEqual(e['artwork_pixels_per_world_pixel'],2)
                for path in e['frames']:
                    with Image.open(ROOT/path) as im:
                        self.assertEqual(im.size,tuple(v*2 for v in size));self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255})

    def test_retained_sources_and_current_exports_have_real_matching_hashes(self):
        manifest=read(ROOT/'assets/maps/sanctuary_reserve_hd/manifest.json')
        for r in self.recipe['sources']:self.assertEqual(sha256((SRC/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in manifest['dependencies']:self.assertEqual(sha256((ROOT/r['path']).read_bytes()).hexdigest(),r['sha256'])
        for r in manifest['exports']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        self.assertNotIn('overworld_refresh/legacy',json.dumps(manifest))
        self.assertIn('landmarks_authored.png',json.dumps(manifest))

    def test_grass_identity_roots_phases_and_new_native_poses_are_explicit(self):
        name='elden_vale_sanctuary';data=self.maps[name];old=self.old[name]
        before={r['id']:r for r in old['grass']['instances']}
        for r in data['grass']['instances']:
            self.assertEqual(r['position'],before[r['id']]['position']);self.assertEqual(r['phase_ms'],before[r['id']]['phase_ms'])
            self.assertTrue(r['variant'].endswith('_hd'))
        self.assertEqual(len(before),len(data['grass']['instances']))
        manifest=read(ROOT/data['grass']['manifest'])
        self.assertTrue(all(key.endswith('_hd') for key in manifest['tall_grass']['variants']))

    def test_native_ground_chunks_cover_the_maps_once_and_stay_bounded(self):
        for name,data in self.maps.items():
            coverage=pygame.Surface(data['size_pixels']);coverage.fill('black');area=0
            for r in data['ground_overlays']:
                rect=pygame.Rect(r['position'],r['logical_size']);self.assertLessEqual(max(rect.size),192)
                self.assertEqual(r['artwork_pixels_per_world_pixel'],2);area+=rect.width*rect.height
                with Image.open(ROOT/r['image']) as im:self.assertEqual(im.size,tuple(v*2 for v in rect.size))
            self.assertEqual(area,data['size_pixels'][0]*data['size_pixels'][1])

class ReserveHDGameplay(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        p=Path(self.temp.name);self.g=Game(fullscreen=False,start_on_title=True,save_path=p/'journey.json',settings_path=p/'settings.json')
        self.addCleanup(self.g.music.stop);self.addCleanup(pygame.quit)
        g=self.g;g.on_title=False;g.opening.stage='disabled';g.opening_fade=g.transfer_cooldown=0
        g.world=g._scene_by_id('elden_vale_sanctuary');g.player.position.update(456,654);g.update(0,(0,0),False)

    def test_native_particles_and_caretaker_pail_keep_logical_sizes(self):
        g=self.g;field=g.world.atmosphere
        self.assertTrue(all(hasattr(frame,'native') for frames in field._petals for frame in frames))
        for frames in field._petals:
            for frame in frames:self.assertEqual(frame.native.get_size(),(10,10));self.assertEqual(frame.get_size(),(5,5))
        caretaker=g.sanctuary_reserve.actors['reserve_caretaker']
        self.assertTrue(all(hasattr(surface,'native') for surface in caretaker.buckets.values()))
        caretaker.clock=7.3;self.assertEqual(caretaker.sprite(0).native.get_size(),tuple(v*2 for v in caretaker.animation['action_canvas']))
        g.audio.set_reduced_motion(True);g.update(0,(0,0),False);before=caretaker._pose();caretaker.update(3)
        self.assertEqual(caretaker._pose(),before);self.assertEqual(caretaker._pose()[1],{})

    def test_repeatable_inspection_cues_follow_actual_controller_and_scene(self):
        g=self.g;g._update_object_cues(.2)
        self.assertIn('reserve_boundary_marker',g.world.object_cues.states)
        self.assertNotIn('reserve_cave',g.world.object_cues.states)
        self.assertTrue(g.world.object_cues.states['reserve_boundary_marker']['near'])
        g.pause.is_open=True;g._update_object_cues(.2);self.assertFalse(g.world.object_cues.enabled)
        g.pause.is_open=False;g.world=g._scene_by_id('elden_vale_sanctuary_hall');g.player.position.update(288,178);g.update(0,(0,0),False);g._update_object_cues(.2)
        self.assertIn('north_remembrance_table',g.world.object_cues.states)
        self.assertTrue(g.world.object_cues.states['north_remembrance_table']['near'])
        self.assertFalse(g.sanctuary_reserve.actors['reserve_caretaker'].conversation_ready)

    def test_focus_and_pause_preserve_environment_and_gameplay_clocks(self):
        g=self.g;g.update(.1,(0,0),False);before=(g.elapsed_ms,tuple(g.player.position))
        g._music_focused=False;g.update(.5,(1,0),True);self.assertEqual((g.elapsed_ms,tuple(g.player.position)),before)
        g._music_focused=True;g.pause.is_open=True;g.update(.5,(1,0),True);self.assertEqual((g.elapsed_ms,tuple(g.player.position)),before)

    def test_new_maps_save_and_reload_without_quest_or_inventory_mutation(self):
        g=self.g;g.saves.pending_scene=None
        for scene,pos in [('elden_vale_sanctuary',(1008,406)),('elden_vale_sanctuary_hall',(288,280)),('elden_vale_sanctuary_relief',(168,225))]:
            g.world=g._scene_by_id(scene);g.player.position.update(pos);g.opening_fade=g.transfer_cooldown=0
            inv=g.inventory.to_dict();quests=g.quests.to_dict();self.assertTrue(g.saves.manual(1))
            row=next(row for row in g.saves.entries() if row[2]==('manual',1))
            self.assertTrue(g.saves.load(row));self.assertEqual(g.world.data['id'],scene)
            self.assertEqual(g.inventory.to_dict(),inv);self.assertEqual(g.quests.to_dict(),quests)

if __name__=='__main__':unittest.main()
