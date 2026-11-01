"""Continue availability and restoration must agree on the gardener loan."""
import copy
from unittest import TestCase

from garden_orchard import empty_state as garden_state
from overworld_travel import OverworldTravel, REGION_ID, WORLD_ID
from purposeful_wildlife import WORKER_HOME, empty_state, valid_context


class WildlifeJourneyValidationTests(TestCase):
    def journey(self):
        garden = garden_state()
        garden['gardener'].update(phase='rest', read=True, position=list(WORKER_HOME))
        wildlife = empty_state()
        wildlife['vignette']['phase'] = 'visit'
        return {'player': {'scene': WORLD_ID}, 'overworld': {
            'version': 1, 'region': REGION_ID,
            'garden_orchard': garden, 'wildlife': wildlife}}

    def test_active_loan_is_accepted_only_when_restore_context_is_valid(self):
        record = self.journey()
        self.assertTrue(OverworldTravel.valid_journey(record))
        record['overworld']['garden_orchard']['gardener']['position'] = [-526, 1190]
        self.assertFalse(valid_context(record['overworld']['wildlife'],
                                      record['overworld']['garden_orchard']))
        self.assertFalse(OverworldTravel.valid_journey(record))

    def test_active_loan_cannot_borrow_unfinished_or_missing_garden(self):
        original = self.journey()
        for garden in (None, garden_state()):
            record = copy.deepcopy(original)
            if garden is None:
                del record['overworld']['garden_orchard']
            else:
                record['overworld']['garden_orchard'] = garden
            self.assertFalse(OverworldTravel.valid_journey(record))

    def test_legacy_journey_without_wildlife_remains_loadable(self):
        record = self.journey()
        del record['overworld']['wildlife']
        self.assertTrue(OverworldTravel.valid_journey(record))
