"""Detailed sanctuary exterior, using the normal game world's draw and feet."""
import pygame

from main import World
from sanctuary_atmosphere import SanctuaryAtmosphere


class SanctuaryReserveWorld(World):
    is_sanctuary_reserve = True

    def __init__(self,path,image_cache=None):
        super().__init__(path,image_cache)
        self.reduced_motion = False
        self.atmosphere = SanctuaryAtmosphere(self)
        self.entities.extend(self.atmosphere.records)

    def location(self,position):
        nearest = min(self.data['landmarks'],key=lambda p:pygame.Vector2(p['position']).distance_squared_to(position))
        return nearest['name'] if pygame.Vector2(nearest['position']).distance_to(position)<110 else self.data['name']

    def draw(self,target,camera,player,elapsed_ms,include_ui=True,party_actors=()):
        self.atmosphere.update(elapsed_ms,reduced_motion=self.reduced_motion)
        original=None
        if not self.atmosphere.enabled:
            original=self.entities
            self.entities=[record for record in original if 'atmosphere_kind' not in record]
        try:
            super().draw(target,camera,player,elapsed_ms,include_ui,party_actors=party_actors)
        finally:
            if original is not None:self.entities=original
