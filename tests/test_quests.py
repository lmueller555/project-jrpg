"""Quest acceptance, ordered task progress, reporting and save integrity."""
from copy import deepcopy
import unittest

from quests import OPENING_QUEST, QuestLog


class QuestLogTests(unittest.TestCase):
    def setUp(self):
        self.log = QuestLog()
        self.quest = OPENING_QUEST

    def complete_visits(self, order=('halden', 'elira', 'venn')):
        self.assertTrue(self.log.accept(self.quest))
        for objective in order:
            self.assertTrue(self.log.complete_objective(self.quest, objective))

    def test_availability_acceptance_and_deliberate_report_are_distinct(self):
        self.assertEqual(self.log.marker_for('mother_serene'), '!')
        self.assertEqual(self.log.tracker_text(), '')
        self.assertFalse(self.log.turn_in(self.quest))
        self.assertFalse(self.log.complete_objective(self.quest, 'halden'))
        self.complete_visits()
        self.assertEqual(self.log.status(self.quest), 'ready')
        self.assertEqual(self.log.marker_for('mother_serene'), '?')
        self.assertEqual(self.log.tracker_text(), 'Return to Mother Serene.')
        self.assertFalse(self.log.turn_in(self.quest, 'tomas'))
        self.assertEqual(self.log.status(self.quest), 'ready')
        self.assertTrue(self.log.turn_in(self.quest, 'mother_serene'))
        self.assertEqual(self.log.status(self.quest), 'completed')
        self.assertIsNone(self.log.marker_for('mother_serene'))
        self.assertEqual(self.log.tracker_text(), '')

    def test_halden_first_then_both_household_orders(self):
        for order in (('elira', 'venn'), ('venn', 'elira')):
            with self.subTest(order=order):
                self.log = QuestLog()
                self.assertTrue(self.log.accept(self.quest))
                self.assertEqual(self.log.objective_status(self.quest, 'halden'), 'active')
                self.assertEqual(self.log.objective_status(self.quest, 'elira'), 'queued')
                self.assertEqual(self.log.objective_status(self.quest, 'venn'), 'queued')
                self.assertFalse(self.log.complete_objective(self.quest, order[0]))
                self.assertEqual(self.log.tracker_text(), 'Visit Halden with Tomas.')
                self.assertTrue(self.log.complete_objective(self.quest, 'halden'))
                self.assertEqual(self.log.tracker_text(), 'Visit Elira and the Venn family.')
                for objective in order:
                    self.assertTrue(self.log.complete_objective(self.quest, objective))
                self.assertEqual(self.log.states[self.quest]['completed_objectives'],
                                 ['halden', 'elira', 'venn'])

    def test_repeated_or_unknown_events_cannot_duplicate_progress_or_notices(self):
        self.assertFalse(self.log.accept('unknown'))
        self.assertFalse(self.log.complete_objective('unknown', 'halden'))
        self.assertEqual(self.log.status('unknown'), 'locked')
        self.assertTrue(self.log.accept(self.quest))
        self.assertFalse(self.log.accept(self.quest))
        self.assertIsNone(self.log.marker_for('mother_serene'))
        self.assertFalse(self.log.complete_objective(self.quest, 'unknown'))
        for objective in ('halden', 'elira', 'venn'):
            self.assertTrue(self.log.complete_objective(self.quest, objective))
            self.assertFalse(self.log.complete_objective(self.quest, objective))
        self.assertTrue(self.log.turn_in(self.quest))
        self.assertFalse(self.log.turn_in(self.quest))
        events = self.log.drain_events()
        self.assertEqual([event['kind'] for event in events],
                         ['accepted', 'objective', 'objective', 'objective', 'ready', 'completed'])
        self.assertTrue(all(event['quest_id'] == self.quest and event['title']
                            and event['text'] for event in events))
        self.assertEqual(self.log.drain_events(), [])

    def test_save_round_trip_at_every_stage_never_replays_notifications(self):
        stages = []
        stages.append(self.log.to_dict())
        self.log.accept(self.quest)
        stages.append(self.log.to_dict())
        self.log.complete_objective(self.quest, 'halden')
        stages.append(self.log.to_dict())
        self.log.complete_objective(self.quest, 'venn')
        stages.append(self.log.to_dict())
        self.log.complete_objective(self.quest, 'elira')
        stages.append(self.log.to_dict())
        self.log.turn_in(self.quest)
        stages.append(self.log.to_dict())
        for saved in stages:
            with self.subTest(status=saved['quests'][self.quest]['status'],
                              progress=saved['quests'][self.quest]['completed_objectives']):
                restored = QuestLog()
                restored.accept(self.quest)
                self.assertTrue(restored.restore(saved))
                self.assertEqual(restored.to_dict(), saved)
                self.assertEqual(restored.drain_events(), [])
                saved['quests'][self.quest]['completed_objectives'].append('external_mutation')
                self.assertNotEqual(restored.to_dict(), saved)

    def test_invalid_or_inconsistent_save_is_rejected_atomically(self):
        self.log.accept(self.quest)
        self.log.complete_objective(self.quest, 'halden')
        before = self.log.to_dict()
        invalid = [None, [], {}, {'version': True, 'quests': {}},
                   {'version': 2, 'quests': {}}, {'version': 1, 'quests': {}},
                   {'version': 1, 'quests': {'unknown': {}}}]
        progress_cases = [
            {'status': 'available', 'completed_objectives': ['halden']},
            {'status': 'active', 'completed_objectives': ['elira']},
            {'status': 'active', 'completed_objectives': ['halden', 'halden']},
            {'status': 'active', 'completed_objectives': ['halden', 'elira', 'venn']},
            {'status': 'ready', 'completed_objectives': ['halden']},
            {'status': 'completed', 'completed_objectives': []},
            {'status': 'active', 'completed_objectives': ['missing']},
            {'status': 'active', 'completed_objectives': [False]},
            {'status': 'active', 'completed_objectives': 'halden'},
            {'status': [], 'completed_objectives': []},
            {'status': 'active', 'completed_objectives': [], 'extra': True},
        ]
        for state in progress_cases:
            invalid.append({'version': 1, 'quests': {self.quest: state}})
        for bad in invalid:
            with self.subTest(bad=bad):
                self.assertFalse(self.log.restore(deepcopy(bad)))
                self.assertEqual(self.log.to_dict(), before)
        self.assertEqual([event['kind'] for event in self.log.drain_events()],
                         ['accepted', 'objective'])

    def test_saved_snapshot_does_not_share_mutable_live_state(self):
        self.log.accept(self.quest)
        saved = self.log.to_dict()
        saved['quests'][self.quest]['status'] = 'completed'
        saved['quests'][self.quest]['completed_objectives'].append('halden')
        self.assertEqual(self.log.status(self.quest), 'active')
        self.assertEqual(self.log.states[self.quest]['completed_objectives'], [])


if __name__ == '__main__':
    unittest.main()
