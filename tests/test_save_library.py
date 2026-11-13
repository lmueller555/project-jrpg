"""Slot isolation and crash-safe publication of autosave history."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from save_library import SaveLibrary


def snapshot(campaign='a'*32, marker=0):
    return {'version':1,'player':{'scene':'sanctuary_cave'}, 'marker':marker,
            'save_context':{'campaign':campaign,'playtime':float(marker),'scene_cooldown':0.}}


class SaveLibraryTests(unittest.TestCase):
    def setUp(self):
        folder=TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.root=Path(folder.name)
        self.library=SaveLibrary(self.root/'journey.json')

    def test_ten_manual_slots_remain_independent_of_checkpoints_and_autosaves(self):
        for slot in range(1,11):self.assertTrue(self.library.write_manual(slot,snapshot(marker=slot)))
        self.assertFalse(self.library.write_manual(0,snapshot()))
        self.assertFalse(self.library.write_manual(11,snapshot()))
        for number in range(5):self.assertTrue(self.library.write_auto(snapshot(marker=number),'battle',str(number)))
        for slot in range(1,11):self.assertEqual(self.library.manual(slot)['payload']['marker'],slot)
        self.assertFalse((self.root/'journey.json').exists())
        self.assertEqual([entry['payload']['marker'] for entry in self.library.autos('a'*32)],[4,3,2])
        self.assertEqual(len(list(self.library.root.glob('auto_*.json'))),4)

    def test_failed_manifest_replace_preserves_all_previous_generations(self):
        for number in range(3):self.assertTrue(self.library.write_auto(snapshot(marker=number),'scene',str(number)))
        before={path.name:path.read_bytes() for path in self.library.root.iterdir()}
        import os
        replace=os.replace
        def fail_index(source,destination):
            if Path(destination).name=='auto_'+'a'*32+'.json':raise OSError('disk full')
            return replace(source,destination)
        with patch('save_game.os.replace',side_effect=fail_index):
            self.assertFalse(self.library.write_auto(snapshot(marker=9),'scene','9'))
        self.assertEqual(before,{path.name:path.read_bytes() for path in self.library.root.iterdir()})

    def test_failed_manual_replace_preserves_original_slot(self):
        self.assertTrue(self.library.write_manual(1,snapshot(marker=1)))
        with patch('save_game.os.replace',side_effect=OSError('read only')):
            self.assertFalse(self.library.write_manual(1,snapshot(marker=2)))
        self.assertEqual(self.library.manual(1)['payload']['marker'],1)

    def test_repeated_event_does_not_rotate_history(self):
        self.assertTrue(self.library.write_auto(snapshot(),'battle','receipt'))
        before=list(self.library.root.iterdir())
        self.assertTrue(self.library.write_auto(snapshot(marker=1),'battle','receipt'))
        self.assertEqual(list(self.library.root.iterdir()),before)
        self.assertEqual(len(self.library.autos('a'*32)),1)

    def test_campaign_histories_and_other_libraries_are_separate(self):
        for campaign in ('a'*32,'b'*32):
            for index in range(4):self.assertTrue(self.library.write_auto(snapshot(campaign,index),'scene',str(index)))
        self.assertEqual(self.library.campaigns(),['a'*32,'b'*32])
        other=SaveLibrary(self.root/'playtests'/'CH01_MQ03'/'checkpoint.json')
        self.assertEqual(other.campaigns(),[])
        other.write_auto(snapshot(),'scene','test')
        self.assertEqual(len(self.library.autos('a'*32)),3)

    def test_corrupt_latest_generation_does_not_destroy_earlier_files(self):
        for index in range(3):self.library.write_auto(snapshot(marker=index),'battle',str(index))
        names=self.library._index('a'*32)['files']
        (self.library.root/names[0]).write_text('{broken')
        entries=self.library.autos('a'*32)
        self.assertIsNone(entries[0])
        self.assertEqual([entry['payload']['marker'] for entry in entries[1:]],[1,0])

    def test_invalid_index_paths_cannot_escape_the_library(self):
        self.library._write('auto_'+'a'*32+'.json',{'version':1,'files':['../../journey.json']})
        self.assertEqual(self.library.autos('a'*32),[])
        self.assertFalse(self.library.write_auto(snapshot(),'scene','x'))
        self.assertEqual(self.library.autos('../../outside'),[])

    def test_memory_library_supports_disposable_playtests_without_io(self):
        library=SaveLibrary()
        with patch('save_game.SaveStore.write',side_effect=AssertionError('unexpected disk access')):
            library.write_manual(1,snapshot())
            library.write_auto(snapshot(),'scene','one')
        entry=library.manual(1);entry['payload']['marker']=99
        self.assertEqual(library.manual(1)['payload']['marker'],0)
        self.assertEqual(len(library.autos('a'*32)),1)

    def test_legacy_import_preserves_original_and_never_overwrites_occupied_slots(self):
        original=snapshot();original.pop('save_context')
        before=deepcopy(original)
        self.library.write_manual(1,snapshot())
        self.assertTrue(self.library.migrate_legacy(original))
        self.assertEqual(original,before)
        self.assertEqual(self.library.manual(2)['metadata']['reason'],'legacy')
        self.assertTrue(self.library.migrate_legacy(original))
        self.assertIsNone(self.library.manual(3))

    def test_malformed_metadata_is_not_a_readable_save(self):
        entry=self.library.entry(snapshot(),'manual')
        for field,value in (('playtime',float('nan')),('campaign','../outside'),('location',[])):
            changed=deepcopy(entry);changed['metadata'][field]=value
            self.assertFalse(self.library.valid_entry(changed))

    def test_full_manual_library_archives_legacy_without_overwriting_any_slot(self):
        for slot in range(1,11):self.library.write_manual(slot,snapshot(marker=slot))
        legacy=snapshot();legacy.pop('save_context')
        self.assertTrue(self.library.migrate_legacy(legacy))
        self.assertEqual(len(self.library.archived()),1)
        self.assertTrue(self.library.migrate_legacy(legacy))
        self.assertEqual(len(self.library.archived()),1)
        for slot in range(1,11):self.assertEqual(self.library.manual(slot)['payload']['marker'],slot)

    def test_different_legacy_snapshots_get_distinct_identities(self):
        first=snapshot(marker=1);first.pop('save_context')
        second=snapshot(marker=2);second.pop('save_context')
        self.assertTrue(self.library.migrate_legacy(first))
        self.assertTrue(self.library.migrate_legacy(second))
        self.assertNotEqual(self.library.manual(1)['metadata']['campaign'],
                            self.library.manual(2)['metadata']['campaign'])
