"""Disposable arm-rig art study; no gameplay actions, costs, unlocks or rewards.

The real battle renderer supplies scenery, formations and status layout. This
study only seeks Mira's authored poses and draws illustrative attachment FX.
Its allocation widget is local presentation state, never a saved loadout.
"""
from __future__ import annotations

import math
import random

import pygame

from battle_model import BattleModel
from battle_scene import BattleScene
from character_attributes import ATTRIBUTE_IDS, CharacterAttributes
from mira_rig_ui import MiraRigUI
from party_state import PartyState
from ui_style import BRASS, FOREST, GOLD, IVORY, MUTED


POSES = (
    ('idle', 'Ready'), ('attack', 'Bolt Shot'),
    ('charged_bolt', 'Charged Bolt'), ('bulwark', 'Bulwark'),
    ('repair_pulse', 'Repair Pulse'), ('impact_bolt', 'Impact Bolt'),
    ('arc_discharge', 'Arc Discharge'), ('guard_enter', 'Brace'),
    ('guard', 'Guard'), ('guard_impact', 'Guard impact'),
    ('hurt', 'Hit reaction'), ('overclock', 'Rig activation'),
    ('victory', 'Victory'), ('defeat', 'KO'), ('walk', 'Movement'),
)
SKILL_ART = (
    ('charged_bolt', 'Charged Bolt', (3, 0, 0)),
    ('bulwark', 'Bulwark', (0, 3, 0)),
    ('repair_pulse', 'Repair Pulse', (0, 0, 3)),
    ('impact_bolt', 'Impact Bolt', (2, 2, 0)),
    ('arc_discharge', 'Arc Discharge', (3, 0, 2)),
)


def _profiles(count):
    profiles = []
    characters = PartyState(CharacterAttributes()).characters
    for key in ('caelan', 'mira', 'lucan')[:count]:
        attributes = characters[key]
        profiles.append(dict(identifier='player' if key == 'caelan' else key,
            name=attributes.name,
            attributes={stat: attributes.value(stat) for stat in ATTRIBUTE_IDS},
            hp=attributes.current_hp, mp=attributes.current_mp,
            attack='bolt_shot' if key == 'mira' else 'attack'))
    return profiles


class _RigStudyScene(BattleScene):
    def _pose(self, actor):
        if actor == 'mira':return self.study.state, self.study.pose_ms
        return super()._pose(actor)

    def _draw_announcement(self, painter):
        painter.panel(self.announcement_rect)
        painter.text('Mira · '+self.study.label+' · Art preview',
            self.announcement_rect.center, color=GOLD, anchor='center', bold=True)

    def _draw_mira_effects(self, canvas):
        """Seekable visual sketches, explicitly outside authoritative combat."""
        study = self.study
        state = study.state
        if state not in ('attack', 'charged_bolt', 'bulwark', 'repair_pulse',
                         'impact_bolt', 'arc_discharge'):return
        positions = self._positions()
        anchor = 'tool' if state == 'repair_pulse' else 'projector' if state == 'bulwark' else 'muzzle'
        origin = self.mira_art.world_anchor(state, study.pose_ms, anchor, positions['mira'])
        origin = pygame.Vector2(origin)
        target = self._hit_point(self.model.enemies[0].identifier, positions)
        target = pygame.Vector2(target)
        progress = study.pose_ms/max(1., study.pose_duration_ms)
        active = .22 < progress < .78
        if self.reduced_motion:active = .3 < progress < .65
        if not active:return
        layer = pygame.Surface((480, 320), pygame.SRCALPHA)
        layer.set_clip(pygame.Rect(0, 34, 480, max(1, self.panel_rect.top-34)))

        def point(value):return round(value[0]), round(value[1])

        if state in ('attack', 'charged_bolt', 'impact_bolt'):
            color = (251, 193, 91) if state != 'attack' else (241, 218, 139)
            charge = state == 'charged_bolt' and progress < .48
            pygame.draw.circle(layer, (*color, 85), point(origin), 5 if charge else 3)
            pygame.draw.circle(layer, (*color, 235), point(origin), 2)
            if not charge and progress > .44:
                fraction = min(1., (progress-.44)/.24)
                projectile = origin.lerp(target, fraction)
                pygame.draw.line(layer, (*color, 220), point(projectile+(7, 0)), point(projectile), 2)
                pygame.draw.circle(layer, (255, 245, 205, 240), point(projectile), 2)
        if state in ('bulwark', 'impact_bolt'):
            center = self._hit_point('mira', positions)+pygame.Vector2(-5, 0)
            radius = 32 if state == 'bulwark' else 24
            points = [point(center+pygame.Vector2(math.cos(index*math.tau/6),
                math.sin(index*math.tau/6))*radius) for index in range(6)]
            pygame.draw.polygon(layer, (110, 213, 234, 35), points)
            pygame.draw.polygon(layer, (148, 234, 245, 205), points, 1)
            pygame.draw.line(layer, (148, 234, 245, 120), point(origin), point(center), 1)
        if state == 'repair_pulse':
            ally = self._hit_point('player', positions)
            pygame.draw.line(layer, (144, 224, 165, 90), point(origin), point(ally), 1)
            for index in range(5):
                fraction = (progress*1.5+index/5) % 1
                mote = origin.lerp(ally, fraction)
                pygame.draw.circle(layer, (164, 241, 178, 225), point(mote), 1)
            pygame.draw.circle(layer, (144, 224, 165, 145), point(ally), 12, 1)
        if state == 'arc_discharge':
            points = []
            for index in range(9):
                value = origin.lerp(target, index/8)
                if index not in (0, 8):value.y += (3 if index % 2 else -3)
                points.append(point(value))
            pygame.draw.lines(layer, (107, 187, 247, 120), False, points, 3)
            pygame.draw.lines(layer, (213, 243, 255, 240), False, points, 1)
        canvas.blit(layer, (0, 0))


