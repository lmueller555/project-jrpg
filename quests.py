"""Quest progress and feedback events, independent of rendering and NPC schedules.

Only the gameplay that finishes a task should call ``complete_objective``.
Walking into a household is not a substitute for its deliveries or practical task.
"""
from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OPENING_QUEST = 'CH01_MQ01'
MILL_QUEST = 'CH01_MQ02'
REGENT_QUEST = 'CH01_MQ03'
LANTERN_QUEST = 'CH01_MQ04'
SAVE_VERSION = 1
STATUSES = frozenset(('locked', 'available', 'active', 'ready', 'completed'))


class QuestLog:
    """A small, ordered quest log with explicit acceptance and reporting."""

    def __init__(self, definitions=None):
        if definitions is None:
            data = json.loads((ROOT/'assets/quests/eldenmere.json').read_text(encoding='utf-8'))
            definitions = {record['id']: record for record in data['quests']}
        self.definitions = deepcopy(definitions)
        self._validate_definitions()
        self.states = {identifier: {'status': 'locked' if record.get('initially_locked') else 'available', 'completed_objectives': []}
                       for identifier, record in self.definitions.items()}
        self._events = []

    def _validate_definitions(self):
        if not isinstance(self.definitions, dict):
            raise ValueError('Quest definitions must be a mapping')
        for identifier, record in self.definitions.items():
            if not isinstance(identifier, str) or not isinstance(record, dict):
                raise ValueError('Each quest needs an identifier and record')
            if not all(isinstance(record.get(key), str) and record[key]
                       for key in ('title', 'summary', 'giver')):
                raise ValueError(f'Incomplete quest definition: {identifier}')
            objectives = record.get('objectives')
            if not isinstance(objectives, list) or not objectives:
                raise ValueError(f'Quest needs objectives: {identifier}')
            if not all(isinstance(item, dict) and isinstance(item.get('id'), str)
                       and item['id'] and isinstance(item.get('text'), str) and item['text']
                       and isinstance(item.get('requires', []), list)
                       and all(isinstance(value, str) for value in item.get('requires', []))
                       for item in objectives):
                raise ValueError(f'Invalid objectives: {identifier}')
            ids = {item['id'] for item in objectives}
            if len(ids) != len(objectives):
                raise ValueError(f'Duplicate objective: {identifier}')
            prerequisites = {item['id']: set(item.get('requires', [])) for item in objectives}
            if any(not requirements <= ids for requirements in prerequisites.values()):
                raise ValueError(f'Unknown prerequisite: {identifier}')
            resolved = set()
            while len(resolved) < len(ids):
                eligible = {key for key, requirements in prerequisites.items()
                            if requirements <= resolved}
                if eligible <= resolved:
                    raise ValueError(f'Cyclic prerequisites: {identifier}')
                resolved.update(eligible)

    def status(self, identifier):
        """Unknown quests remain unavailable rather than creating progress."""
        return self.states.get(identifier, {}).get('status', 'locked')

    def _event(self, kind, identifier, text):
        self._events.append({'kind': kind, 'quest_id': identifier,
                             'title': self.definitions[identifier]['title'], 'text': text})

    def unlock(self, identifier):
        if identifier not in self.definitions or self.status(identifier) != 'locked':return False
        record = self.definitions[identifier]
        if any(self.status(q) != 'completed' for q in record.get('requires_quests', [])):return False
        self.states[identifier]['status'] = 'available'
        self._event('unlocked', identifier, record.get('available_tracker_text', 'A new request is available.'))
        return True

    def accept(self, identifier):
        if self.status(identifier) != 'available':
            return False
        self.states[identifier]['status'] = 'active'
        record = self.definitions[identifier]
        self._event('accepted', identifier,
                    record.get('accept_text', 'Your objectives are in the journal.'))
        return True

    def objective_status(self, identifier, objective_id):
        record = self.definitions.get(identifier)
        if record is None:
            return 'queued'
        objective = next((item for item in record['objectives'] if item['id'] == objective_id), None)
        if objective is None:
            return 'queued'
        state = self.states[identifier]
        done = set(state['completed_objectives'])
        if objective_id in done:
            return 'completed'
        if state['status'] == 'active' and set(objective.get('requires', [])) <= done:
            return 'active'
        return 'queued'

    def complete_objective(self, identifier, objective_id):
        """Record a finished task once; enforce prerequisites before progress."""
        if self.objective_status(identifier, objective_id) != 'active':
            return False
        record = self.definitions[identifier]
        objective = next(item for item in record['objectives'] if item['id'] == objective_id)
        state = self.states[identifier]
        done = set(state['completed_objectives']) | {objective_id}
        # Canonical serialization order does not depend on which later home was first.
        state['completed_objectives'] = [item['id'] for item in record['objectives']
                                         if item['id'] in done]
        self._event('objective', identifier, objective.get('completion_text', objective['text']))
        if len(done) == len(record['objectives']):
            state['status'] = 'ready'
            self._event('ready', identifier, record.get('report_text', 'Return to the quest giver.'))
        return True

    def turn_in(self, identifier, giver_id=None):
        """Reporting is separate from completing the final household task."""
        if self.status(identifier) != 'ready':
            return False
        record = self.definitions[identifier]
        if giver_id is not None and giver_id != record['giver']:
            return False
        self.states[identifier]['status'] = 'completed'
        self._event('completed', identifier,
                    record.get('completion_text', 'Your work here is complete.'))
        return True

    def complete_and_turn_in(self, identifier, objective_id, giver_id=None):
        """Finish the last task and its authored closing scene together.

        A closing scene can both finish an objective and receive its report.
        Check everything before mutation, and emit only the completed notice:
        no saved or visible ready-to-report state can interrupt that ending.
        Omitting the giver follows ``turn_in``'s scripted-report convention.
        """
        if self.objective_status(identifier, objective_id) != 'active':return False
        record = self.definitions[identifier]
        if giver_id is not None and giver_id != record['giver']:return False
        state = self.states[identifier]
        objectives = [item['id'] for item in record['objectives']]
        if set(objectives)-set(state['completed_objectives']) != {objective_id}:return False
        state['completed_objectives'] = objectives
        state['status'] = 'completed'
        self._event('completed', identifier,
                    record.get('completion_text', 'Your work here is complete.'))
        return True

    def marker_for(self, npc_id):
        statuses = [self.status(identifier) for identifier, record in self.definitions.items()
                    if record['giver'] == npc_id]
        if 'ready' in statuses:
            return '?'
        if 'available' in statuses:
            return '!'
        return None

    def tracker_text(self):
        # A ready report takes precedence over unrelated active work.
        for identifier, record in self.definitions.items():
            if self.status(identifier) == 'ready':
                return record.get('report_text', 'Return to the quest giver.')
        for identifier, record in self.definitions.items():
            if self.status(identifier) != 'active':
                continue
            active = [item for item in record['objectives']
                      if self.objective_status(identifier, item['id']) == 'active']
            if len(active) > 1:
                return record.get('parallel_tracker_text', 'Complete the remaining objectives.')
            if active:
                return active[0].get('tracker_text', active[0]['text'])
        for identifier, record in self.definitions.items():
            if self.status(identifier) == 'available' and record.get('available_tracker_text'):
                return record['available_tracker_text']
        return ''

    def drain_events(self):
        result, self._events = self._events, []
        return result

    def to_dict(self):
        return {'version': SAVE_VERSION, 'quests': deepcopy(self.states)}

    def restore(self, data):
        """Validate a complete snapshot before replacing any current progress.

        Saves never carry feedback events. Reloading cannot replay acceptance,
        objective or completion announcements.
        """
        if not isinstance(data, dict) or type(data.get('version')) is not int:
            return False
        if data['version'] != SAVE_VERSION or set(data) != {'version', 'quests'}:
            return False
        states = data.get('quests')
        if not isinstance(states, dict) or not set(states) <= set(self.definitions):return False
        states = deepcopy(states)
        for identifier in set(self.definitions)-set(states):
            # New gated quests may be absent from older version-one saves.
            if not self.definitions[identifier].get('initially_locked'):return False
            states[identifier] = {'status': 'locked', 'completed_objectives': []}
        restored = {}
        for identifier, record in self.definitions.items():
            state = states[identifier]
            if not isinstance(state, dict) or set(state) != {'status', 'completed_objectives'}:
                return False
            status = state['status']
            done = state['completed_objectives']
            # The former MQ02 placeholder could end after only meeting Mira.
            # Preserve that meeting, but expose the newly implemented adventure.
            legacy = record.get('legacy_objectives')
            if legacy and status in ('ready','completed') and done == legacy and len(record['objectives']) > len(legacy):
                status = 'active'
            if not isinstance(status, str) or status not in STATUSES:
                return False
            if not isinstance(done, list) or not all(isinstance(value, str) for value in done):
                return False
            done_set = set(done)
            ids = {item['id'] for item in record['objectives']}
            if len(done_set) != len(done) or not done_set <= ids:
                return False
            if any(item['id'] in done_set and not set(item.get('requires', [])) <= done_set
                   for item in record['objectives']):
                return False
            if status == 'locked' and not record.get('initially_locked'):return False
            if status != 'locked' and any(states.get(q, {}).get('status') != 'completed' for q in record.get('requires_quests', [])):return False
            if status in ('locked', 'available') and done:
                return False
            if status == 'active' and done_set == ids:
                return False
            if status in ('ready', 'completed') and done_set != ids:
                return False
            restored[identifier] = {'status': status,
                                    'completed_objectives': [item['id'] for item in record['objectives']
                                                             if item['id'] in done_set]}
        self.states = restored
        self._events = []
        return True
