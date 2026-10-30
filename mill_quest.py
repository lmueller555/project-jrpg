"""Mira's river-path encounter, modest successful spell and practical repair.

Durable facts never contain animation clocks or partially read dialogue. One
existing Mira actor accompanies the player; repair props and the wheel read the
same restored milestone.
"""
from collections import deque
import json
from pathlib import Path

import pygame

from halden_visit import point, town_path
from npc_routines import find_path
from npc_following import following_facing, idle_following_facing, reset_following_facing
from quests import MILL_QUEST, REGENT_QUEST, QuestLog
from social import facing_toward

ROOT = Path(__file__).resolve().parent
ART = 'assets/story/mill/'
REPAIR_FACTS = ('prepared', 'spell_done', 'encouraged', 'restored', 'verified', 'resolved')
ENCOUNTER_FACTS = ('warned', 'encounter_cleared', 'aftermath_done', 'legacy_bypass')
FACTS = (*REPAIR_FACTS, *ENCOUNTER_FACTS)
OBJECTIVES = ('meet_mira', 'diagnose_mill', 'prepare_journey', 'secure_trail', 'reach_intake', 'prepare_intake',
              'small_spell', 'repair_intake', 'verify_mill', 'report')


def read(name):return json.loads((ROOT/ART/name).read_text())


