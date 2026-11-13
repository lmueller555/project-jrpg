"""Greenwell recovery and post-boss encounter distance contracts."""
import json
import unittest
from types import SimpleNamespace as NS
from pathlib import Path
from character_attributes import CharacterAttributes
from cave_random_encounters import CaveRandomEncounters
import test_sanctuary_cave_controller as controller_tests

ROOT=Path(__file__).resolve().parents[1]

class GreenwellTests(unittest.TestCase):
    def test_half_distance_and_exact_trigger_after_boss(self):
        for defeated,expected in ((False,10),(True,20)):
            owner=CaveRandomEncounters(seed=42)
            state=owner.to_dict();state['remaining']=10
            self.assertTrue(owner.restore(state))
            ticket=owner.travel((456,1280),(486,1280),boss_defeated=defeated)
            self.assertAlmostEqual(ticket['position'][0],456+expected)
            self.assertEqual(owner.pending,ticket)
            self.assertEqual(owner.travel((486,1280),(500,1280),boss_defeated=True),ticket)

    def test_safe_chamber_and_reachable_bank(self):
        import pygame
        from main import World
        data=json.loads((ROOT/'assets/maps/sanctuary_cave/map.json').read_text())
        pool=next(r for r in data['cave']['inspections'] if r.get('healing_pool'))
        owner=CaveRandomEncounters()
        self.assertIsNone(owner.region_at(pool['approach'])['area'])
        pygame.init();pygame.display.set_mode((320,240))
        self.addCleanup(pygame.quit)
        world=World(ROOT/'assets/maps/sanctuary_cave/map.json')
        self.assertTrue(world.can_stand(pool['approach']))
        self.assertFalse(world.can_stand((2052,780)))
        pygame.quit()

    def test_recovery_is_repeatable_and_modal_guarded(self):
        fixture=controller_tests.CaveControllerTests('runTest');fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        game=fixture.game;controller=fixture.scene
        attributes=CharacterAttributes();attributes.set_current(hp=0,mp=0)
        game.party=NS(active_ids=('caelan',),attributes=lambda _:attributes)
        game.world.data['cave']['treasures']=[]
        game.world.data['cave']['inspections']=[dict(id='spring',position=[120,90],healing_pool=True,text='Restored.')]
        game.pause.is_open=True
        self.assertFalse(controller.interact());self.assertEqual(attributes.current_hp,0)
        game.pause.is_open=False
        for _ in range(2):
            attributes.set_current(hp=0,mp=0);game.social.locked=False
            self.assertTrue(controller.interact())
            self.assertEqual(attributes.current_hp,attributes.value('hp'))
            self.assertEqual(attributes.current_mp,attributes.value('mp'))
        self.assertEqual(len(fixture.checkpoints),2)
