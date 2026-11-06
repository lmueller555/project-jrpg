"""Character/lore boundaries and compatibility of the revised sanctuary visit."""
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import test_regent_quest as regent_tests
from regent_quest import RegentQuest
from quests import REGENT_QUEST, LANTERN_QUEST

ROOT = Path(__file__).resolve().parents[1]


class RevisedVisitTests(unittest.TestCase):
    def setUp(self):
        self.driver = regent_tests.RegentQuestTests()
        self.driver.setUp()
        self.addCleanup(self.driver.doCleanups)
        self.addCleanup(self.driver.tearDown)
        self.g = self.driver.g;self.quest = self.g.regent_quest

    def test_new_version_cannot_reintroduce_removed_cart_stages(self):
        for stage in ('met', 'dispute', 'releasing'):
            self.assertTrue(RegentQuest.valid_snapshot({'version': 1, 'stage': stage}))
            self.assertFalse(RegentQuest.valid_snapshot({'version': 2, 'stage': stage}))
        for record in ({'version': True, 'stage': 'idle'},
                       {'version': 2, 'stage': 'escorting', 'cart_released': True},
                       {'version': 3, 'stage': 'done'}):
            self.assertFalse(RegentQuest.valid_snapshot(record))

    def test_lucan_has_approved_directional_motion_and_a_matching_dialogue_portrait(self):
        lucan = self.quest.lucan
        self.assertEqual(lucan.data['id'], 'lucan')
        self.assertEqual(set(lucan.walks), {'front', 'back', 'left', 'right'})
        self.assertTrue(all(len(frames) >= 4 for frames in lucan.walks.values()))
        self.assertEqual(self.quest.party[-1], lucan)
        profile = self.g.social.data['speakers']['lucan']
        self.assertIn('Lucan', profile['name'])
        self.assertIn('lucan', profile['portrait'].lower())
        self.assertIn(profile['portrait'], self.g.social.portraits)

    def test_main_dialogue_establishes_guard_royal_role_and_the_whole_reserve(self):
        scenes = self.quest.lines
        self.assertTrue({'preparations', 'arrival', 'welcome', 'discussion', 'aftermath'} <= set(scenes))
        self.assertFalse(any('dispute' in key or 'foreman' in key or 'venn' in key for key in scenes))
        arrival = ' '.join(line['text'] for line in scenes['arrival'])
        self.assertIn('Lucan Rooke', arrival)
        self.assertIn('my guard', arrival)
        self.assertIn('early birthday present', arrival.lower())
        discussion = ' '.join(line['text'] for line in scenes['discussion'])
        self.assertIn('monarch', discussion)
        self.assertIn('brother', discussion)
        self.assertIn('Aether gathers there naturally', discussion)
        self.assertIn('remembrance', discussion)
        self.assertIn('cannot endorse', discussion)
        self.assertIn('inspect', discussion.lower())
        for line in (line for lines in scenes.values() for line in lines):
            self.assertEqual(line['text'].count('*') % 2, 0, line['text'])

    def test_revised_visit_preserves_player_progress_and_does_not_recruit_the_guard(self):
        abilities = self.g.character_abilities.to_dict()
        inventory = self.g.inventory.to_dict()
        self.driver.complete()
        self.assertEqual(self.g.character_abilities.to_dict(), abilities)
        self.assertEqual(self.g.inventory.to_dict(), inventory)
        self.assertIn(self.quest.lucan, self.quest.party)
        self.assertIs(self.quest._world(self.quest.lucan), self.quest.dining)
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'completed')
        self.assertEqual(self.g.quests.status(LANTERN_QUEST), 'available')
        self.assertFalse(any('AUTHORIZ' in flag.upper() or 'EXCAVATION_STARTED' in flag.upper()
                             for flag in self.g.social.flags))

    def test_legacy_unarmed_arrival_does_not_invent_the_gift_or_homecoming(self):
        self.assertEqual(self.g.inventory.quantity('caelan_gearblade'), 0)
        self.driver.assign();self.driver.at('arrival');self.driver.interact('arrival')
        actual = self.g.social._source_lines
        text = ' '.join(line['text'] for line in actual)
        self.assertNotIn('birthday', text)
        self.assertNotIn('Mira made it', text)
        self.assertNotIn('finished setting the table', text)
        self.assertFalse(any(line.get('cue') == 'caelan_scabbard' for line in actual))
        self.assertIn('Lucan Rooke', text)
        self.assertNotEqual(self.g.quests.objective_status(REGENT_QUEST, 'meet_visitors'), 'completed')
        self.driver.read_current()
        self.assertEqual(self.quest.stage, 'escorting')

    def test_older_owned_blade_keeps_its_intro_without_claiming_the_new_homecoming(self):
        self.assertTrue(self.g.character_abilities.acquire_weapon('caelan', 'caelan_gearblade'))
        self.assertFalse(self.g.mill_quest.cups_placed)
        self.driver.assign();self.driver.at('arrival');self.driver.interact('arrival')
        actual = self.g.social._source_lines
        text = ' '.join(line['text'] for line in actual)
        self.assertIn('early birthday present', text.lower())
        self.assertNotIn('finished setting the table', text)
        self.assertTrue(any(line.get('cue') == 'caelan_scabbard' for line in actual))
        self.g.social.cancel()
        self.assertEqual(self.quest.stage, 'assigned')

    def test_dialogue_does_not_disclose_the_hidden_planetary_history(self):
        text = ' '.join(line['text'] for lines in self.quest.lines.values() for line in lines)
        for disclosure in ('Aethersphere', 'sleeping Ancients', 'cosmic catastrophe',
                           'protective barrier', 'Queen Isolde', 'House Maroven'):
            self.assertNotIn(disclosure, text)
        self.assertNotIn('hire note', text)
        self.assertNotIn('Return the cart', text)

    def test_narrative_script_contains_the_exact_runtime_main_dialogue(self):
        script = (ROOT/'docs/narrative/game_01/CH01_MQ03.md').read_text().replace('\\*', '*')
        for name in ('preparations', 'arrival', 'welcome', 'discussion', 'aftermath'):
            for line in self.quest.lines[name]:
                self.assertIn(line['text'], script, (name, line['text']))


if __name__ == '__main__':unittest.main()