class MiraRigPreview:
    """An art-only gallery controller; changing controls never mutates Game."""
    def __init__(self, game, *, party_count=2):
        self.game = game
        self.rig = MiraRigUI()
        self.pose_index = 0
        self.pose_ms = 0.
        self._pose_elapsed_ms = 0.
        self.elapsed = 0.
        self.playing = True
        self.focused = True
        self.buttons = {}
        self.party_count = party_count
        self._make_scene()

    def _make_scene(self):
        self.model = BattleModel.from_bestiary_group(self.game.attributes,
            [{'enemy_id': 'cave_bat', 'level': 2}]*2, party_members=_profiles(self.party_count),
            weapon_equipped=True, learned_abilities=('aether_edge',),
            bot_loadouts={}, guest_abilities={}, rng=random.Random(9))
        # A frozen command-ready composition, not a played encounter.
        self.model.phase = 'ready';self.model._active_actor = 'mira'
        self.model.combatant('mira').atb = 1.
        self.model.player.atb = .4
        self.scene = _RigStudyScene(self.game, self.model, battlefield='cave_depths')
        self.scene.study = self
        self.scene._elapsed = self.elapsed

    @property
    def state(self):return POSES[self.pose_index][0]

    @property
    def label(self):return POSES[self.pose_index][1]

    @property
    def pose_duration_ms(self):
        data = self.scene.mira_art.animations.get(self.state,
            self.scene.mira_art.animations['idle'])
        return sum(frame['duration_ms'] for frame in data['frames'])

    def select_pose(self, value):
        self.pose_index = value % len(POSES);self.pose_ms = 0.;self._pose_elapsed_ms = 0.

    def update(self, seconds):
        if not self.focused:return
        self.elapsed += max(0., seconds)
        self.scene._elapsed = self.elapsed
        if self.playing:
            self._pose_elapsed_ms += max(0., seconds)*1000
            self.pose_ms = (self.pose_duration_ms*.55 if self.scene.reduced_motion
                            else self._pose_elapsed_ms)
            if self._pose_elapsed_ms > self.pose_duration_ms+450:self.select_pose(self.pose_index+1)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.WINDOWFOCUSLOST:
                self.focused = False;self.rig.handle_event(event);continue
            if event.type == pygame.WINDOWFOCUSGAINED:self.focused = True;continue
            if not self.focused:continue
            if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
                if event.key == pygame.K_TAB and not self.rig.focused:
                    self.rig.focused = True;continue
                if self.rig.focused and self.rig.handle_event(event):continue
            if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
                if event.key == pygame.K_SPACE:self.playing = not self.playing;continue
                if event.key == pygame.K_LEFTBRACKET:self.select_pose(self.pose_index-1);continue
                if event.key == pygame.K_RIGHTBRACKET:self.select_pose(self.pose_index+1);continue
                if event.key == pygame.K_3:self.party_count = 5-self.party_count;self._make_scene();continue
            point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and point is not None:
                selected = next((key for key, rect in self.buttons.items() if rect.collidepoint(point)), None)
                if selected is not None:
                    self.rig.focused = False
                    self.select_pose(next(index for index, pair in enumerate(POSES) if pair[0] == selected))
                    continue
            self.rig.handle_event(event, point=point, enabled=True)

    def draw(self):
        _, _, origin = self.game._ensure_ui_surface()
        self.game.ui_surface.fill(FOREST)
        self.scene.draw(self.game.canvas, self.game.ui_surface)
        painter = self.game.ui.painter(self.game.ui_surface)
        self.rig.draw(painter, self.scene.party_rows['mira']['interactable'], enabled=True)
        commands = self.scene.commands_panel
        painter.rect(FOREST, commands.inflate(-2, -2))
        line = painter.font('small').get_linesize()
        painter.text('SKILL ART', (commands.centerx, commands.top+5), role='small',
                     color=GOLD, anchor='midtop', bold=True)
        self.buttons = {}
        y = commands.top+line+10
        footer_height = line+7
        row_height = max(line+2, (commands.bottom-y-footer_height-5)//len(SKILL_ART))
        for state, label, requirements in SKILL_ART:
            rect = pygame.Rect(commands.left+5, y, commands.width-10, row_height-1)
            if state == self.state:painter.rect('#314f40', rect);painter.rect(GOLD, rect, 1)
            else:painter.rect(BRASS, rect, 1)
            short = {'charged_bolt': 'Charge', 'repair_pulse': 'Repair',
                     'impact_bolt': 'Impact', 'arc_discharge': 'Arc'}.get(state, label)
            # Use full names whenever the accessible font fits the narrow menu.
            if painter.font('small').size(label)[0] <= rect.width-6:short = label
            painter.text(short, rect.center, role='small', anchor='center', color=IVORY)
            self.buttons[state] = rect;y += row_height
        selected = next((row for row in SKILL_ART if row[0] == self.state), None)
        requirements = ('W'+str(selected[2][0])+' P'+str(selected[2][1])+' S'+str(selected[2][2])
                        if selected else '6 power')
        painter.text(requirements, (commands.centerx, commands.bottom-5), role='small',
                     color=MUTED, anchor='midbottom')
        # Never imply these sketches have dealt damage or healed a combatant.
        self.game.window.fill('#101b19')
        self.game.window.blit(self.game.ui_surface, origin)
