"""Actual MQ03 cave approach, one-time boss settlement and Continue ownership."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from leveling import total_xp_for_level
from main import Game
from post_battle import valid_pending_snapshot
from quests import LANTERN_QUEST, REGENT_QUEST
from sanctuary_cave import RESERVE_ENTRY_APPROACH
from test_mill_battle_gameplay import finish_spoils_presentation, wait_for_spoils
from tools.capture_mq03_emergency import Driver


class SanctuaryBossGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Earlier work is the Driver's explicit fixture. MQ03's emergency,
        # Mira's return and the Sanctuary journey use actual production input.
        with tempfile.TemporaryDirectory(prefix='boss-story-') as directory:
            driver = Driver(directory)
            driver.meal(); driver.attack_report(); driver.departure()
            driver.rejoin_mira(); driver.arrive()
            # Earlier cave discovery is an explicit fixture for these boss
            # ownership tests; its actual tutorial is exercised separately.
            owner = driver.game.character_abilities
            if not owner.has_weapon():assert owner.acquire_weapon('caelan', 'caelan_gearblade')
            assert owner.learn_ability('caelan', 'aqua_edge')
            assert driver.game.cave_lesson.restore({'version': 1, 'resonance_seen': True,
                                                   'battle_cleared': True, 'deferred': False})
            driver.walk(RESERVE_ENTRY_APPROACH)
            driver.game.handle_events([
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=False),
                pygame.event.Event(pygame.KEYUP, key=pygame.K_e)])
            driver.until(lambda: not driver.game.transfer_cooldown)
            assert driver.game.world.data['id'] == 'sanctuary_cave'
            assert driver.game.save_progress()
            cls.journey = json.loads(driver.save.read_text())
        pygame.quit()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='boss-gameplay-')
        self.addCleanup(temporary.cleanup)
        self.addCleanup(pygame.quit)
        self.directory = Path(temporary.name)
        self.path = self.directory/'journey.json'
        self.path.write_text(json.dumps(self.journey))
        self.game = self.load()
        # A labelled level-five fixture keeps the owner tests independent of
        # grinding random battles. No recruitment or story flags are invented.
        for identifier in self.game.party.active_ids:
            progression = self.game.character_progression
            amount = max(0, total_xp_for_level(5)-progression[identifier].total_xp)
            plan = progression.preview(amount, (identifier,),
                                       {identifier: self.game.party.characters[identifier].current_hp})
            self.assertTrue(progression.apply(plan))
            self.game.party.characters[identifier].recover()

    def load(self):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=True,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(0); game.audio.set_effects(0)
        self.assertTrue(game.has_saved_journey, game.save_error)
        self.assertTrue(game.begin_journey(True), game.save_error)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def key(self, key):
        self.assertTrue(self.game.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=key)]))

    def position(self, point=(1940, 492)):
        # Fixture placement selects a nearby valid approach; production input
        # performs the actual interaction and battle entry afterward.
        self.assertTrue(self.game.world.can_stand(point), point)
        self.game.player.position.update(point)
        self.game.player.facing = 'back'
        self.game.player.moving = self.game.player.running = False
        self.game.camera.reset()

    def choices(self):
        for _ in range(40):
            if self.game.social.choosing:
                self.game.draw()
                return
            self.assertTrue(self.game.social.active,
                            self.game.social.script_identifier)
            self.key(pygame.K_SPACE)
        self.fail('The boss dialogue did not reach its explicit choices')

    def choose(self, text):
        self.choices()
        options = self.game.social.choice_options
        index = next(index for index, option in enumerate(options)
                     if text.casefold() in option['text'].casefold())
        rect = self.game.social.choice_rects[index]
        _, size, origin = self.game._ensure_ui_surface()
        point = (round(origin[0]+rect.centerx*size[0]/480),
                 round(origin[1]+rect.centery*size[1]/320))
        self.assertTrue(self.game.handle_events([
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point),
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)]))

    def offer(self):
        self.position()
        if not self.game.social.active:self.key(pygame.K_e)
        self.choices()
        self.assertFalse(self.game.combat.active)

    def start(self):
        self.offer()
        self.choose('Enter')
        self.assertEqual(self.game.combat.kind, 'cave_boss')
        self.assertTrue(self.game.combat.active)
        return self.enter_battle()

    def enter_battle(self):
        for _ in range(240):
            if self.game.combat.model is not None and not self.game.combat.transitioning:
                return self.game.combat
            if self.game.social.active and not self.game.social.choosing:
                self.key(pygame.K_SPACE)
            self.game.draw()
            self.game.update(.05, (0, 0), False)
        self.fail('The real boss introduction/loading did not reveal combat')

    def context(self):
        game = self.game
        return deepcopy({
            'quests': game.quests.to_dict(), 'regent': game.regent_quest.to_dict(),
            'mill': game.mill_quest.to_dict(), 'lantern': game.lantern_quest.to_dict(),
            'flags': sorted(game.social.flags), 'party_event': game.party.event_id,
            'members': game.party.members, 'active': game.party.active_ids,
            'treasure': game.sanctuary_cave.to_dict(),
            'random_encounters': game.cave_random_encounters.to_dict(),
        })

    def resources(self):
        return {identifier: (member.current_hp, member.current_mp)
                for identifier, member in self.game.party.characters.items()}

    def story(self):
        game = self.game
        self.assertEqual(game.regent_quest.stage, 'sanctuary_arrival_pending')
        self.assertEqual(game.quests.status(REGENT_QUEST), 'active')
        self.assertEqual(game.quests.status(LANTERN_QUEST), 'locked')
        self.assertEqual(game.party.current_event_id, 'mq03_sanctuary')
        self.assertIn('mira', game.party.active_ids)
        self.assertNotIn('lucan', game.party.members)
        self.assertEqual(game.music.desired_track, 'battle')

    def victory(self, owner):
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        return owner.snapshot()

    def finish_spoils(self):
        owner = self.game.combat
        spoils = wait_for_spoils(self.game)
        self.assertTrue(spoils.ready, spoils.result_error)
        finish_spoils_presentation(self.game)
        self.game.draw()
        _, size, origin = self.game._ensure_ui_surface()
        point = (round(origin[0]+spoils.continue_rect.centerx*size[0]/480),
                 round(origin[1]+spoils.continue_rect.centery*size[1]/320))
        self.game.handle_events([
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point),
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)])
        self.game.update(0, (0, 0), False)
        self.assertFalse(owner.active)

    def test_previous_curve_awarded_boss_spoils_preserve_original_exp(self):
        from bestiary import build_enemy
        owner = self.start()
        before = {key: self.game.character_progression[key].total_xp for key in self.game.party.active_ids}
        def previous_enemy(*args, **kwargs):
            result = build_enemy(*args, **kwargs)
            result['xp_reward'] = 1110
            return result
        with patch('post_battle.build_enemy', side_effect=previous_enemy):
            self.victory(owner)
            wait_for_spoils(self.game)
        self.game = self.load()
        for key, total in before.items():
            self.assertEqual(self.game.character_progression[key].total_xp, total+1110)
        self.assertTrue(valid_pending_snapshot(self.game.combat.snapshot(), json.loads(self.path.read_text())))

    def test_approach_offers_party_or_retreat_without_healing_or_story_progress(self):
        before, resources = self.context(), self.resources()
        self.offer()
        self.choose('Party')
        self.assertTrue(self.game.party_ui.is_open)
        self.key(pygame.K_ESCAPE)
        if not self.game.social.active:self.offer()
        self.choose('Step back')
        self.assertFalse(self.game.combat.active)
        self.assertIsNone(self.game.sanctuary_boss.pending)
        self.assertFalse(self.game.sanctuary_boss.to_dict()['defeated'])
        self.assertEqual(self.resources(), resources)
        self.assertEqual(self.context(), before)
        self.story()

    def test_entry_checkpoint_and_continue_preserve_party_resources_and_opening_atb(self):
        self.game.attributes.set_current(hp=73, mp=3)
        self.game.party.characters['mira'].set_current(hp=91, mp=4)
        before, resources = self.context(), self.resources()
        self.offer(); self.choose('Enter')
        self.assertEqual(self.game.combat.kind, 'cave_boss')
        ticket = deepcopy(self.game.sanctuary_boss.pending)
        self.assertIsNotNone(ticket)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['sanctuary_boss']['pending'], ticket)
        owner = self.enter_battle()
        atb = dict(owner.model.initial_atb_values)
        self.assertTrue(atb and all(0 <= value <= .5 for value in atb.values()))
        self.assertEqual(owner.scene.battlefield, 'cave_echo_chamber')
        self.assertEqual(owner.model.enemy_bestiary_id, 'vespermaw')
        self.assertFalse(owner.model.choose_action('flee'))
        self.game = self.load()
        self.assertEqual(self.game.sanctuary_boss.pending, ticket)
        restored = self.enter_battle()
        self.assertEqual(restored.model.initial_atb_values, atb)
        self.assertEqual(self.resources(), resources)
        self.assertEqual(self.context(), before)
        self.story()

    def test_victory_continue_awards_survivor_exp_and_materials_exactly_once(self):
        before = self.context()
        xp = {key: self.game.character_progression[key].total_xp
              for key in self.game.party.active_ids}
        quantities = {key: self.game.inventory.quantity(key)
                      for key in ('aether_amethyst', 'aether_sapphire')}
        owner = self.start()
        owner.model.player.hp = 0; owner.model.player.mp = 2
        mira = owner.model.combatant('mira')
        mira.hp = 97; mira.mp = 3
        pending = self.victory(owner)
        self.assertEqual(pending['resources'], {'hp': 0, 'mp': 2})
        self.assertTrue(valid_pending_snapshot(pending, json.loads(self.path.read_text())))
        self.game = self.load()
        self.assertEqual(self.game.combat.post_phase, 'spoils')
        self.assertEqual(self.game.character_progression['caelan'].total_xp, xp['caelan'])
        self.assertEqual(self.game.character_progression['mira'].total_xp, xp['mira']+520)
        for key, quantity in quantities.items():
            self.assertEqual(self.game.inventory.quantity(key), quantity+1)
        self.assertEqual((self.game.attributes.current_hp, self.game.attributes.current_mp), (0, 2))
        self.assertTrue(self.game.sanctuary_boss.to_dict()['defeated'])
        self.assertTrue(self.game.battle_rewards.has_receipt('boss:vespermaw'))
        expected = (self.game.character_progression.to_dict(), self.game.inventory.to_dict(),
                    self.game.battle_rewards.to_dict())
        self.game = self.load()
        self.finish_spoils()
        self.assertIsNone(self.game.sanctuary_boss.pending)
        self.assertTrue(self.game.sanctuary_boss.to_dict()['defeated'])
        self.assertEqual(self.context(), before)
        self.game = self.load()
        self.position(); self.game.update(.05, (0, 0), False)
        self.assertFalse(self.game.combat.active)
        self.assertFalse(self.game.social.choosing)
        self.assertEqual((self.game.character_progression.to_dict(), self.game.inventory.to_dict(),
                          self.game.battle_rewards.to_dict()), expected)
        self.story()

    def test_defeat_retry_and_retreat_restore_entry_resources_without_rewards(self):
        self.game.attributes.set_current(hp=71, mp=3)
        self.game.party.characters['mira'].set_current(hp=95, mp=4)
        resources, context = self.resources(), self.context()
        inventory = self.game.inventory.to_dict()
        xp = self.game.character_progression.to_dict()
        owner = self.start()
        for member in owner.model.party:member.hp = member.mp = 0
        owner.model._result('defeat'); owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.assertEqual(self.resources(), resources)
        self.choose('Retry')
        owner = self.enter_battle()
        self.assertEqual(owner.model.player.hp, 71)
        self.assertEqual(owner.model.combatant('mira').hp, 95)
        for member in owner.model.party:member.hp = member.mp = 0
        owner.model._result('defeat'); owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.choose('Return')
        self.assertFalse(self.game.combat.active)
        self.assertIsNone(self.game.sanctuary_boss.pending)
        self.assertFalse(self.game.sanctuary_boss.to_dict()['defeated'])
        self.assertTrue(self.game.world.can_stand(self.game.player.position))
        self.assertEqual(self.resources(), resources)
        self.assertEqual(self.game.inventory.to_dict(), inventory)
        self.assertEqual(self.game.character_progression.to_dict(), xp)
        self.assertEqual(self.context(), context)
        self.story()

    def test_failed_reward_application_rolls_back_boss_flag_exp_items_and_retries(self):
        before = (self.game.character_progression.to_dict(), self.game.inventory.to_dict(),
                  self.game.party.to_dict())
        owner = self.start()
        self.victory(owner)
        with patch.object(owner, '_apply_resources', return_value=False):
            spoils = wait_for_spoils(self.game)
        self.assertTrue(spoils.result_error)
        self.assertFalse(self.game.sanctuary_boss.to_dict()['defeated'])
        self.assertFalse(self.game.battle_rewards.has_receipt('boss:vespermaw'))
        self.assertEqual((self.game.character_progression.to_dict(), self.game.inventory.to_dict(),
                          self.game.party.to_dict()), before)
        spoils.retry_requested = True
        self.game.update(0, (0, 0), False)
        self.assertTrue(spoils.ready, spoils.result_error)
        self.assertTrue(self.game.sanctuary_boss.to_dict()['defeated'])
        self.assertTrue(self.game.battle_rewards.has_receipt('boss:vespermaw'))
        self.finish_spoils()
        self.story()

    def test_failed_entry_checkpoint_waits_for_explicit_retry_before_loading(self):
        self.position()
        self.assertTrue(self.game.save_progress())
        original = json.loads(self.path.read_text())
        resources = self.resources()
        with patch.object(self.game.save_store, 'write', return_value=False):
            self.offer(); self.choose('Enter')
        owner = self.game.combat
        self.assertTrue(owner.active)
        self.assertTrue(owner.entry.error)
        for _ in range(5):
            self.game.draw(); self.game.update(.2, (1, 0), False)
        self.assertIsNone(owner.model)
        self.assertEqual(json.loads(self.path.read_text()), original)
        self.assertEqual(self.resources(), resources)
        self.key(pygame.K_RETURN)
        self.game.update(0, (0, 0), False)
        self.assertFalse(owner.entry.error)
        self.assertIsNotNone(json.loads(self.path.read_text())['sanctuary_boss']['pending'])
        self.enter_battle()
        self.assertEqual(self.resources(), resources)
        self.story()

    def test_failed_defeat_retreat_save_restores_checkpoint_position_and_camera(self):
        owner = self.start()
        resources = self.resources()
        for member in owner.model.party:member.hp = member.mp = 0
        owner.model._result('defeat'); owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.choices()
        ticket = deepcopy(self.game.sanctuary_boss.pending)
        position = tuple(self.game.player.position)
        camera = self.game.camera.position()
        saved = self.path.read_bytes()
        with patch.object(self.game.save_store, 'write', return_value=False):
            self.choose('Return')
        self.assertEqual(self.game.sanctuary_boss.pending, ticket)
        self.assertEqual(tuple(self.game.player.position), position)
        self.assertEqual(self.game.camera.position(), camera)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertEqual(self.resources(), resources)
        self.assertFalse(self.game.combat.active)
        self.choose('Return')
        self.assertIsNone(self.game.sanctuary_boss.pending)
        self.assertEqual(tuple(self.game.player.position), (1810, 600))
        self.assertEqual(self.resources(), resources)
        self.game = self.load()
        self.assertFalse(self.game.combat.active)
        self.assertFalse(self.game.sanctuary_boss.to_dict()['defeated'])
        self.assertEqual(self.resources(), resources)
        self.story()

    def test_failed_award_save_rolls_back_then_saves_the_reward_once(self):
        owner = self.start()
        self.victory(owner)
        before = (self.game.character_progression.to_dict(), self.game.inventory.to_dict(),
                  self.game.battle_rewards.to_dict(), self.game.party.to_dict())
        with patch.object(self.game.save_store, 'write', return_value=False):
            spoils = wait_for_spoils(self.game)
        self.assertTrue(spoils.result_error)
        self.assertEqual(owner.snapshot()['stage'], 'pending')
        self.assertFalse(self.game.sanctuary_boss.to_dict()['defeated'])
        self.assertEqual((self.game.character_progression.to_dict(), self.game.inventory.to_dict(),
                          self.game.battle_rewards.to_dict(), self.game.party.to_dict()), before)
        with patch.object(self.game.character_progression, 'apply',
                          wraps=self.game.character_progression.apply) as apply_progress:
            spoils.retry_requested = True
            self.game.update(0, (0, 0), False)
        self.assertEqual(apply_progress.call_count, 1)
        self.assertTrue(spoils.ready, spoils.result_error)
        self.assertTrue(self.game.sanctuary_boss.to_dict()['defeated'])
        expected = (self.game.character_progression.to_dict(), self.game.inventory.to_dict(),
                    self.game.battle_rewards.to_dict(), self.game.party.to_dict())
        self.game = self.load()
        self.finish_spoils()
        self.assertEqual((self.game.character_progression.to_dict(), self.game.inventory.to_dict(),
                          self.game.battle_rewards.to_dict(), self.game.party.to_dict()), expected)
        self.story()

    def test_legacy_save_inside_arena_offers_safe_entry_without_inventing_completion(self):
        self.position((2000, 420))
        before = self.context()
        self.assertTrue(self.game.save_progress())
        saved = json.loads(self.path.read_text())
        saved.pop('sanctuary_boss')
        self.path.write_text(json.dumps(saved))
        self.game = self.load()
        self.game.update(.05, (0, 0), False)
        self.choices()
        self.assertFalse(self.game.combat.active)
        self.assertFalse(self.game.sanctuary_boss.to_dict()['defeated'])
        self.choose('Step back')
        self.assertTrue(self.game.world.can_stand(self.game.player.position))
        self.assertEqual(self.context(), before)
        self.story()

    def test_crossing_the_chamber_boundary_uses_the_real_player_movement_trigger(self):
        self.position()
        start = self.game.player.position.copy()
        for _ in range(6):
            self.game.update(.04, (0, -1), False)
            if self.game.social.active:break
        self.assertLess(self.game.player.position.y, start.y)
        self.choices()
        self.assertFalse(self.game.combat.active)
        self.assertIsNone(self.game.cave_random_encounters.pending)
        self.choose('Step back')
        self.story()
