"""Show the proposed front walks moving through the actual town renderer."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont, ImageSequence

from main import World, VIEW_SIZE, WALK_SPEED


OUT = ROOT/'docs/reviews/companion_front_walks'
NAMES = {'caelan': 'Caelan reference', 'lucan': 'Lucan',
         'rhea': 'Rhea', 'edran': 'Edran'}
STEP_MS = 20
CYCLES = 4
PERIOD_MS = 560


class PreviewActor:
    def __init__(self, world, actor, position):
        folder = ROOT/f'assets/characters/{actor}/walk_front'
        meta = json.loads((folder/'animation.json').read_text())
        self.actor = actor
        self.position = pygame.Vector2(position)
        self.draw_anchor = meta['foot_anchor']
        self.frames = [world.image((folder/frame['file']).relative_to(ROOT).as_posix())
                       for frame in meta['frames']]
        self.durations = [frame['duration_ms'] for frame in meta['frames']]
        self.clock_ms = 0
        self.probe_size = world.probe_size

    @property
    def blocker(self):
        return pygame.Rect(round(self.position.x)-self.probe_size[0]//2,
                           round(self.position.y)-self.probe_size[1]//2,
                           *self.probe_size)

    def sprite(self, elapsed_ms):
        time = self.clock_ms % sum(self.durations)
        for frame, duration in zip(self.frames, self.durations):
            if time < duration:return frame
            time -= duration
        return self.frames[-1]


def find_route(world, distance):
    """Find four parallel, straight, genuinely walkable paths for the review."""
    def visible_and_walkable(x, y):
        if not world.can_stand((x, y)):return False
        sprite = pygame.Rect(x-12, y-35, 24, 36)
        return not any(entity['sort_y'] > y+world.probe_size[1]/2
                       and entity['rect'].colliderect(sprite)
                       for entity in world.entities)
    span = 48*3
    preferred_y = sorted(range(84, world.size[1]-distance-20, 12),
                         key=lambda y: abs(y-540))
    preferred_x = sorted(range(36, world.size[0]-span-24, 12),
                         key=lambda x: abs(x-420))
    for y in preferred_y:
        for x in preferred_x:
            if all(visible_and_walkable(x+48*index, y+dy)
                   for dy in range(0, distance+1, 4) for index in range(4)):
                return [(x+48*index, y) for index in range(4)]
    raise ValueError('No collision-free four-character route found for preview.')


def fixed_palette(frames, actor_colors):
    colors = list(dict.fromkeys(actor_colors))
    background = frames[0].quantize(colors=max(2, 256-len(colors)),
                                    method=Image.Quantize.FASTOCTREE)
    table = background.getpalette()
    for _, index in sorted(background.getcolors(), reverse=True):
        color = tuple(table[index*3:index*3+3])
        if color not in colors:colors.append(color)
        if len(colors) >= 256:break
    palette = Image.new('P', (1, 1))
    palette.putpalette([v for c in colors for v in c]+[0]*(768-3*len(colors)))
    return palette


def capture():
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        world = World()
        world.npcs.clear()
        duration = CYCLES*PERIOD_MS
        distance = round(WALK_SPEED*duration/1000)
        starts = find_route(world, distance)
        actors = [PreviewActor(world, actor, start)
                  for actor, start in zip(NAMES, starts)]
        world.npcs.extend(actors)
        invisible = type('HiddenPlayer', (), {'story_visible': False})()
        camera = (max(0, min(world.size[0]-VIEW_SIZE[0],
                            round(starts[0][0]+72-VIEW_SIZE[0]/2))),
                  max(0, min(world.size[1]-VIEW_SIZE[1], starts[0][1]-90)))
        native = pygame.Surface(VIEW_SIZE)
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), 18)
        small = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), 15)
        frames = []
        for time in range(0, duration, STEP_MS):
            for actor, start in zip(actors, starts):
                actor.position.update(start[0], start[1]+WALK_SPEED*time/1000)
                actor.clock_ms = time
                assert world.can_stand(actor.position, ignore_npc=actor)
            # Static scenery isolates the new character motion. Rendering,
            # occlusion and sprite ordering are the real World.draw path.
            world.draw(native, camera, invisible, 0, include_ui=False)
            image = Image.frombytes('RGB', VIEW_SIZE,
                                    pygame.image.tobytes(native, 'RGB')).resize(
                                        (960, 640), Image.Resampling.NEAREST)
            card = Image.new('RGB', (960, 720), '#e8edf2')
            card.paste(image, (0, 40))
            draw = ImageDraw.Draw(card)
            draw.text((16, 9), 'Front walks in Eldenmere — actual town renderer',
                      font=font, fill='#26343e')
            for actor, start in zip(actors, starts):
                x = (start[0]-camera[0])*2
                label = NAMES[actor.actor]
                box = draw.textbbox((0, 0), label, font=small)
                draw.text((x-(box[2]-box[0])/2, 691), label,
                          font=small, fill='#26343e')
            frames.append(card)
        colors = []
        for actor in NAMES:
            idle = Image.open(ROOT/f'assets/characters/{actor}/idle_front.png').convert('RGBA')
            pixels = getattr(idle, 'get_flattened_data', idle.getdata)()
            colors.extend(p[:3] for p in pixels if p[3])
        colors.extend([(232, 237, 242), (38, 52, 62)])
        palette = fixed_palette(frames, colors)
        indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE)
                   for frame in frames]
        gif = OUT/'walking_in_eldenmere.gif'
        indexed[0].save(gif, save_all=True, append_images=indexed[1:],
                        duration=STEP_MS, loop=0, disposal=1, optimize=False)
        frames[0].save(OUT/'walking_in_eldenmere.png')
        with Image.open(gif) as image:
            durations = [frame.info['duration'] for frame in ImageSequence.Iterator(image)]
            assert sum(durations) == duration and image.info['loop'] == 0
        report = {'actual_renderer': True, 'preview_only': True,
                  'walking_speed_pixels_per_second': WALK_SPEED,
                  'gait_period_ms': PERIOD_MS, 'duration_ms': duration,
                  'frame_step_ms': STEP_MS, 'route_starts': starts,
                  'distance_pixels': distance, 'collision_free_paths': True,
                  'actors': list(NAMES), 'gif': gif.name}
        (OUT/'world_preview.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
    finally:
        pygame.quit()


if __name__ == '__main__':
    capture()