class MillQuest:
    def __init__(self, game):
        self.game = game;self.town = game.town
        self.mira = next(n for n in self.town.npcs if n.data['id'] == 'mira_worker')
        self.halden = game.halden_visit.halden
        self.layout = read('layout.json');self.lines = read('scene.json')
        self.points = {**self.layout,
                       'mechanism': self.layout['mill_mechanism'],
                       'race': self.layout['mill_race'],
                       'mill_station': self.layout['mill_return'],
                       'combat_position': self.layout.get('combat_position', [360, 312])}
        self.upstream = game._scene_by_id(self.layout['scene_id'])
        self.bench_position = tuple(self.mira.position)
        self.inspected = set()
        for fact in FACTS:setattr(self, fact, False)
        self.action = None;self.action_time = 0.;self.align_time = 0.
        self.dialogue = None;self.paths = {};self.retry = {}
        self.trail = deque(maxlen=1024);self.last_scene = None
        self._mira_world = self.town;self._player_pose = False;self._mira_pose = False
        self._returning = False
        self._return_dialogue = None
        self._encounter_callback = None
        self._encounter_music_started = False
        self._encounter_phase = None
        self._encounter_elapsed = 0.0
        self._encounter_warning_acknowledged = False
        self._encounter_auto_armed = True
        self._aftermath_recovered = False
        self.cast = read('poses/animation.json')
        sheet = self.town.image(ART+'poses/poses.png')
        self.cast_poses = {name: [sheet.subsurface(f['rect']).copy() for f in rec['frames']]
                           for name, rec in self.cast['animations'].items()}
        self._player_route = None
        self._approach_walk_ms = 0.
        mill = next(e for e in self.town.data['entities'] if e['id'] == 'mill')
        wheel = json.loads((ROOT/'assets/terrain/eldenmere/watermill/mill.json').read_text())['wheel']
        self._wheel_bounds = pygame.Rect(wheel['position'], wheel['size']).move(mill['position'])
        self._race_bounds = pygame.Rect(self.layout['race_bounds_offset']).move(mill['position'])
        self.surface_props = []
        art = read('art.json')
        for record in (art if isinstance(art, list) else art.get('props', [])):
            states = {key: self.town.image(path) for key, path in record['states'].items()}
            prop = {**record, 'states': states, 'surface': next(iter(states.values()))}
            for key in ('animation', 'moving_frames', 'restored_frames'):
                if key in record:prop[key] = [self.town.image(path) for path in record[key]]
            self.surface_props.append(prop)
        for world in (self.town, self.upstream):world.attach_routine_props(self)
        self._sync_props()

    @property
    def active(self):return self.game.quests.status(MILL_QUEST) in ('active', 'ready')
    @property
    def mill_restored(self):return self.restored
    @property
    def locks_player(self):return self.action is not None or self.encounter_cutscene_active
    @property
    def encounter_cutscene_active(self):return getattr(self, '_encounter_phase', None) is not None
    @property
    def encounter_cutscene_phase(self):return getattr(self, '_encounter_phase', None)
    @property
    def encounter_camera_returning(self):return self.encounter_cutscene_phase == 'pan_back'
    @property
    def combat_unlocked(self):return self.encounter_cleared or self.legacy_bypass
    @property
    def mira_armed(self):
        return ((self.active or self._returning) and self._done('meet_mira')
                and not self.legacy_bypass
                and ('intake' not in self.inspected or self.restored))
    @property
    def mira_spear_stowed(self):
        return (self.active and self._done('meet_mira') and not self.legacy_bypass
                and 'intake' in self.inspected and not self.restored)
    @property
    def encounter_pending(self):
        return (self.active and self._done('diagnose_mill') and self.warned
                and not self.combat_unlocked)
    def _at_encounter_approach(self):
        # The encounter now belongs to arrival, before the player walks up the
        # bank. Keep this query for interaction/owner compatibility.
        return self.game.world is self.upstream
    @property
    def encounter_ready(self):
        game = self.game
        return (self.encounter_pending and game.world is self.upstream
                and getattr(self, '_encounter_auto_armed', True)
                and self.encounter_cutscene_phase in (None, 'arrival') and self._with_mira()
                and not self.action and not game.social.locked and not self.dialogue
                and not game.pause.is_open and not game.inventory_ui.is_open
                and not game.quest_ui.journal_open and not game.map_open
                and not game.opening.locks_player and not game.opening_fade
                and not game.transfer_cooldown
                and not game.on_title and game.attributes.current_hp > 0
                and not any(visit.locks_player for visit in game.household_visits if visit is not self)
                and not getattr(getattr(game, 'combat', None), 'active', False))
    @property
    def stage(self):
        if self.resolved:return 'completed'
        if not self.active:return self.game.quests.status(MILL_QUEST)
        if self.verified:return 'report'
        if self.restored:return 'return_mill'
        if not self._done('diagnose_mill'):return 'diagnose'
        if not self.warned and not self.legacy_bypass:return 'warning'
        if not self.combat_unlocked:return 'encounter'
        if self.encounter_cleared and not self.aftermath_done:return 'aftermath'
        if 'intake' not in self.inspected:return 'reach_intake'
        if not self.prepared:return 'prepare_intake'
        if not self.spell_done:return 'small_spell'
        if not self.encouraged:return 'encouragement'
        return 'repair_intake'

    def _done(self, objective):return self.game.quests.objective_status(MILL_QUEST, objective) == 'completed'
    def _complete(self, objective):return self.game.quests.complete_objective(MILL_QUEST, objective)

    def to_dict(self):
        return {'version': 2, 'inspected': [key for key in ('mechanism', 'race', 'intake') if key in self.inspected],
                **{key: bool(getattr(self, key)) for key in FACTS}}

    @staticmethod
    def migrate_snapshot(data):
        """Translate the old completed route without inventing a battle victory."""
        if not isinstance(data, dict):return data
        result = dict(data)
        if (type(result.get('version')) is int and result['version'] == 1
                and set(result) == {'version', 'inspected', *REPAIR_FACTS}
                and isinstance(result['inspected'], list)):
            result.update(version=2, warned=False, encounter_cleared=False,
                          aftermath_done=False, legacy_bypass='intake' in result['inspected'])
        return result

    @staticmethod
    def valid_snapshot(data):
        if not isinstance(data, dict):return False
        # Validate the legacy shape before migration, including the inspection
        # type, so malformed old records cannot become accepted new facts.
        if data.get('version') == 1:
            if (set(data) != {'version', 'inspected', *REPAIR_FACTS}
                    or type(data['version']) is not int
                    or not isinstance(data.get('inspected'), list)):
                return False
            data = MillQuest.migrate_snapshot(data)
        if (not isinstance(data, dict) or set(data) != {'version', 'inspected', *FACTS} or
                type(data['version']) is not int or data['version'] != 2 or
                not isinstance(data['inspected'], list) or
                any(not isinstance(i, str) or i not in ('mechanism', 'race', 'intake') for i in data['inspected']) or
                len(set(data['inspected'])) != len(data['inspected']) or
                any(type(data[key]) is not bool for key in FACTS)):
            return False
        previous = 'intake' in data['inspected']
        for key in REPAIR_FACTS:
            if data[key] and not previous:return False
            previous = data[key]
        diagnosed = {'mechanism', 'race'} <= set(data['inspected'])
        if 'intake' in data['inspected'] and not diagnosed:return False
        if data['legacy_bypass']:
            return ('intake' in data['inspected']
                    and not any(data[key] for key in ('warned', 'encounter_cleared', 'aftermath_done')))
        if data['warned'] and not diagnosed:return False
        if data['encounter_cleared'] and not data['warned']:return False
        if data['aftermath_done'] and not data['encounter_cleared']:return False
        return 'intake' not in data['inspected'] or data['aftermath_done']

    @staticmethod
    def valid_journey(data):
        record = data['mill_quest']
        if not MillQuest.valid_snapshot(record):return False
        record = MillQuest.migrate_snapshot(record)
        quests = QuestLog()
        if not quests.restore(data.get('quests')):return False
        status = quests.status(MILL_QUEST)
        done = lambda name: quests.objective_status(MILL_QUEST, name) == 'completed'
        progress = bool(record['inspected'] or any(record[key] for key in FACTS))
        if progress and status not in ('active', 'ready', 'completed'):return False
        if status in ('active', 'ready', 'completed') and not done('meet_mira'):return False
        if 'intake' in record['inspected'] and not done('diagnose_mill'):return False
        if done('prepare_journey') != (record['warned'] or record['legacy_bypass']):return False
        if done('secure_trail') != (record['encounter_cleared'] or record['legacy_bypass']):return False
        pairs = [('prepared', 'prepare_intake'), ('spell_done', 'small_spell'),
                 ('restored', 'repair_intake'), ('verified', 'verify_mill'), ('resolved', 'report')]
        if any(record[fact] != done(objective) for fact, objective in pairs):return False
        if done('reach_intake') != ('intake' in record['inspected']):return False
        if done('diagnose_mill') and not {'mechanism', 'race'} <= set(record['inspected']):return False
        if record['resolved'] != (status == 'completed'):return False
        return True

    def restore(self, data=None):
        if data is not None and not self.valid_snapshot(data):return False
        self._cancel_encounter()
        old_upstream = (data is not None and data.get('version') == 1
                        and 'intake' not in data['inspected']
                        and self.active and self.game.world is self.upstream)
        data = self.migrate_snapshot(data) if data is not None else None
        self.release_pose();self.action = None;self.action_time = 0.;self.align_time = 0.
        self.dialogue = None;self.paths.clear();self.retry.clear();self.trail.clear();self.last_scene = None
        self._player_route = None
        self._return_dialogue = None;self._encounter_callback = None
        self._encounter_music_started = False
        self._encounter_phase = None
        self._encounter_elapsed = 0.0
        self._encounter_warning_acknowledged = False
        self._encounter_auto_armed = True
        self._aftermath_recovered = False
        self.inspected = set(data['inspected']) if data else set()
        if data:
            for fact in FACTS:setattr(self, fact, data[fact])
        else:
            inferred = {'prepared': self._done('prepare_intake'), 'spell_done': self._done('small_spell'),
                        'encouraged': self._done('repair_intake'), 'restored': self._done('repair_intake'),
                        'verified': self._done('verify_mill'), 'resolved': self.game.quests.status(MILL_QUEST) == 'completed',
                        'warned': False, 'encounter_cleared': False, 'aftermath_done': False,
                        'legacy_bypass': self._done('reach_intake')}
            for fact in FACTS:setattr(self, fact, inferred[fact])
            if self._done('diagnose_mill'):self.inspected.update(('mechanism', 'race'))
            if self._done('reach_intake'):self.inspected.add('intake')
        self.mira.end_conversation();self.mira.quest_mode = self.active
        self.mira.story_following = self.active;self.mira.moving = False
        self._returning = False
        if old_upstream or self.encounter_pending and self.game.world is self.upstream:
            # Old pre-intake checkpoints may stand beyond the new approach.
            # Rejoin that safe approach rather than strand the new objective.
            self.game.player.position.update(self.upstream.data['spawn'])
            self.game.player.facing = 'back'
        if self.active:
            landing = self._near_player()
            if landing is not None:self._place_mira(self.game.world, landing)
        else:
            self._place_mira(self.town, self.bench_position)
            self.mira.quest_mode = False;self.mira.story_following = False
        if self.restored:self._stage_halden(force=True)
        self._sync_props();self._sync_mill()
        return True

    def _save(self):
        self._sync_props();self._sync_mill();self.game.save_progress()

    def _sync_mill(self):
        conclusion = getattr(self.game, 'opening_conclusion', None)
        if conclusion is not None:conclusion._stop_mill()

    def surface_prop_visible(self, prop):return True

    def _sync_props(self):
        base_state = 'restored' if self.restored else 'prepared' if self.prepared else 'blocked'
        for prop in self.surface_props:
            state = 'cleared' if prop['id'] == 'inspection_pool' and self.spell_done else base_state
            frames = None;fraction = 0.
            if self.restored and prop.get('restored_frames'):
                frames = prop['restored_frames'];fraction = (int(self.game.elapsed_ms//180)%len(frames))/len(frames)
            if prop['id'] == 'inspection_pool' and self.action == 'spell':
                frames = prop.get('animation');fraction = max(0., min(1., (self.action_time-.65)/1.2))
            elif prop['id'] == 'intake_screen' and self.action == 'repair':
                frames = prop.get('moving_frames');fraction = max(0., min(1., (self.action_time-.4)/1.6))
            prop['surface'] = (frames[min(len(frames)-1, int(fraction*len(frames)))] if frames else
                               prop['states'].get(state, next(iter(prop['states'].values()))))

    def _near(self, position, radius=18):
        return self.game.player.position.distance_to(position) <= radius

    def interaction_bounds(self, kind):
        """Use the actual object, independently of the actor's work station."""
        if kind in ('mechanism', 'verify'):return self._wheel_bounds.copy()
        if kind == 'race':return self._race_bounds.copy()
        identifier = {'intake': 'intake_screen', 'prepare': 'bypass',
                      'spell_intro': 'inspection_pool', 'repair': 'lever'}[kind]
        prop = next(p for p in self.surface_props if p['id'] == identifier)
        return prop['surface'].get_bounding_rect().move(prop['position'])

    def _object_distance(self, kind):
        target = self.interaction_bounds(kind)
        player = self.game.world.probe_rect(self.game.player.position)
        dx = max(target.left-player.right, player.left-target.right, 0)
        dy = max(target.top-player.bottom, player.top-target.bottom, 0)
        return pygame.Vector2(dx, dy).length()

    def _near_object(self, kind):return self._object_distance(kind) <= 20

    def _with_mira(self, radius=84):
        return self._mira_world is self.game.world and self.mira.position.distance_to(self.game.player.position) <= radius

    def _speak(self, kind, callback=None):
        if self.game.social.locked or self.action:return False
        if self._mira_world is self.game.world:
            self.mira.end_conversation()
            self.mira.facing = facing_toward(self.game.player.position-self.mira.position)
            self.mira.request_conversation(self.mira.facing)
        def finished():
            self.dialogue = None;self.mira.end_conversation()
            if kind == 'repair_done':self.release_pose()
            if callback is not None:callback()
        source = ('aftermath_recovered' if kind == 'aftermath' and self._aftermath_recovered else
                  kind+'_combat' if self.encounter_cleared and kind+'_combat' in self.lines else kind)
        result = self.game.social.start_script(self.lines[source], finished, 'mill_'+kind)
        self.dialogue = kind if result else None
        if result:self.game.social.blocked.add(self.mira)
        return result

    def on_dialogue_cancelled(self, identifier):
        if identifier and identifier.startswith('mill_'):
            self.dialogue = None;self.mira.end_conversation()
            if identifier == 'mill_repair_done':self.release_pose()
            if identifier == 'mill_encounter_intro':
                self._cancel_encounter()

    def can_speak(self, identifier):
        if identifier in ('mira_worker', 'halden') and (self.action or self.encounter_cutscene_active):return False
        return True

    def marker_for(self, identifier):
        if identifier == 'mira_worker':
            return '!' if self.game.quests.status(MILL_QUEST) == 'available' else None
        if identifier == 'halden' and self.active:return '?' if self.verified else None
        return NotImplemented

    def try_conversation(self, actor):
        if self.encounter_cutscene_active:return False
        if actor is self.mira:
            status = self.game.quests.status(MILL_QUEST)
            if status == 'available':return self._speak('reunion', self._recruit)
            if self.active:
                if self.stage == 'warning':return self._speak('warning', self._warned)
                if self.stage == 'aftermath':return self._speak('aftermath', self._aftermath_finished)
                if (self.stage == 'encounter' and self.game.world is self.upstream
                        and self._at_encounter_approach()):
                    return self.begin_encounter(getattr(getattr(self.game, 'combat', None), 'start_mill', None))
                if self.spell_done and not self.encouraged and self.game.world is self.upstream:
                    return self._encouragement()
                reminder = {'diagnose': 'diagnose', 'reach_intake': 'intake',
                            'warning': 'warning', 'encounter': 'encounter',
                            'prepare_intake': 'prepare', 'small_spell': 'spell',
                            'repair_intake': 'repair', 'return_mill': 'verify',
                            'report': 'report'}.get(self.stage)
                return self._speak('reminder_'+reminder if reminder else 'reminder')
            if self.resolved:return self._speak('after')
            return None
        if actor is self.halden:
            if self.active and self.verified and self._with_mira(104):return self._speak('resolution', self._resolve)
            if self.resolved:return self._speak('halden_after')
            if self.active:return self._speak('halden_waiting')
        return None

    def _recruit(self):
        if self.game.world is not self.town or not self._near(self.mira.position, 48):return
        if not self.game.accept_quest(MILL_QUEST):return
        self._complete('meet_mira');self.mira.quest_mode = True;self.mira.story_following = True
        self.mira.moving = False;self.trail.clear();self._save()

    def _target(self):
        if self.action or not self.active:return None
        if self.stage == 'warning' and self._near(self.mira.position, 84):
            return 'warning', 'E: Hear Mira before leaving town'
        if self.stage == 'aftermath' and self._near(self.mira.position, 84):
            return 'aftermath', 'E: Speak with Mira after the encounter'
        if self.game.world is self.town:
            if not self._done('diagnose_mill'):
                candidates = [kind for kind in ('mechanism', 'race') if self._near_object(kind)]
                if candidates:
                    if {'mechanism', 'race'} <= self.inspected:return 'diagnosis', 'E: Discuss the mill with Mira'
                    pending = [kind for kind in candidates if kind not in self.inspected]
                    kind = min(pending or candidates, key=self._object_distance)
                    return kind, 'E: Inspect the mill mechanism' if kind == 'mechanism' else 'E: Inspect the millrace'
            if self.restored and not self.verified and self._near_object('verify'):
                return 'verify', 'E: Watch the working mill with Mira'
            if self.verified and self._near(self.halden.position, 44) and self.halden in self.town.npcs:
                return 'resolution', 'E: Speak with Halden and Mira'
        if self.game.world is self.upstream and self._done('diagnose_mill'):
            if not self.combat_unlocked:
                if self.encounter_pending and self._at_encounter_approach():
                    return 'encounter', 'E: Face the riverbank monster with Mira'
                return None
            if self.encounter_cleared and not self.aftermath_done:return None
            if 'intake' not in self.inspected and self._near_object('intake'):return 'intake', 'E: Inspect the blocked intake'
            if 'intake' in self.inspected and not self.prepared and self._near_object('prepare'):return 'prepare', 'E: Set the bypass with Mira'
            if self.prepared and not self.spell_done and self._near_object('spell_intro'):return 'spell_intro', 'E: Clear the inspection recess with magicks'
            if self.spell_done and not self.encouraged and self._near(self.mira.position, 44) and self._with_mira():return 'encouragement', 'E: Speak with Mira'
            if self.encouraged and not self.restored and self._near_object('repair'):return 'repair', 'E: Help Mira free the intake screen'
        return None

    def interact(self):
        if self.game.social.locked or self.encounter_cutscene_active:return False
        target = self._target()
        if target is None:
            if (self.game.quests.status(MILL_QUEST) == 'available' and self.mira in self.game.world.npcs
                    and self._near(self.mira.position, 36)):
                return self._speak('reunion', self._recruit)
            return False
        if not self._with_mira():return False
        kind = target[0]
        if kind == 'warning':return self._speak('warning', self._warned)
        if kind == 'aftermath':return self._speak('aftermath', self._aftermath_finished)
        if kind == 'encounter':
            return self.begin_encounter(getattr(getattr(self.game, 'combat', None), 'start_mill', None))
        if kind in ('mechanism', 'race', 'intake'):
            return self._speak(kind, lambda: self._record_inspection(kind))
        if kind == 'diagnosis':return self._speak('diagnosis', self._diagnose)
        if kind == 'prepare':return self._speak(kind, lambda: self._start_action('prepare'))
        if kind == 'spell_intro':return self._speak(kind, lambda: self._start_action('spell'))
        if kind == 'encouragement':return self._encouragement()
        if kind == 'repair':return self._speak(kind, lambda: self._start_action('repair'))
        if kind == 'verify':return self._speak(kind, self._verify)
        if kind == 'resolution':return self._speak(kind, self._resolve)
        return False

    def _record_inspection(self, kind):
        if not self.active:return
        if kind == 'intake' and (not self.combat_unlocked or
                                self.encounter_cleared and not self.aftermath_done):return
        self.inspected.add(kind)
        if kind == 'intake':self._complete('reach_intake')
        self._save()
        if {'mechanism', 'race'} <= self.inspected and not self._done('diagnose_mill'):
            self._speak('diagnosis', self._diagnose)

    def _diagnose(self):
        if self.active and {'mechanism', 'race'} <= self.inspected:
            self._complete('diagnose_mill');self._save()
            if not self.warned and not self.legacy_bypass:self._speak('warning', self._warned)

    def _warned(self):
        if not self.active or not self._done('diagnose_mill') or self.warned:return False
        if not self._complete('prepare_journey'):return False
        self.warned = True;self._save()
        return True

    def can_enter_upstream(self):
        """The first departure follows the fully read practical warning."""
        return not self.active or self.warned or self.legacy_bypass

    def begin_encounter(self, on_finished):
        """Stop the arriving party, reveal the threat, then read the exchange."""
        if (not self.encounter_pending or self.game.world is not self.upstream
                or self.encounter_cutscene_phase not in (None, 'arrival')
                or not self._with_mira() or not callable(on_finished)):
            return False
        self._encounter_callback = on_finished
        self._encounter_music_started = False
        self._encounter_auto_armed = False
        self._encounter_warning_acknowledged = False
        self._encounter_phase = 'noticing';self._encounter_elapsed = 0.0
        self._stop_encounter_actors()
        return True

    def _stop_encounter_actors(self):
        """Use the existing standing sprites at their actual arrival positions."""
        player = self.game.player
        player.moving = player.running = False;player.walk_ms = 0.0
        self.mira.moving = False;self.mira.walk_ms = 0.0
        self.paths.pop(self.mira, None)
        threat = pygame.Vector2(self.points['combat_position'])
        player.facing = facing_toward(threat-player.position)
        self.mira.facing = facing_toward(
            player.position-self.mira.position if self.encounter_camera_returning else threat-self.mira.position)

    def _encounter_can_tick(self):
        game = self.game
        return (not game.pause.is_open and not game.inventory_ui.is_open
                and getattr(game, '_music_focused', True))

    def _cancel_encounter(self):
        """Release transient staging without completing dialogue or the fight."""
        was_active = self.encounter_cutscene_active
        self._encounter_phase = None;self._encounter_elapsed = 0.0
        self._encounter_callback = None;self._encounter_warning_acknowledged = False
        social = getattr(self.game, 'social', None)
        if social is not None and getattr(social, 'script_identifier', None) == 'mill_encounter_intro':
            social.cancel_script()
        if getattr(self, 'dialogue', None) == 'encounter_intro':self.dialogue = None
        camera = getattr(self.game, 'camera', None)
        if was_active and camera is not None:camera.return_to_player(duration=0)
        if getattr(self, '_encounter_music_started', False):
            music = getattr(self.game, 'music', None)
            if music is not None:music.play('eldenmere')
        self._encounter_music_started = False

    def _encounter_dialogue_finished(self):
        # A quick acknowledgement never skips the return pan.
        self._encounter_warning_acknowledged = True

    def _begin_encounter_return(self):
        if self.encounter_cutscene_phase != 'conversation':return
        self._encounter_phase = 'pan_back';self._encounter_elapsed = 0.0
        self.game.camera.return_to_player(duration=0 if self.game.audio.reduced_motion else .65)

    def _finish_encounter_cutscene(self):
        callback, self._encounter_callback = self._encounter_callback, None
        self._encounter_phase = None;self._encounter_elapsed = 0.0
        self._encounter_warning_acknowledged = False
        self.mira.end_conversation()
        if not self.encounter_pending or callback is None:return
        music = getattr(self.game, 'music', None)
        self._encounter_music_started = True
        if music is not None:music.play('battle')
        if callback() is False:
            self._encounter_music_started = False
            if music is not None:music.play('eldenmere')

    def _update_encounter_cutscene(self, seconds):
        if not self.encounter_cutscene_active:return
        game = self.game
        if game.world is not self.upstream or not self.encounter_pending:
            self._cancel_encounter();return
        if not self._encounter_can_tick():return
        if self.encounter_cutscene_phase == 'arrival':
            # Caelan waits at the link while the existing Mira follows through
            # it using the ordinary path and authored transition landing.
            game.player.moving = game.player.running = False;game.player.walk_ms = 0.0
            self._follow(seconds)
            return
        if game.audio.reduced_motion:
            if self.encounter_cutscene_phase == 'pan_to_boar' and not game.camera.settled:
                game.camera.focus(self.points['combat_position'], duration=0, anchor=(.5, .34))
            elif self.encounter_camera_returning and not game.camera.settled:
                game.camera.return_to_player(duration=0)
        self._stop_encounter_actors()
        self._encounter_elapsed += max(0.0, seconds)
        if self.encounter_cutscene_phase == 'noticing' and self._encounter_elapsed >= .25:
            duration = 0 if game.audio.reduced_motion else .75
            game.camera.focus(self.points['combat_position'], duration=duration, anchor=(.5, .34))
            self._encounter_phase = 'pan_to_boar';self._encounter_elapsed = 0.0
        elif self.encounter_cutscene_phase == 'pan_to_boar' and game.camera.settled:
            self._encounter_phase = 'conversation';self._encounter_elapsed = 0.0
            if not self._speak('encounter_intro', self._encounter_dialogue_finished):
                self._cancel_encounter()
        elif (self.encounter_cutscene_phase == 'conversation'
              and self._encounter_warning_acknowledged):
            # Script drivers/accessibility input can acknowledge several pages
            # between ticks. The return shot is still mandatory in that case.
            self._begin_encounter_return()
        elif (self.encounter_camera_returning and game.camera.settled
              and self._encounter_warning_acknowledged):
            self._finish_encounter_cutscene()

    def sync_encounter_music(self):
        """The final warning requests a return shot; music waits for arrival."""
        game = self.game
        intro = (self.dialogue == 'encounter_intro'
                 and game.social.script_identifier == 'mill_encounter_intro'
                 and game.social.active)
        if intro and self.encounter_cutscene_phase == 'conversation' and self._encounter_can_tick():
            page = game.social.page
            if page and page.get('cue') == 'mill_return_to_party':
                self._begin_encounter_return()
        elif (self._encounter_music_started and not intro
              and not self.encounter_cutscene_active
              and not getattr(getattr(game, 'combat', None), 'active', False)):
            self._encounter_music_started = False
            music = getattr(game, 'music', None)
            if music is not None:
                music.play('eldenmere')

    def battle_won(self):
        """Commit the encounter fact; its owner saves this with resources/rewards."""
        if (not self.encounter_pending or
                self.game.quests.objective_status(MILL_QUEST, 'secure_trail') != 'active'):
            return False
        if not self._complete('secure_trail'):return False
        self.encounter_cleared = True
        self.game.social.flags.add('CH01_MQ02_ENCOUNTER_CLEARED')
        return True

    def battle_returned(self, outcome, recovered=False):
        """Resume one linear aftermath; no continue/rest choice is introduced."""
        if not self.active:return False
        if not self._with_mira():
            landing = self._near_player()
            if landing is not None:self._place_mira(self.game.world, landing)
        self.mira.moving = False;self.paths.clear();self.trail.clear()
        if outcome == 'victory' and self.encounter_cleared and not self.aftermath_done:
            # The encounter owner already applied first aid to an incapacitated
            # Caelan. This transient prose branch describes that recovery only;
            # it grants no resources and resumes as neutral checks after reload.
            self._aftermath_recovered = bool(recovered)
            self._return_dialogue = 'aftermath'
            result = self._speak('aftermath', self._aftermath_finished)
        elif outcome in ('fled', 'defeat') and self.encounter_pending:
            self._return_dialogue = 'withdrawal' if outcome == 'fled' else 'retry'
            result = self._speak(self._return_dialogue, self._return_finished)
        else:return False
        return result

    def _return_finished(self):self._return_dialogue = None

    def _aftermath_finished(self):
        if not self.encounter_cleared or self.aftermath_done:return False
        self.aftermath_done = True;self._return_dialogue = None;self._save()
        return True

    def _start_action(self, kind):
        if not self.active or self.action or self.game.world is not self.upstream or not self._with_mira():return False
        prerequisites = {'prepare': 'intake' in self.inspected and not self.prepared,
                         'spell': self.prepared and not self.spell_done,
                         'repair': self.encouraged and not self.restored}
        if not prerequisites.get(kind):return False
        if not self._near_object({'prepare': 'prepare', 'spell': 'spell_intro', 'repair': 'repair'}[kind]):return False
        self.action = kind;self.action_time = 0.;self.align_time = 0.;self.mira.end_conversation()
        self._player_route = None;self._approach_walk_ms = self.game.player.walk_ms
        self.paths.pop(self.mira, None);return True

    def _encouragement(self):
        kind = 'encouragement_failed' if self.game.venn_visit.magicks_failed else 'encouragement'
        return self._speak(kind, self._encouraged)

    def _encouraged(self):
        if self.spell_done:self.encouraged = True;self._save()

    def _verify(self):
        if self.restored:
            self.verified = True;self._complete('verify_mill');self._save()

    def _resolve(self):
        if not self.active or not self.verified:return
        self._complete('report')
        if not self.game.quests.turn_in(MILL_QUEST, 'mira_worker'):return
        self.resolved = True;self.game.social.flags.add('CH01_MQ02_COMPLETE')
        self.game.quests.unlock(REGENT_QUEST)
        self.mira.end_conversation();self.mira.story_following = True;self._returning = True
        self._save()

    def interaction_hint(self):
        if self.action:return {'prepare': 'Relieving pressure at the intake…', 'spell': 'Moving the trapped water…', 'repair': 'Freeing the intake screen…'}[self.action]
        target = self._target()
        if target:
            return target[1] if self._with_mira() else 'Wait for Mira to catch up.'
        return ''

    def tracker_text(self):
        if not self.active:return ''
        if self.action:return self.interaction_hint()
        return {'diagnose': 'Inspect the mill mechanism and millrace with Mira.',
                'warning': 'Speak with Mira before taking the north road.',
                'encounter': 'Follow the north trail with Mira. Stay together near the riverbank.',
                'aftermath': 'Speak with Mira, then continue to the intake.',
                'reach_intake': 'Take the north road to the upper millrace with Mira. Inspect the intake.',
                'prepare_intake': 'Set the bypass with Mira.',
                'small_spell': 'Clear the trapped water from the inspection recess.',
                'encouragement': 'Speak with Mira about the successful spell.',
                'repair_intake': 'Help Mira free the intake screen.',
                'return_mill': 'Return to the mill with Mira and check the wheel.',
                'report': 'Speak with Halden and Mira by the mill.'}.get(self.stage, '')

    def journal_detail(self):return self.tracker_text()

    def _worlds(self):return list(self.game.scenes.values())

    def _place_mira(self, world, position):
        reset_following_facing(self.mira)
        for room in self._worlds():
            if self.mira in room.npcs:room.npcs.remove(self.mira)
        world.npcs.append(self.mira);self._mira_world = world
        self.mira.scene_id = world.data['id'];self.mira.position.update(position)
        self.mira.moving = False;self.paths.pop(self.mira, None)

    def _near_player(self):
        world = self.game.world;avoid = world.probe_rect(self.game.player.position).inflate(3, 3)
        for radius in (28, 36, 44, 20, 52):
            for dx, dy in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                p = point(self.game.player.position+pygame.Vector2(dx, dy))
                if world.can_stand(p, self.mira.probe_size, self.mira, avoid):return p
        return None

    def _move(self, goal, seconds, speed=82):
        with following_facing(self.mira, seconds):
            return self._move_path(goal, seconds, speed)

    def _move_path(self, goal, seconds, speed=82):
        actor = self.mira;world = self._mira_world;goal = point(goal);actor.moving = False
        avoid = world.probe_rect(self.game.player.position) if self.game.world is world else None
        if actor.position.distance_to(goal)<.2:self.paths.pop(actor, None);return True
        cached = self.paths.get(actor)
        self.retry[actor] = max(0., self.retry.get(actor, 0.)-seconds)
        if cached is None or cached[0] != goal:
            if self.retry[actor]>0:return False
            route = (town_path(world, actor.position, goal, actor, avoid)
                     if world is self.town and actor.position.distance_to(goal)>200 else
                     find_path(world, actor.position, goal, actor.probe_size, actor, avoid))
            if route is None:self.retry[actor] = .3;return False
            self.paths[actor] = (goal, deque(route));cached = self.paths[actor]
        route = cached[1];budget = max(0., seconds)*speed
        while route and budget>1e-7:
            delta = pygame.Vector2(route[0])-actor.position;distance = delta.length()
            if distance<1e-7:route.popleft();continue
            travel = min(1., budget, distance);candidate = actor.position+delta/distance*travel
            if not world.can_stand(candidate, actor.probe_size, actor, avoid):
                self.paths.pop(actor, None);self.retry[actor] = .15;return False
            actor.position.update(candidate);actor.facing = facing_toward(delta)
            actor.moving = True;actor.walk_ms += travel/speed*1000;budget -= travel
            if travel>=distance-1e-7:route.popleft()
        return actor.position.distance_to(goal)<.2

    def _destination(self, data):
        value = data['destination']
        return self.game._load_scene(ROOT/value) if '/' in value else self.game._scene_by_id(value)

    def _edges(self, world):
        for door in world.doors:yield door.data['anchor'], door.data, self._destination(door.data), door
        for link in world.data.get('world_links', []):
            yield link.get('position', link.get('anchor')), link, self._destination(link), None

    def _travel_to(self, destination, seconds):
        if self._mira_world is destination:return True
        queue = deque([(self._mira_world, None)]);seen = {self._mira_world.path};first = None
        while queue:
            world, edge = queue.popleft()
            if world is destination:first = edge;break
            for anchor, data, room, door in self._edges(world):
                if room.path in seen:continue
                seen.add(room.path);queue.append((room, edge or (anchor, data, room, door)))
        if first is None:return False
        anchor, data, room, door = first
        if not self._move(anchor, seconds):return False
        if door is not None and data.get('requires_open') and door.state != 'open':return False
        avoid = room.probe_rect(self.game.player.position) if room is self.game.world else None
        spawn = data['spawn'];landing = None
        for radius in (0, 16, 24, 32):
            for dx, dy in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = (spawn[0]+dx, spawn[1]+dy)
                if room.can_stand(candidate, self.mira.probe_size, self.mira, avoid):landing = candidate;break
            if landing is not None:break
        if landing is None:return False
        self._place_mira(room, landing)
        arrival = next((d for d in room.doors if d.data['id'] == data.get('arrival_door')), None)
        if arrival is not None:arrival.force_open()
        self.trail.clear();self.last_scene = None
        return room is destination

    def _follow(self, seconds):
        if not self._travel_to(self.game.world, seconds):return
        player = self.game.player.position
        if self.last_scene is not self.game.world:
            self.trail.clear();self.last_scene = self.game.world
        if not self.trail or pygame.Vector2(self.trail[-1]).distance_to(player)>=4:
            if self.trail and pygame.Vector2(self.trail[-1]).distance_to(player)>128:self.trail.clear()
            self.trail.append(point(player))
        distance = self.mira.position.distance_to(player)
        if distance<20:
            landing = self._near_player()
            if landing is not None:self._move(landing, seconds)
            return
        if distance<=36:
            self.mira.moving = False;self.paths.pop(self.mira, None)
            idle_following_facing(self.mira, seconds);return
        goal = self.trail[-1];length = 0.
        for previous in reversed(self.trail):
            length += pygame.Vector2(goal).distance_to(previous);goal = previous
            if length>=30:break
        avoid = self.game.world.probe_rect(player).inflate(2, 2)
        if (self.mira.position.distance_to(goal)<8 and distance>40 or
                not self.game.world.can_stand(goal, self.mira.probe_size, self.mira, avoid)):
            goal = self._near_player()
        if goal is not None:self._move(goal, seconds, 116 if distance>72 else 82)

    def on_enter_scene(self, origin, transition):
        if self.encounter_cutscene_active:self._cancel_encounter()
        self.trail.clear();self.last_scene = None;self.paths.pop(self.mira, None)
        if self.game.world is self.upstream and self.encounter_pending:
            self._encounter_auto_armed = True
            self._encounter_phase = 'arrival';self._encounter_elapsed = 0.0
            self.game.player.moving = self.game.player.running = False
            self.game.player.walk_ms = 0.0
        elif self.game.world is not self.upstream:self._encounter_auto_armed = True

    def _stage_halden(self, force=False):
        if not self.restored:return
        if not force and self.game.world is self.town:return
        conclusion = self.game.opening_conclusion
        if self.halden in self.town.npcs:return
        preferred = self.layout['halden_resolution'];avoid = self.town.probe_rect(self.game.player.position) if self.game.world is self.town else None
        for dx, dy in ((0, 0), (0, 20), (20, 0), (-20, 0)):
            candidate = (preferred[0]+dx, preferred[1]+dy)
            if self.town.can_stand(candidate, self.halden.probe_size, self.halden, avoid):
                conclusion._place(self.halden, self.town, candidate)
                self.halden.end_conversation();self.halden.facing = 'left';return

    def _set_pose(self, actor, image, anchor=(20, 38)):
        actor.story_sprite = image;actor.story_draw_anchor = anchor
        if actor is self.game.player:self._player_pose = True
        else:self._mira_pose = True

    def release_pose(self):
        for actor, flag in ((self.game.player, '_player_pose'), (self.mira, '_mira_pose')):
            if not getattr(self, flag, False):continue
            for name in ('story_sprite', 'story_draw_anchor'):
                if hasattr(actor, name):delattr(actor, name)
            setattr(self, flag, False)

    def _cast_pose(self):
        time = self.action_time
        for name in self.cast.get('sequence', self.cast['animations']):
            record = self.cast['animations'][name];duration = record['duration_ms']/1000
            if time<duration:
                frames = self.cast_poses[name]
                self._set_pose(self.game.player, frames[min(len(frames)-1, int(time/duration*len(frames)))], tuple(self.cast['anchor']))
                return
            time -= duration
        self._set_pose(self.game.player, self.cast_poses[list(self.cast_poses)[-1]][-1], tuple(self.cast['anchor']))

    def _action_update(self, seconds):
        kind = self.action;key = {'prepare': 'bypass', 'spell': 'spell', 'repair': 'lever'}[kind]
        player = self.game.player;goal = pygame.Vector2(self.layout['action_positions'][kind])
        player_ready = player.position.distance_to(goal)<.2
        if not player_ready:
            self._align_player(goal, seconds)
        else:
            player.position.update(goal);player.moving = False;player.facing = 'right'
        mira_ready = self._move(self.layout['mira_'+key], seconds)
        if not player_ready or not mira_ready:
            self.align_time += seconds
            if self.align_time>12:
                self.action = None;self.release_pose();self.mira.moving = False
            return
        self.mira.facing = 'right'
        self.action_time += seconds;time = self.action_time
        if kind == 'spell':self._cast_pose()
        elif kind == 'repair':
            # The compact grip is attached to a real haul rope, never an
            # overextended arm or a tool swinging away from the mechanism.
            self._set_pose(player, self.cast_poses['raise_hand'][-1], tuple(self.cast['anchor']))
        mira_kind = {'prepare': 'bypass', 'spell': 'catch', 'repair': 'lever'}[kind]
        path = ART+'poses/mira_'+mira_kind+'_'+str(min(3, int(time/.35)%4))+'.png'
        if (ROOT/path).exists():self._set_pose(self.mira, self.town.image(path))
        duration = (sum(r['duration_ms'] for r in self.cast['animations'].values())/1000 if kind == 'spell' else 1.2 if kind == 'prepare' else 2.4)
        self._sync_props()
        if time<duration:return
        self.action = None
        if kind != 'repair':self.release_pose()
        self.mira.moving = False
        if kind == 'prepare':self.prepared = True;self._complete('prepare_intake')
        elif kind == 'spell':
            self.spell_done = True;self._complete('small_spell')
            self.game.social.flags.add('CH01_MQ02_SMALL_MAGICK')
        else:
            self.restored = True;self._complete('repair_intake')
            self.game.social.flags.add('CH01_MQ02_MILL_RESTORED');self._stage_halden()
        self._save()
        if kind == 'spell':self._encouragement()
        elif kind == 'prepare':self._speak('prepare_done')
        elif not self._speak('repair_done'):self.release_pose()

    def _holding_repair_pose(self):
        return (self.dialogue == 'repair_done' and self._player_pose and
                self.game.world is self.upstream and not self.game.player.moving and
                self.game.player.position.distance_to(self.layout['action_positions']['repair'])<.2 and
                self.game.social.active and self.game.social.page['source_line'] == 0)

    def _align_player(self, goal, seconds):
        """Walk around the recess and controls from any valid nearby approach."""
        player = self.game.player
        if self._player_route is None:
            route = find_path(self.upstream, player.position, goal, self.upstream.probe_size, None)
            if route is None:return
            self._player_route = deque(route)
        budget = seconds
        while self._player_route and budget>1e-7:
            delta = pygame.Vector2(self._player_route[0])-player.position
            if delta.length()<.04:self._player_route.popleft();continue
            duration = min(budget, delta.length()/72)
            player.walk_ms = self._approach_walk_ms
            before = player.position.copy();player.update(delta, duration, self.upstream)
            self._approach_walk_ms = player.walk_ms
            if player.position == before:self._player_route = None;return
            budget -= duration

    def return_mira_to_bench(self):
        """Resume the existing worker's real walk home after a later scene."""
        if self.active or not self.resolved:return False
        self.mira.end_conversation();self.paths.clear();self.retry.clear()
        self.mira.quest_mode = True;self.mira.story_following = True
        self._returning = True
        return True

    def update(self, seconds):
        self.sync_encounter_music()
        if self.encounter_cutscene_active:
            self._update_encounter_cutscene(seconds)
            self._sync_props();return
        if self.game.map_open or self.game.quest_ui.journal_open:return
        if self.dialogue == 'repair_done' and not self._holding_repair_pose():self.release_pose()
        if self.active:
            self.mira.quest_mode = True;self.mira.story_following = True
            if self.action:self._action_update(seconds)
            elif self.dialogue or self.game.social.resolve_speaker() is self.mira:self.mira.moving = False
            else:self._follow(seconds)
            if self.restored:self._stage_halden()
            if (not self.action and not self.dialogue and not self.game.social.locked
                    and self._with_mira() and not getattr(getattr(self.game, 'combat', None), 'active', False)):
                if self.stage == 'aftermath':self._speak('aftermath', self._aftermath_finished)
                elif self.stage == 'warning' and self.game.world is self.upstream:
                    self._speak('warning', self._warned)
                elif self._return_dialogue:
                    self._speak(self._return_dialogue, self._return_finished)
        elif self._returning:
            if self.dialogue or self.game.social.resolve_speaker() is self.mira:
                self.mira.moving = False
                self._sync_props();return
            if self._travel_to(self.town, seconds) and self._move(self.bench_position, seconds):
                self.mira.quest_mode = False;self.mira.story_following = False;self._returning = False
                self.mira.end_conversation()
        self._sync_props()

    def draw_world(self, canvas, camera):
        repairing = self.action == 'repair' and self.action_time>0
        if (not repairing and not self._holding_repair_pose()) or self.game.world is not self.upstream:return
        # Rope joins the approved chest-height grip to the lever Mira holds.
        hand = self.game.player.position+pygame.Vector2(2, -11)
        grip = self.layout.get('lever_grip', [498, 374])
        a = (round(hand.x)-camera[0], round(hand.y)-camera[1])
        b = (round(grip[0])-camera[0], round(grip[1])-camera[1])
        pygame.draw.line(canvas, '#836347', a, b, 1)
