"""Opt-in roster fidelity and fixed identity/behavior across all seven residents."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from main import Game, StationaryNPC
from npc_roster_art import RosterArt, bindings
from rendering import snapshot, WorldCanvas

ROOT=Path(__file__).resolve().parents[1]


class RosterBindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        p=Path(cls.temp.name)
        cls.game=Game(fullscreen=False,start_on_title=True,
                      save_path=p/'save.json',settings_path=p/'settings.json')

    @classmethod
    def tearDownClass(cls):
        cls.game.music.stop();pygame.quit();cls.temp.cleanup()

    def actors(self):
        for scene in ('home_a','home_b','home_c','inn','item_shop'):
            self.game._scene_by_id(scene)
        return {a.data['id']:(world,a) for world in self.game.scenes.values()
                for a in world.npcs if a.data['id'] in bindings()}

    def test_exact_seven_without_mutating_map_or_actor_identity(self):
        expected={'villager_male_01','villager_female_01','villager_male_02',
                  'villager_female_03','villager_male_03','inn_keeper','item_shop_keeper'}
        self.assertEqual(set(bindings()),expected)
        self.assertEqual(set(self.actors()),expected)
        for actor_id,(world,actor) in self.actors().items():
            record=next(r for r in json.loads(world.path.read_text())['npcs'] if r['id']==actor_id)
            self.assertEqual(actor.data,record)
            self.assertEqual(tuple(actor.position),tuple(record['position']))
            self.assertEqual(tuple(actor.draw_anchor),tuple(record['draw_anchor']))
            self.assertEqual(actor.blocker.size,tuple(record['probe_size']))
            self.assertFalse(actor.moving)
            self.assertFalse(hasattr(actor,'behavior'))
            self.assertFalse(hasattr(actor,'request_conversation'))
            self.assertIsInstance(actor,StationaryNPC)

    def test_native_idles_and_all_walk_frames_are_exact_at_world_scale(self):
        for _,(world,actor) in self.actors().items():
            bank=actor.roster_art
            folder=ROOT/'assets/characters/npc_roster_hd'/bank.design_id
            for direction in ('front','back','left','right'):
                idle=bank.sprite(direction)
                self.assertEqual(idle.get_size(),(24,36))
                self.assertEqual(pygame.image.tobytes(snapshot(idle),'RGBA'),
                                 pygame.image.tobytes(pygame.image.load(str(folder/f'idle_{direction}.png')),'RGBA'))
                self.assertEqual(len(bank.walks[direction]),8)
                for index,(frame,duration) in enumerate(bank.walks[direction]):
                    self.assertEqual(duration,70)
                    self.assertIs(bank.sprite(direction,True,index*70),frame)
                    self.assertIs(bank.sprite(direction,True,index*70+69),frame)
                    original=pygame.image.load(str(folder/f'walk_{direction}/frame_{index+1:02}.png'))
                    target=WorldCanvas((24,36),pygame.SRCALPHA);target.blit(frame,(0,0))
                    self.assertEqual(pygame.image.tobytes(snapshot(target),'RGBA'),
                                     pygame.image.tobytes(original,'RGBA'))
                self.assertIs(bank.sprite(direction,True,560),bank.walks[direction][0][0])

    def test_service_portraits_are_bound_without_changing_shared_civilian_portraits(self):
        social=self.game.social
        for speaker,design in [('innkeeper','innkeeper_05'),('shopkeeper','shopkeeper_03')]:
            key=social.data['speakers'][speaker]['portrait']
            self.assertEqual(key,'npc_roster_hd:'+design)
            original=pygame.image.load(str(ROOT/f'assets/characters/npc_roster_hd/{design}/portrait.png'))
            self.assertEqual(pygame.image.tobytes(social.portraits[key],'RGBA'),
                             pygame.image.tobytes(original,'RGBA'))
        for speaker in ('bridge_mason','regent_driver'):
            self.assertEqual(social.data['speakers'][speaker]['portrait'],'male_01')
        source=json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())
        for key,value in source['speakers'].items():
            if key not in ('innkeeper','shopkeeper'):
                self.assertEqual(social.data['speakers'][key],value)

    def test_unmigrated_character_art_and_five_household_portrait_bindings(self):
        for identifier,(world,actor) in self.actors().items():
            self.assertTrue((ROOT/actor.roster_art.portrait_path).is_file())
        home=self.game._scene_by_id('home_a')
        tessa=next(a for a in home.npcs if a.data['id']=='tessa')
        self.assertNotIn('tessa',bindings())
        self.assertEqual(tessa.sprite(0).get_size(),pygame.image.load(str(ROOT/tessa.data['sprite'])).get_size())
