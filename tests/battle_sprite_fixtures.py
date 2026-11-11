"""Minimal colored combat banks for renderer tests."""
import pygame

class FieldSprites:
    def __init__(self):
        self.calls = []
        self.frames = {}
        for actor, size, anchor, body in (
                ('caelan', (48, 48), (24, 42), (16, 6, 18, 36)),
                ('mira', (64, 64), (32, 54), (9, 18, 37, 36)),
                ('ridgeback_tusker', (96, 72), (48, 62), (4, 8, 88, 54))):
            image = pygame.Surface(size, pygame.SRCALPHA)
            image.fill('#f1cd77', body)
            self.frames[actor] = image, anchor

    def frame(self, actor, state, elapsed_ms):
        self.calls.append((actor, state))
        return self.frames[actor]
