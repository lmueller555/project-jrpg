"""Explicit per-actor regional travel/portrait migrations, separate from activities.

Absent binding files retain the original complete performance. A binding opts in
only one persistent actor ID; it never changes maps, controller state or shared
legacy banks. Activity drawings remain legacy until separately authored/validated.
"""
from functools import lru_cache
import json
from pathlib import Path
import pygame
from rendering import layer
from npc_roster_art import RosterArt

ROOT=Path(__file__).resolve().parent
BINDINGS=ROOT/'assets/characters/regional_npc_hd'
ROLES={
    'grain_loader':'adult_man_02', 'grain_coworker':'adult_man_03',
    'regional_gardener':'adult_woman_01', 'regional_picker':'adult_man_02',
    'bridge_mason':'adult_man_01', 'bridge_tender':'adult_man_03',
}


def actor_binding(actor_id):
    if actor_id not in ROLES:return None
    path=BINDINGS/actor_id/'binding.json'
    if not path.is_file():return None
    record=json.loads(path.read_text())
    if (record.get('version')!=1 or record.get('actor_id')!=actor_id or record.get('design_id')!=ROLES[actor_id]
            or not isinstance(record.get('activation'),dict)
            or set(record['activation'])!={'idle','walk','activity'}
            or record['activation']['idle'] is not True or record['activation']['walk'] is not True
            or type(record['activation']['activity']) is not bool
            or record.get('logical_canvas')!=[40,44]
            or record.get('draw_anchor_logical')!=[20,38]
            or record.get('body_offset_logical')!=[8,3.5]
            or record.get('travel_cycle_ms')!=(680 if actor_id.startswith('regional_') else 560)):
        raise ValueError('Invalid explicit regional migration: '+actor_id)
    if record['activation']['activity']:
        if not isinstance(record.get('activity_manifest'),str) or not isinstance(record.get('activity_manifest_sha256'),str):
            raise ValueError('Native activity opt-in lacks reviewed manifest: '+actor_id)
    return record


def bound_regional_design(actor_id):
    record=actor_binding(actor_id)
    return record['design_id'] if record else None


class _Loader:
    @staticmethod
    @lru_cache(maxsize=256)
    def image(path):return pygame.image.load(str(ROOT/path)).convert_alpha()


class RegionalRosterArt:
    """Pad native bodies into the role's existing canvas without losing detail."""
    def __init__(self, actor_id):
        self.record=actor_binding(actor_id)
        if self.record is None:raise ValueError('Actor has no regional art opt-in')
        self.design_id=self.record['design_id']
        self.bank=RosterArt(_Loader(),self.design_id)
        self.portrait_path=self.bank.portrait_path
        self._padded={}

    def sprite(self,facing,moving,elapsed_ms):
        # Preserve each controller's original full gait duration. New eight-frame
        # bodies use 70ms grain/bridge or 85ms garden phases, not faster footsteps.
        bank_cycle=sum(ms for _,ms in self.bank.walks[facing])
        time=elapsed_ms*bank_cycle/self.record['travel_cycle_ms']
        body=self.bank.sprite(facing,moving,time)
        if body not in self._padded:
            canvas=layer(tuple(self.record['logical_canvas']),pygame.SRCALPHA)
            canvas.blit(body,tuple(self.record['body_offset_logical']))
            self._padded[body]=canvas
        return self._padded[body]


def for_actor(actor):
    return RegionalRosterArt(actor.data['id']) if actor_binding(actor.data['id']) else None
