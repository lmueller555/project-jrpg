"""An elemental guardian's own live chamber shot before honest battle loading."""
import math

import pygame

from cave_battle_entry import CaveBattleEntry
from elemental_bosses import definition


class ElementalBossEntry(CaveBattleEntry):
    def __init__(self, world_frame, focus, enemy_id, *, intro_seen, reduced_motion=False):
        self.definition = definition(enemy_id)
        if self.definition is None:raise ValueError('Unknown elemental guardian')
        super().__init__(world_frame, focus, self.definition['location'], reduced_motion=reduced_motion)
        self.intro_seen = bool(intro_seen)
        self.duration = .35 if intro_seen else .8 if reduced_motion else 1.8

    def draw(self, game, canvas, ui_surface):
        if self.phase == 'cutscene' and not self.intro_seen:
            progress = min(1., self.elapsed/self.duration)
            origin = pygame.Vector2(game.camera.position())
            if not self.reduced_motion:
                destination = pygame.Vector2(self.definition['center'])-pygame.Vector2(canvas.get_size())/2
                ease = math.sin(min(1., progress/.8)*math.pi/2)**2
                origin = origin.lerp(destination, .7*ease)
            frame = pygame.Surface(canvas.get_size())
            game.world.draw(frame, origin, game.player, game.elapsed_ms+self.elapsed*1000,
                            include_ui=False, party_actors=game.party_travel.actors())
            game.elemental_bosses.draw_world(frame, origin, elapsed_ms=game.elapsed_ms+self.elapsed*1000)
            self.world_frame = frame
        super().draw(game, canvas, ui_surface)
