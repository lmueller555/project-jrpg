"""Detailed sanctuary exterior, using the normal game world's draw and feet."""
import math
import pygame

from main import World


class SanctuaryReserveWorld(World):
    is_sanctuary_reserve = True

    def __init__(self,path,image_cache=None):
        super().__init__(path,image_cache)
        self.reduced_motion = False

    def location(self,position):
        nearest = min(self.data['landmarks'],key=lambda p:pygame.Vector2(p['position']).distance_squared_to(position))
        return nearest['name'] if pygame.Vector2(nearest['position']).distance_to(position)<110 else self.data['name']

    def draw(self,target,camera,player,elapsed_ms,include_ui=True,party_actors=()):
        super().draw(target,camera,player,elapsed_ms,include_ui,party_actors=party_actors)
        # A few slow currents are visible in the grove. Their tiny native
        # glimmers accompany the retained plate's faint lights, not a new rune.
        record = self.data['confluence_motes'];cx,cy = record['center']
        rx,ry = record['radius'];time = 0 if self.reduced_motion else elapsed_ms/1000
        surface = pygame.Surface(target.get_size(),pygame.SRCALPHA)
        for index in range(record['count']):
            phase = index*2.39996
            x = cx+math.cos(phase)*rx*.72+math.sin(time*.31+phase)*4
            y = cy+math.sin(phase)*ry*.72+math.cos(time*.26+phase)*3
            pulse = .55+.45*math.sin(time*.7+phase)
            point = (round(x-camera[0]),round(y-camera[1]))
            pygame.draw.circle(surface,(215,234,143,round(30+35*pulse)),point,3)
            pygame.draw.circle(surface,(247,249,193,round(100+100*pulse)),point,1)
        target.blit(surface,(0,0))
