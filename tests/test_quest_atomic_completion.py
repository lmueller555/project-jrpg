"""Story endings complete their final task without a stale report prompt."""
from copy import deepcopy
import unittest

from quests import QuestLog


DEFINITIONS = {
    'lantern': {
        'title': 'A Light of His Own', 'summary': 'Make a lantern.', 'giver': 'tomas',
        'completion_text': 'Liam is ready for tomorrow.',
        'objectives': [
            {'id': 'start', 'text': 'Begin.', 'requires': []},
            {'id': 'closing', 'text': 'Finish together.', 'requires': ['start']},
            {'id': 'prepare', 'text': 'Prepare.', 'requires': ['start']},
        ],
    },
    'neighbour': {
        'title': 'Neighbour', 'summary': 'Visit a neighbour.', 'giver': 'elira',
        'objectives': [{'id': 'visit', 'text': 'Visit.', 'requires': []}],
    },
    'festival': {
        'title': 'Festival', 'summary': 'Gather tomorrow.', 'giver': 'serene',
        'initially_locked': True, 'requires_quests': ['lantern'],
        'objectives': [{'id': 'gather', 'text': 'Gather.', 'requires': []}],
    },
}


class QuestAtomicCompletionTests(unittest.TestCase):
    def setUp(self):self.log = QuestLog(DEFINITIONS)

    def before_closing(self):
        self.assertTrue(self.log.accept('lantern'))
        self.assertTrue(self.log.complete_objective('lantern', 'start'))
        self.assertTrue(self.log.complete_objective('lantern', 'prepare'))

    def assert_rejected_without_changes(self, *args):
        state = self.log.to_dict();events = deepcopy(self.log._events)
        self.assertFalse(self.log.complete_and_turn_in(*args))
        self.assertEqual(self.log.to_dict(), state)
        self.assertEqual(self.log._events, events)

    def test_authored_closing_scene_completes_last_task_in_canonical_order(self):
        self.before_closing();self.log.drain_events()
        self.assertTrue(self.log.complete_and_turn_in('lantern', 'closing'))
        self.assertEqual(self.log.states['lantern'], {
            'status': 'completed', 'completed_objectives': ['start', 'closing', 'prepare']})
        self.assertEqual(self.log.drain_events(), [{
            'kind': 'completed', 'quest_id': 'lantern', 'title': 'A Light of His Own',
            'text': 'Liam is ready for tomorrow.'}])
        self.assertIsNone(self.log.marker_for('tomas'))

    def test_explicit_correct_giver_can_receive_the_last_task(self):
        self.before_closing()
        self.assertTrue(self.log.complete_and_turn_in('lantern', 'closing', 'tomas'))
        self.assertEqual(self.log.status('lantern'), 'completed')

    def test_wrong_giver_is_rejected_before_final_objective_changes(self):
        self.before_closing()
        self.assert_rejected_without_changes('lantern', 'closing', 'someone_else')
        self.assertEqual(self.log.objective_status('lantern', 'closing'), 'active')

    def test_available_locked_and_unknown_quests_do_not_complete(self):
        for args in (('lantern', 'closing'), ('festival', 'gather'), ('missing', 'closing')):
            with self.subTest(args=args):self.assert_rejected_without_changes(*args)

    def test_queued_unknown_and_already_completed_objectives_are_rejected(self):
        self.assertTrue(self.log.accept('lantern'))
        self.assert_rejected_without_changes('lantern', 'closing')
        self.assert_rejected_without_changes('lantern', 'missing')
        self.assertTrue(self.log.complete_objective('lantern', 'start'))
        self.assert_rejected_without_changes('lantern', 'start')

    def test_an_active_objective_cannot_complete_other_outstanding_work(self):
        self.assertTrue(self.log.accept('lantern'))
        self.assertEqual(self.log.objective_status('lantern', 'start'), 'active')
        self.assert_rejected_without_changes('lantern', 'start')
        self.assertTrue(self.log.complete_objective('lantern', 'start'))
        self.assertEqual(self.log.objective_status('lantern', 'closing'), 'active')
        self.assert_rejected_without_changes('lantern', 'closing')

    def test_ready_and_completed_quests_retain_their_existing_events(self):
        self.before_closing()
        self.assertTrue(self.log.complete_objective('lantern', 'closing'))
        self.assertEqual(self.log.status('lantern'), 'ready')
        self.assert_rejected_without_changes('lantern', 'closing')
        self.assertTrue(self.log.turn_in('lantern'))
        self.assert_rejected_without_changes('lantern', 'closing')

    def test_existing_pending_events_are_preserved_and_only_completion_is_added(self):
        self.before_closing()
        self.assertTrue(self.log.accept('neighbour'))
        pending = deepcopy(self.log._events)
        self.assertTrue(self.log.complete_and_turn_in('lantern', 'closing'))
        actual = self.log.drain_events()
        self.assertEqual(actual[:-1], pending)
        self.assertEqual(actual[-1]['kind'], 'completed')
        self.assertEqual(actual[-1]['quest_id'], 'lantern')

    def test_completion_is_idempotent_and_does_not_unlock_future_content(self):
        self.before_closing();self.log.drain_events()
        self.assertTrue(self.log.complete_and_turn_in('lantern', 'closing'))
        self.assert_rejected_without_changes('lantern', 'closing')
        self.assertEqual([e['kind'] for e in self.log.drain_events()], ['completed'])
        self.assertEqual(self.log.status('festival'), 'locked')

    def test_completed_snapshot_restores_without_replaying_notifications(self):
        self.before_closing()
        self.assertTrue(self.log.complete_and_turn_in('lantern', 'closing'))
        saved = self.log.to_dict();restored = QuestLog(DEFINITIONS)
        self.assertTrue(restored.restore(saved))
        self.assertEqual(restored.to_dict(), saved)
        self.assertEqual(restored.drain_events(), [])
        self.assertEqual(restored.status('lantern'), 'completed')

    def test_single_objective_quest_can_close_with_default_completion_text(self):
        self.assertTrue(self.log.accept('neighbour'));self.log.drain_events()
        self.assertTrue(self.log.complete_and_turn_in('neighbour', 'visit', 'elira'))
        self.assertEqual(self.log.status('neighbour'), 'completed')
        self.assertEqual(self.log.drain_events(), [{
            'kind': 'completed', 'quest_id': 'neighbour', 'title': 'Neighbour',
            'text': 'Your work here is complete.'}])


if __name__ == '__main__':unittest.main()
