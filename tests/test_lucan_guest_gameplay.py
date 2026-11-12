"""Lucan's temporary rescue role survives real battle and travel owners.

Earlier story is a labelled arrival fixture. Production arrival, menus,
encounter settlement, cave links and Continue own the behavior under test.
"""
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

from cave_random_encounters import CaveRandomEncounters
from leveling import CharacterLevel, character_stats
from main import Game
from post_battle import valid_pending_snapshot
from sanctuary_cave import RESERVE_ENTRY_APPROACH
import test_sanctuary_arrival_state as arrival_tests
import test_sanctuary_boss_gameplay as boss_tests
from test_mill_battle_gameplay import (click, finish_spoils_presentation,
                                      key, wait_for_spoils)
from ui_style import Painter


class LucanGuestGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = arrival_tests.SanctuaryArrivalStateTests()
        fixture.setUp()
        try:
            fixture.until(lambda: fixture.g.sanctuary_arrival.completed)
            game = fixture.g
            if not game.character_abilities.has_weapon():
                assert game.character_abilities.acquire_weapon('caelan', 'caelan_gearblade')
            assert game.character_abilities.learn_ability('caelan', 'aqua_edge')
            # This suite starts after the separate Aqua discovery lesson.
            assert game.cave_lesson.restore({'version': 1, 'resonance_seen': True,
                                             'battle_cleared': True, 'deferred': False})
            assert game.save_progress()
            cls.journey = json.loads(fixture.path.read_text())
        finally:
            fixture.doCleanups()

    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix='lucan-guest-')
        self.addCleanup(folder.cleanup)
        self.addCleanup(pygame.quit)
        self.folder = Path(folder.name)
        self.path = self.folder/'journey.json'
        self.path.write_text(json.dumps(self.journey))
        self.game = self.load()

    def load(self):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=True,
                    save_path=self.path, settings_path=self.folder/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        self.assertTrue(game.has_saved_journey, game.save_error)
        self.assertTrue(game.begin_journey(True), game.save_error)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def enter_cave(self):
        game = self.game
        game.player.position.update(RESERVE_ENTRY_APPROACH)
        game.player.moving = game.player.running = False
        game.transfer_cooldown = game.opening_fade = 0
        self.assertTrue(game.sanctuary_cave.interact())
        game.transfer_cooldown = game.opening_fade = 0
        self.assertEqual(game.world.data['id'], 'sanctuary_cave')

    def exit_cave(self):
        game = self.game
        link = next(link for link in game.world.data['cave']['links']
                    if link['destination'] == 'elden_vale_sanctuary')
        game.player.position.update(link['approach'])
        game.player.moving = game.player.running = False
        game.transfer_cooldown = game.opening_fade = 0
        self.assertTrue(game.sanctuary_cave.interact())
        game.transfer_cooldown = game.opening_fade = 0
        self.assertEqual(game.world.data['id'], 'elden_vale_sanctuary')

    def finish_entry(self):
        game = self.game
        for _ in range(240):
            if game.combat.model is not None and not game.combat.transitioning:return game.combat.model
            game.draw();game.update(.05, (0, 0), False)
        self.fail('The real encounter loader did not reach combat')

    def random_battle(self):
        if self.game.world.data['id'] != 'sanctuary_cave':self.enter_cave()
        game = self.game
        counter = CaveRandomEncounters(41)
        ticket = counter.advance(1000, (456, 1280))
        self.assertIsNotNone(ticket)
        game.player.position.update(ticket['position']);game.camera.reset()
        self.assertTrue(game.cave_random_encounters.restore(counter.to_dict()))
        self.assertTrue(game.combat.start_cave(ticket))
        return self.finish_entry()

    def ready(self, actor='lucan'):
        model = self.game.combat.model
        self.assertIsNone(model.current_action)
        for member in (*model.party, *model.enemies):member.atb = 0
        model.combatant(actor).atb = 1
        model.update(0)
        self.game.draw()
        self.assertEqual(model.ready_actor, actor)

    def command(self, name):
        scene = self.game.combat.scene
        for _ in range(len(scene._command_actions())+1):
            self.game.draw()
            if name in scene.command_rects:break
            key(self.game, pygame.K_DOWN)
        self.assertIn(name, scene.command_rects)
        click(self.game, scene.command_rects[name].center)

    def win(self):
        owner = self.game.combat
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), json.loads(self.path.read_text())))
        return wait_for_spoils(self.game)

    def dismiss_spoils(self):
        finish_spoils_presentation(self.game)
        self.game.draw();click(self.game, self.game.combat.spoils.continue_rect.center)
        self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.combat.active)

    # Reuse actual choice-menu input, without inheriting unrelated boss tests.
    position = boss_tests.SanctuaryBossGameplayTests.position
    choices = boss_tests.SanctuaryBossGameplayTests.choices
    choose = boss_tests.SanctuaryBossGameplayTests.choose
    offer = boss_tests.SanctuaryBossGameplayTests.offer
    start_boss = boss_tests.SanctuaryBossGameplayTests.start
    enter_battle = boss_tests.SanctuaryBossGameplayTests.enter_battle

    def key(self, value):key(self.game, value)

    def test_arrival_installs_level_five_once_and_continue_does_not_restore_resources(self):
        game = self.game
        self.assertTrue(game.party.members['lucan']['temporary'])
        self.assertEqual(game.character_progression.level('lucan'), 5)
        self.assertEqual(game.party.characters['lucan'].to_dict()['attributes'], character_stats('lucan', 5))
        lucan = game.party.characters['lucan']
        lucan.set_current(hp=17, mp=3)
        before = deepcopy(lucan.to_dict())
        for _ in range(3):game._sync_story_party()
        self.assertEqual(lucan.to_dict(), before)
        self.assertTrue(game.save_progress())
        self.game = restored = self.load()
        self.assertEqual(restored.party.characters['lucan'].to_dict(), before)
        self.assertEqual(restored.character_progression.level('lucan'), 5)

    def test_guest_skills_use_lucans_turn_without_changing_persistent_base_stats(self):
        model = self.random_battle()
        scene = self.game.combat.scene
        before = {identifier: deepcopy(value.to_dict())
                  for identifier, value in self.game.party.characters.items()}
        self.ready();self.command('skills')
        self.assertEqual(set(model.skill_actions('lucan')), {'inspire', 'bolster', 'provoke'})
        self.assertTrue(all(skill in scene._command_actions() for skill in ('inspire','bolster','provoke')))
        self.command('inspire')
        self.assertEqual(model.current_action.actor, 'lucan')
        self.assertEqual(model.combatant('lucan').mp, before['lucan']['current_mp']-5)
        scene.update(model.current_action.duration)
        for actor in model.party:
            self.assertEqual(actor.value('str'), min(999, actor.attributes['str']*3//2))
            self.assertEqual(actor.buffs['inspire'], 5)
        self.ready();self.command('skills');self.command('bolster')
        scene.update(model.current_action.duration)
        for actor in model.party:
            self.assertEqual(actor.value('def'), min(999, actor.attributes['def']*3//2))
        self.assertEqual({identifier:value.to_dict() for identifier,value in self.game.party.characters.items()}, before)
        model._result('defeat')
        self.assertTrue(all(not actor.buffs for actor in model.party))
        self.assertEqual({identifier:value.to_dict() for identifier,value in self.game.party.characters.items()}, before)

    def test_surviving_guest_receives_no_exp_or_exp_bar_while_survivors_receive_full_reward(self):
        model = self.random_battle()
        before = {identifier:self.game.character_progression[identifier].total_xp
                  for identifier in self.game.party.active_ids}
        spoils = self.win()
        self.assertTrue(spoils.awarded, spoils.result_error)
        amount = spoils.progression['amount']
        self.assertGreater(amount, 0)
        for identifier in ('caelan','mira'):
            self.assertEqual(self.game.character_progression[identifier].total_xp, before[identifier]+amount)
        self.assertEqual(self.game.character_progression['lucan'].total_xp, before['lucan'])
        self.assertEqual(self.game.character_progression.level('lucan'), 5)
        self.game.draw()
        self.assertNotIn('lucan', spoils.bar_rects)
        self.assertFalse(any(entry['character_id']=='lucan' for entry in spoils._level_queue))
        self.dismiss_spoils()
        self.game = restored = self.load()
        self.assertEqual(restored.character_progression['lucan'].total_xp, before['lucan'])

    def test_early_exit_for_rest_retains_guest_and_reentry_does_not_reinitialize_him(self):
        self.enter_cave()
        lucan = self.game.party.characters['lucan'];lucan.set_current(hp=19, mp=2)
        before = deepcopy(lucan.to_dict())
        self.exit_cave()
        self.assertIn('lucan', self.game.party.active_ids)
        self.game = self.load()
        self.assertIn('lucan', self.game.party.active_ids)
        self.enter_cave()
        self.assertEqual(self.game.party.characters['lucan'].to_dict(), before)

    def test_boss_victory_retains_guest_until_actual_exit_then_continue_prevents_rejoining(self):
        self.enter_cave();self.start_boss()
        self.assertTrue(self.game.combat.model.flee_allowed is False)
        before = self.game.character_progression['lucan'].total_xp
        spoils = self.win()
        self.assertTrue(spoils.awarded, spoils.result_error)
        self.dismiss_spoils()
        self.assertTrue(self.game.sanctuary_boss.defeated)
        self.assertIn('lucan', self.game.party.active_ids)
        self.assertEqual(self.game.character_progression['lucan'].total_xp, before)
        self.assertTrue(self.game.save_progress())
        self.game = self.load()
        self.assertIn('lucan', self.game.party.active_ids)
        self.exit_cave()
        self.assertNotIn('lucan', self.game.party.active_ids)
        self.assertFalse(self.game.party.members['lucan']['available'])
        self.game = self.load()
        self.assertNotIn('lucan', self.game.party.active_ids)
        self.enter_cave()
        self.game._sync_story_party()
        self.assertNotIn('lucan', self.game.party.active_ids)

    def test_guest_can_use_items_and_flee_without_gaining_an_interactable(self):
        model = self.random_battle();self.ready()
        scene = self.game.combat.scene
        self.assertEqual(model.command_actions('lucan'), ['attack','skills','items','guard','flee'])
        model.player.hp = max(1,model.player.max_hp-40)
        self.command('items');self.command('item:potion');self.command('ally:player')
        self.assertEqual(model.current_action.actor,'lucan')
        scene.update(model.current_action.duration)
        self.ready()
        self.assertFalse(model.action_reason('flee', 'lucan'))
        self.command('flee');scene.update(model.current_action.duration)
        self.assertEqual(model.phase,'fled')
        # The only authored mini-games remain Caelan's gear and Mira's rig.
        self.assertEqual(scene.rig.allocation,model.rig_allocation)
        self.assertFalse(hasattr(scene, 'lucan_interactable'))

    def test_guest_character_menu_shows_level_five_without_an_exp_progress_claim(self):
        status = self.game.status_ui
        status.open();self.assertTrue(status.select_character('lucan'))
        original = Painter.text
        with patch.object(Painter, 'text', autospec=True, side_effect=original) as text:
            status.draw(self.game.ui_surface)
        strings = [str(call.args[1]) for call in text.call_args_list]
        self.assertIn('Lv. 5', strings)
        self.assertTrue(any('guest' in value.casefold() for value in strings))
        self.assertFalse(any(value.startswith('EXP ') for value in strings))

    def test_failed_departure_checkpoint_keeps_the_guest_inside_until_successful_retry(self):
        self.enter_cave();self.start_boss();self.win();self.dismiss_spoils()
        game = self.game
        before = game.party.to_dict()
        link = next(link for link in game.world.data['cave']['links']
                    if link['destination'] == 'elden_vale_sanctuary')
        game.player.position.update(link['approach'])
        game.transfer_cooldown = game.opening_fade = 0
        with patch.object(game.save_store, 'write', return_value=False):
            self.assertFalse(game.sanctuary_cave.interact())
        self.assertEqual(game.world.data['id'],'sanctuary_cave')
        self.assertEqual(game.party.to_dict(),before)
        self.assertFalse(game.sanctuary_cave.to_dict().get('lucan_departed',False))
        self.exit_cave()
        self.assertNotIn('lucan',game.party.active_ids)

    def test_future_permanent_lucan_keeps_progression_and_remains_after_the_boss_exit(self):
        # A labelled future recruitment checkpoint exercises protection of an
        # already permanent member; this update does not author that quest.
        game = self.game
        party = game.party.to_dict()
        party['members']['lucan']['temporary'] = False
        self.assertTrue(game.party.restore(party))
        hp = {'lucan':game.party.characters['lucan'].current_hp}
        plan = game.character_progression.preview(2000, ['lucan'], hp)
        self.assertTrue(game.character_progression.apply(plan))
        before = game.character_progression['lucan'].total_xp
        self.enter_cave();self.start_boss();spoils=self.win()
        self.assertGreater(game.character_progression['lucan'].total_xp,before)
        expected = game.character_progression['lucan'].total_xp
        self.dismiss_spoils();self.exit_cave()
        self.assertIn('lucan',game.party.active_ids)
        self.assertFalse(game.party.members['lucan']['temporary'])
        self.assertEqual(game.character_progression['lucan'].total_xp,expected)
        self.game = restored = self.load()
        self.assertIn('lucan',restored.party.active_ids)
        self.assertEqual(restored.character_progression['lucan'].total_xp,expected)

    def test_legacy_pending_victory_settles_before_guest_profile_migration(self):
        self.random_battle()
        owner = self.game.combat
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        saved = json.loads(self.path.read_text())
        # This labelled pre-update receipt models the old level-one guest and
        # v1 full-survivor EXP plan; unfinished historical awards keep their
        # original before-state until the existing transaction is complete.
        legacy_stats = character_stats('lucan',1)
        attributes = saved['party']['characters']['lucan']
        attributes['attributes'] = legacy_stats
        attributes['current_hp'],attributes['current_mp'] = 71,8
        saved['character_levels']['characters']['lucan'] = CharacterLevel('lucan').to_dict()
        saved['sanctuary_cave'].pop('lucan_guest_initialized',None)
        pending = saved['post_battle']
        for field in ('party_before','party_resources'):
            pending[field]['lucan'] = {'hp':71,'mp':8}
        plan = pending['progression']
        plan['version'] = 1;plan.pop('guest_ids',None)
        plan['end_hp']['lucan'] = 71
        award = CharacterLevel('lucan').award_xp(plan['amount']).to_dict()
        plan['characters']['lucan'] = {**award,'stats_before':legacy_stats,
            'stats_after':{stat:value+award['stat_gains'][stat] for stat,value in legacy_stats.items()}}
        self.assertTrue(valid_pending_snapshot(pending,saved))
        self.path.write_text(json.dumps(saved))
        self.game = resumed = self.load()
        self.assertEqual(resumed.character_progression.level('lucan'),1)
        spoils = wait_for_spoils(resumed)
        self.assertTrue(spoils.awarded,spoils.result_error)
        self.dismiss_spoils()
        self.assertEqual(resumed.character_progression.level('lucan'),5)
        self.assertTrue(resumed.sanctuary_cave.to_dict()['lucan_guest_initialized'])
        resources = resumed.party.characters['lucan'].to_dict()
        items = resumed.inventory.to_dict()
        self.game = restored = self.load()
        self.assertEqual(restored.character_progression.level('lucan'),5)
        self.assertEqual(restored.party.characters['lucan'].to_dict(),resources)
        self.assertEqual(restored.inventory.to_dict(),items)


if __name__ == '__main__':unittest.main()
