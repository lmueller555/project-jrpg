"""Refreshed carrying art preserves Halden's single existing ownership cue."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import unittest
import pygame

import test_halden_visit as fixtures
from halden_visit import SOURCES
from caelan_scene_art import image as scene_image


class CaelanPickupContinuityTests(unittest.TestCase):
    def test_world_sack_transfers_once_at_existing_cue_then_uses_refreshed_carry(self):
        fixture=fixtures.HaldenGameplayTests(methodName='runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.addCleanup(fixture.tearDown)
        fixture.medicine()
        game,visit=fixture.game,fixture.visit
        game.player.position.update(SOURCES[0][0],SOURCES[0][1]+18)
        game.player.facing='back'
        visit.action=('lift',0);visit.action_time=0.;visit.contact=False
        inventory=game.inventory.to_dict()
        visit._update_player(.18)
        self.assertFalse(visit.contact)
        self.assertIsNone(visit.carried)
        self.assertTrue(visit.surface_prop_visible(visit.surface_props[0]))
        self.assertTrue(hasattr(game.player,'story_sprite'))
        empty=scene_image(visit.home,'assets/story/halden/caelan/lift_back_1.png')
        self.assertEqual(pygame.image.tobytes(game.player.story_sprite,'RGBA'),pygame.image.tobytes(empty,'RGBA'))
        visit._update_player(.179)
        self.assertFalse(visit.contact)
        self.assertTrue(visit.surface_prop_visible(visit.surface_props[0]))
        visit._update_player(.001)
        self.assertTrue(visit.contact)
        self.assertEqual(visit.carried,0)
        self.assertFalse(visit.surface_prop_visible(visit.surface_props[0]))
        held=scene_image(visit.home,'assets/story/halden/caelan/lift_back_2.png')
        self.assertEqual(pygame.image.tobytes(game.player.story_sprite,'RGBA'),pygame.image.tobytes(held,'RGBA'))
        visit._update_player(.36)
        self.assertIsNone(visit.action)
        self.assertEqual(visit.carried,0)
        self.assertFalse(visit.surface_prop_visible(visit.surface_props[0]))
        self.assertEqual(game.inventory.to_dict(),inventory)

    def test_blocked_approach_cannot_animate_or_transfer_the_sack(self):
        from unittest.mock import patch
        fixture=fixtures.HaldenGameplayTests(methodName='runTest')
        fixture.setUp();self.addCleanup(fixture.doCleanups);self.addCleanup(fixture.tearDown)
        fixture.medicine();game,visit=fixture.game,fixture.visit
        game.player.position.update(SOURCES[0][0]+12,SOURCES[0][1]+18)
        visit.action=('lift',0);visit.action_time=0.;visit.contact=False
        with patch.object(visit.home,'can_stand',return_value=False):
            visit._update_player(.2)
        self.assertEqual(visit.action_time,0.)
        self.assertFalse(visit.contact);self.assertIsNone(visit.carried)
        self.assertTrue(visit.surface_prop_visible(visit.surface_props[0]))
        self.assertIsNone(visit.action)
        visit.action=('lift',0)
        for _ in range(90):visit._update_player(1/60)
        self.assertEqual(visit.carried,0);self.assertIsNone(visit.action)
