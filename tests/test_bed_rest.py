"""Bedside input restores resources without resetting the journey or growth."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from character_attributes import CharacterAttributes
from main import Game


class BedRestTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='bed-rest-test-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'

    def tearDown(self):
        pygame.quit()

    def game(self, title=False):
        game = Game(window_size=(960, 640), fullscreen=False,
                    start_on_title=title, save_path=self.path,
                    settings_path=self.directory/'settings.json')
        game.audio.set_music(0)
        game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def bedside(self, game, position=(60, 186)):
        game.world = game._scene_by_id('sanctuary_bedroom')
        game.player.position.update(position)
        game.player.facing = 'back'
        self.assertTrue(game.world.can_stand(game.player.position))
        game.camera.reset()

    def key(self, game, key):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=key, repeat=False))
        self.assertTrue(game.handle_events())

    def click(self, game, logical):
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = (round((width-480*scale)//2+logical[0]*scale),
                 round((height-320*scale)//2+logical[1]*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(game.handle_events())

    def offer(self, game):
        self.assertEqual(game.bed_rest.interaction_hint(), 'E: rest')
        self.key(game, pygame.K_e)
        self.assertEqual(game.social.script_identifier, 'bed_rest_offer')
        for _ in range(20):
            if game.social.choosing:
                game.draw()
                return
            self.assertTrue(game.social.active)
            self.key(game, pygame.K_SPACE)
        self.fail('The bedside offer did not expose its choices.')

    def choose(self, game, action):
        options = game.social.choice_options
        index = next(index for index, option in enumerate(options)
                     if option['action'] == action)
        self.click(game, game.social.choice_rects[index].center)

    def resources(self, attributes):
        return attributes.current_hp, attributes.current_mp

    def journey(self, game):
        return (game.lattice.to_dict(), game.inventory.to_dict(),
                game.quests.to_dict(), sorted(game.social.flags),
                game.opening.to_dict(), game.mill_quest.to_dict(),
                game.regent_quest.to_dict(), game.lantern_quest.to_dict())

    def grow_resources(self, game):
        self.assertTrue(game.award_battle_rewards(
            'bed-rest-growth', {'caelan': 10000},
            {'aether_emerald': 2, 'aether_sapphire': 2, 'aether_diamond': 1}))
        for identifier in ('hp_01', 'mp_01', 'mend_01'):
            self.assertTrue(game.move_lattice(identifier))
            self.assertTrue(game.activate_lattice(identifier))

    def test_rest_is_available_at_the_foot_and_side_in_existing_journeys(self):
        game = self.game()
        self.assertTrue(game.attributes.set_current(hp=17, mp=2))
        for stage, position in (('disabled', (60, 186)), ('done', (96, 156))):
            with self.subTest(stage=stage, position=position):
                game.opening.stage = stage
                self.bedside(game, position)
                self.assertTrue(game.bed_rest.nearby())
                self.offer(game)
                self.assertEqual(self.resources(game.attributes), (17, 2))
                self.choose(game, 'leave')
                self.assertFalse(game.social.locked)
                self.assertEqual(self.resources(game.attributes), (17, 2))

    def test_only_an_explicit_rest_choice_heals_and_cancel_discards_the_offer(self):
        game = self.game()
        self.bedside(game)
        self.assertTrue(game.attributes.set_current(hp=11, mp=1))
        self.offer(game)
        self.key(game, pygame.K_SPACE)
        self.key(game, pygame.K_e)
        self.assertTrue(game.social.choosing)
        self.assertEqual(self.resources(game.attributes), (11, 1))
        self.choose(game, 'leave')
        self.offer(game)
        self.assertTrue(game.social.cancel())
        self.assertIsNone(game.social._choice_callback)
        self.assertEqual(self.resources(game.attributes), (11, 1))

    def test_drawing_above_the_headboard_keeps_its_inspection(self):
        game = self.game()
        game.opening.stage = 'explore'
        self.bedside(game, (60, 90))
        self.assertTrue(game.attributes.set_current(hp=13, mp=2))
        self.assertFalse(game.bed_rest.nearby())
        self.key(game, pygame.K_e)
        self.assertEqual(game.social.script_identifier, 'bedroom_inspect_drawing')
        self.assertEqual(self.resources(game.attributes), (13, 2))

    def test_stale_choice_outside_bedside_range_does_not_heal(self):
        game = self.game()
        self.bedside(game)
        self.assertTrue(game.attributes.set_current(hp=19, mp=3))
        self.offer(game)
        rest_index = next(index for index, option in enumerate(game.social.choice_options)
                          if option['action'] == 'rest')
        stale_button = game.social.choice_rects[rest_index].center
        # This remains within conversation range but leaves the physical bed.
        game.player.position.update(60, 212)
        self.assertTrue(game.world.can_stand(game.player.position))
        self.click(game, stale_button)
        self.assertEqual(self.resources(game.attributes), (19, 3))
        self.assertNotEqual(game.social.script_identifier, 'bed_rest_complete')
        self.assertFalse(game.bed_rest.nearby())

    def test_walking_away_cancels_without_recovery_or_a_saved_resource_change(self):
        game = self.game()
        self.bedside(game)
        self.assertTrue(game.attributes.set_current(hp=23, mp=4))
        self.assertTrue(game.save_progress())
        self.offer(game)
        for _ in range(120):
            if not game.social.locked:
                break
            game.update(1/60, (1, 0), False)
        self.assertFalse(game.social.locked)
        self.assertIsNone(game.social._choice_callback)
        self.assertEqual(self.resources(game.attributes), (23, 4))
        saved = json.loads(self.path.read_text())['character_attributes']
        self.assertEqual((saved['current_hp'], saved['current_mp']), (23, 4))

    def test_inventory_combat_and_other_bedrooms_cannot_trigger_rest(self):
        game = self.game()
        self.bedside(game)
        self.assertTrue(game.attributes.set_current(hp=29, mp=5))
        game.inventory_ui.open()
        self.assertFalse(game.bed_rest.nearby())
        self.key(game, pygame.K_e)
        self.assertFalse(game.social.locked)
        self.assertEqual(self.resources(game.attributes), (29, 5))
        game.inventory_ui.close()
        game.world = game._scene_by_id('elira')
        self.assertFalse(game.bed_rest.interact())
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        self.assertTrue(game.combat.interact())
        self.bedside(game)
        self.assertFalse(game.bed_rest.interact())
        self.key(game, pygame.K_e)
        self.assertFalse(game.social.locked)
        self.assertEqual(self.resources(game.attributes), (29, 5))

    def test_rest_revives_and_fully_restores_before_the_completion_message(self):
        game = self.game()
        self.bedside(game)
        self.assertTrue(game.attributes.set_current(hp=0, mp=0))
        self.offer(game)
        self.choose(game, 'rest')
        self.assertEqual(self.resources(game.attributes), (140, 30))
        self.assertEqual(game.social.script_identifier, 'bed_rest_complete')
        self.assertGreater(game.opening_fade, 0)
        saved = json.loads(self.path.read_text())['character_attributes']
        self.assertEqual((saved['current_hp'], saved['current_mp']), (140, 30))

    def test_lattice_maxima_and_caps_survive_rest_and_continue_without_other_changes(self):
        for capped in (False, True):
            with self.subTest(capped=capped):
                game = self.game()
                self.bedside(game)
                if capped:
                    record = game.attributes.to_dict()
                    record['attributes'].update(hp=9950, mp=997, spr=21)
                    self.assertTrue(game.attributes.restore(record))
                self.grow_resources(game)
                self.assertTrue(game.attributes.set_current(hp=7, mp=0))
                game.social.flags.add('bed_rest_preserves_flags')
                prior = self.journey(game)
                base = deepcopy(game.attributes.to_dict()['attributes'])
                ratings = {key: game.attributes.value(key)
                           for key in game.attributes.definitions}
                expected = (9999, 999) if capped else (240, 35)
                self.offer(game)
                self.choose(game, 'rest')
                self.assertEqual(self.resources(game.attributes), expected)
                self.assertEqual(self.journey(game), prior)
                self.assertEqual(game.attributes.to_dict()['attributes'], base)
                self.assertEqual({key: game.attributes.value(key)
                                  for key in game.attributes.definitions}, ratings)
                recovered = game.attributes.to_dict()
                restored = self.game(title=True)
                self.assertTrue(restored.has_saved_journey)
                self.assertTrue(restored.begin_journey(True))
                self.assertEqual(restored.attributes.to_dict(), recovered)
                self.assertEqual(self.resources(restored.attributes), expected)
                self.assertEqual(self.journey(restored), prior)
                self.assertEqual({key: restored.attributes.value(key)
                                  for key in restored.attributes.definitions}, ratings)

    def test_rest_recovers_every_registered_character_without_resetting_modifiers(self):
        game = self.game()
        self.bedside(game)
        catalog = deepcopy(game.attributes.catalog)
        catalog['characters']['companion'] = deepcopy(catalog['characters']['caelan'])
        catalog['characters']['companion']['name'] = 'Companion'
        companion = CharacterAttributes('companion', catalog)
        self.assertTrue(companion.set_modifiers('equipment', {'hp': 37, 'mp': 4, 'def': 9}))
        self.assertTrue(companion.set_current(hp=0, mp=0))
        game.lattice_progression.attributes['companion'] = companion
        base = deepcopy(companion.to_dict()['attributes'])
        self.assertTrue(game.attributes.set_current(hp=1, mp=0))
        self.offer(game)
        self.choose(game, 'rest')
        self.assertEqual(self.resources(game.attributes), (140, 30))
        self.assertEqual(self.resources(companion), (177, 34))
        self.assertEqual(companion.to_dict()['attributes'], base)
        self.assertEqual(companion.value('def'), 19)


if __name__ == '__main__':
    unittest.main()
