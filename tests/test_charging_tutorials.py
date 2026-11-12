"""Guided battles teach preparation without requiring a ready-time override."""
import unittest

import pygame

import test_gear_battle_scene as gear_scene_tests


class ChargingTutorialTests(unittest.TestCase):
    def setUp(self):
        self.driver = gear_scene_tests.GearBattleSceneTests()
        self.driver.setUp()
        self.addCleanup(self.driver.tearDown)

    def test_mill_guidance_precedes_the_charging_cutoff_and_discovery_still_completes(self):
        driver = self.driver
        driver.make_scene(tutorial=True, learned=())
        scene, model = driver.scene, driver.model
        charging_seen = set()
        for _ in range(4000):
            scene.update(.05)
            driver.draw()
            if scene.tutorial_active:
                key = scene._tutorial_queue[0]['key']
                if key in ('gear_instruction', 'rig_instruction'):
                    self.assertEqual(model.phase, 'charging')
                    self.assertGreaterEqual(model.charging_boundary_seconds(), 1.)
                    self.assertLess(model.player.atb, 1)
                    charging_seen.add(key)
                driver.key(pygame.K_RETURN)
                continue
            if model.waiting_for_player:
                self.assertFalse(scene.gear_enabled)
                self.assertFalse(scene.rig_enabled)
                command = 'aqua_edge' if model.spellblade_stage == 'first_edge' else 'guard'
                if command == 'aqua_edge':
                    driver.click(scene.command_rects['skills'].center)
                    driver.draw()
                driver.click(scene.command_rects[command].center)
            if model.aether_edge_discovered and 'rig_instruction' in charging_seen:
                self.assertIn('gear_instruction', charging_seen)
                self.assertIn('blue_focus_ready', scene._tutorial_seen)
                self.assertEqual(model.active_gem, 'water')
                return
            self.assertFalse(model.ended, model.phase)
        self.fail('Guided preparation or Aether discovery did not complete')


if __name__ == '__main__':unittest.main()
