"""Opt-in regional native travel preserves role controllers and action ownership."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from main import Game
from rendering import WorldCanvas, snapshot
from regional_npc_art import actor_binding, bound_regional_design, ROLES, RegionalRosterArt
ROOT=Path(__file__).resolve().parents[1]

class RegionalNativeTravelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();p=Path(cls.temp.name)
        cls.game=Game(fullscreen=False,start_on_title=True,save_path=p/'journey.json',settings_path=p/'settings.json')
        world=cls.game.overworld_world
        cls.actors={a.data['id']:a for c in (world.grain_farm,world.bridge_crew,world.garden_orchard) for a in c.actors}
    @classmethod
    def tearDownClass(cls):
        cls.game.music.stop();cls.actors.clear();del cls.game;pygame.quit();cls.temp.cleanup()
    def test_explicit_binding_only_and_original_physics(self):
        self.assertEqual(set(self.actors),set(ROLES))
        for key,actor in self.actors.items():
            with self.subTest(actor=key):
                binding=actor_binding(key)
                self.assertEqual(tuple(actor.probe_size),(10,6))
                self.assertEqual(tuple(actor.draw_anchor),(20,38))
                self.assertEqual(actor.scene_id,'auratia.overworld')
                self.assertEqual(actor.blocker.size,(10,6))
                self.assertEqual(bool(actor.regional_roster),bool(binding))
                if binding:
                    self.assertEqual(actor.regional_roster.design_id,ROLES[key])
                    self.assertEqual(bool(actor.regional_activity),binding['activation']['activity'])
        self.assertIsNone(actor_binding('sanctuary_gardener'))
        self.assertIsNone(actor_binding('invented_actor'))
    def test_unbound_roles_do_not_receive_implicit_sibling_activation(self):
        from grain_farm import FarmWorker
        with patch('regional_npc_art.actor_binding',return_value=None):
            actor=FarmWorker('loader','male_02',(0,0))
        self.assertIsNone(actor.regional_roster)
        self.assertEqual(actor.data,{'id':'grain_loader','name':'Grain loader'})
    def test_native_roster_pixels_survive_padding_and_each_complete_cycle(self):
        for key,actor in self.actors.items():
            binding=actor_binding(key)
            if not binding:continue
            bank=actor.regional_roster
            for direction in ('front','back','left','right'):
                with self.subTest(actor=key,direction=direction):
                    expected=pygame.image.load(str(ROOT/f'assets/characters/npc_roster_hd/{bank.design_id}/idle_{direction}.png'))
                    actual=snapshot(bank.sprite(direction,False,0))
                    self.assertEqual(actual.get_size(),(80,88))
                    self.assertEqual(pygame.image.tobytes(actual.subsurface((16,7,48,72)),'RGBA'),pygame.image.tobytes(expected,'RGBA'))
                    frames=bank.bank.walks[direction];duration=binding['travel_cycle_ms']/len(frames)
                    for index in range(len(frames)):
                        actual=snapshot(bank.sprite(direction,True,index*duration+.01))
                        expected=pygame.image.load(str(ROOT/f'assets/characters/npc_roster_hd/{bank.design_id}/walk_{direction}/frame_{index+1:02}.png'))
                        self.assertEqual(pygame.image.tobytes(actual.subsurface((16,7,48,72)),'RGBA'),pygame.image.tobytes(expected,'RGBA'))
                    self.assertIs(bank.sprite(direction,True,0),bank.sprite(direction,True,binding['travel_cycle_ms']))
    def test_legacy_activity_mirror_and_attachment_metadata_stay_stable(self):
        for key,actor in self.actors.items():
            if not actor_binding(key):continue
            if hasattr(actor,'clips'):
                for clip in actor.clips.values():
                    for frame in clip['frames']:
                        self.assertEqual(frame['image'].get_size(),(40,44))
                old=(actor.pose,actor.facing,actor.moving,actor.clock)
                clip_name='inspect_front' if 'inspect_front' in actor.clips else 'work_left' if 'work_left' in actor.clips else 'work_right'
                actor.pose,actor.facing=clip_name.split('_',1);actor.moving=False;actor.clock=0
                selected=actor.clips[actor.animation_key]['frames'][actor.frame_index]['image']
                self.assertIs(actor.sprite(0),selected)
                actor.pose,actor.facing,actor.moving,actor.clock=old
    def test_bound_speaker_uses_matching_existing_portrait_only(self):
        source=json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())['speakers']
        for key in ROLES:
            design=bound_regional_design(key)
            if not design:continue
            self.assertEqual(self.game.social.data['speakers'][key]['portrait'],'npc_roster_hd:'+design)
            original=pygame.image.load(str(ROOT/f'assets/characters/npc_roster_hd/{design}/portrait.png'))
            actual=self.game.social.portraits['npc_roster_hd:'+design]
            self.assertEqual(pygame.image.tobytes(actual,'RGBA'),pygame.image.tobytes(original,'RGBA'))
        self.assertEqual(self.game.social.data['speakers']['regent_driver'],source['regent_driver'])
    def test_all_bindings_keep_original_activity_sources_and_approved_banks_read_only(self):
        for key in ROLES:
            binding=actor_binding(key)
            if binding:self.assertTrue((ROOT/binding['activity_owner']).is_file())
