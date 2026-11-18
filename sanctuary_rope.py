"""Fixed Sanctuary posts and a hand-authored, separately moving rope."""
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent


class SanctuaryRope:
    def __init__(self, game, art):
        self.game = game
        self.art = art
        self.record = None
        self.original = None
        self.frames = None
        self.progress = 0.
        self._sound = self._voice = None
        self._sounded = False
        self._world = self._prior_blockers = self._blocker_callback = None

    @property
    def duration_ms(self):
        return sum(frame['duration_ms'] for frame in self.art['rope_frames'])

    @property
    def opened(self):
        return self.record is not None and self.progress >= 1.

    def restore(self):
        self.stop_audio()
        world = self._world
        if world is not None and getattr(world, 'task_blockers', None) is self._blocker_callback:
            if self._prior_blockers is None:del world.task_blockers
            else:world.task_blockers = self._prior_blockers
        if self.record is not None and self.original is not None:
            self.record.update(self.original)
        self.record = self.original = self.frames = None
        self._world = self._prior_blockers = self._blocker_callback = None
        self.progress = 0.
        self._sounded = False

    def _load(self, world):
        if self.record is not None:return
        self.record = next(record for record in world.entities
                           if record['id'] == 'reserve_cave_keeper_rail')
        self.original = {key:self.record[key] for key in
                         ('position', 'rect', 'surfaces', 'sort_y')}
        posts = world.image(self.art['posts'])
        self.frames = []
        for frame in self.art['rope_frames']:
            image = pygame.Surface(posts.get_size(), pygame.SRCALPHA)
            image.blit(world.image(frame['file']), (0, 0))
            image.blit(posts, (0, 0))
            self.frames.append(image)
        self._world = world
        self._prior_blockers = getattr(world, 'task_blockers', None)
        prior = self._prior_blockers
        def blockers():
            own = self._footprints(world) if self._blocker_callback is blockers else ()
            return (*(prior() if prior else ()), *own)
        self._blocker_callback = blockers
        world.task_blockers = blockers

    def _footprints(self, world):
        if self._world is not world:return ()
        x, y = self.art['position']
        rectangles = list(self.art.get('post_footprints', ()))
        if self.progress*self.duration_ms < self.art.get('release_ms', 0):
            footprint = self.art.get('closed_rope_footprint')
            if footprint is not None:rectangles.append(footprint)
        return tuple(pygame.Rect(x+left, y+top, width, height)
                     for left, top, width, height in rectangles)

    def set_progress(self, progress, world):
        self._load(world)
        self.progress = max(0., min(1., float(progress)))
        elapsed = self.progress*self.duration_ms
        index = len(self.frames)-1
        for number, frame in enumerate(self.art['rope_frames']):
            if elapsed < frame['duration_ms']:
                index = number
                break
            elapsed -= frame['duration_ms']
        image = self.frames[index]
        position = list(self.art['position'])
        self.record.update(position=position, rect=image.get_rect(topleft=position),
                           surfaces=[image], sort_y=self.art.get('sort_y', position[1]+48))

    def play_release(self):
        if self._sounded:return
        self._sounded = True
        if not pygame.mixer.get_init() or self.game.audio.effects_volume <= 0:return
        path = self.art.get('sound')
        if not path:return
        try:
            if self._sound is None:self._sound = pygame.mixer.Sound(str(ROOT/path))
            self._voice = self._sound.play()
            self.sync_audio(False)
        except (pygame.error, OSError):self._voice = None

    def sync_audio(self, paused):
        if self._voice is None:return
        try:
            if self._voice.get_sound() is not self._sound:
                self._voice = None
                return
            self._voice.set_volume(.22*self.game.audio.effects_volume)
            if paused:self._voice.pause()
            else:self._voice.unpause()
        except pygame.error:self._voice = None

    def stop_audio(self):
        if self._voice is None:return
        try:
            if self._voice.get_sound() is self._sound:self._voice.stop()
        except pygame.error:pass
        self._voice = None
