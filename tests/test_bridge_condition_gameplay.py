"""Bridge conditions survive real journey ownership without inventing events.

Selected conditions below are save/render fixtures. Playable transition safety
is covered separately; retired layout placeholders now roll forward to intact.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from bridge_condition import BridgeCondition, DEFAULT_REPAIR_FLAG
from bridge_crew import SCENE_ID
from main import Game
from regional_audio import Source
from tools.scenario_fixtures import seed_mill_completed


class BridgeConditionGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='bridge-condition-game-')
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.path = self.folder/'journey.json'
        self.games = []

    def tearDown(self):
        for game in self.games:
            game.social.cancel_script()
            game.opening_audio.reset();game.regional_audio.reset();game.music.stop()
        pygame.quit()

    def game(self, *, title=False):
        game = Game(fullscreen=False, start_on_title=title, window_size=(960, 640),
                    save_path=self.path, settings_path=self.folder/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        self.games.append(game)
        pygame.event.clear()
        return game

    def payload(self, *, completed_mill=False):
        game = self.game()
        if completed_mill:seed_mill_completed(game)
        payload = game.journey_snapshot()
        self.assertEqual(payload['story_revision'], 2)
        self.assertIsNotNone(game._validate_journey(payload), game.save_error)
        return game, payload

    def write_payload(self, payload):
        self.path.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
        return self.path.read_bytes()

    @staticmethod
    def facts(payload):
        return {key: deepcopy(payload[key]) for key in (
            'quests', 'inventory', 'dialogue_flags', 'party', 'battle_rewards',
            'character_levels', 'character_abilities', 'sanctuary_boss', 'elemental_bosses')}

    @staticmethod
    def stage(game, phase):
        game.overworld_travel.restore_bridge_condition(
            {'bridge_condition': BridgeCondition(phase).to_dict()})

    @staticmethod
    def deck(world):
        return world._tile_rect(world.region['bridge']['deck_rect_tiles'])

    def test_revision_two_missing_component_validates_without_mutation_then_rolls_forward(self):
        original, payload = self.payload(completed_mill=True)
        payload['overworld'].pop('bridge_condition')
        before = deepcopy(payload)
        raw = self.write_payload(payload)
        self.assertIsNotNone(original._validate_journey(payload), original.save_error)
        self.assertEqual(payload, before)
        self.assertEqual(self.path.read_bytes(), raw)
        loaded = self.game(title=True)
        self.assertTrue(loaded.has_saved_journey, loaded.save_error)
        self.assertIsNone(loaded._overworld_world)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertTrue(loaded.begin_journey(True), loaded.save_error)
        expected = {'version': 1, 'phase': 'intact', 'origin': 'explicit'}
        self.assertEqual(loaded.overworld_travel.bridge_condition.to_dict(), expected)
        snapshot = loaded.journey_snapshot()
        self.assertEqual(snapshot['overworld']['bridge_condition'], expected)
        self.assertEqual(self.facts(snapshot), self.facts(before))
        self.assertTrue(loaded.overworld_world.can_stand(self.deck(loaded.overworld_world).center))

    def test_legacy_repair_flag_survives_continue_without_fabricating_story_receipts(self):
        _, payload = self.payload(completed_mill=True)
        payload['overworld'].pop('bridge_condition')
        payload['dialogue_flags'].append(DEFAULT_REPAIR_FLAG)
        raw = self.write_payload(payload)
        loaded = self.game(title=True)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertTrue(loaded.begin_journey(True), loaded.save_error)
        expected = {'version': 1, 'phase': 'restored', 'origin': 'legacy_repair'}
        self.assertEqual(loaded.overworld_travel.bridge_condition.to_dict(), expected)
        self.assertEqual(self.facts(loaded.journey_snapshot()), self.facts(payload))
        world = loaded.overworld_world
        self.assertTrue(world.can_stand(self.deck(world).center))
        self.assertEqual(world.bridge_condition.to_dict(), expected)

    def test_explicit_conditions_win_flags_after_lazy_town_continue(self):
        _, base = self.payload()
        for phase in ('intact', 'destroyed', 'restored'):
            with self.subTest(phase=phase):
                payload = deepcopy(base)
                condition = BridgeCondition(phase).to_dict()
                payload['overworld']['bridge_condition'] = condition
                # Both passable states must work without a repair flag; an
                # explicit destroyed state must override an old positive flag.
                payload['dialogue_flags'] = ([DEFAULT_REPAIR_FLAG] if phase == 'destroyed' else [])
                self.write_payload(payload)
                loaded = self.game(title=True)
                self.assertIsNone(loaded._overworld_world)
                self.assertTrue(loaded.begin_journey(True), loaded.save_error)
                self.assertIsNone(loaded._overworld_world)
                self.assertEqual(loaded.overworld_travel.bridge_condition.to_dict(), condition)
                world = loaded.overworld_world
                self.assertEqual(world.bridge_condition.to_dict(), condition)
                self.assertEqual(world.can_stand(self.deck(world).center), phase != 'destroyed')
                self.assertTrue(loaded.save_progress())
                saved = json.loads(self.path.read_text())
                self.assertEqual(saved['overworld']['bridge_condition'], condition)
                self.assertEqual(saved['dialogue_flags'], payload['dialogue_flags'])

    def test_passable_condition_is_staged_before_regional_player_landing(self):
        source, base = self.payload()
        world = source.overworld_world
        center = list(self.deck(world).center)
        for phase in ('intact', 'restored'):
            with self.subTest(phase=phase):
                payload = deepcopy(base)
                payload['overworld']['bridge_condition'] = BridgeCondition(phase).to_dict()
                payload['player'].update(scene=world.data['id'], position=center, facing='left')
                payload['dialogue_flags'] = []
                raw = self.write_payload(payload)
                loaded = self.game(title=True)
                self.assertTrue(loaded.has_saved_journey, loaded.save_error)
                self.assertIsNone(loaded._overworld_world)
                self.assertEqual(self.path.read_bytes(), raw)
                self.assertTrue(loaded.begin_journey(True), loaded.save_error)
                self.assertEqual(loaded.world.data['id'], world.data['id'])
                self.assertEqual(list(loaded.player.position), center)
                self.assertEqual(loaded.player.facing, 'left')
                self.assertTrue(loaded.world.can_stand(loaded.player.position))
                loaded.draw()

    def test_selected_fixture_conditions_refresh_cached_collision_and_real_rendering(self):
        game = self.game()
        self.stage(game, 'destroyed')
        world = game.overworld_world
        center = self.deck(world).center
        game.world = world
        landing = game.overworld_travel._landing(world, (-2240, 704))
        self.assertIsNotNone(landing)
        game.player.position.update(landing)
        game.camera.focus(center, duration=0)
        self.assertFalse(world.can_stand(center))
        game.draw()
        broken = pygame.image.tobytes(game.window, 'RGB')
        facts = self.facts(game.journey_snapshot())
        self.stage(game, 'intact')
        self.assertIs(game.overworld_world, world)
        self.assertTrue(world.can_stand(center))
        game.draw()
        intact = pygame.image.tobytes(game.window, 'RGB')
        self.assertNotEqual(intact, broken)
        self.stage(game, 'destroyed')
        self.assertIs(game.overworld_world, world)
        self.assertFalse(world.can_stand(center))
        game.draw()
        self.assertNotEqual(pygame.image.tobytes(game.window, 'RGB'), intact)
        self.assertEqual(self.facts(game.journey_snapshot()), facts)

    def test_inactive_crew_keeps_interrupted_cup_receipts_without_invisible_blockers(self):
        game = self.game()
        self.stage(game, 'destroyed')
        world = game.overworld_world
        crew = world.bridge_crew
        state = {'sorted': 3, 'tea_beat': 3, 'request_read': True,
                 'greeted': ['mason'], 'cup_phase': 'mason'}
        crew.restore(state)
        for phase in ('intact', 'restored'):
            with self.subTest(phase=phase):
                self.stage(game, phase);self.assertIs(game.overworld_world, world)
                game.world = world;game.player.position.update(crew.mason.position)
                before = (crew.to_dict(), crew.timer, tuple(actor.clock for actor in crew.actors))
                self.assertFalse(crew.active)
                self.assertEqual(crew.props(), [])
                self.assertEqual(crew.ground_blockers(), [])
                self.assertTrue(all(actor.blocker.width == 0 or actor.blocker.height == 0
                                    for actor in crew.actors))
                self.assertTrue(world.can_stand(game.player.position))
                self.assertEqual(crew.interaction_hint(game), '')
                self.assertFalse(crew.interact(game))
                crew.update(.5, game)
                self.assertEqual((crew.to_dict(), crew.timer,
                                  tuple(actor.clock for actor in crew.actors)), before)
                self.assertEqual(game.journey_snapshot()['overworld']['bridge_crew'], state)
        self.stage(game, 'destroyed');self.assertIs(game.overworld_world, world)
        self.assertTrue(crew.active)
        self.assertEqual(crew.to_dict(), state)
        self.assertEqual(crew.stage, 'exchange')
        self.assertEqual(crew.cup_owner, crew.mason)

    def test_invalid_component_rejects_loading_without_rewriting_payload_or_live_state(self):
        game, base = self.payload()
        before = deepcopy(base)
        invalid = (None, {'version': True, 'phase': 'intact', 'origin': 'explicit'},
                   {'version': 1, 'phase': 'repaired', 'origin': 'explicit'},
                   {'version': 1, 'phase': 'intact', 'origin': 'legacy_layout'},
                   {'version': 1, 'phase': 'intact', 'origin': 'unknown'})
        for value in invalid:
            with self.subTest(component=value):
                payload = deepcopy(base);payload['overworld']['bridge_condition'] = value
                unchanged = deepcopy(payload)
                raw = self.write_payload(payload)
                self.assertIsNone(game._validate_journey(payload))
                self.assertEqual(payload, unchanged)
                self.assertEqual(self.path.read_bytes(), raw)
                self.assertEqual(game.journey_snapshot()['overworld'], before['overworld'])
                self.assertIsNone(game._overworld_world)
        loaded = self.game(title=True)
        self.assertFalse(loaded.has_saved_journey)
        self.assertFalse(loaded.begin_journey(True))
        self.assertEqual(self.path.read_bytes(), raw)

    def test_phase_suppression_cancels_owned_dialogue_without_acknowledging_it(self):
        game = self.game()
        self.stage(game, 'destroyed')
        world = game.overworld_world;game.world = world
        crew = world.bridge_crew
        state = {'sorted': 3, 'tea_beat': 1, 'request_read': False,
                 'greeted': [], 'cup_phase': 'tender'}
        crew.restore(state)
        game.player.position.update(-2376, 642)
        self.assertEqual(crew.stage, 'request')
        self.assertTrue(crew.interact(game))
        self.assertTrue(game.social.active)
        self.assertEqual(game.social.script_identifier, SCENE_ID)
        self.stage(game, 'intact');self.assertIs(game.overworld_world, world)
        crew.update(.05, game)
        self.assertFalse(game.social.active)
        self.assertFalse(crew.dialogue_running)
        self.assertEqual(crew.to_dict(), state)
        self.assertTrue(game.social.start_script(
            [{'speaker': 'caelan', 'text': 'An unrelated conversation.'}],
            identifier='unrelated_bridge_condition_probe'))
        crew.update(.5, game)
        self.assertTrue(game.social.active)
        self.assertEqual(game.social.script_identifier, 'unrelated_bridge_condition_probe')
        self.assertEqual(crew.to_dict(), state)

    def test_phase_suppression_releases_bridge_audio_and_preserves_the_river_voice(self):
        game = self.game()
        self.stage(game, 'destroyed')
        world = game.overworld_world;game.world = world
        game.player.position.update(-2376, 642)
        game.audio.set_effects(1)
        audio = game.regional_audio
        self.assertTrue(audio.play(Source('bridge_tool', 'stone', 'masonry',
                                          tuple(game.player.position))))
        self.assertTrue(audio.play(Source('condition_test_river', 'river', 'water',
                                          tuple(game.player.position), ambient=True)))
        _, river_channel, river_sound, _ = audio.voices['condition_test_river']
        self.assertIs(river_channel.get_sound(), river_sound)
        self.stage(game, 'restored');self.assertIs(game.overworld_world, world)
        world.bridge_crew.update(.05, game)
        self.assertNotIn('bridge_tool', audio.voices)
        self.assertIn('condition_test_river', audio.voices)
        self.assertIs(river_channel.get_sound(), river_sound)

    def test_new_game_resets_condition_and_cached_world_after_restored_continue(self):
        _, payload = self.payload(completed_mill=True)
        payload['overworld']['bridge_condition'] = BridgeCondition('restored').to_dict()
        payload['dialogue_flags'].append(DEFAULT_REPAIR_FLAG)
        self.write_payload(payload)
        loaded = self.game(title=True)
        self.assertTrue(loaded.begin_journey(True), loaded.save_error)
        world = loaded.overworld_world
        self.assertTrue(world.can_stand(self.deck(world).center))
        self.assertTrue(loaded.begin_journey(False), loaded.save_error)
        expected = {'version': 1, 'phase': 'intact', 'origin': 'explicit'}
        self.assertEqual(loaded.overworld_travel.bridge_condition.to_dict(), expected)
        self.assertNotIn(DEFAULT_REPAIR_FLAG, loaded.social.flags)
        self.assertIs(loaded.overworld_world, world)
        self.assertEqual(world.bridge_condition.to_dict(), expected)
        self.assertTrue(world.can_stand(self.deck(world).center))
        self.assertEqual(loaded.world.data['id'], 'sanctuary_bedroom')

    def test_manual_and_scene_autosave_reconstruct_their_own_conditions(self):
        game = self.game()
        self.stage(game, 'intact')
        self.assertTrue(game.saves.manual(1), game.saves.notice)
        manual = deepcopy(game.saves.library.manual(1))
        self.assertEqual(manual['payload']['overworld']['bridge_condition'],
                         BridgeCondition('intact').to_dict())
        self.stage(game, 'destroyed')
        game.world = game._scene_by_id('sanctuary_dining')
        landing = game.overworld_travel._landing(game.world, game.world.data['spawn'])
        self.assertIsNotNone(landing)
        game.player.position.update(landing)
        game.saves.update(.1)
        autos = game.saves.library.autos(game.saves.campaign)
        self.assertEqual(len(autos), 1)
        self.assertEqual(autos[0]['metadata']['reason'], 'scene')
        self.assertEqual(autos[0]['payload']['overworld']['bridge_condition'],
                         BridgeCondition('destroyed').to_dict())
        self.assertEqual(game.saves.library.manual(1), manual)
        auto_row = next(row for row in game.saves.entries() if row[2][0] == 'auto')
        self.assertTrue(game.saves.load(('Slot 1', manual, ('manual', 1))))
        self.assertEqual(game.overworld_travel.bridge_condition.phase, 'intact')
        self.assertTrue(game.saves.load(auto_row))
        self.assertEqual(game.overworld_travel.bridge_condition.phase, 'destroyed')


if __name__ == '__main__':unittest.main()
