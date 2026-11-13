"""The acknowledged MQ03 emergency, from the survivor's run to safe arrival.

Only the owning quest's stage is durable. Routes, partial conversations,
entrance movement and gathered render actors are reconstructed from that stage.
"""
from __future__ import annotations

import math

import pygame

from social import facing_toward
from overworld_travel import CAVE_SCENES


EMERGENCY_STAGES = frozenset((
    'interruption', 'attack_report', 'departure', 'rejoin_mira',
    'sanctuary_travel', 'sanctuary_arrival_pending'))
from regent_resolution import STAGES as RESOLUTION_STAGES
MIRA_STAGES = frozenset(('sanctuary_travel', 'sanctuary_arrival_pending', *(s for s in RESOLUTION_STAGES if s!='resolution_family')))
RESERVE_ID = 'elden_vale_sanctuary'


def legacy_cave_entered(data):
    """Infer an older journey's cave visit from durable cave facts only.

    This never reads assets, mutates data or substitutes for journey validation.
    A completed MQ03 stage alone is not evidence: older visits could finish
    before the cave existed. Incomplete/invalid owners still face their normal
    validators before the migrated journey can be resumed.
    """
    if not isinstance(data,dict):return False
    player=data.get('player')
    if isinstance(player,dict) and player.get('scene') in (
            'sanctuary_cave','sanctuary_cave_entrance',
            'sanctuary_cave_hollow','sanctuary_cave_depths'):
        return True
    from cave_lesson import CaveLesson
    from sanctuary_cave import SanctuaryCave
    from sanctuary_boss import SanctuaryBoss
    lesson=data.get('cave_lesson')
    if CaveLesson.valid_snapshot(lesson) and lesson['resonance_seen']:return True
    cave=data.get('sanctuary_cave')
    if SanctuaryCave.valid_snapshot(cave) and cave['opened']:return True
    boss=data.get('sanctuary_boss')
    if SanctuaryBoss.valid_snapshot(boss) and (boss['defeated'] or boss['pending'] is not None):return True
    # A completed random encounter also covers pre-lesson cave visitors.
    # Pending encounters require a cave position or acknowledged lesson above.
    counter=data.get('cave_random_encounters')
    fields={'version','identity','rng_state','sequence','threshold','remaining','was_safe','pending'}
    return bool(isinstance(counter,dict) and set(counter)==fields
                and type(counter['version']) is int and counter['version']==1
                and all(type(counter[k]) is int and 0<=counter[k]<=2**32-1
                        for k in ('identity','rng_state','sequence'))
                and counter['sequence']>0 and counter['pending'] is None
                and all(type(counter[k]) in (int,float) and 0<counter[k]<1e7
                        and math.isfinite(counter[k]) for k in ('threshold','remaining'))
                and counter['remaining']<=counter['threshold']
                and (counter['was_safe'] is None or type(counter['was_safe']) is bool))


