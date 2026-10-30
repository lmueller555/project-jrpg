"""The repeatable town test Bat is available before the story tutorial."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from main import Game
from quests import MILL_QUEST, OPENING_QUEST
import test_battle_gameplay as battle_fixture
from test_mill_battle_gameplay import acknowledge_battle_result, click, key, wait_for_spoils


class BatContactEncounterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='bat-contact-test-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'

    def tearDown(self):pygame.quit()

    def game(self, *, title=False):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def place(self, game, distance=24):
        game.world = game.town
        game.player.position.update(game.combat.position+(0, distance))
        self.assertTrue(game.world.can_stand(game.player.position))
        game.player.facing = 'back'
        game.camera.reset()

    def trigger(self, game):
        self.place(game)
        game.update(.05, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.kind, 'bat')
        return game.combat.scene

    def finish(self, game, scene, command='attack'):
        battle_fixture.BattleGameplayTests().finish(game, scene, command)
        self.assertTrue(scene.model.ended)

    def test_fresh_journey_draws_the_bat_without_mill_progress(self):
        game = self.game()
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        self.assertEqual(game.quests.status(MILL_QUEST), 'locked')
        self.assertFalse(game.mill_quest.combat_unlocked)
        self.place(game, 48)
        game.draw()
        visible = pygame.image.tobytes(game.canvas, 'RGB')
        game.combat.cooldown = 4
        game.draw()
        self.assertNotEqual(visible, pygame.image.tobytes(game.canvas, 'RGB'))
        self.assertFalse(game.combat.active)

    def test_running_into_the_bat_starts_without_an_action_key_and_freezes_trigger_frame(self):
        game = self.game();self.place(game, 48)
        for _ in range(20):
            world = (game.elapsed_ms, tuple(game.player.position),
                     [tuple(npc.position) for npc in game.persistent_npcs])
            game.update(.05, (0, -1), True)
            if game.combat.active:
                self.assertEqual(game.combat.kind, 'bat')
                self.assertEqual((game.elapsed_ms, tuple(game.player.position),
                                  [tuple(npc.position) for npc in game.persistent_npcs]), world)
                self.assertTrue(game.combat.transitioning)
                self.assertTrue(all(actor.atb == 0 for actor in
                                    (*game.combat.model.party, game.combat.model.enemy)))
                return
        self.fail('Running into the visible Bat did not start its encounter')

    def test_dialogue_menus_and_story_actions_block_contact_without_spending_resources(self):
        blockers = {
            'pause': lambda game: game.pause.open(),
            'inventory': lambda game: game.inventory_ui.open(),
            'journal': lambda game: game.quest_ui.toggle_journal(),
            'map': lambda game: setattr(game, 'map_open', True),
            'dialogue': lambda game: game.social.start_script(
                [{'speaker': 'caelan', 'text': 'One moment.'}], identifier='bat_test_busy'),
            'quest action': lambda game: setattr(game.mill_quest, 'action', 'prepare'),
            'door transfer': lambda game: setattr(game, 'transfer_cooldown', .5),
            'opening fade': lambda game: setattr(game, 'opening_fade', .5),
            'opening pose': lambda game: (setattr(game.opening, 'stage', 'wake'),
                                          setattr(game.opening, '_sleeping', True)),
            'incapacitated': lambda game: game.attributes.set_current(hp=0),
        }
        for label, block in blockers.items():
            with self.subTest(label=label):
                game = self.game();self.place(game);block(game)
                before = (game.attributes.to_dict(), game.lattice.to_dict(),
                          game.inventory.to_dict(), game.quests.to_dict())
                game.combat.tick_world(.1)
                self.assertFalse(game.combat.active)
                self.assertEqual((game.attributes.to_dict(), game.lattice.to_dict(),
                                  game.inventory.to_dict(), game.quests.to_dict()), before)

    def test_a_conversation_can_end_while_overlapping_then_contact_can_start(self):
        game = self.game();self.place(game)
        self.assertTrue(game.social.start_script(
            [{'speaker': 'caelan', 'text': 'One moment.'}], identifier='bat_test_busy'))
        game.update(.05, (0, 0), False)
        self.assertFalse(game.combat.active)
        key(game, pygame.K_SPACE)
        game.update(.05, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.kind, 'bat')

    def test_title_interiors_and_millrace_never_trigger_the_town_bat(self):
        game = self.game(title=True);self.place(game)
        game.combat.tick_world(.1)
        self.assertFalse(game.combat.active)
        game.on_title = False
        for identifier in ('sanctuary_hall', 'upstream'):
            with self.subTest(scene=identifier):
                game.world = game._scene_by_id(identifier)
                game.player.position.update(game.combat.position+(0, 24))
                game.combat.tick_world(.1)
                self.assertFalse(game.combat.active)

    def test_remaining_in_contact_does_not_repeat_and_leaving_rearms_the_bat(self):
        game = self.game();scene = self.trigger(game)
        self.finish(game, scene, 'flee');acknowledge_battle_result(game, scene)
        self.assertFalse(game.combat.active)
        game.update(10, (0, 0), False)
        self.assertFalse(game.combat.active)
        self.place(game, 48);game.update(.05, (0, 0), False)
        self.place(game);game.update(.05, (0, 0), False)
        self.assertTrue(game.combat.active)

    def test_leaving_during_respawn_rearms_but_waits_for_the_cooldown(self):
        game = self.game();scene = self.trigger(game)
        self.finish(game, scene, 'flee');acknowledge_battle_result(game, scene)
        self.place(game, 48);game.update(.05, (0, 0), False)
        self.place(game);game.update(.05, (0, 0), False)
        self.assertFalse(game.combat.active)
        self.assertGreater(game.combat.cooldown, 0)
        game.update(4, (0, 0), False)
        self.assertTrue(game.combat.active)

    def test_loading_an_unfinished_bat_does_not_force_another_fight_until_reapproach(self):
        game = self.game();self.trigger(game)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        self.assertIsNone(json.loads(self.path.read_text()).get('post_battle'))
        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(restored.begin_journey(True))
        pygame.event.clear()
        restored.update(2, (0, 0), False)
        self.assertFalse(restored.combat.active)
        self.place(restored, 48);restored.update(.05, (0, 0), False)
        self.place(restored);restored.update(.05, (0, 0), False)
        self.assertTrue(restored.combat.active)

    def test_pre_mill_victory_resumes_spoils_once_without_inventing_quest_progress(self):
        for awarded in (False, True):
            with self.subTest(awarded=awarded):
                game = self.game();quests = game.quests.to_dict();mill = game.mill_quest.to_dict()
                scene = self.trigger(game);self.finish(game, scene)
                self.assertEqual(scene.model.phase, 'victory')
                if awarded:self.assertTrue(wait_for_spoils(game).awarded)
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                self.assertFalse(game.handle_events())
                saved = json.loads(self.path.read_text())
                self.assertEqual(saved['post_battle']['stage'], 'awarded' if awarded else 'pending')
                restored = self.game(title=True)
                self.assertTrue(restored.has_saved_journey)
                self.assertTrue(restored.begin_journey(True))
                pygame.event.clear()
                spoils = wait_for_spoils(restored)
                self.assertTrue(spoils.awarded)
                self.assertEqual(restored.lattice.state()['rp'], 20)
                self.assertEqual(restored.inventory.quantity('aether_emerald'), 1)
                self.assertEqual(restored.quests.to_dict(), quests)
                self.assertEqual(restored.mill_quest.to_dict(), mill)
                self.assertFalse(restored.music.playing)
                restored.draw()
                click(restored, spoils.continue_rect.center)
                self.assertFalse(restored.combat.active)
                self.place(restored)
                restored.update(10, (0, 0), False)
                self.assertFalse(restored.combat.active)
                self.assertEqual(restored.lattice.state()['rp'], 20)


if __name__ == '__main__':unittest.main()
