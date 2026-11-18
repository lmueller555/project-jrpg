"""Home migration preserves travel, wake registration and actual inspection use."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
import pygame

from rendering import WorldCanvas

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary_home_hd'
BANK=ROOT/'assets/terrain/eldenmere/sanctuary_home_hd'


class HomeAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe=json.loads((SOURCE/'recipe.json').read_text())
        cls.manifest=json.loads((BANK/'manifest.json').read_text())

    def test_sources_and_gameplay_registration_are_preserved(self):
        self.assertEqual(hashlib.sha256((SOURCE/'props_atlas.png').read_bytes()).hexdigest(),self.recipe['source_sha256'])
        for room,spec in self.recipe['rooms'].items():
            current=json.loads((ROOT/spec['map']).read_text());old=spec['original_map']
            for key in ('size_pixels','size_tiles','tile_size','floor_rect','player_probe_size',
                        'player_draw_anchor','spawn','collision','ground_frame_duration_ms'):
                self.assertEqual(current[key],old[key],(room,key))
            self.assertEqual(hashlib.sha256((ROOT/current['collision']).read_bytes()).hexdigest(),spec['collision_sha256'])
            for door,previous in zip(current['doors'],old['doors']):
                for key,value in previous.items():
                    if key!='frames':self.assertEqual(door[key],value,(room,key))
            for key,value in old['destinations'].items():self.assertEqual(current['destinations'][key],value)
            by_id={e['id']:e for e in current['entities']}
            for entity in old['entities']:
                for key in ('position','sort_y','frame_duration_ms','phase_offset'):
                    self.assertEqual(by_id[entity['id']][key],entity[key])

    def test_new_props_have_native_detail_black_contours_and_stable_support(self):
        for record in self.manifest['props']:
            with self.subTest(record['id']):
                image=Image.open(ROOT/record['image']).convert('RGBA')
                self.assertEqual(image.size,tuple(v*2 for v in record['logical_size']))
                self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                self.assertIn((17,18,20,255),set(image.get_flattened_data()))
                self.assertEqual(image.getbbox()[3],record['logical_bounds'][3]*2)
        image=Image.open(BANK/'props/bed.png').convert('RGBA')
        self.assertTrue(any(len({image.getpixel((x+dx,y+dy)) for dx in (0,1) for dy in (0,1)})>1
                            for x in range(0,image.width,2) for y in range(0,image.height,2)))

    def test_architecture_is_shared_and_all_five_door_poses_have_same_registration(self):
        for spec in self.recipe['rooms'].values():
            current=json.loads((ROOT/spec['map']).read_text())
            self.assertEqual(len(set(current['ground_frames'])),1)
            with Image.open(ROOT/current['ground_frames'][0]) as image:
                self.assertEqual(image.size,tuple(v*2 for v in current['size_pixels']))
        frames=[Image.open(ROOT/p).convert('RGBA') for p in self.manifest['doors']]
        self.assertEqual(len({f.tobytes() for f in frames}),5)
        for image in frames:
            self.assertEqual(image.size,(48,72))
            # The jamb/cap remain fixed while the rigid leaf narrows leftward.
            self.assertEqual(image.crop((0,0,48,6)).tobytes(),frames[0].crop((0,0,48,6)).tobytes())


    def test_passage_and_sill_are_registered_and_builder_owned(self):
        from tools.build_sanctuary_home_hd import door_poses
        source=Image.open(SOURCE/'props_atlas.png').convert('RGBA')
        frames=[Image.open(ROOT/p).convert('RGBA') for p in self.manifest['doors']]
        for actual,expected in zip(frames,door_poses(source)):
            self.assertEqual(actual.tobytes(),expected.tobytes())
            self.assertEqual(actual.crop((4,68,44,72)).tobytes(),
                             frames[0].crop((4,68,44,72)).tobytes())
            self.assertEqual(actual.crop((44,0,48,72)).tobytes(),
                             frames[0].crop((44,0,48,72)).tobytes())
        opened=frames[-1]
        self.assertNotEqual(opened.getpixel((25,30)),(36,48,45,255))
        # Floor seams and the upper shaded room remain visible behind the leaf.
        self.assertNotEqual(opened.getpixel((25,30)),opened.getpixel((25,56)))
        self.assertNotEqual(opened.getpixel((25,56)),opened.getpixel((25,69)))
        # Already-exposed background never shifts as the leaf narrows.
        for index,(current,following) in enumerate(zip(frames,frames[1:])):
            exposed=4+(40,32,23,12)[index]
            self.assertEqual(current.crop((exposed,6,44,68)).tobytes(),
                             following.crop((exposed,6,44,68)).tobytes())


class HomeGameplayTests(unittest.TestCase):
    def setUp(self):
        from main import Game
        self.temp=tempfile.TemporaryDirectory();p=Path(self.temp.name)
        self.game=Game(fullscreen=False,start_on_title=True,save_path=p/'save.json',settings_path=p/'settings.json')
        g=self.game;g.on_title=False;g.opening_fade=0;g.opening.stage='explore'
        g.world=g._scene_by_id('sanctuary_bedroom');g.player.position.update(144,276)

    def tearDown(self):
        self.game.music.stop();pygame.quit();self.temp.cleanup()

    def test_all_five_inspections_are_reachable_cued_and_use_original_dialogue(self):
        g=self.game;before=g.quests.to_dict()
        positions={'books':(108,90),'drawing':(60,90),'notes':(168,150),
                   'wardrobe':(228,118),'window':(180,90)}
        records={r['id']:r for r in g.world.object_cues.records}
        self.assertEqual(set(records),set(g.opening.data['inspections']))
        for key,position in positions.items():
            with self.subTest(key):
                g.player.position.update(position);self.assertTrue(g.world.can_stand(position))
                g._update_object_cues(.12)
                self.assertTrue(g.world.object_cues.states[records[key]['entity']]['near'])
                self.assertEqual(g.opening.interaction_hint(),'E: inspect '+g.opening.data['inspections'][key]['label'])
                self.assertTrue(g.opening.inspect_nearby())
                self.assertEqual(g.social.script_identifier,'bedroom_inspect_'+key)
                rendered=' '.join(g.social.page['lines'])
                self.assertEqual(rendered,g.opening.data['inspections'][key]['text'])
                g._update_object_cues(0);self.assertFalse(g.world.object_cues.enabled)
                g.social.cancel_script()
        self.assertEqual(g.quests.to_dict(),before)

    def test_repeatable_inspections_restore_eligibility_and_wake_suppresses_it(self):
        g=self.game;g.player.position.update(108,90);g._update_object_cues(.12)
        self.assertEqual(len(g.world.object_cues.states),5)
        snapshot=g.opening.to_dict();g.opening.stage='wake';g._update_object_cues(.12)
        self.assertEqual(g.world.object_cues.states,{})
        self.assertTrue(g.opening.restore(snapshot));g._update_object_cues(.12)
        self.assertEqual(len(g.world.object_cues.states),5)
        self.assertTrue(g.opening.inspect_nearby());g.social.cancel_script()
        g._update_object_cues(.12);self.assertTrue(g.opening.inspect_nearby())

    def test_real_doors_join_all_three_migrated_rooms_and_courtyard(self):
        g=self.game;g.opening.stage='disabled'
        for actor in g.persistent_npcs:actor.story_paused=True
        for world in g.scenes.values():world.npcs.clear()
        g.world=g._scene_by_id('sanctuary_hall')
        for key,destination in [('bedroom','sanctuary_bedroom'),('hall','sanctuary_hall'),
                                ('dining','sanctuary_dining'),('hall','sanctuary_hall'),
                                ('courtyard','eldenmere.playable'),('sanctuary','sanctuary_hall')]:
            door=next(d for d in g.world.doors if d.data['id']==key)
            north=door.data['entry_side']=='north'
            g.player.position.update(pygame.Vector2(door.data['anchor'])+(0,12 if north else -12))
            g.transfer_cooldown=0;g.update(.5,(0,0),False)
            for _ in range(90):
                g.update(1/60,(0,-1 if north else 1),False)
                if g.world.data['id']==destination:break
            self.assertEqual(g.world.data['id'],destination,key)
            self.assertTrue(g.world.can_stand(g.player.position))

    def test_wake_uses_native_bed_surface_with_existing_pose_and_quilt_registration(self):
        g=self.game;g.opening.start_new_game();g.opening._queue_wake()
        bed=next(e for e in g.world.entities if e['id']=='bed')
        self.assertIsInstance(bed['surfaces'][0],WorldCanvas)
        saw_quilt=False
        for _ in range(12):
            g.opening._update_actions(.06)
            canvas=WorldCanvas(g.world.size);g.world.draw(canvas,(0,0),g.player,0,False)
            g.opening.draw_world(canvas,(0,0))
            if g.opening._bed_occlusion:saw_quilt=True
        self.assertTrue(saw_quilt)
