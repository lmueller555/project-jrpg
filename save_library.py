"""Manual slots and immutable autosave generations, separate from checkpoints."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import re
import math
import json
from hashlib import sha256
from uuid import uuid4

from save_game import SaveStore
from leveling import level_for_total_xp

MANUAL_SLOTS = 10
AUTO_GENERATIONS = 3
CAMPAIGN = re.compile(r'[a-f0-9]{32}\Z')


class SaveLibrary:
    def __init__(self, checkpoint=None):
        checkpoint = Path(checkpoint) if checkpoint is not None else None
        self.root = checkpoint.parent/(checkpoint.stem+'_slots') if checkpoint else None
        self.memory = {}
        self.error = None

    def _read(self, name):
        if self.root is None:
            self.error=None
            return deepcopy(self.memory.get(name))
        store = SaveStore(self.root/name)
        result = store.load()
        self.error = store.error
        return result

    def _write(self, name, data):
        if self.root is None:
            self.memory[name] = deepcopy(data)
            self.error = None
            return True
        store = SaveStore(self.root/name)
        result = store.write(data)
        self.error = store.error
        return result

    @staticmethod
    def valid_entry(entry):
        if not isinstance(entry,dict) or type(entry.get('version')) is not int or entry['version']!=1:return False
        metadata,payload=entry.get('metadata'),entry.get('payload')
        if not isinstance(metadata,dict) or not isinstance(payload,dict):return False
        campaign=metadata.get('campaign')
        playtime=metadata.get('playtime')
        return (isinstance(campaign,str) and CAMPAIGN.fullmatch(campaign) is not None
                and isinstance(metadata.get('saved_at'),str) and len(metadata['saved_at'])<=64
                and type(playtime) in (int,float) and math.isfinite(playtime) and 0<=playtime<=1e10
                and isinstance(metadata.get('location'),str) and len(metadata['location'])<=128
                and isinstance(metadata.get('reason'),str)
                and isinstance(metadata.get('quest',''),str) and len(metadata.get('quest',''))<=256
                and isinstance(payload.get('save_context'),dict)
                and payload['save_context'].get('campaign')==campaign)


    @staticmethod
    def entry(payload, reason, summary=None):
        context = payload['save_context']
        summary = summary or {}
        return {'version': 1, 'metadata': {
            'campaign': context['campaign'], 'playtime': context['playtime'],
            'saved_at': datetime.now(timezone.utc).isoformat(), 'reason': reason,
            'location': summary.get('location', payload['player']['scene']),
            'quest': summary.get('quest',''),
            'levels': {key: level_for_total_xp(value['total_xp']) for key, value in
                       payload.get('character_levels', {}).get('characters', {}).items()
                       if isinstance(value, dict) and 'total_xp' in value},
        }, 'payload': deepcopy(payload)}

    def occupied(self, slot):
        name = f'manual_{slot:02}.json'
        return name in self.memory if self.root is None else (self.root/name).exists()

    def manual(self, slot):
        if type(slot) is not int or not 1 <= slot <= MANUAL_SLOTS:return None
        result = self._read(f'manual_{slot:02}.json')
        return result if self.valid_entry(result) else None

    def write_manual(self, slot, payload, *, reason='manual', summary=None):
        if type(slot) is not int or not 1 <= slot <= MANUAL_SLOTS:return False
        return self._write(f'manual_{slot:02}.json', self.entry(payload, reason, summary))

    def _index(self, campaign):
        if not isinstance(campaign, str) or not CAMPAIGN.fullmatch(campaign):return None
        data = self._read(f'auto_{campaign}.json')
        if data is None:
            return None if self.error else {'version': 1, 'files': []}
        files = data.get('files')
        if (type(data.get('version')) is not int or data['version'] != 1 or not isinstance(files, list)
                or len(files) > AUTO_GENERATIONS
                or any(not isinstance(name, str) or not re.fullmatch(
                    rf'auto_{campaign}_[a-f0-9]{{32}}\.json', name) for name in files)):
            self.error = 'The autosave history could not be read.'
            return None
        return data

    def autos(self, campaign):
        index = self._index(campaign)
        if index is None:return []
        return [self._read(name) for name in index['files']]

    def write_auto(self, payload, reason, event, *, summary=None):
        campaign = payload['save_context']['campaign']
        index = self._index(campaign)
        if index is None:return False
        prior = [self._read(name) for name in index['files']]
        if any(self.valid_entry(entry) and entry['metadata'].get('event') == event for entry in prior):
            return True
        entry = self.entry(payload, reason, summary)
        entry['metadata']['event'] = event
        name = f'auto_{campaign}_{uuid4().hex}.json'
        if not self._write(name, entry):return False
        files = [name, *index['files']][:AUTO_GENERATIONS]
        if not self._write(f'auto_{campaign}.json', {'version': 1, 'files': files}):
            self._remove(name)
            return False
        for old in index['files'][AUTO_GENERATIONS-1:]:self._remove(old)
        return True

    def _remove(self, name):
        if self.root is None:self.memory.pop(name, None)
        else:
            try:(self.root/name).unlink(missing_ok=True)
            except OSError:pass

    def campaigns(self):
        names = self.memory if self.root is None else (
            [path.name for path in self.root.glob('auto_*.json')] if self.root.exists() else [])
        return sorted({match.group(1) for name in names
                       if (match := re.fullmatch(r'auto_([a-f0-9]{32})\.json', name))})

    def archive_checkpoint(self, payload):
        campaign=payload['save_context']['campaign']
        return self._write(f'resume_{campaign}.json',self.entry(payload,'resume'))

    def archived(self):
        names=self.memory if self.root is None else (
            [path.name for path in self.root.glob('resume_*.json')] if self.root.exists() else [])
        entries=[]
        for name in names:
            if re.fullmatch(r'resume_[a-f0-9]{32}\.json',name):
                entry=self._read(name)
                if self.valid_entry(entry):entries.append(entry)
        return entries

    @staticmethod
    def legacy_context(payload):
        identity=sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()[:32]
        return {'campaign':identity,'playtime':0.,'scene_cooldown':0.}

    def migrate_legacy(self, payload):
        if payload is None or 'save_context' in payload:return True
        context=self.legacy_context(payload)
        for slot in range(1, MANUAL_SLOTS+1):
            entry=self.manual(slot)
            if entry and entry['metadata'].get('reason')=='legacy' and entry['metadata']['campaign']==context['campaign']:
                return True
        copied=deepcopy(payload)
        copied['save_context']=context
        slot=next((slot for slot in range(1,MANUAL_SLOTS+1) if not self.occupied(slot)),None)
        if slot is None:return self.archive_checkpoint(copied)
        return self.write_manual(slot,copied,reason='legacy')
