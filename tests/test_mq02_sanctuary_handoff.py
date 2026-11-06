"""MQ02 ends at home only after the player reads and performs the cup help."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame
from main import Game
from mill_quest import MillQuest
from quests import MILL_QUEST, REGENT_QUEST
from test_mill_battle_gameplay import seed_mill_handoff


class SanctuaryHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journey.json'
        self.g = self.game();seed_mill_handoff(self.g)
        self.assertTrue(self.g.accept_quest(MILL_QUEST))
        for objective in self.g.quests.definitions[MILL_QUEST]['objectives']:
            if objective['id'] == 'report':break
            self.assertTrue(self.g.quests.complete_objective(MILL_QUEST, objective['id']))
        self.g.world = self.g.town
        self.g.player.position.update(self.g.mill_quest.points['mill_station'])
        # A legitimate legacy journey has repaired/verified the mill but has
        # not reported it, owned the new blade or invented a boar victory.
        self.assertTrue(self.g.mill_quest.restore({
            'version': 1, 'inspected': ['mechanism', 'race', 'intake'],
            'prepared': True, 'spell_done': True, 'encouraged': True,
            'restored': True, 'verified': True, 'resolved': False}))
        self.g.social.blocked.clear();self.g.quests.drain_events()

    def tearDown(self):pygame.quit()

    def game(self, title=False):
        game = Game(fullscreen=False, start_on_title=title, save_path=self.path,
                    settings_path=self.path.with_name('settings.json'))
        game.audio.set_music(0);game.audio.set_effects(0);pygame.event.clear()
        return game

    @property
    def quest(self):return self.g.mill_quest
    @property
    def home(self):return self.quest.sanctuary_return

    def tick(self, seconds=.05):self.g.update(seconds, (0, 0), False)

    def until(self, predicate, seconds=30):
        for _ in range(round(seconds/.05)):
            if predicate():return
            self.tick()
        self.fail(('Handoff stalled', self.quest.stage,
                   self.g.social.script_identifier, self.g.world.data['id']))

    def read_current(self):
        identifier = self.g.social.script_identifier
        for _ in range(120):
            if not self.g.social.active or self.g.social.script_identifier != identifier:return
            self.assertFalse(self.g.social.choosing)
            self.g.social.advance()
        self.fail('Unread '+str(identifier))

    def report(self):
        self.g.social.blocked.clear()
        self.assertTrue(self.quest.interact())
        self.assertEqual(self.g.social.script_identifier, 'mill_resolution')
        self.read_current()
        self.assertTrue(self.quest.reported_to_halden)

    def enter_home(self):
        self.g.world = self.home.dining
        self.until(lambda: self.home.ready)
        for offset in ((-24, 12), (0, 24), (24, 0), (-24, 0)):
            point = self.home.serene.position+offset
            if self.g.world.can_stand(point):
                self.g.player.position.update(point);break
        else:self.fail('No clear position beside Serene')
        self.g.social.blocked.clear()

    def speak(self):
        self.assertTrue(self.g.social.start(self.home.serene))

    def reload(self):
        self.assertTrue(self.g.save_progress())
        other = self.game(True)
        self.assertTrue(other.has_saved_journey)
        self.assertTrue(other.begin_journey(True))
        other.opening_fade = other.transfer_cooldown = 0
        self.g = other

    def reach_setting(self):
        self.report();self.enter_home();self.speak();self.read_current()
        self.assertTrue(self.home.action_active)
        self.until(lambda: self.g.social.script_identifier == 'mill_sanctuary_setting')
        self.assertTrue(self.home.holding_cups)
        self.assertFalse(self.quest.cups_placed)

    def test_halden_report_records_repair_but_keeps_quest_and_arrival_unfinished(self):
        self.assertTrue(self.quest.interact())
        self.g.social.advance();self.g.social.cancel()
        self.assertFalse(self.quest.reported_to_halden)
        self.report()
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'active')
        self.assertEqual(self.g.quests.objective_status(MILL_QUEST, 'report'), 'completed')
        self.assertEqual(self.g.quests.objective_status(MILL_QUEST, 'return_sanctuary'), 'active')
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'locked')
        self.assertEqual(self.g.regent_arrival.state, 'waiting')
        self.assertFalse(self.quest.resolved)
        self.assertFalse(self.quest.cups_placed)
        self.assertNotIn('CH01_MQ02_COMPLETE', self.g.social.flags)
        self.assertTrue(all(not a.story_visible for a in self.g.regent_quest.actors.values()))
        self.assertIsNotNone(self.g._read_saved_journey())
        self.reload()
        self.assertTrue(self.quest.reported_to_halden)
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'active')
        self.assertEqual(self.g.regent_arrival.state, 'waiting')

    def test_family_is_inside_once_and_wrong_room_coordinates_do_not_start_return(self):
        self.report()
        self.until(lambda: self.home.ready)
        for actor in (self.home.serene, self.home.tomas):
            self.assertIn(actor, self.home.dining.npcs)
            self.assertEqual(sum(actor in room.npcs for room in self.g.scenes.values()), 1)
            self.assertNotIn(actor, self.g.town.npcs)
        self.g.world = self.g.town
        self.g.player.position.update(self.home.serene.position+(-24, 12))
        self.assertFalse(self.quest.try_conversation(self.home.serene))
        self.assertFalse(self.g.social.active)
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'locked')
        self.enter_home();self.speak()
        self.assertEqual(self.g.social.script_identifier, 'mill_sanctuary_return')

    def test_unread_return_and_interrupted_carry_restart_safely_without_progress(self):
        self.report();self.enter_home();self.speak()
        self.g.social.advance();self.g.social.cancel();self.reload()
        self.assertTrue(self.quest.reported_to_halden)
        self.assertFalse(self.quest.cups_placed)
        self.assertFalse(self.home.action_active)
        self.enter_home();self.speak();self.read_current()
        self.assertTrue(self.home.action_active)
        self.tick(.15);self.reload()
        self.assertFalse(self.home.action_active)
        self.assertFalse(self.home.holding_cups)
        self.assertFalse(self.quest.cups_placed)
        self.assertFalse(self.quest.resolved)
        self.enter_home();self.speak()
        self.assertEqual(self.g.social.script_identifier, 'mill_sanctuary_return')

    def test_held_cups_and_cancelled_destination_dialogue_do_not_complete_quest(self):
        self.reach_setting()
        self.g.social.advance();self.g.social.cancel()
        self.assertFalse(self.quest.resolved)
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'active')
        self.assertEqual(self.g.regent_arrival.state, 'waiting')
        self.assertFalse(self.quest.cups_placed)
        self.assertIsNotNone(self.g._read_saved_journey())
        self.reload();self.enter_home();self.speak()
        self.assertEqual(self.g.social.script_identifier, 'mill_sanctuary_return')

    def test_game_modals_freeze_the_staged_cup_walk(self):
        self.report();self.enter_home();self.speak();self.read_current()
        self.until(lambda: self.home.action_active and self.g.player.moving)
        for owner, field in ((self.g.pause, 'is_open'), (self.g.inventory_ui, 'is_open'),
                             (self.g, 'map_open'), (self.g.quest_ui, 'journal_open')):
            with self.subTest(modal=field):
                before = tuple(self.g.player.position), self.home.holding_cups
                setattr(owner, field, True)
                self.tick(.8)
                setattr(owner, field, False)
                self.assertEqual((tuple(self.g.player.position), self.home.holding_cups), before)
                self.assertTrue(self.home.action_active)
                self.assertFalse(self.quest.cups_placed)
                self.assertFalse(self.quest.resolved)

    def test_destination_acknowledgment_then_physical_placement_completes_once(self):
        self.reach_setting()
        self.read_current()
        self.assertTrue(self.home.action_active)
        self.assertFalse(self.quest.resolved)
        self.assertFalse(self.quest.cups_placed)
        self.until(lambda: self.quest.resolved)
        self.assertTrue(self.quest.cups_placed)
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'completed')
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'available')
        self.assertIn('CH01_MQ02_COMPLETE', self.g.social.flags)
        self.assertEqual(self.g.world.data['id'], 'sanctuary_dining')
        self.assertEqual(self.g.regent_arrival.state, 'pending')
        self.assertFalse(self.g.regent_arrival.active)
        state = self.g.lattice.to_dict(), self.g.inventory.to_dict()
        self.assertFalse(self.g.regent_arrival.request())
        self.reload()
        self.assertTrue(self.quest.resolved)
        self.assertEqual(state, (self.g.lattice.to_dict(), self.g.inventory.to_dict()))
        self.assertFalse(self.home.action_active)
        self.assertIsNotNone(self.g._read_saved_journey())

    def test_new_game_resets_return_state_and_releases_the_existing_family(self):
        self.reach_setting()
        self.assertTrue(self.g.begin_journey(False, show_cinematic=False))
        self.assertFalse(self.quest.reported_to_halden)
        self.assertFalse(self.quest.cups_placed)
        self.assertFalse(self.home.action_active)
        self.assertFalse(self.home.holding_cups)
        self.assertEqual(self.g.regent_arrival.state, 'waiting')
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'locked')
        for actor in (self.home.serene, self.home.tomas):
            self.assertEqual(sum(actor in room.npcs for room in self.g.scenes.values()), 1)

    def test_old_completed_ten_objective_save_keeps_completion_without_replaying_ending(self):
        self.assertTrue(self.g.save_progress())
        journey = json.loads(self.path.read_text())
        old_objectives = [objective['id'] for objective in self.g.quests.definitions[MILL_QUEST]['objectives']
                          if objective['id'] != 'return_sanctuary']
        self.assertEqual(len(old_objectives), 10)
        journey['quests']['quests'][MILL_QUEST] = {
            'status': 'completed', 'completed_objectives': old_objectives}
        journey['quests']['quests'][REGENT_QUEST] = {
            'status': 'available', 'completed_objectives': []}
        journey['mill_quest']['resolved'] = True
        journey['mill_quest'].pop('reported_to_halden', None)
        journey['mill_quest'].pop('cups_placed', None)
        journey['regent_arrival'] = {'version': 1, 'state': 'seen'}
        self.path.write_text(json.dumps(journey))
        other = self.game(True)
        self.assertTrue(other.has_saved_journey)
        self.assertTrue(other.begin_journey(True));self.g = other
        self.assertEqual(other.quests.status(MILL_QUEST), 'completed')
        self.assertEqual(other.quests.objective_status(MILL_QUEST, 'return_sanctuary'), 'completed')
        self.assertEqual(other.quests.status(REGENT_QUEST), 'available')
        self.assertTrue(other.mill_quest.resolved)
        self.assertFalse(self.home.action_active)
        self.assertEqual(other.regent_arrival.state, 'seen')
        other.update(.1, (0, 0), False)
        self.assertFalse(other.regent_arrival.active)
        self.assertFalse(other.social.script_identifier in ('mill_sanctuary_return', 'mill_sanctuary_setting'))

    def test_return_extension_rejects_partial_non_boolean_and_premature_placement(self):
        original = self.quest.to_dict()
        self.assertTrue(MillQuest.valid_snapshot(original))
        malformed = [dict(original, reported_to_halden=True),
                     dict(original, cups_placed=False),
                     dict(original, reported_to_halden=1, cups_placed=False),
                     dict(original, reported_to_halden=False, cups_placed='yes'),
                     dict(original, reported_to_halden=False, cups_placed=True),
                     dict(original, reported_to_halden=True, cups_placed=True)]
        for record in malformed:
            with self.subTest(record=record):
                self.assertFalse(MillQuest.valid_snapshot(record))

    def test_old_ready_ten_objective_report_becomes_active_return_home(self):
        self.assertTrue(self.g.save_progress())
        journey = json.loads(self.path.read_text())
        old_objectives = [objective['id'] for objective in self.g.quests.definitions[MILL_QUEST]['objectives']
                          if objective['id'] != 'return_sanctuary']
        journey['quests']['quests'][MILL_QUEST] = {
            'status': 'ready', 'completed_objectives': old_objectives}
        journey['mill_quest'].pop('reported_to_halden', None)
        journey['mill_quest'].pop('cups_placed', None)
        self.path.write_text(json.dumps(journey))
        other = self.game(True)
        self.assertTrue(other.has_saved_journey)
        self.assertTrue(other.begin_journey(True));self.g = other
        self.assertEqual(other.quests.status(MILL_QUEST), 'active')
        self.assertEqual(other.quests.objective_status(MILL_QUEST, 'report'), 'completed')
        self.assertEqual(other.quests.objective_status(MILL_QUEST, 'return_sanctuary'), 'active')
        self.assertTrue(self.quest.reported_to_halden)
        self.assertFalse(self.quest.resolved)
        self.assertFalse(self.quest.cups_placed)
        self.assertEqual(other.regent_arrival.state, 'waiting')
        self.assertEqual(other.quests.status(REGENT_QUEST), 'locked')

    def test_dialogue_uses_exact_approved_lines_and_only_one_bow_question(self):
        mill = self.quest.lines
        lines = mill['sanctuary_return']
        tomas = next(i for i, line in enumerate(lines)
                     if line['speaker'] == 'tomas' and line['text'].startswith('The tables'))
        self.assertEqual([line['text'] for line in lines[tomas:tomas+3]], [
            "The tables are finished, we're just setting them if you can grab the cups.",
            'You could bring those clean ones over, if you have a moment.',
            'Yep, on it.'])
        self.assertNotIn('I thought they might be.', [line['text'] for line in lines])
        self.assertTrue(any('Do we have to bow' in line['text']
                            for line in mill['sanctuary_setting']))
        self.assertFalse(any('bow' in line['text']
                             for line in self.g.regent_quest.lines['preparations']))
        self.assertEqual(len(self.g.regent_quest.lines['preparations']), 2)


if __name__ == '__main__':unittest.main()
