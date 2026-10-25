"""Save I/O preserves an existing journey when replacement fails."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from save_game import MAX_SAVE_BYTES, SaveStore


class SaveStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'nested' / 'journey.json'
        self.store = SaveStore(self.path)

    def test_round_trip_creates_directory_and_preserves_unicode(self):
        payload = {'version': 1, 'quest': 'Elira’s lantern', 'flags': ['accepted']}
        self.assertTrue(self.store.enabled)
        self.assertIsNone(self.store.load())
        self.assertIsNone(self.store.error)
        self.assertTrue(self.store.write(payload))
        self.assertEqual(self.store.load(), payload)
        self.assertIsNone(self.store.error)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_disabled_store_never_accesses_disk(self):
        store = SaveStore(None)
        self.assertFalse(store.enabled)
        with patch('save_game.tempfile.NamedTemporaryFile') as temporary:
            self.assertIsNone(store.load())
            self.assertFalse(store.write({'version': 1}))
            temporary.assert_not_called()
        self.assertIsNone(store.error)

    def test_bad_json_non_dict_and_bad_utf8_are_nonfatal(self):
        self.path.parent.mkdir(parents=True)
        for raw in (b'{incomplete', b'[]', b'null', b'"text"', b'\xff'):
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                self.assertIsNone(self.store.load())
                self.assertIsNotNone(self.store.error)
        self.path.write_text(json.dumps({'version': 1}), encoding='utf-8')
        self.assertEqual(self.store.load(), {'version': 1})
        self.assertIsNone(self.store.error)

    def test_failed_replace_preserves_save_and_removes_temporary_file(self):
        original = {'version': 1, 'progress': 'accepted'}
        self.assertTrue(self.store.write(original))
        before = self.path.read_bytes()
        with patch('save_game.os.replace', side_effect=OSError('disk unavailable')):
            self.assertFalse(self.store.write({'version': 1, 'progress': 'completed'}))
        self.assertIsNotNone(self.store.error)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_invalid_write_payload_does_not_overwrite_existing_save(self):
        original = {'version': 1}
        self.assertTrue(self.store.write(original))
        for payload in ([], {'number': float('nan')}, {'unsupported': object()},
                        {'text': 'x' * MAX_SAVE_BYTES}):
            with self.subTest(payload_type=type(payload).__name__):
                self.assertFalse(self.store.write(payload))
                self.assertIsNotNone(self.store.error)
                self.assertEqual(json.loads(self.path.read_text()), original)
                self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_oversized_or_unreadable_save_is_nonfatal(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b' ' * (MAX_SAVE_BYTES + 1))
        self.assertIsNone(self.store.load())
        self.assertIsNotNone(self.store.error)
        self.path.unlink()
        self.path.mkdir()
        self.assertIsNone(self.store.load())
        self.assertIsNotNone(self.store.error)


if __name__ == '__main__':
    unittest.main()
