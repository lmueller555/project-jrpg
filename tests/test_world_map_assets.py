"""Approval integrity and read-only verification for the classroom map exports."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import build_auratia_world_map as builder


class WorldMapAssetTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        paths = (builder.APPROVAL, builder.SOURCE, builder.OUTPUT/'world_map.png')
        for source in paths:
            destination = self.root/source.relative_to(builder.ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            copyfile(source, destination)
        self.output = self.root/'assets/world/auratia'
        stack = ExitStack()
        self.addCleanup(stack.close)
        for name, value in (
            ('ROOT', self.root),
            ('APPROVAL', self.root/builder.APPROVAL.relative_to(builder.ROOT)),
            ('SOURCE', self.root/builder.SOURCE.relative_to(builder.ROOT)),
            ('OUTPUT', self.output),
        ):
            stack.enter_context(patch.object(builder, name, value))

    def test_export_preserves_approved_pixels_and_uses_recorded_provenance(self):
        approved = self.output/'world_map.png'
        before = approved.read_bytes()
        native = builder.build()
        self.assertEqual(approved.read_bytes(), before)
        self.assertEqual(native.size, (42, 40))
        self.assertEqual(set(native.getchannel('A').tobytes()), {0, 255})
        metadata = json.loads((self.output/'map.json').read_text())
        record = json.loads(builder.APPROVAL.read_text())
        self.assertEqual(metadata['approved_original_filename'],
                         record['approved_original_filename'])
        self.assertEqual(metadata['world_map_sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(metadata['wall_sprite_geography_sha256'], metadata['world_map_sha256'])

    def test_unapproved_art_is_rejected_before_existing_exports_are_changed(self):
        builder.build()
        saved = {path: path.read_bytes() for path in
                 (self.output/'wall_map.png', self.output/'map.json')}
        approved = self.output/'world_map.png'
        approved.write_bytes(approved.read_bytes()+b'unapproved alteration')
        with self.assertRaisesRegex(ValueError, 'artwork differs'):
            builder.build()
        for path, content in saved.items():
            self.assertEqual(path.read_bytes(), content)

    def test_check_never_writes_and_reports_stale_exports(self):
        builder.build()
        with patch.object(Path, 'write_bytes', side_effect=AssertionError('Check wrote a file')):
            builder.build(check=True)
        sprite = self.output/'wall_map.png'
        sprite.write_bytes(b'stale sprite')
        with patch.object(Path, 'write_bytes', side_effect=AssertionError('Check repaired a file')):
            with self.assertRaisesRegex(ValueError, 'Stale world-map export'):
                builder.build(check=True)
        self.assertEqual(sprite.read_bytes(), b'stale sprite')

    def test_classroom_source_cannot_silently_follow_another_map_revision(self):
        record = json.loads(builder.APPROVAL.read_text())
        record['wall_sprite_geography_sha256'] = 'another revision'
        builder.APPROVAL.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'different world-map revision'):
            builder.build()
        self.assertFalse((self.output/'wall_map.png').exists())