class RegentEmergency:
    """Own the new post-meal sequence without borrowing the mill's progress."""

    def __init__(self, owner):
        self.owner = owner
        self.game = owner.game
        self.survivor = owner.actors.get('regent_survivor')
        self.reset()

    @property
    def mira(self):return self.game.mill_quest.mira

    def reset(self):
        self._emergency_music_started = False
        self._auto_dialogue = None
        self._staged_world = None
        self._station_goals = {}

    def point(self, name, fallback):return self.owner.points.get(name, fallback)

    def _place(self, actor, world, desired):
        landing = self.owner._landing(actor, desired, world)
        if landing is None:return False
        self.owner._place(actor, world, landing)
        return True

    def _care_stations(self):
        c = self.owner
        return ((c.serene, self.point('serene_aid', (96, 276))),
                (c.tomas, self.point('tomas_aid', (108, 288))),
                (c.driver, self.point('driver_aid', (144, 288))))

    def _station_goal(self, actor, preferred):
        """Resolve a physical station around the player before owning input.

        The player can be standing at a published aid/rest point when the
        discussion ends or an interrupted checkpoint resumes. A clear nearby
        landing is a transient route target, never a reason to move the player
        or overlap them with a newly solid actor.
        """
        world = self.owner.dining
        avoid = world.probe_rect(self.game.player.position) if world is self.game.world else None
        cached = self._station_goals.get(actor)
        if cached is not None and world.can_stand(cached, actor.probe_size, actor, avoid):return cached
        landing = self.owner._landing(actor, preferred, world)
        if landing is not None:self._station_goals[actor] = landing
        return landing

    def setup(self, *, force=False):
        c = self.owner
        c._claim()
        c._setup = c._preps_ready = True
        c._meal_ready = False
        # The driver stays to help Serene and Tomas; only these three visitors
        # become the later escort. Existing actor instances remain authoritative.
        for actor in c.sanctuary_escorts:actor.story_following = True
        c.driver.story_following = False
        for actor, desired in self._care_stations():
            if force:self._place(actor, c.dining, desired)
        if self.survivor is not None:
            if c.stage == 'interruption':
                if force or not self.survivor.story_visible:
                    self._place(self.survivor, c.town,
                                self.point('survivor_start', (384, 372)))
                self.survivor.story_following = True
            else:
                self.survivor.story_following = False
                self._place(self.survivor, c.dining,
                            self.point('survivor_rest', (60, 276)))
        if c.sanctuary_escort_active:
            self._stage_escorts(force=True)
        elif force:
            for actor, prefix in ((c.aldric, 'aldric'), (c.lucan, 'lucan'), (c.clerk, 'clerk')):
                self._place(actor, c.dining, c.points[prefix+'_courtyard'])

    def _care(self, seconds):
        ready = []
        for actor, desired in self._care_stations():
            goal = self._station_goal(actor, desired)
            ready.append(goal is not None
                         and self.owner._travel(actor, self.owner.dining, seconds)
                         and self.owner._move(actor, goal, seconds))
        return all(ready)

    def _settle_survivor(self, seconds):
        if self.survivor is None:return
        c = self.owner
        preferred = self.point('survivor_rest', (60,276))
        avoid = c.dining.probe_rect(self.game.player.position) if c.dining is self.game.world else None
        # Once the player clears the bench approach, the same injured actor can
        # walk the few remaining pixels to it; fixed bench art remains honest.
        if c.dining.can_stand(preferred, self.survivor.probe_size, self.survivor, avoid):
            self._station_goals[self.survivor] = tuple(preferred)
        goal = self._station_goal(self.survivor, preferred)
        if goal is not None and c._travel(self.survivor, c.dining, seconds):
            c._move(self.survivor, goal, seconds, 46)

    def _stage_escorts(self, *, force=False):
        c = self.owner
        world = self.game.world
        if getattr(world, 'is_overworld', False):
            for actor in c.sanctuary_escorts:c._hide(actor)
            self._staged_world = world
            return
        if self._staged_world is world and not force:return
        for index, actor in enumerate(c.sanctuary_escorts):
            offset = ((-28, 16), (28, 16), (-28, 40))[index]
            self._place(actor, world, self.game.player.position+pygame.Vector2(offset))
            actor.story_following = True
            actor.facing = self.game.player.facing
        self._staged_world = world

    def _stage_mira(self):
        if not self.owner.sanctuary_party_active:return False
        if getattr(self.game.world, 'is_overworld', False):return False
        # The passive follower owns Mira after she agrees to come. Its API
        # validates every pixel of a nearby route before publishing the actor.
        stage = getattr(self.game.party_travel, 'stage_companion', None)
        if stage is None:return False
        leader = self.game.player.position
        for radius in (24, 32, 40, 48):
            for dx, dy in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                if stage('mira', leader+pygame.Vector2(dx, dy), facing=self.game.player.facing):return True
        return False

    def on_enter_scene(self, origin, transition):
        world = self.game.world
        if getattr(world, 'is_overworld', False):
            self._stage_escorts(force=True)
            return
        if getattr(origin, 'is_overworld', False):
            self._stage_escorts(force=True)
            self._stage_mira()
            self._arrive()
        elif world.data['id'] in CAVE_SCENES or origin.data['id'] in CAVE_SCENES:
            self._stage_escorts(force=True)
            self._stage_mira()
        else:
            self._staged_world = world

    def on_travel_restored(self):
        self._stage_escorts(force=True)
        self._stage_mira()
        self._arrive()

    def _arrive(self):
        c = self.owner
        if c.stage != 'sanctuary_travel' or self.game.world.data['id'] != RESERVE_ID:return
        if not all(c._world(actor) is self.game.world and actor.story_visible
                   for actor in c.sanctuary_escorts):return
        if not any(getattr(actor, 'identifier', None) == 'mira'
                   for actor in self.game.party_travel.actors()):
            if not self._stage_mira():return
        # Arrival is a persisted handoff, not quest completion or a placeholder
        # cutscene. The existing peaceful reserve and its cave rail stay intact.
        c._transition('sanctuary_arrival_pending')

    def reported(self):
        if self.owner.stage != 'attack_report':return
        self.owner.scene_actions.release()
        self.owner._transition('departure')
        self._auto_dialogue = 'departure'

    def departed(self):
        if self.owner.stage != 'departure':return
        self.owner.scene_actions.release()
        self.owner._transition('rejoin_mira')
        self._staged_world = self.game.world
        for actor in self.owner.sanctuary_escorts:actor.story_following = True

    def mira_joined(self):
        c = self.owner
        if c.stage != 'rejoin_mira':return
        # Membership/event restoration and story progress are checkpointed
        # together. A conflicting party event cannot publish an invalid save.
        c.stage = 'sanctuary_travel'
        if self.game._sync_story_party() is False:
            c.stage = 'rejoin_mira'
            return
        c._transition('sanctuary_travel')

    def _start_mira(self):
        result = self.owner._speak('mira_departure', self.mira_joined)
        if result:self.mira.request_conversation(facing_toward(self.game.player.position-self.mira.position))
        return result

    def target(self):
        c = self.owner
        if self.game.world is c.dining:
            if c.stage == 'attack_report' and c._near(self.point('survivor_rest', (60,276)), 180):return 'attack_report'
            if c.stage == 'departure' and c._near(c.serene.position, 180):return 'departure'
        if (c.stage == 'rejoin_mira' and self.game.world is c.town
                and c._near(self.mira.position, 72)):return 'mira_departure'
        return None

    def try_conversation(self, actor):
        c = self.owner
        target = self.target()
        if target == 'attack_report' and actor in (self.survivor, c.serene, c.aldric):
            return c._speak(target, self.reported)
        if target == 'departure' and actor in (self.survivor, c.serene, c.aldric, c.lucan):
            return c._speak(target, self.departed)
        if actor is self.mira and c.stage == 'rejoin_mira':
            return self._start_mira() if target == 'mira_departure' else False
        keys = {c.serene:'emergency_serene', c.tomas:'emergency_tomas',
                c.driver:'emergency_driver', self.survivor:'survivor_waiting',
                c.aldric:'travel_aldric', c.lucan:'travel_lucan', c.clerk:'travel_page'}
        if actor not in keys:return None
        if c._world(actor) is not self.game.world:return False
        if getattr(getattr(self.game,'sanctuary_arrival',None),'completed',False):
            keys.update({c.aldric:'arrival_aldric_waiting',c.clerk:'arrival_page_waiting'})
            return c._speak(keys[actor])
        key = 'sanctuary_waiting' if c.stage == 'sanctuary_arrival_pending' and actor in c.sanctuary_escorts else keys[actor]
        if key not in c.lines:return False
        return c._speak(key)

    def marker_for(self, identifier):
        if identifier == 'mira_worker':return '!' if self.owner.stage == 'rejoin_mira' else None
        if identifier == 'regent_survivor':return '?' if self.owner.stage == 'attack_report' else None
        if identifier == 'mother_serene':return '?' if self.owner.stage == 'departure' else None
        if identifier in self.owner.actors or identifier == 'tomas':return None
        return NotImplemented

    def interaction_hint(self):
        return {'attack_report':'E: Hear what happened at the Sanctuary',
                'departure':'E: Help with the Sanctuary emergency',
                'mira_departure':'E: Ask Mira to come to the Sanctuary'}.get(self.target(), '')

    def sync_music(self, *, restoring=False):
        """Hold the emergency score until the journey's first cave entry.

        Report pages restart on load, so their silent opening restarts too.
        Later durable stages restore the ongoing score without a dialogue cue.
        Cave entry permanently releases this override, including on Continue
        and later returns to the reserve or Eldenmere.
        """
        if getattr(getattr(self.game,'sanctuary_arrival',None),'cave_entered',False):return
        if self.owner.stage not in EMERGENCY_STAGES:return
        if self.game.combat.active:return
        social = self.game.social
        if (self.owner.stage == 'attack_report'
                and social.script_identifier == 'regent_attack_report'
                and social.page is not None
                and social.page.get('source_line', 0) >= 3):
            self._emergency_music_started = True
        if self.owner.stage not in ('interruption', 'attack_report') or self._emergency_music_started:
            self.game.music.play('something_is_wrong', fade_ms=0 if restoring else 450)
        elif restoring:
            self.game.music.stop()
        else:
            self.game.music.fade_out(700)

    def tracker_text(self):
        if getattr(getattr(self.game,'sanctuary_arrival',None),'completed',False):
            rescue = getattr(self.game, 'sanctuary_rescue', None)
            stage = getattr(rescue, 'stage', 'undiscovered')
            if stage == 'evacuated':
                return 'Join Lucan and Aldric at Elden Vale Sanctuary.'
            if stage in ('greenwell', 'handoff'):
                return 'Speak to Lucan at Greenwell to escort the worker outside.'
            if getattr(getattr(self.game, 'sanctuary_boss', None), 'defeated', False):
                return 'Help Mira and Lucan bring the trapped worker to safety.'
            if not self.game.sanctuary_cave.active:
                return 'Return to Elden Vale Sanctuary and enter the cave.'
            if self.game.cave_lesson.needs_intro:
                return 'Practice Aqua Edge against the cave bats.'
            if stage=='confrontation':
                return 'Confront Vespermaw in the Echo Chamber.'
            return 'Reach the Echo Chamber and search for the worker.'
        return {'interruption':'Someone is hurrying into the house.',
                'attack_report':'Hear the survivor’s report in the dining room.',
                'departure':'Speak with Serene before leaving.',
                'rejoin_mira':'Meet Mira at her workshop before heading to the Sanctuary.',
                'sanctuary_travel':'Reach Elden Vale Sanctuary with Mira and the visitors.',
                'sanctuary_arrival_pending':'The party has reached Elden Vale Sanctuary.'}[self.owner.stage]

    def update(self, seconds):
        c = self.owner
        if c.dialogue:return
        if c.stage == 'interruption':
            if self.game.world is not c.dining:return
            self._care(seconds)
            if self.survivor is None:return
            self.survivor.moving = False
            goal = self._station_goal(self.survivor, self.point('survivor_rest', (60,276)))
            ready = (goal is not None and c._travel(self.survivor, c.dining, seconds)
                     and c._move(self.survivor, goal, seconds, 110))
            if ready:
                self.survivor.story_following = False
                self.survivor.facing = 'front'
                c._transition('attack_report')
                self._auto_dialogue = 'attack_report'
        elif c.sanctuary_escort_active:
            self._care(seconds)
            self._settle_survivor(seconds)
            if not getattr(self.game.world, 'is_overworld', False):
                c._follow_party(seconds)
                self._arrive()
        elif c.stage in ('attack_report', 'departure'):
            self._care(seconds)
            self._settle_survivor(seconds)
        if self._auto_dialogue and not self.game.social.locked and self.game.world is c.dining:
            kind = self._auto_dialogue
            callback = self.reported if kind == 'attack_report' else self.departed
            if c._speak(kind, callback):self._auto_dialogue = None
