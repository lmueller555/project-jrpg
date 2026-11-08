"""Import old room checkpoints without replaying rewards or changing resources."""
import copy
import unittest

from sanctuary_cave import (CAVE_SCENES, LEGACY_SCENES, SCENE_ID, SCENE_FILES,
                            SanctuaryCave, migrate_legacy_cave)


LANDINGS = {'sanctuary_cave_entrance': [288, 1660],
            'sanctuary_cave_hollow': [1100, 1200],
            'sanctuary_cave_depths': [1680, 970]}


class CaveMigrationTests(unittest.TestCase):
    def test_each_legacy_room_keeps_receipts_story_and_resources(self):
        for scene in LEGACY_SCENES:
            with self.subTest(scene=scene):
                saved = {'player': {'scene': scene, 'position': [240, 180], 'facing': 'left'},
                         'sanctuary_cave': {'version': 1, 'opened': ['cave_vein_cache']},
                         'inventory': {'items': {'aether_sapphire': 1}},
                         'party': {'current_hp': 19, 'current_mp': 3},
                         'regent_quest': {'stage': 'sanctuary_arrival_pending'}}
                before = copy.deepcopy(saved)
                result = migrate_legacy_cave(saved, LANDINGS)
                self.assertEqual(saved, before)
                self.assertEqual(result['player'], {'scene': SCENE_ID,
                                                    'position': LANDINGS[scene], 'facing': 'left'})
                for key in saved.keys()-{'player'}:
                    self.assertEqual(result[key], saved[key])
                result['sanctuary_cave']['opened'].clear()
                self.assertEqual(saved['sanctuary_cave']['opened'], ['cave_vein_cache'])

    def test_only_continuous_map_is_registered_for_play(self):
        self.assertEqual(CAVE_SCENES, frozenset((SCENE_ID,)))
        self.assertEqual(set(SCENE_FILES), {SCENE_ID})
        self.assertFalse(CAVE_SCENES & LEGACY_SCENES)

    def test_new_checkpoints_keep_exact_position_without_reading_map(self):
        saved = {'player': {'scene': SCENE_ID, 'position': [123.5, 456.25]}}
        self.assertIs(migrate_legacy_cave(saved, {}), saved)
        for data in ({}, {'player': None}, {'player': {'scene': []}},
                     {'player': {'scene': 'eldenmere', 'position': [12, 34]}}):
            self.assertIs(migrate_legacy_cave(data, {}), data)

    def test_invalid_legacy_coordinates_are_rejected_instead_of_repaired(self):
        for position in (None, [], [True, 2], [float('inf'), 2], [0, float('nan')],
                         [1e7, 2], [12, 34, 56]):
            with self.subTest(position=position):
                saved = {'player': {'scene': 'sanctuary_cave_hollow', 'position': position}}
                with self.assertRaises(ValueError):migrate_legacy_cave(saved, LANDINGS)

    def test_missing_receipts_remain_invalid_after_migration(self):
        saved = {'player': {'scene': 'sanctuary_cave_depths', 'position': [20, 30]}}
        migrated = migrate_legacy_cave(saved, LANDINGS)
        self.assertFalse(SanctuaryCave.valid_journey(migrated))
        self.assertNotIn('sanctuary_cave', migrated)

    def test_missing_or_invalid_authored_landing_cannot_import_checkpoint(self):
        saved = {'player': {'scene': 'sanctuary_cave_hollow', 'position': [20, 30]}}
        for landings in ({}, {'sanctuary_cave_hollow': [1, float('inf')]},
                         {'sanctuary_cave_hollow': [True, 20]}):
            with self.subTest(landings=landings):
                with self.assertRaises(ValueError):migrate_legacy_cave(saved, landings)


if __name__ == '__main__':unittest.main()
