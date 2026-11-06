"""Keep Mira's familiar kit, authored script and cooperative MQ02 repair aligned."""
import copy
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from mill_quest import FACTS, REPAIR_FACTS, MillQuest
from inventory import Inventory
from quests import MILL_QUEST, OPENING_QUEST, QuestLog


ROOT = Path(__file__).resolve().parents[1]


class MiraMachinistStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = json.loads((ROOT/'assets/story/mill/scene.json').read_text())
        cls.document = (ROOT/'docs/narrative/game_01/CH01_MQ02.md').read_text()

    def controller(self):
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
        controller.game = SimpleNamespace(quests=quests, inventory=Inventory(),
            social=SimpleNamespace(flags=set(), locked=False, blocked=set(),
                                   start_script=Mock(return_value=True)),
            player=SimpleNamespace(walk_ms=0.0))
        controller.inspected = {'mechanism', 'race'}
        for fact in FACTS:setattr(controller, fact, False)
        controller.reported_to_halden = controller.cups_placed = False
        controller._returning = False
        controller.action = None
        controller._aftermath_recovered = False
        controller._save = Mock()
        controller.mira = Mock()
        controller.upstream = object()
        controller.game.world = controller.upstream
        controller._mira_world = object()
        controller._with_mira = Mock(return_value=True)
        controller._near_object = Mock(return_value=True)
        controller.paths = {}
        controller.lines = self.lines
        return controller

    def test_required_reunion_establishes_the_mill_problem_before_the_early_gift(self):
        reunion = self.lines['reunion']
        self.assertEqual(reunion[0]['speaker'], 'caelan')
        self.assertIn('Halden', reunion[0]['text'])
        self.assertIn('mill has stopped', reunion[0]['text'])
        self.assertTrue(any('water' in line['text'] for line in reunion))
        gift = ' '.join(line['text'] for line in self.lines['gift'])
        for detail in ('birthday', 'grip', 'housing', 'ring', 'Water', 'Nature', 'Fire', 'Ice', 'aether'):
            self.assertIn(detail, gift)
        self.assertTrue(any(line.get('cue') == 'handoff' for line in self.lines['gift']))

    def test_route_weapon_checks_and_both_aftermaths_match_the_machinist_kit(self):
        self.assertEqual(self.lines['warning'], self.lines['reminder_warning'])
        warning = ' '.join(line['text'] for line in self.lines['warning'])
        for detail in ('water', 'launcher', 'Rivet', 'sword sheathed'):
            self.assertIn(detail, warning)
        for name in ('aftermath', 'aftermath_recovered'):
            text = ' '.join(line['text'] for line in self.lines[name])
            self.assertIn('elements', text)
            self.assertIn('sheathed', text)
            self.assertIn('quieter', text)
            self.assertNotIn('better reach', text)
        for name, lines in self.lines.items():
            self.assertNotRegex(' '.join(line['text'] for line in lines), r'(?i)\bspear\w*', name)
        self.assertEqual(self.lines['encounter_intro'][-1], {
            'speaker': 'mira',
            'text': 'Caelan, back towards me. Slowly.',
            'cue': 'mill_return_to_party'})

    def test_full_current_implementation_script_matches_every_runtime_exchange(self):
        blocks = re.findall(r'<!-- mill-script: (\w+) -->\n(.*?)\n<!-- /mill-script -->',
                            self.document, re.DOTALL)
        self.assertEqual(len(blocks), len(self.lines))
        self.assertEqual({name for name, _ in blocks}, set(self.lines))
        for name, text in blocks:
            with self.subTest(exchange=name):
                actual = [(speaker, prose.replace('\\*', '*')) for speaker, prose in
                          re.findall(r'^- \*\*(\w+):\*\* “(.*)”$', text, re.MULTILINE)]
                expected = [(line['speaker'].title(), line['text']) for line in self.lines[name]]
                self.assertEqual(actual, expected)

    def test_launcher_carry_and_stow_recompute_from_the_existing_mill_facts(self):
        controller = self.controller()
        self.assertTrue(controller.mira_armed)
        self.assertFalse(controller.mira_weapon_stowed)
        self.assertTrue(controller._warned())
        self.assertTrue(controller.battle_won())
        self.assertTrue(controller._aftermath_finished())
        controller._record_inspection('intake')
        self.assertFalse(controller.mira_armed)
        self.assertTrue(controller.mira_weapon_stowed)
        self.assertFalse(controller.restored)
        before = copy.deepcopy(controller.to_dict())
        for _ in range(3):
            self.assertTrue(controller.mira_weapon_stowed)
            self.assertFalse(controller.mira_armed)
        self.assertEqual(controller.to_dict(), before)
        self.assertEqual(set(before), {'version', 'inspected', *FACTS})
        for fact in ('prepared', 'spell_done', 'encouraged', 'restored'):
            setattr(controller, fact, True)
        self.assertTrue(controller.mira_armed)
        self.assertFalse(controller.mira_weapon_stowed)
        self.assertTrue(MillQuest.valid_snapshot(controller.to_dict()))

    def test_rivet_does_not_replace_caelans_water_spell_or_miras_repair_work(self):
        controller = self.controller()
        controller._warned();controller.battle_won();controller._aftermath_finished()
        controller._record_inspection('intake')
        controller.prepared = True
        controller._complete('prepare_intake')
        self.assertEqual(controller.stage, 'small_spell')
        controller._encouraged()
        self.assertFalse(controller.encouraged)
        self.assertFalse(controller._start_action('repair'))
        self.assertFalse(controller.restored)
        controller.spell_done = True
        controller._complete('small_spell')
        self.assertFalse(controller._start_action('repair'))
        controller._encouraged()
        controller._with_mira.return_value = False
        self.assertFalse(controller._start_action('repair'))
        controller._with_mira.return_value = True
        self.assertTrue(controller._start_action('repair'))
        self.assertEqual(controller.action, 'repair')
        self.assertFalse(controller.restored)
        self.assertEqual(controller.game.quests.objective_status(MILL_QUEST, 'repair_intake'),
                         'active')

    def test_launcher_retrieval_uses_the_existing_repair_dialogue_and_legacy_branch(self):
        for armed, fought in ((True, False), (True, True), (False, False), (False, True)):
            with self.subTest(armed=armed, fought=fought):
                controller = self.controller()
                if armed:self.assertTrue(controller.game.inventory.add('caelan_gearblade'))
                controller.encounter_cleared = fought
                controller.release_pose = Mock()
                self.assertTrue(controller._speak('repair_done'))
                lines, finished, identifier = controller.game.social.start_script.call_args.args
                self.assertEqual(identifier, 'mill_repair_done')
                source = 'repair_done_combat' if fought else 'repair_done'
                if not armed:source = 'legacy_'+source
                self.assertIs(lines, self.lines[source])
                base = 'repair_done' if armed else 'legacy_repair_done'
                self.assertEqual(lines[:2], self.lines[base][:2])
                self.assertEqual(any('launcher' in line['text'] for line in lines), fought)
                finished()
                controller.release_pose.assert_called_once_with()
                self.assertIsNone(controller.dialogue)

    def test_old_repair_saves_keep_their_progress_without_inventing_rivet_battle_facts(self):
        old = {'version': 1, 'inspected': ['mechanism', 'race', 'intake'],
               **{fact: fact in ('prepared', 'spell_done', 'encouraged') for fact in REPAIR_FACTS}}
        self.assertTrue(MillQuest.valid_snapshot(old))
        migrated = MillQuest.migrate_snapshot(old)
        self.assertTrue(migrated['legacy_bypass'])
        for fact in REPAIR_FACTS:self.assertEqual(migrated[fact], old[fact])
        for fact in ('warned', 'encounter_cleared', 'aftermath_done'):
            self.assertFalse(migrated[fact])
        controller = self.controller()
        controller.inspected = set(migrated['inspected'])
        for fact in FACTS:setattr(controller, fact, migrated[fact])
        self.assertEqual(controller.stage, 'repair_intake')
        self.assertFalse(controller.mira_armed)
        self.assertFalse(controller.mira_weapon_stowed)


if __name__ == '__main__':unittest.main()
