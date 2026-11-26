"""Retained character libraries and old saved guard text keep one identity."""
import json
from pathlib import Path
import unittest

from party_state import PartyState
from character_attributes import CharacterAttributes

ROOT = Path(__file__).resolve().parents[1]


class ReplacementTests(unittest.TestCase):
    def test_retained_character_resources_register_iselin_native_art(self):
        for name in ('assets/characters/iselin/actor.json',
                     'assets/characters/iselin/animation.json',
                     'assets/characters/iselin/cinematic/ground/animation.json',
                     'assets/portraits/eldenmere/portraits.json'):
            with self.subTest(file=name):
                self.assertNotIn('aldric', (ROOT/name).read_text().lower())
        actor = json.loads((ROOT/'assets/characters/iselin/actor.json').read_text())
        self.assertEqual(actor['art'], 'assets/characters/iselin/animation.json')
        self.assertEqual(actor['draw_anchor'], [12, 30])
        self.assertEqual(actor['probe_size'], [8, 4])
        manifest = json.loads((ROOT/'assets/characters/iselin/cinematic/ground/animation.json').read_text())
        for direction in ('left', 'left_back', 'back'):
            self.assertEqual(len(manifest['loops']['walk_'+direction]), 16)

    def test_legacy_guard_reason_migrates_identity_without_mutating_source(self):
        party = PartyState(CharacterAttributes())
        self.assertTrue(party.recruit('lucan', temporary=True))
        for old in ('Returned to Aldric.', 'Returned to Aldric after the cave rescue.'):
            party.set_available('lucan', False, old)
            snapshot = party.to_dict()
            self.assertTrue(party.restore(snapshot))
            self.assertNotIn('Aldric', party.to_dict()['members']['lucan']['reason'])
            self.assertEqual(snapshot['members']['lucan']['reason'], old)


if __name__ == '__main__':unittest.main()
