"""Durable MQ02 encounter facts, legacy route migration and linear prose."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from mill_quest import MillQuest, FACTS, REPAIR_FACTS
from quests import MILL_QUEST, OPENING_QUEST, QuestLog


ROOT = Path(__file__).resolve().parents[1]


class MillCombatStoryTests(unittest.TestCase):
    def controller(self, warned=False):
        quests = QuestLog()
        self.assertTrue(quests.accept(OPENING_QUEST))
        for objective in quests.definitions[OPENING_QUEST]['objectives']:
            self.assertTrue(quests.complete_objective(OPENING_QUEST, objective['id']))
        self.assertTrue(quests.turn_in(OPENING_QUEST, 'mother_serene'))
        self.assertTrue(quests.unlock(MILL_QUEST))
        self.assertTrue(quests.accept(MILL_QUEST))
        for objective in ('meet_mira', 'diagnose_mill'):
            self.assertTrue(quests.complete_objective(MILL_QUEST, objective))
        controller = MillQuest.__new__(MillQuest)
        controller.game = SimpleNamespace(quests=quests, social=SimpleNamespace(flags=set()),
                                          save_progress=Mock())
        controller.inspected = {'mechanism', 'race'}
        controller._returning = False
        for fact in FACTS:setattr(controller, fact, False)
        controller._save = Mock()
        if warned:self.assertTrue(controller._warned())
        return controller

    def test_warning_is_a_read_milestone_and_blocks_the_first_departure(self):
        controller = self.controller()
        self.assertFalse(controller.can_enter_upstream())
        self.assertEqual(controller.stage, 'warning')
        self.assertTrue(controller._warned())
        self.assertTrue(controller.can_enter_upstream())
        self.assertTrue(controller.encounter_pending)
        self.assertEqual(controller.stage, 'encounter')
        self.assertEqual(controller.game.quests.objective_status(MILL_QUEST, 'prepare_journey'),
                         'completed')
        before = controller.game.quests.to_dict()
        self.assertFalse(controller._warned())
        self.assertEqual(controller.game.quests.to_dict(), before)

    def test_victory_commits_once_without_saving_or_restoring_the_mill(self):
        controller = self.controller(warned=True)
        controller._save.reset_mock()
        self.assertTrue(controller.battle_won())
        self.assertTrue(controller.combat_unlocked)
        self.assertEqual(controller.stage, 'aftermath')
        self.assertFalse(controller.mill_restored)
        self.assertFalse(controller.aftermath_done)
        self.assertFalse(controller.battle_won())
        controller._save.assert_not_called()
        controller.game.save_progress.assert_not_called()
        self.assertTrue(MillQuest.valid_snapshot(controller.to_dict()))

    def test_spear_is_carried_out_stowed_for_tools_and_carried_home(self):
        controller = self.controller(warned=True)
        self.assertTrue(controller.mira_armed)
        self.assertFalse(controller.mira_spear_stowed)
        self.assertTrue(controller.battle_won())
        self.assertTrue(controller._aftermath_finished())
        controller._record_inspection('intake')
        self.assertFalse(controller.mira_armed)
        self.assertTrue(controller.mira_spear_stowed)
        for objective, fact in (('prepare_intake', 'prepared'), ('small_spell', 'spell_done')):
            self.assertTrue(controller._complete(objective))
            setattr(controller, fact, True)
        controller.encouraged = True
        self.assertTrue(controller._complete('repair_intake'));controller.restored = True
        self.assertTrue(controller.mira_armed)
        self.assertFalse(controller.mira_spear_stowed)
        self.assertTrue(controller._complete('verify_mill'));controller.verified = True
        self.assertTrue(controller._complete('report'))
        self.assertTrue(controller.game.quests.turn_in(MILL_QUEST, 'mira_worker'))
        controller.resolved = True;controller._returning = True
        self.assertTrue(controller.mira_armed)
        controller._returning = False
        self.assertFalse(controller.mira_armed)
        self.assertTrue(MillQuest.valid_snapshot(controller.to_dict()))

    def test_intake_requires_the_acknowledged_linear_aftermath(self):
        controller = self.controller(warned=True)
        controller._record_inspection('intake')
        self.assertNotIn('intake', controller.inspected)
        self.assertTrue(controller.battle_won())
        controller._record_inspection('intake')
        self.assertNotIn('intake', controller.inspected)
        self.assertTrue(controller._aftermath_finished())
        self.assertEqual(controller.stage, 'reach_intake')
        controller._record_inspection('intake')
        self.assertIn('intake', controller.inspected)
        self.assertEqual(controller.stage, 'prepare_intake')
        self.assertFalse(controller.mill_restored)

    def test_old_completed_route_migrates_without_inventing_a_won_battle(self):
        controller = self.controller()
        old_done = ['meet_mira', 'diagnose_mill', 'reach_intake', 'prepare_intake',
                    'small_spell', 'repair_intake', 'verify_mill', 'report']
        data = controller.game.quests.to_dict()
        data['quests'][MILL_QUEST] = {'status': 'completed', 'completed_objectives': old_done}
        old_record = {'version': 1, 'inspected': ['mechanism', 'race', 'intake'],
                      **{fact: True for fact in REPAIR_FACTS}}
        journey = {'quests': data, 'mill_quest': old_record}
        self.assertTrue(MillQuest.valid_journey(journey))
        migrated = MillQuest.migrate_snapshot(old_record)
        self.assertTrue(migrated['legacy_bypass'])
        self.assertFalse(migrated['warned'])
        self.assertFalse(migrated['encounter_cleared'])
        self.assertFalse(migrated['aftermath_done'])
        self.assertTrue(migrated['restored'])
        quests = QuestLog();self.assertTrue(quests.restore(data))
        self.assertEqual(quests.status(MILL_QUEST), 'completed')
        for objective in ('prepare_journey', 'secure_trail'):
            self.assertEqual(quests.objective_status(MILL_QUEST, objective), 'completed')
        self.assertEqual(data['quests'][MILL_QUEST]['completed_objectives'], old_done)

    def test_new_records_cannot_forge_the_legacy_route_or_skip_the_battle(self):
        controller = self.controller(warned=True)
        record = controller.to_dict()
        forged = copy.deepcopy(record);forged['legacy_bypass'] = True
        self.assertFalse(MillQuest.valid_snapshot(forged))
        forged = copy.deepcopy(record);forged['inspected'].append('intake')
        self.assertFalse(MillQuest.valid_snapshot(forged))
        forged = copy.deepcopy(record);forged['warned'] = False;forged['encounter_cleared'] = True
        self.assertFalse(MillQuest.valid_snapshot(forged))
        for version in (True, 1.0, 3):
            forged = copy.deepcopy(record);forged['version'] = version
            self.assertFalse(MillQuest.valid_snapshot(forged))
        malformed = {'version': 1, 'inspected': None,
                     **{fact: False for fact in REPAIR_FACTS}}
        self.assertFalse(MillQuest.valid_snapshot(malformed))

    def test_encounter_prose_is_linear_and_legacy_reports_stay_truthful(self):
        lines = json.loads((ROOT/'assets/story/mill/scene.json').read_text())
        for name in ('warning', 'encounter_intro', 'aftermath', 'aftermath_recovered', 'withdrawal', 'retry'):
            self.assertGreater(len(lines[name]), 1)
            for line in lines[name]:
                self.assertEqual(set(line), {'speaker', 'text'})
                self.assertIn(line['speaker'], ('caelan', 'mira'))
                self.assertNotIn('ATB', line['text'])
        self.assertFalse(any('rest' in line['text'].lower() for line in lines['aftermath']))
        self.assertTrue(any('tusker' in line['text'].lower() for line in lines['resolution_combat']))
        self.assertFalse(any('tusker' in line['text'].lower() for line in lines['resolution']))
        self.assertTrue(any('spear' in line['text'] for line in lines['warning']))
        self.assertTrue(any('bandage' in line['text'] for line in lines['aftermath_recovered']))
        self.assertTrue(any('tree' in line['text'] for line in lines['encounter_intro']))


if __name__ == '__main__':unittest.main()
