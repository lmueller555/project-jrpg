"""Player saves and event-driven autosaves over the game's checkpoint model."""
from __future__ import annotations

from copy import deepcopy
import math
from uuid import uuid4

from save_library import CAMPAIGN, MANUAL_SLOTS, SaveLibrary


class GameSaves:
    def __init__(self, game, checkpoint=None):
        self.game = game
        self.library = SaveLibrary(checkpoint)
        self.campaign = uuid4().hex
        self.branch = uuid4().hex
        self.playtime = self.clock = 0.
        self.scene_deadline = 0.
        self.scene = game.world.data['id']
        self.pending_scene = None
        self.pending_battles = []
        self.retry_at = 0.
        self.notice = ''
        self.notice_seconds = 0.
        self.enabled = checkpoint is not None or game._is_quest_playtest

    @staticmethod
    def valid_context(context):
        return (isinstance(context, dict) and set(context) in ({'campaign','playtime','scene_cooldown'},
                                     {'campaign','playtime','scene_cooldown','branch'})
                and isinstance(context['campaign'], str) and CAMPAIGN.fullmatch(context['campaign']) is not None
                and ('branch' not in context or isinstance(context['branch'],str)
                     and CAMPAIGN.fullmatch(context['branch']) is not None)
                and all(type(context[key]) in (int,float) and math.isfinite(context[key])
                        and 0 <= context[key] <= (60 if key == 'scene_cooldown' else 1e10)
                        for key in ('playtime','scene_cooldown')))

    def context(self):
        return {'campaign': self.campaign, 'branch': self.branch, 'playtime': self.playtime,
                'scene_cooldown': min(60., max(0., self.scene_deadline-self.clock))}

    def begin(self, data=None):
        context = data.get('save_context') if data else None
        self.campaign = context['campaign'] if self.valid_context(context) else uuid4().hex
        self.branch = context.get('branch',self.campaign) if self.valid_context(context) else uuid4().hex
        self.playtime = context['playtime'] if self.valid_context(context) else 0.
        self.clock = 0.
        self.scene_deadline = context['scene_cooldown'] if self.valid_context(context) else 0.
        self.pending_scene = None if data else (self.game.world.data['id'], uuid4().hex)
        self.pending_battles.clear()
        self.scene = self.game.world.data['id']
        self.retry_at = 0.
        self.notice = ''
        self.notice_seconds = 0.

    def eligible(self, *, manual=False):
        g = self.game
        return (self.enabled and not g._is_gallery_preview and not g.on_title
                and not g.game_over and not g.combat.active and g._music_focused
                and not g.opening_cinematic.active and not g.household_action
                and not g.social.active and not g.social.locked
                and not g.opening.locks_player and not g.opening.controls_player
                and not g.regent_quest.locks_player
                and not g.sanctuary_boss.locks_player and not g.elemental_bosses.locks_player
                and not g.cave_lesson.locks_player
                and not g.opening_fade and not g.transfer_cooldown
                and (manual or not (g.pause.is_open or g.inventory_ui.is_open or g.party_ui.is_open
                                    or g.status_ui.is_open or g.world_map_viewer.is_open
                                    or g.map_open or g.quest_ui.journal_open or g.save_menu.is_open))
                and any(g.party.characters[key].current_hp > 0 for key in g.party.active_ids)
                and self.safe_ground())

    def safe_ground(self):
        """Require the complete footprint and a short clear route away."""
        g=self.game
        if not g.world.can_stand(g.player.position):return False
        return any(all(g.world.can_stand((g.player.position.x+dx*step,
                                         g.player.position.y+dy*step))
                       for step in range(1,5))
                   for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)))

    def _snapshot(self):
        data = self.game.journey_snapshot()
        return self.game._validate_journey(data)

    def summary(self):
        g=self.game
        active=[key for key,state in g.quests.states.items() if state['status'] in ('active','ready')]
        quest=g.quests.definitions[active[-1]]['title'] if active else 'Exploration'
        return {'location':g.world.data.get('name','Journey'),'quest':quest}

    def manual(self, slot):
        if not self.eligible(manual=True):
            self.notice = 'Save when the party returns to exploration.'
            return False
        data = self._snapshot()
        if data is None:
            self.notice = 'This moment could not be saved.'
            return False
        result = self.library.write_manual(slot, data, summary=self.summary())
        self.notice = 'Game saved.' if result else self.library.error or 'The game could not be saved.'
        self.notice_seconds = 4.
        return result

    def request_battle(self, receipt):
        event = 'battle:'+self.branch+':'+receipt
        if event not in self.pending_battles:self.pending_battles.append(event)

    def update(self, seconds):
        g = self.game
        self.notice_seconds = max(0., self.notice_seconds-seconds)
        if not self.enabled or g._is_gallery_preview:return
        if (not g.on_title and not g.game_over and not g.save_menu.is_open
                and g._music_focused and not g.pause.is_open
                and not (g.combat.active and g.combat.paused)):
            self.playtime += seconds
        current = g.world.data['id']
        if current != self.scene:
            self.pending_scene = ((current, uuid4().hex) if self.clock >= self.scene_deadline else None)
            self.scene = current
        if not self.eligible():return
        self.clock += seconds
        if self.clock < self.retry_at:return
        if not self.pending_battles and self.pending_scene is None:return
        battle = bool(self.pending_battles)
        event = self.pending_battles[0] if battle else 'scene:'+self.pending_scene[1]
        if not battle and self.pending_scene[0] != current:
            self.pending_scene = None
            return
        deadline = self.scene_deadline
        # Snapshot the cooldown itself so loading cannot evade doorway throttling.
        if not battle:self.scene_deadline = self.clock+60.
        data = self._snapshot()
        result = data is not None and self.library.write_auto(data, 'battle' if battle else 'scene', event, summary=self.summary())
        if result:
            if battle:self.pending_battles.pop(0)
            # A completed battle also covers a pending arrival in this scene.
            self.pending_scene = None
            self.notice = 'Autosaved.'
            self.notice_seconds = 2.5
        else:
            self.scene_deadline = deadline
            self.retry_at = self.clock+10.
            self.notice = self.library.error or 'Autosave could not be written. Retrying shortly.'
            self.notice_seconds = 4.

    def entries(self, *, all_campaigns=False):
        result = []
        for slot in range(1, MANUAL_SLOTS+1):
            entry = self.library.manual(slot)
            result.append((f'Slot {slot}', entry, ('manual', slot)))
        campaigns = self.library.campaigns() if all_campaigns else [self.campaign]
        autos = []
        for campaign in campaigns:
            for index, entry in enumerate(self.library.autos(campaign)):
                if self.library.valid_entry(entry):
                    autos.append((('Latest','Previous','Earlier')[index]+' autosave', entry, ('auto',campaign,index)))
        autos.sort(key=lambda item: item[1]['metadata']['saved_at'], reverse=True)
        archives=[('Journey checkpoint',entry,('resume',entry['metadata']['campaign']))
                  for entry in self.library.archived()] if all_campaigns else []
        return result+autos+archives

    def latest(self, kind):
        rows = [row for row in self.entries() if row[2][0] == kind and row[1]
                and row[1]['metadata']['campaign'] == self.campaign]
        previous_error=self.game.save_error
        try:
            for row in sorted(rows, key=lambda item: item[1]['metadata']['saved_at'], reverse=True):
                if self.game._validate_journey(deepcopy(row[1]['payload'])) is not None:return row
        finally:self.game.save_error=previous_error
        return None

    def load(self, row):
        entry = row[1]
        if not self.library.valid_entry(entry):return False
        data = self.game._validate_journey(deepcopy(entry['payload']))
        if data is None:
            self.notice = 'This save could not be loaded. Choose another save.'
            return False
        g = self.game
        g.save_menu.close()
        g.social.cancel()
        g.game_over = False
        g.saved_journey = data
        g.title.fade = 0.
        result = g.begin_journey(True)
        if not result:self.notice = g.save_error or 'This save could not be loaded.'
        else:
            g.save_error=None
            # Explicit slot loading starts a new attempt. Internal Continue keeps
            # its persisted branch so finishing the same receipt stays idempotent.
            self.branch=uuid4().hex
        return result
