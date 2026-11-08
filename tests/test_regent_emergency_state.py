"""MQ03 save versions distinguish acknowledged emergency facts from old visits."""
from copy import deepcopy
import unittest

from quests import OPENING_QUEST, MILL_QUEST, REGENT_QUEST, LANTERN_QUEST, QuestLog
from regent_quest import RegentQuest


def journey(stage, version=3, *, completed=False):
    quests = QuestLog()
    for identifier in (OPENING_QUEST, MILL_QUEST):
        if quests.status(identifier) == 'locked':quests.unlock(identifier)
        quests.accept(identifier)
        for objective in quests.definitions[identifier]['objectives']:
            quests.complete_objective(identifier, objective['id'])
        quests.turn_in(identifier, quests.definitions[identifier]['giver'])
    quests.unlock(REGENT_QUEST)
    quests.accept(REGENT_QUEST)
    objectives = quests.definitions[REGENT_QUEST]['objectives']
    for objective in objectives[:4 if completed else 3]:
        quests.complete_objective(REGENT_QUEST, objective['id'])
    if completed:quests.turn_in(REGENT_QUEST, quests.definitions[REGENT_QUEST]['giver'])
    return {'regent_quest': {'version': version, 'stage': stage}, 'quests': quests.to_dict()}


class RegentEmergencyStateTests(unittest.TestCase):
    def test_older_unfinished_discussion_resumes_before_new_facts(self):
        for version in (1, 2):
            with self.subTest(version=version):
                record = {'version': version, 'stage': 'discussion'}
                original = deepcopy(record)
                self.assertEqual(RegentQuest.migrate_snapshot(record),
                                 {'version': 3, 'stage': 'hosted'})
                self.assertEqual(record, original)
                self.assertFalse(RegentQuest.sanctuary_party_snapshot(record))
                self.assertTrue(RegentQuest.valid_journey(journey('discussion', version)))

    def test_old_completed_visits_stay_completed_without_an_invented_new_outing(self):
        for version in (1, 2):
            with self.subTest(version=version):
                data = journey('done', version, completed=True)
                self.assertTrue(RegentQuest.valid_journey(data))
                self.assertEqual(RegentQuest.migrate_snapshot(data['regent_quest']),
                                 {'version': 3, 'stage': 'done'})
                self.assertFalse(RegentQuest.sanctuary_party_snapshot(data['regent_quest']))
                self.assertNotIn('party', data)

    def test_removed_roadside_stages_only_migrate_to_the_original_household_escort(self):
        for stage in ('met', 'dispute', 'releasing', 'escorting'):
            with self.subTest(stage=stage):
                migrated = RegentQuest.migrate_snapshot({'version': 1, 'stage': stage})
                self.assertEqual(migrated, {'version': 3, 'stage': 'escorting'})
                self.assertFalse(RegentQuest.sanctuary_party_snapshot(migrated))

    def test_new_emergency_checkpoints_never_complete_the_last_objective_or_unlock_lanterns(self):
        for stage in ('interruption', 'attack_report', 'departure', 'rejoin_mira',
                      'sanctuary_travel', 'sanctuary_arrival_pending'):
            with self.subTest(stage=stage):
                data = journey(stage)
                if stage in ('sanctuary_travel', 'sanctuary_arrival_pending'):
                    # The complete party payload is validated atomically by
                    # Game; this controller also requires its presence.
                    data['party'] = {}
                self.assertTrue(RegentQuest.valid_journey(data))
                restored = QuestLog()
                self.assertTrue(restored.restore(data['quests']))
                self.assertEqual(restored.status(REGENT_QUEST), 'active')
                self.assertEqual(restored.objective_status(REGENT_QUEST, 'speak_serene'), 'active')
                self.assertEqual(restored.status(LANTERN_QUEST), 'locked')
                corrupted = journey(stage, completed=True)
                corrupted['party'] = {}
                self.assertFalse(RegentQuest.valid_journey(corrupted))

    def test_mira_trip_requires_a_party_snapshot_and_cannot_come_from_old_schema(self):
        for stage in ('sanctuary_travel', 'sanctuary_arrival_pending'):
            with self.subTest(stage=stage):
                self.assertFalse(RegentQuest.valid_journey(journey(stage)))
                self.assertTrue(RegentQuest.sanctuary_party_snapshot({'version': 3, 'stage': stage}))
                for version in (1, 2):
                    self.assertFalse(RegentQuest.valid_snapshot({'version': version, 'stage': stage}))

    def test_invalid_versions_extra_state_and_unknown_stages_are_rejected(self):
        for record in ({'version': True, 'stage': 'hosted'},
                       {'version': 3.0, 'stage': 'hosted'},
                       {'version': 4, 'stage': 'hosted'},
                       {'version': 3, 'stage': 'discussion'},
                       {'version': 3, 'stage': 'sanctuary_cutscene_finished'},
                       {'version': 3, 'stage': 'attack_report', 'report_read': True}):
            with self.subTest(record=record):self.assertFalse(RegentQuest.valid_snapshot(record))


if __name__ == '__main__':unittest.main()
