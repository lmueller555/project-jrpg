"""The Sanctuary confluence and Caelan's one-time Aqua Edge discovery.

Encounter tickets own the battle seed and formation. This controller owns only
story milestones and a deferred retry, so fleeing never rerolls the lesson and
preparing at the Sanctuary bed never requires replaying its dialogue.
"""
from __future__ import annotations

import math

import pygame

SCENE_ID = 'sanctuary_cave'
SCRIPT_ID = 'cave_blue_resonance'
FIELDS = {'version', 'resonance_seen', 'battle_cleared', 'deferred'}


class CaveLesson:
    def __init__(self, game):
        self.game = game
        self.resonance_seen = self.battle_cleared = self.deferred = False
        self._elapsed = 0.
        self._glowing = False
        self._retry_offered = False
        self._focus = None
        self._pose_prior = None

    @property
    def active(self):return self.game.world.data.get('id') == SCENE_ID

    @property
    def needs_intro(self):return not self.battle_cleared

    @property
    def locks_player(self):return self.glowing

    @property
    def glowing(self):
        return self._glowing and self.active and self.game.social.script_identifier == SCRIPT_ID

    @property
    def blade_presented(self):
        page = getattr(self.game.social, 'page', None) or {}
        return self.glowing and page.get('source_line', 0) < 3

    @staticmethod
    def is_intro(ticket):
        return isinstance(ticket,dict) and ticket.get('lesson') == 'aqua_edge'

    @staticmethod
    def valid_snapshot(record):
        return (isinstance(record,dict) and set(record) == FIELDS
                and type(record['version']) is int and record['version'] == 1
                and all(type(record[key]) is bool for key in FIELDS-{'version'})
                and (not record['battle_cleared'] or record['resonance_seen'])
                and not (record['battle_cleared'] and record['deferred']))

    @classmethod
    def valid_journey(cls, data):
        try:return cls._valid_journey(data)
        except (KeyError,TypeError,ValueError,AttributeError):return False

    @classmethod
    def _valid_journey(cls, data):
        if not isinstance(data,dict):return False
        state = data.get('cave_lesson')
        counter = data.get('cave_random_encounters',{})
        if not isinstance(counter,dict):return False
        ticket = counter.get('pending')
        intro = cls.is_intro(ticket)
        if state is None:return not intro  # Pre-lesson saves migrate on Continue.
        if not cls.valid_snapshot(state):return False
        learned = (data.get('character_abilities') or {}).get('learned_abilities',{})
        if state['battle_cleared'] and 'aqua_edge' not in learned.get('caelan',[]):return False
        post = data.get('post_battle')
        if state['deferred'] and (not intro or post is not None):return False
        if not intro:return True
        if not state['resonance_seen']:return False
        # Clearing the battle is part of the same transaction as its rewards.
        awarded = (isinstance(post,dict) and post.get('encounter') == ticket
                   and post.get('stage') == 'awarded')
        if state['battle_cleared'] != awarded:return False
        return True

    def to_dict(self):
        return {'version':1,'resonance_seen':self.resonance_seen,
                'battle_cleared':self.battle_cleared,'deferred':self.deferred}

    def restore(self, record=None, *, legacy_journey=None):
        if record is not None and not self.valid_snapshot(record):return False
        self.release_pose()
        self.resonance_seen = self.battle_cleared = self.deferred = False
        if record is not None:
            self.resonance_seen = record['resonance_seen']
            self.battle_cleared = record['battle_cleared']
            self.deferred = record['deferred']
        elif legacy_journey is not None:
            # Existing cave visitors retain their completed outing; they do not
            # receive a surprise forced battle or replay an obsolete lesson.
            counter = legacy_journey.get('cave_random_encounters') or {}
            boss = legacy_journey.get('sanctuary_boss') or {}
            visited = (counter.get('sequence',0) > 0 or boss.get('defeated')
                       or boss.get('pending') is not None)
            owner = self.game.character_abilities
            if visited and 'aether_edge' in owner.known_abilities():
                owner.learn_ability('caelan','aqua_edge')
                self.resonance_seen = self.battle_cleared = True
        self._elapsed = 0.
        self._glowing = self._retry_offered = False
        return True

    def mark_cleared(self, ticket):
        if not self.is_intro(ticket) or self.battle_cleared:return False
        self.resonance_seen = self.battle_cleared = True
        self.deferred = False
        return True

    def defer(self, ticket):
        if not self.is_intro(ticket) or self.battle_cleared:return False
        self.deferred = True
        self._retry_offered = False
        return True

    def ready_reason(self):
        g = self.game
        party = g.party
        if 'caelan' not in party.active_ids:return 'Caelan must be in the combat party.'
        if not party.characters['caelan'].current_hp:
            return 'Caelan needs to recover before he can try the blade again.'
        owner = g.character_abilities
        equipped = owner.to_dict()['characters']['caelan']['equipped_weapon']
        if not owner.has_weapon() or equipped != 'caelan_gearblade':
            return 'Equip Mira’s Blade to try Aqua Edge.'
        if 'water' not in owner.owned_gems():return 'The blade needs its blue gem before I can focus Aqua Edge.'
        return party.battle_reason() or None

    def _available(self):
        g = self.game
        return (self.active and not g.on_title and not g.combat.active
                and not g.social.locked and not g.social.active
                and not g.opening_cinematic.active and not g.household_action
                and not g.opening.locks_player and not g.transfer_cooldown and not g.opening_fade
                and not g.map_open and not g.quest_ui.journal_open
                and getattr(g,'_music_focused',True)
                and not any(getattr(getattr(g,key,None),'is_open',False)
                            for key in ('pause','inventory_ui','world_map_viewer','party_ui','status_ui')))

    def _checkpoint(self):
        return not self.game.save_store.enabled or self.game.save_progress()

    def release_pose(self):
        if self._pose_prior is None:return
        actor = self.game.player
        for key in ('story_sprite','story_draw_anchor'):
            if key in self._pose_prior:setattr(actor,key,self._pose_prior[key])
            elif hasattr(actor,key):delattr(actor,key)
        self._pose_prior = None

    def _stage_pose(self):
        from gearblade_art import GearbladeFocus
        g = self.game
        if self._focus is None:self._focus = GearbladeFocus(g.town.image)
        if self._pose_prior is None:
            self._pose_prior = {key:getattr(g.player,key) for key in ('story_sprite','story_draw_anchor')
                                if hasattr(g.player,key)}
        g.player.story_sprite = self._focus.frame(.9)
        g.player.story_draw_anchor = self._focus.anchor
        g.player.facing = 'right'

    def _resonance_complete(self):
        self._glowing = False
        self.release_pose()
        self.game.player.facing = 'back'
        before = self.resonance_seen
        self.resonance_seen = True
        if not self._checkpoint():self.resonance_seen = before

    def _resonate(self):
        g = self.game
        g.player.moving = g.player.running = False
        g.player.facing = 'front'
        opened = g.social.start_script([
            {'speaker':'caelan','text':'The Aether is so much stronger in here…'},
            {'speaker':'caelan','text':'My blade—the blue gem is glowing. It is answering the Aether in the walls.'},
            {'speaker':'caelan','text':'Maybe I can focus it better here. I should try Aqua Edge again.'},
            {'speaker':'caelan','text':'Mira… do you think they could be here?'},
            {'speaker':'mira','text':'Who?'},
            {'speaker':'caelan','text':'My parents. Somewhere in all this aether.'},
            {'speaker':'caelan','text':'I know we came for—'},
            {'speaker':'mira','text':'I know. I’ve wondered the same thing about mine.'},
            {'speaker':'caelan','text':'…Have you?'},
            {'speaker':'mira','text':'I wish I knew.'},
            {'speaker':'lucan','text':'Keep moving. Stay close.'},
        ], on_complete=self._resonance_complete, identifier=SCRIPT_ID)
        if opened:
            self._glowing = True;self._elapsed = 0.
            travel = getattr(g, 'party_travel', None)
            if travel is not None:
                # Use checked passive actors, rather than duplicating story NPCs.
                active = travel._active()
                if active and set(active) <= {'mira', 'lucan'}:
                    positions = {'mira':g.player.position+pygame.Vector2(-24,0),
                                 'lucan':g.player.position+pygame.Vector2(24,24)}
                    travel.stage_companions({key:tuple(positions[key]) for key in active},
                                            {key:('right' if key == 'mira' else 'back')
                                             for key in active})
            self._stage_pose()
        return opened

    def _near_retry(self):
        ticket = self.game.cave_random_encounters.pending
        return (self.is_intro(ticket) and self.deferred and self.active
                and self.game.player.position.distance_squared_to(ticket['position']) <= 52**2)

    def interaction_hint(self):
        if self._near_retry():return 'E: try the blue gem again'
        if self.needs_intro and self.game.sanctuary_boss.nearby():return 'E: consider the Echo Chamber'
        return ''

    def interact(self):
        if not self._available():return False
        g = self.game
        if not self._near_retry():
            if not self.needs_intro or not g.sanctuary_boss.nearby():return False
            text = self.ready_reason() or 'Before we face whatever is in there, I should try the blue gem against the creatures in these passages.'
            return g.social.start_script([{'speaker':'caelan','text':text}],identifier='cave_aqua_before_chamber')
        reason = self.ready_reason()
        lines = [{'speaker':'caelan','text': reason or 'The bats are still in the passage. I can try Aqua Edge here.'}]
        return g.social.start_choice(lines,[{'text':'Try again','action':'retry'},
                                           {'text':'Prepare first','action':'prepare'}],
                                     self._choose_retry,identifier='cave_aqua_retry',
                                     prompt=reason or 'Return to the encounter?')

    def _choose_retry(self, action):
        if action != 'retry' or not self._available() or self.ready_reason():return
        g = self.game
        ticket = g.cave_random_encounters.pending
        if not self.is_intro(ticket):return
        old_position = tuple(g.player.position)
        old_deferred = self.deferred
        g.player.position.update(ticket['position'])
        g.player.moving = g.player.running = False
        g.player.walk_ms = 0.
        self.deferred = False
        if not g.combat.start_cave(ticket, restoring=True):
            self.deferred = old_deferred
            g.player.position.update(old_position)
        g.party_travel.reset();g.camera.reset()

    def update(self, seconds=0):
        if self.glowing:
            self._elapsed += max(0.,seconds)
            if not self.blade_presented:
                self.release_pose()
                page = self.game.social.page or {}
                self.game.player.facing = 'back' if page.get('source_line') == 10 else 'left'
            return False
        self._glowing = False
        self.release_pose()
        if not self._available():return False
        if (not self.resonance_seen and not self.ready_reason()
                and self.game.sanctuary_boss.pending is None):return self._resonate()
        return False

    def draw_world(self, target, camera):
        """A bounded blue glimmer on the blade during the confluence exchange."""
        if not self.blade_presented:return
        point = self.game.player.position-pygame.Vector2(camera)
        # Registered .9s world drawing: foot(20,38), focus(27,23), tip(34,15).
        hand = point+pygame.Vector2(7,-15)
        tip = point+pygame.Vector2(14,-23)
        reduced = self.game.audio.reduced_motion
        strength = .72 if reduced else .65+.18*math.sin(self._elapsed*2.2)
        layer = pygame.Surface(target.get_size(),pygame.SRCALPHA)
        pygame.draw.line(layer,(50,130,230,round(65*strength)),hand,tip,7)
        pygame.draw.line(layer,(85,185,250,round(150*strength)),hand,tip,3)
        pygame.draw.circle(layer,(45,145,245,round(150*strength)),hand,4)
        pygame.draw.circle(layer,(185,245,255,255),hand,1)
        if not reduced:
            for index in range(5):
                age=(self._elapsed*.26+index/5)%1
                x=hand.x+math.sin(index*2.1+age*4)*9
                y=hand.y-age*23
                pygame.draw.rect(layer,(130,215,255,round((1-age)*130)),(round(x),round(y),1,1))
        target.blit(layer,(0,0))
