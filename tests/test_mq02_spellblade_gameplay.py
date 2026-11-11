"""MQ02's Blue-only gift, failed Aqua and accidental durable Aether discovery."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame
from main import Game
from quests import MILL_QUEST
import test_opening_dialogue_pass as opening
from test_mill_battle_gameplay import (
    acknowledge_battle_result, click, key, read_social, seed_mill_handoff,
    wait_for_spoils,
)


WEAPON = 'caelan_gearblade'
ATTEMPTS = ('aqua_edge',)


def drive_spellblade_battle(game, command='attack', *, dismiss=True,
                            read_aftermath=False, on_step=None, on_frame=None,
                            first='aqua_edge', second=None,
                            stop_after_discovery=False):
    """Operate production menus; model fields are observed, never advanced here."""
    # Legacy review callers may still provide first/second; Blue is now the
    # only installed focus and one Aqua selection releases accidental Aether.
    scene, model = game.combat.scene, game.combat.model
    assert game.combat.kind == 'mill'
    assert model.spellblade_stage is not None
    model.rng = random.Random(7)
    seen_actions, seen_guidance, trace = [], set(), []
    normal_edge_used = False
    emitted = set()

    def frame(tag, action=None):
        if on_frame:on_frame(game, tag, action)

    def choose(action):
        game.draw()
        if action in (*ATTEMPTS, 'aether_edge'):
            if scene.command_menu != 'skills':
                assert not model.command_reason('skills')
                click(game, scene.command_rects['skills'].center)
                game.draw()
            frame('skills_'+str(model.spellblade_stage))
        assert action in scene.command_rects, (action, scene.command_rects)
        assert not model.action_reason(action), model.action_reason(action)
        click(game, scene.command_rects[action].center)

    for _ in range(16000):
        if on_step:on_step(scene)
        action = model.current_action or model.last_action
        if (action is not None and action.resolved
                and not any(action is previous for previous in seen_actions)):
            seen_actions.append(action);trace.append(asdict(action))
            if action.actor == 'player':
                frame('resolved_'+action.action, action)
        if stop_after_discovery and model.aether_edge_discovered:
            scene.review_trace = trace
            return scene
        if game.combat.transitioning:
            game.update(.05, (0, 0), False)
        elif scene.tutorial_active:
            text = scene.tutorial_text
            if text not in seen_guidance:
                seen_guidance.add(text);frame('guidance', text)
                before = tuple(actor.atb for actor in (*model.party, model.enemy))
                game.update(.5, (0, 0), False)
                assert before == tuple(actor.atb for actor in (*model.party, model.enemy))
            key(game, pygame.K_SPACE)
        elif model.ended:
            frame('victory' if model.phase == 'victory' else model.phase)
            if dismiss:
                if model.phase == 'victory':
                    wait_for_spoils(game);frame('spoils')
                acknowledge_battle_result(game, scene)
                if read_aftermath:read_social(game)
            scene.review_trace = trace
            return scene
        elif model.waiting_for_player:
            if 'ready' not in emitted:
                emitted.add('ready');frame('ready')
            stage = model.spellblade_stage
            if stage in ('opening', 'guard', 'charge'):
                choose('guard')
            elif stage == 'first_edge':choose('aqua_edge')
            else:
                if 'normal' not in emitted:
                    emitted.add('normal');frame('normal_controls')
                if command != 'attack':choose(command)
                elif model.telegraphed_target == model.ready_actor:choose('guard')
                elif (model.ready_actor == 'player' and not normal_edge_used
                      and 'aether_edge' in model.skill_actions()
                      and not model.action_reason('aether_edge')):
                    choose('aether_edge');normal_edge_used = True
                else:choose('attack')
        else:game.update(.05, (0, 0), False)
    raise AssertionError(('Spellblade lesson stalled', model.phase, model.spellblade_stage))


class MQ02SpellbladeGameplayTests(unittest.TestCase):
    def driver(self, *, method='magicks', seeded=True):
        driver = opening.OpeningDialogueDriver(method=method)
        self.addCleanup(driver.close)
        if seeded:
            driver.start_new_game()
            seed_mill_handoff(driver.g)
            driver.travel(driver.g.town.data['id'])
        return driver

    def begin_gift(self, driver):
        game, quest = driver.g, driver.g.mill_quest
        driver.travel(game.town.data['id'])
        for offset in ((0, 28), (28, 0), (-28, 0), (0, -28)):
            spot = quest.mira.position+offset
            if game.town.can_stand(spot):
                driver.walk(spot, read=False);break
        game.social.blocked.clear()
        if not game.social.locked:self.assertTrue(game.social.start(quest.mira))
        for _ in range(1000):
            if game.mill_gift.active:return
            if game.social.active:
                driver.record_page();key(game, pygame.K_SPACE)
            else:
                # Mira may first finish her workbench pose before accepting
                # the pending proximity conversation.
                driver.tick(.05)
        self.fail('The reunion did not begin Mira’s gift')

    def start_battle(self, driver):
        game, quest = driver.g, driver.g.mill_quest
        if game.quests.status(MILL_QUEST) == 'available':
            driver.actor(quest.mira, 'mill_reunion')
        self.assertTrue(quest.active)
        driver.mill_at('mechanism');driver.mill_event('mechanism')
        driver.mill_at('race');driver.mill_event('race')
        driver.mill_link(True)
        for _ in range(1000):
            if game.combat.active:return game.combat.scene
            if game.social.active or quest.encounter_cutscene_active:driver.read()
            game.update(.05, (0, 0), False)
        self.fail('The real departure did not reach the tutorial battle')

    def reload(self, driver):
        old = driver.g
        self.assertTrue(old.save_progress())
        other = Game(fullscreen=False, start_on_title=True, save_path=driver.path,
                     settings_path=driver.path.with_name('settings.json'))
        other.audio.set_music(0);other.audio.set_effects(0);pygame.event.clear()
        self.assertTrue(other.has_saved_journey)
        self.assertTrue(other.begin_journey(True))
        other.opening_fade = other.transfer_cooldown = 0
        driver.g = other
        return other

    def test_gift_commits_one_equipped_weapon_but_defers_aether_edge_across_reload(self):
        driver = self.driver();game = driver.g
        self.begin_gift(driver)
        self.assertEqual(game.quests.status(MILL_QUEST), 'available')
        self.assertEqual(game.inventory.quantity(WEAPON), 0)
        game = self.reload(driver)
        self.assertFalse(game.mill_gift.active)
        self.assertEqual(game.quests.status(MILL_QUEST), 'available')
        self.assertEqual(game.inventory.quantity(WEAPON), 0)
        self.begin_gift(driver);driver.read()
        self.assertTrue(game.mill_quest.active)
        self.assertEqual(game.inventory.quantity(WEAPON), 1)
        self.assertTrue(game.character_abilities.has_weapon())
        self.assertEqual(game.character_abilities.owned_gems(), ('water',))
        self.assertFalse(game.character_abilities.set_active_gem('caelan', 'fire'))
        self.assertTrue(game.character_abilities.starter_skills_pending())
        self.assertNotIn('aether_edge', game.character_abilities.known_abilities())
        game = self.reload(driver)
        self.assertEqual(game.inventory.quantity(WEAPON), 1)
        self.assertTrue(game.character_abilities.starter_skills_pending())
        self.assertNotIn('aether_edge', game.character_abilities.known_abilities())
        game.social.blocked.clear()
        self.assertTrue(game.social.start(game.mill_quest.mira));driver.read()
        self.assertFalse(game.mill_gift.active)
        self.assertEqual(game.inventory.quantity(WEAPON), 1)

    def test_guard_then_failed_aqua_automatically_discovers_and_checkpoints_aether_edge(self):
        driver = self.driver();game = driver.g
        self.start_battle(driver)
        entry_mp = game.combat.model.player.mp
        scene = drive_spellblade_battle(game, stop_after_discovery=True,
                                        first='aqua_edge')
        actions = [action for action in scene.review_trace if action['actor'] == 'player']
        self.assertEqual([action['action'] for action in actions[:3]],
                         ['guard', 'aqua_edge_attempt', 'aether_edge'])
        self.assertEqual(actions[1]['damage'], 0)
        self.assertGreater(actions[2]['damage'], 0)
        self.assertTrue(scene.model.aether_edge_discovered)
        self.assertEqual(scene.model.player.aether_edge_hits, 0)
        self.assertIn('aether_edge', game.character_abilities.known_abilities())
        self.assertFalse(game.character_abilities.starter_skills_pending())
        self.assertTrue(set(ATTEMPTS).isdisjoint(game.character_abilities.known_abilities()))
        saved = json.loads(driver.path.read_text())
        self.assertEqual(saved['character_attributes']['current_mp'], entry_mp-4)
        self.assertFalse(saved['mill_quest']['encounter_cleared'])
        before = game.battle_rewards.to_dict(), game.inventory.to_dict()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        game = self.reload(driver)
        self.assertFalse(game.combat.active)
        self.assertEqual(game.attributes.current_mp, entry_mp-4)
        self.assertIn('aether_edge', game.character_abilities.known_abilities())
        self.assertEqual(before, (game.battle_rewards.to_dict(), game.inventory.to_dict()))
        self.assertFalse(game.mill_quest.encounter_cleared)
        self.assertEqual(game.inventory.quantity(WEAPON), 1)

    def test_discovery_survives_flee_and_retry_without_repeating_the_gift_or_lesson(self):
        driver = self.driver();game = driver.g
        self.start_battle(driver)
        drive_spellblade_battle(game, stop_after_discovery=True)
        before = game.battle_rewards.to_dict(), game.inventory.to_dict()
        scene = drive_spellblade_battle(game, command='flee', read_aftermath=True)
        self.assertEqual(scene.model.phase, 'fled')
        self.assertFalse(game.mill_quest.encounter_cleared)
        self.assertEqual(before, (game.battle_rewards.to_dict(), game.inventory.to_dict()))
        game = self.reload(driver)
        quest = game.mill_quest
        self.assertTrue(quest.begin_encounter(game.combat.start_mill))
        for _ in range(1000):
            if game.combat.active:break
            if game.social.active or quest.encounter_cutscene_active:driver.read()
            game.update(.05, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertFalse(game.combat.model.spellblade_guided)
        self.assertIn('aether_edge', game.combat.model.skill_actions('player'))
        self.assertTrue(set(ATTEMPTS).isdisjoint(game.combat.model.skill_actions('player')))
        self.assertEqual(game.inventory.quantity(WEAPON), 1)

    def test_depleted_first_tutorial_prepares_viable_resources_before_the_guard_lesson(self):
        driver = self.driver();game = driver.g
        driver.actor(game.mill_quest.mira, 'mill_reunion')
        self.assertTrue(game.equip_weapon('caelan', None))
        self.assertFalse(game.character_abilities.has_weapon())
        self.assertTrue(game.attributes.set_current(hp=30, mp=0))
        self.start_battle(driver)
        self.assertTrue(game.character_abilities.has_weapon())
        self.assertTrue(game.combat.model.weapon_equipped)
        self.assertGreaterEqual(game.combat.model.player.hp, 80)
        self.assertGreaterEqual(game.combat.model.player.mp, 4)
        self.assertIn('mill_tutorial_preparation', driver.sources)
        self.assertTrue(game.character_abilities.starter_skills_pending())

    def test_unseeded_opening_both_venn_histories_finish_spellblade_repair_and_aldric_handoff(self):
        for method in ('magicks', 'tools'):
            with self.subTest(method=method):
                driver = self.driver(method=method, seeded=False)
                game = driver.g
                water = []
                tick = driver.tick

                def observe(seconds=.05, direction=(0, 0)):
                    tick(seconds, direction)
                    if game.mill_quest.action == 'spell':
                        water.append(game.mill_quest.spell_focus)

                driver.tick = observe
                battles = []

                def battle(*args, **kwargs):
                    scene = drive_spellblade_battle(*args, **kwargs)
                    battles.append(scene)
                    return scene

                with patch.object(opening, 'finish_mill_battle', battle):driver.run()
                self.assertEqual(len(battles), 1)
                scene = battles[0]
                self.assertEqual(scene.model.phase, 'victory')
                self.assertTrue(scene.model.aether_edge_discovered)
                self.assertIn('water', water)
                self.assertEqual(set(water), {'water'})
                self.assertTrue(game.mill_quest.spell_done)
                self.assertTrue(game.mill_quest.restored)
                self.assertTrue(game.mill_quest.reported_to_halden)
                self.assertTrue(game.mill_quest.cups_placed)
                self.assertEqual(game.world.data['id'], 'sanctuary_dining')
                self.assertIn('mill_sanctuary_return', driver.sources)
                self.assertIn('mill_sanctuary_setting', driver.sources)
                self.assertEqual(game.quests.status(MILL_QUEST), 'completed')
                self.assertEqual(game.quests.status('CH01_MQ03'), 'available')
                self.assertIn(game.regent_arrival.state, ('pending', 'seen'))
                self.assertEqual(game.inventory.quantity(WEAPON), 1)
                self.assertIn('aether_edge', game.character_abilities.known_abilities())
                self.assertTrue(set(ATTEMPTS).isdisjoint(game.character_abilities.known_abilities()))
                expected = 'mill_encouragement_failed' if method == 'magicks' else 'mill_encouragement'
                self.assertIn(expected, driver.sources)
                self.assertEqual(game.venn_visit.magicks_failed, method == 'magicks')
                committed = game.battle_rewards.to_dict(), game.inventory.to_dict()
                game.combat.update(0);game.combat.update(0)
                self.assertEqual(committed, (game.battle_rewards.to_dict(), game.inventory.to_dict()))
                self.assertIsNotNone(game._read_saved_journey())


if __name__ == '__main__':unittest.main()
