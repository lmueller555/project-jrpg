"""Real MQ02 battle input, durable quest outcomes and safe return paths."""
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from main import Game
from npc_routines import find_path
from quests import MILL_QUEST, OPENING_QUEST


def key(game, value):
    for kind in (pygame.KEYDOWN, pygame.KEYUP):
        pygame.event.post(pygame.event.Event(kind, key=value, repeat=False))
    assert game.handle_events()


def click(game, logical):
    width, height = game.window.get_size()
    scale = max(1, min(width//480, height//320))
    point = (round((width-480*scale)//2+logical[0]*scale),
             round((height-320*scale)//2+logical[1]*scale))
    for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
    assert game.handle_events()


def read_social(game):
    for _ in range(1000):
        if not game.social.active:return
        assert not game.social.choosing, 'MQ02 has a linear aftermath, not a continue/rest choice'
        key(game, pygame.K_SPACE)
    raise AssertionError('MQ02 dialogue did not finish')


def seed_mill_handoff(game):
    """Public APIs seed prior work; MQ02 itself remains unfinished."""
    assert game.accept_quest(OPENING_QUEST)
    for identifier in ('halden', 'elira', 'venn'):
        assert game.quests.complete_objective(OPENING_QUEST, identifier)
    game._sync_inventory()
    game.halden_visit.restore();game.elira_visit.restore();game.venn_visit.restore()
    assert game.quests.turn_in(OPENING_QUEST, 'mother_serene')
    assert game.quests.unlock(MILL_QUEST)
    game.opening_conclusion.restore({'version': 1, 'stage': 'done'})
    game.opening.restore({'version': 1, 'stage': 'disabled'})
    game.opening_fade = game.transfer_cooldown = 0
    game.social.blocked.clear();game.quests.drain_events();game.quest_ui.reset()


def seed_completed_mill(game):
    """A legitimate old completed journey unlocks the repeatable test Bat."""
    seed_mill_handoff(game)
    assert game.accept_quest(MILL_QUEST)
    for objective in game.quests.definitions[MILL_QUEST]['objectives']:
        assert game.quests.complete_objective(MILL_QUEST, objective['id'])
    assert game.quests.turn_in(MILL_QUEST, 'mira_worker')
    assert game.mill_quest.restore({'version': 1,
                                  'inspected': ['mechanism', 'race', 'intake'],
                                  'prepared': True, 'spell_done': True,
                                  'encouraged': True, 'restored': True,
                                  'verified': True, 'resolved': True})
    # Continuing a completed MQ02 automatically exposes the next story quest.
    # Seed that same public handoff so loading does not add unrelated progress.
    if game.quests.status('CH01_MQ03') == 'locked':
        assert game.quests.unlock('CH01_MQ03')
    game.regent_quest.restore(None)
    game.quests.drain_events();game.social.blocked.clear()
    assert game.save_progress()


def wait_for_spoils(game, limit=200):
    """Let the production banner and transition reach the reward screen."""
    for _ in range(limit):
        spoils = getattr(game.combat, 'spoils', None)
        if (spoils is not None and game.combat.post_phase == 'spoils'
                and (spoils.awarded or spoils.result_error)):
            return spoils
        game.update(.05, (0, 0), False)
    raise AssertionError('Victory did not reach Spoils of Battle')


def acknowledge_battle_result(game, scene):
    """Use the appropriate real result screen, including an explicit retry."""
    if scene.model.phase == 'victory':
        spoils = wait_for_spoils(game)
        if spoils.result_error:
            game.draw();click(game, spoils.retry_rect.center)
            game.update(0, (0, 0), False)
            assert spoils.awarded and not spoils.result_error
        game.draw();click(game, spoils.continue_rect.center)
    else:
        game.draw();click(game, scene.continue_rect.center)
    game.update(0, (0, 0), False)
    assert not game.combat.active


def finish_mill_battle(game, command='attack', *, dismiss=True, read_aftermath=True,
                       on_step=None):
    """Use actual tutorial acknowledgement and mouse command/result input."""
    assert game.combat.active
    scene = game.combat.scene
    for _ in range(4000):
        if on_step:on_step(scene)
        if getattr(game.combat, 'transitioning', False):
            game.update(.1, (0, 0), False)
            continue
        if getattr(scene, 'tutorial_active', False):
            key(game, pygame.K_SPACE)
        elif scene.model.ended:
            if dismiss:
                acknowledge_battle_result(game, scene)
                if read_aftermath:read_social(game)
            return scene
        elif scene.model.waiting_for_player:
            action = command
            if (command == 'attack' and scene.model.telegraphed_target
                    == scene.model.ready_actor):
                action = 'guard'
            game.draw()
            assert action in scene.command_rects
            click(game, scene.command_rects[action].center)
        else:
            game.update(.1, (0, 0), False)
    raise AssertionError('The mill battle did not finish')


class MillBattleGameplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='mill-battle-gameplay-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory/'journey.json'
        self.game = self.new_game()

    def tearDown(self):pygame.quit()

    def new_game(self, title=False):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0);pygame.event.clear()
        return game

    def place(self, point, world=None):
        game = self.game
        world = world or game.world
        game.world = world
        for radius in (0, 8, 16, 24):
            for offset in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
                position = pygame.Vector2(point)+offset
                if world.can_stand(position):
                    game.player.position.update(position)
                    for companion_offset in ((-24, 0), (24, 0), (0, 24), (0, -24)):
                        companion = position+companion_offset
                        if world.can_stand(companion):
                            game.mill_quest._place_mira(world, companion)
                            break
                    game.camera.reset();game.transfer_cooldown = 0
                    return
        self.fail(('No clear fixture position', world.data['id'], point))

    def diagnose(self, finish_warning=True):
        game = self.game;c = game.mill_quest
        seed_mill_handoff(game)
        self.place(c.mira.position+(0, 28), game.town)
        key(game, pygame.K_e)
        self.assertEqual(game.social.script_identifier, 'mill_reunion')
        read_social(game)
        for name in ('mechanism', 'race'):
            self.place(c.points[name])
            key(game, pygame.K_e)
            self.assertEqual(game.social.script_identifier, 'mill_'+name)
            if name == 'mechanism':read_social(game)
        if finish_warning:
            read_social(game)
            self.assertTrue(c.warned)
        else:
            for _ in range(1000):
                if game.social.script_identifier == 'mill_warning':return
                key(game, pygame.K_SPACE)
            self.fail('Diagnosis did not lead to the departure warning')

    def enter_path(self):
        game = self.game;c = game.mill_quest
        self.place((720, 12), game.town)
        key(game, pygame.K_e)
        self.assertEqual(game.world.data['id'], 'upstream')
        self.assertFalse(game.combat.active)
        self.assertIsNone(game.nearby_world_link())
        game.update(.35, (0, 0), False)
        return c

    def start(self, approach=None):
        self.diagnose();c = self.enter_path();game = self.game
        # Approach along the visible western bank rather than using the
        # controller's own trigger centre as evidence of good placement.
        target = approach if approach is not None else (180, 374)
        route = find_path(game.world, game.player.position, target, game.world.probe_size, None)
        self.assertIsNotNone(route)
        for corner in route:
            for _ in range(1000):
                if game.combat.active:break
                if game.social.active:read_social(game)
                if game.combat.active:break
                delta = pygame.Vector2(corner)-game.player.position
                if delta.length()<.04:break
                game.update(min(.05, delta.length()/72), delta, False)
            if game.combat.active:break
        for _ in range(500):
            if game.combat.active:break
            if game.social.active:read_social(game)
            game.update(.05, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.model.enemy_id, 'ridgeback_tusker')
        game.combat.model.rng = random.Random(7)
        return game.combat.scene

    def snapshot(self):
        game = self.game
        return (game.attributes.to_dict(), game.lattice.to_dict(), game.inventory.to_dict(),
                game.quests.to_dict(), game.mill_quest.to_dict())

    def test_fresh_journey_can_fight_the_test_bat_before_miras_introduction(self):
        game = self.game
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        self.assertFalse(game.mill_quest.combat_unlocked)
        game.update(.05, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.model.enemy_id, 'bat')
        self.assertFalse(game.mill_quest.combat_unlocked)

    def test_unread_warning_blocks_departure_and_encounter_precedes_intake(self):
        self.diagnose(False);game = self.game;c = game.mill_quest
        self.assertFalse(c.warned)
        game.social.cancel()
        self.place((720, 12), game.town)
        link = next(link for link in game.town.data['world_links']
                    if link['id'] == 'town_to_upstream')
        self.assertFalse(game.travel_link(link))
        self.assertIs(game.world, game.town)
        self.assertFalse(c.combat_unlocked)

    def test_first_story_fight_has_two_real_characters_and_freezes_world_and_all_gauges(self):
        scene = self.start();game = self.game;c = game.mill_quest
        self.assertEqual([member.name for member in scene.model.party], ['Caelan', 'Mira'])
        self.assertEqual(sum(c.mira in world.npcs for world in game.scenes.values()), 1)
        while getattr(scene, 'tutorial_active', False):key(game, pygame.K_SPACE)
        for _ in range(200):
            if scene.model.waiting_for_player:break
            game.update(.1, (0, 0), False)
            while getattr(scene, 'tutorial_active', False):key(game, pygame.K_SPACE)
        self.assertTrue(scene.model.waiting_for_player)
        before = [member.atb for member in (*scene.model.party, scene.model.enemy)]
        world = game.elapsed_ms, game.player.position.copy(), c.mira.position.copy()
        game.update(60, (1, 0), True)
        self.assertEqual(before, [member.atb for member in (*scene.model.party, scene.model.enemy)])
        self.assertEqual(world, (game.elapsed_ms, game.player.position, c.mira.position))
        self.assertNotIn('intake', c.inspected)
        self.assertFalse(c.mill_restored)

    def test_direct_eastern_approach_to_intake_still_encounters_the_monster(self):
        # The open bank permits a real route east along y500 before turning
        # north. It must not strand the player at a gated intake simply because
        # the first authored trigger covered only the western trail.
        self.start(approach=(480, 240))
        self.assertNotIn('intake', self.game.mill_quest.inspected)
        self.assertFalse(self.game.mill_quest.encounter_cleared)

    def test_victory_settles_once_then_linear_aftermath_unlocks_intake(self):
        scene = self.start();game = self.game;c = game.mill_quest
        before_rp = game.lattice.state()['rp']
        finish_mill_battle(game, dismiss=False)
        self.assertEqual(scene.model.phase, 'victory')
        self.assertFalse(c.encounter_cleared)
        expected = scene.model.enemy_definition['rewards']
        acknowledge_battle_result(game, scene)
        self.assertTrue(c.encounter_cleared)
        self.assertFalse(c.aftermath_done)
        self.assertFalse(game.social.choosing)
        self.assertEqual(game.lattice.state()['rp'], before_rp+expected['rp'])
        self.assertFalse(c.mill_restored)
        saved = json.loads(self.path.read_text())
        self.assertTrue(saved['mill_quest']['encounter_cleared'])
        committed = game.lattice.to_dict(), game.inventory.to_dict()
        game.combat.update(0);game.combat.update(0)
        self.assertEqual(committed, (game.lattice.to_dict(), game.inventory.to_dict()))
        read_social(game)
        self.assertTrue(c.aftermath_done)
        self.assertEqual(c.stage, 'reach_intake')
        game.save_progress();other = self.new_game(True)
        self.assertTrue(other.begin_journey(True))
        self.assertTrue(other.mill_quest.encounter_cleared)
        self.assertTrue(other.mill_quest.aftermath_done)
        self.assertFalse(other.mill_quest.encounter_pending)
        self.assertEqual(committed, (other.lattice.to_dict(), other.inventory.to_dict()))

    def test_reward_rejection_keeps_victory_and_quest_progress_atomic_for_retry(self):
        scene = self.start();game = self.game
        finish_mill_battle(game, dismiss=False)
        before = self.snapshot()
        with patch.object(game.lattice_progression, 'award_battle_rewards', return_value=False):
            spoils = wait_for_spoils(game)
        self.assertTrue(game.combat.active)
        self.assertTrue(spoils.result_error)
        self.assertEqual(self.snapshot(), before)
        finish_mill_battle(game)
        self.assertTrue(game.mill_quest.encounter_cleared)

    def test_unread_aftermath_survives_reload_without_repeating_the_battle_or_reward(self):
        scene = self.start();game = self.game
        finish_mill_battle(game, dismiss=False)
        acknowledge_battle_result(game, scene)
        self.assertTrue(game.mill_quest.encounter_cleared)
        self.assertFalse(game.mill_quest.aftermath_done)
        committed = game.lattice.to_dict(), game.inventory.to_dict()
        other = self.new_game(True)
        self.assertTrue(other.begin_journey(True))
        self.assertFalse(other.combat.active)
        self.assertTrue(other.mill_quest.encounter_cleared)
        self.assertFalse(other.mill_quest.aftermath_done)
        other.update(.6, (0, 0), False)
        self.assertFalse(other.combat.active)
        self.assertEqual(other.social.script_identifier, 'mill_aftermath')
        read_social(other)
        self.assertTrue(other.mill_quest.aftermath_done)
        self.assertEqual(other.mill_quest.stage, 'reach_intake')
        self.assertEqual(committed, (other.lattice.to_dict(), other.inventory.to_dict()))

    def test_mira_can_finish_after_caelans_incapacitation_and_first_aid_allows_return(self):
        scene = self.start();game = self.game
        scene.model.player.hp = 0
        finish_mill_battle(game)
        self.assertEqual(scene.model.phase, 'victory')
        self.assertEqual(scene.model.player.hp, 0)
        self.assertGreater(scene.model.combatant('mira').hp, 0)
        self.assertGreater(game.attributes.current_hp, 0)
        self.assertTrue(game.mill_quest.encounter_cleared)
        self.assertTrue(game.mill_quest.aftermath_done)
        self.assertTrue(game.world.can_stand(game.player.position))

    def test_flee_returns_to_safe_unfinished_approach_without_rewards(self):
        self.start();game = self.game;c = game.mill_quest
        before = game.lattice.to_dict(), game.inventory.to_dict()
        scene = finish_mill_battle(game, command='flee')
        self.assertEqual(scene.model.phase, 'fled')
        self.assertFalse(c.encounter_cleared)
        self.assertFalse(c.aftermath_done)
        self.assertEqual(c.stage, 'encounter')
        self.assertEqual(before, (game.lattice.to_dict(), game.inventory.to_dict()))
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertFalse(c.encounter_ready)
        self.assertGreater(game.attributes.current_hp, 0)

    def test_party_defeat_offers_viable_retry_without_losing_previous_quest_work(self):
        scene = self.start();game = self.game;c = game.mill_quest
        before = game.lattice.to_dict(), game.inventory.to_dict()
        for member in scene.model.party:member.hp = 1
        finish_mill_battle(game, command='guard')
        self.assertEqual(scene.model.phase, 'defeat')
        self.assertFalse(c.encounter_cleared)
        self.assertTrue(c.warned)
        self.assertEqual(c.inspected, {'mechanism', 'race'})
        self.assertEqual(before, (game.lattice.to_dict(), game.inventory.to_dict()))
        self.assertGreater(game.attributes.current_hp, 0)
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertFalse(c.encounter_ready)

    def test_quit_during_fight_loads_safe_unfinished_checkpoint_without_partial_battle(self):
        self.start();game = self.game
        before = game.lattice.to_dict(), game.inventory.to_dict()
        attributes = game.attributes.to_dict()
        safe_spawn = list(game.mill_quest.upstream.data['spawn'])
        key_scene = game.combat.scene
        while getattr(key_scene, 'tutorial_active', False):key(game, pygame.K_SPACE)
        game.update(1, (0, 0), False)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['player']['position'], safe_spawn)
        self.assertEqual(saved['character_attributes'], attributes)
        other = self.new_game(True)
        self.assertTrue(other.begin_journey(True))
        self.assertFalse(other.combat.active)
        self.assertTrue(other.mill_quest.encounter_pending)
        self.assertEqual(list(other.player.position), safe_spawn)
        other.opening_fade = other.transfer_cooldown = 0
        other.update(0, (0, 0), False)
        self.assertFalse(other.mill_quest.encounter_ready)
        self.assertEqual(before, (other.lattice.to_dict(), other.inventory.to_dict()))

    def test_legacy_completed_mill_preserves_repairs_without_inventing_victory_or_rewards(self):
        game = self.game
        seed_completed_mill(game)
        data = json.loads(self.path.read_text())
        old = data['mill_quest']
        data['mill_quest'] = {name: value for name, value in old.items()
                              if name not in ('warned', 'encounter_cleared', 'aftermath_done', 'legacy_bypass')}
        data['mill_quest']['version'] = 1
        done = data['quests']['quests'][MILL_QUEST]['completed_objectives']
        done[:] = [name for name in done if name not in ('prepare_journey', 'secure_trail')]
        self.path.write_text(json.dumps(data))
        other = self.new_game(True)
        self.assertTrue(other.begin_journey(True))
        self.assertTrue(other.mill_quest.mill_restored)
        self.assertTrue(other.mill_quest.legacy_bypass)
        self.assertFalse(other.mill_quest.encounter_cleared)
        self.assertFalse(other.mill_quest.aftermath_done)
        self.assertEqual(other.lattice.state()['rp'], 0)
        self.assertEqual(other.inventory.quantity('aether_emerald'), 0)
        other.world = other.town
        other.player.position.update(other.combat.position+(0, 24))
        other.transfer_cooldown = other.opening_fade = 0
        self.assertTrue(other.combat.interact())


if __name__ == '__main__':unittest.main()
