"""Capture review-only directional walks through the real town renderer."""
from __future__ import annotations

import argparse
import hashlib
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


OUT = ROOT/'docs/reviews/companion_directional_walks'
NAMES = {'caelan': 'Caelan reference', 'lucan': 'Lucan',
         'rhea': 'Rhea', 'edran': 'Edran'}
VECTORS = {'left': (-1, 0), 'right': (1, 0), 'back': (0, -1)}
STEP_MS = 20
CYCLES = 4
PERIOD_MS = 560
DURATION_MS = CYCLES*PERIOD_MS
LANE_SPACING = 48
CARD_SIZE = (960, 720)
CARD_BG = (232, 237, 242)
INK = (38, 52, 62)


class PreviewActor:
    """Standalone metadata consumer; never changes game actor placement."""

    def __init__(self, world, actor, direction, source_actor=None):
        self.actor = actor
        self.folder = ROOT/f'assets/characters/{source_actor or actor}/walk_{direction}'
        self.meta = json.loads((self.folder/'animation.json').read_text())
        self.draw_anchor = tuple(self.meta['foot_anchor'])
        self.frames = [world.image((self.folder/frame['file']).relative_to(ROOT).as_posix())
                       for frame in self.meta['frames']]
        self.durations = [frame['duration_ms'] for frame in self.meta['frames']]
        if len(self.frames) != 4 or self.durations != [140]*4:
            raise ValueError(f'{self.folder}: expected four 140 ms gait frames')
        self.position = pygame.Vector2()
        self.clock_ms = 0
        self.probe_size = world.probe_size
        # Full frame bounds, including transparent padding, make the visibility
        # checks conservative for every authored pose and foot anchor.
        self.body_size = (max(frame.get_width() for frame in self.frames),
                          max(frame.get_height() for frame in self.frames))
        self.opaque_pixels = [
            [(x, y, tuple(frame.get_at((x, y)))[:3])
             for y in range(frame.get_height()) for x in range(frame.get_width())
             if frame.get_at((x, y)).a == 255]
            for frame in self.frames]

    @property
    def blocker(self):
        return pygame.Rect(round(self.position.x)-self.probe_size[0]//2,
                           round(self.position.y)-self.probe_size[1]//2,
                           *self.probe_size)

    def body_rect(self, position):
        return pygame.Rect(round(position[0])-self.draw_anchor[0],
                           round(position[1])-self.draw_anchor[1], *self.body_size)

    def sprite(self, elapsed_ms):
        time = self.clock_ms % sum(self.durations)
        for frame, duration in zip(self.frames, self.durations):
            if time < duration:
                return frame
            time -= duration
        return self.frames[-1]


def route_positions(starts, direction, elapsed_ms):
    dx, dy = VECTORS[direction]
    offset = WALK_SPEED*elapsed_ms/1000
    return [(x+dx*offset, y+dy*offset) for x, y in starts]


def unobscured(world, actor, position):
    body = actor.body_rect(position)
    if not pygame.Rect((0, 0), world.size).contains(body):
        return False
    sort_key = (position[1]+world.probe_size[1]/2, 2)
    if any((entity['sort_y'], entity.get('sort_priority', 0)) > sort_key
           and entity['rect'].colliderect(body) for entity in world.entities):
        return False
    # Foreground rails are drawn after all actors regardless of their baseline.
    return not any(surface.get_rect(topleft=origin).colliderect(body)
                   for surface, origin in world.foreground)


def route_camera(world, actors, starts, direction):
    ends = route_positions(starts, direction, DURATION_MS)
    bodies = [actor.body_rect(position)
              for positions in (starts, ends)
              for actor, position in zip(actors, positions)]
    bounds = bodies[0].unionall(bodies[1:])
    # Horizontal lanes reserve a fixed label column beside the whole route.
    x = bounds.left-110 if direction != 'back' else bounds.centerx-VIEW_SIZE[0]//2
    y = bounds.centery-VIEW_SIZE[1]//2
    camera = (max(0, min(world.size[0]-VIEW_SIZE[0], x)),
              max(0, min(world.size[1]-VIEW_SIZE[1], y)))
    visible = pygame.Rect(camera, VIEW_SIZE).inflate(-16, -16)
    if not visible.contains(bounds):
        return None
    if direction != 'back' and bounds.left-camera[0] < 102:
        return None
    return camera


def find_route(world, actors, direction):
    """Find four parallel, visible routes on actual collision-free town ground."""
    distance = WALK_SPEED*DURATION_MS/1000
    preferred_x = sorted(range(120, world.size[0]-220, 12), key=lambda x: abs(x-420))
    preferred_y = sorted(range(84, world.size[1]-200, 12), key=lambda y: abs(y-540))
    # Every rendered position and the exact final endpoint are checked. At the
    # real walking speed these probes are only 1.44 native pixels apart.
    times = range(0, DURATION_MS+STEP_MS, STEP_MS)
    for y in preferred_y:
        for x in preferred_x:
            if direction == 'back':
                starts = [(x+LANE_SPACING*index, y+distance) for index in range(4)]
            else:
                start_x = x+distance if direction == 'left' else x
                starts = [(start_x, y+LANE_SPACING*index) for index in range(4)]
            camera = route_camera(world, actors, starts, direction)
            if camera is None:
                continue
            if all(world.can_stand(position, actor.probe_size)
                   and unobscured(world, actor, position)
                   for time in times
                   for actor, position in zip(actors, route_positions(starts, direction, time))):
                return starts, camera
    raise ValueError(f'No visible four-character {direction} route found')


def actor_palette(actors):
    colors = []
    for actor in actors:
        for frame in actor.meta['frames']:
            with Image.open(actor.folder/frame['file']) as image:
                image = image.convert('RGBA')
                pixels = getattr(image, 'get_flattened_data', image.getdata)()
                colors.extend(pixel[:3] for pixel in pixels if pixel[3])
    return list(dict.fromkeys(colors))


def fixed_palette(frame, reserved_colors):
    """Reserve every native sprite color before quantizing the static scenery."""
    colors = list(reserved_colors)
    if len(colors) > 254:
        raise ValueError(f'Too many reserved actor colors for a GIF: {len(colors)}')
    background = frame.quantize(colors=256-len(colors), method=Image.Quantize.FASTOCTREE)
    table = background.getpalette()
    for _, index in sorted(background.getcolors(), reverse=True):
        color = tuple(table[index*3:index*3+3])
        if color not in colors:
            colors.append(color)
        if len(colors) == 256:
            break
    palette = Image.new('P', (1, 1))
    palette.putpalette([channel for color in colors for channel in color]
                       +[0]*(768-3*len(colors)))
    return palette


def encode_frame(frame, palette, reserved_indices, actors, starts, direction, time, camera):
    indexed = frame.quantize(palette=palette, dither=Image.Dither.NONE)
    original = frame.load()
    encoded = indexed.load()
    for actor, position in zip(actors, route_positions(starts, direction, time)):
        left = (round(position[0])-actor.draw_anchor[0]-camera[0])*2
        top = 40+(round(position[1])-actor.draw_anchor[1]-camera[1])*2
        opaque = actor.opaque_pixels[(time % PERIOD_MS)//140]
        for x, y, color in opaque:
            for sx, sy in ((0, 0), (0, 1), (1, 0), (1, 1)):
                point = (left+x*2+sx, top+y*2+sy)
                # Check actual World.draw pixels before preserving their exact
                # RGB values. Pillow's coarse palette lookup otherwise shifts
                # some reserved colors by one channel value even without dithering.
                assert original[point] == color, (direction, time, actor.actor, point)
                encoded[point] = reserved_indices[color]
    return indexed


def annotate(image, direction, actors, starts, camera, font, small):
    card = Image.new('RGB', CARD_SIZE, CARD_BG)
    card.paste(image, (0, 40))
    draw = ImageDraw.Draw(card)
    draw.text((16, 9), f'{direction.title()} walks in Eldenmere — actual town renderer',
              font=font, fill=INK)
    if direction == 'back':
        for actor, start in zip(actors, starts):
            x = (start[0]-camera[0])*2
            labels = ('Caelan', 'reference') if actor.actor == 'caelan' else (NAMES[actor.actor],)
            for index, label in enumerate(labels):
                draw.text((x, 681+index*18 if len(labels) == 2 else 691), label,
                          anchor='mt', font=small, fill=INK)
    else:
        for actor, start in zip(actors, starts):
            y = 40+(start[1]-camera[1])*2-30
            draw.rounded_rectangle((14, y, 202, y+34), radius=5, fill=CARD_BG)
            draw.text((24, y+8), NAMES[actor.actor], font=small, fill=INK)
        draw.text((16, 691), f'{WALK_SPEED:g} px/s  ·  four 560 ms gait cycles  ·  fixed camera  ·  review actors only',
                  font=small, fill=INK)
    return card


def capture_direction(world, direction, check_routes=False):
    actors = [PreviewActor(world, actor, direction, 'caelan' if check_routes else None)
              for actor in NAMES]
    starts, camera = find_route(world, actors, direction)
    world.npcs.extend(actors)
    try:
        for time in range(0, DURATION_MS+STEP_MS, STEP_MS):
            for actor, position in zip(actors, route_positions(starts, direction, time)):
                actor.position.update(position)
            for actor in actors:
                assert world.can_stand(actor.position, actor.probe_size, ignore_npc=actor)
                assert unobscured(world, actor, actor.position)
                assert pygame.Rect(camera, VIEW_SIZE).contains(actor.body_rect(actor.position))
        report = {
            'actual_renderer': 'World.draw', 'preview_only': True,
            'world': world.data['id'], 'direction': direction,
            'movement_vector': list(VECTORS[direction]), 'camera': list(camera),
            'native_viewport': list(VIEW_SIZE), 'view_scale': 2,
            'walking_speed_pixels_per_second': WALK_SPEED,
            'gait_period_ms': PERIOD_MS, 'gait_cycles': CYCLES,
            'duration_ms': DURATION_MS, 'frame_step_ms': STEP_MS,
            'expected_frame_count': DURATION_MS//STEP_MS,
            'distance_pixels': WALK_SPEED*DURATION_MS/1000,
            'collision_free_paths': True, 'unobscured_body_bounds': True,
            'trajectory_samples_per_actor_including_endpoint': DURATION_MS//STEP_MS+1,
            'static_world_time_ms': 0,
            'map_actors_removed_for_review': True,
            'actors': [{
                'character': actor.actor, 'label': NAMES[actor.actor],
                'animation': (actor.folder/'animation.json').relative_to(ROOT).as_posix(),
                'foot_anchor': list(actor.draw_anchor), 'frame_size': list(actor.body_size),
                'frame_files': [frame['file'] for frame in actor.meta['frames']],
                'frame_sha256': [hashlib.sha256((actor.folder/frame['file']).read_bytes()).hexdigest()
                                 for frame in actor.meta['frames']],
                'frame_durations_ms': actor.durations, 'route_start': list(start),
                'route_end': list(end),
            } for actor, start, end in zip(actors, starts,
                                           route_positions(starts, direction, DURATION_MS))],
        }
        if check_routes:
            return report
        font_path = ROOT/'assets/ui/fonts/DejaVuSans.ttf'
        font = ImageFont.truetype(str(font_path), 18)
        small = ImageFont.truetype(str(font_path), 15)
        native = pygame.Surface(VIEW_SIZE)
        hidden_player = type('HiddenPlayer', (), {'story_visible': False})()
        frames = []
        for time in range(0, DURATION_MS, STEP_MS):
            for actor, position in zip(actors, route_positions(starts, direction, time)):
                actor.position.update(position)
                actor.clock_ms = time
            # World.draw handles actual sprite anchoring, depth, and scenery.
            # Freezing only world time isolates the authored walking motion.
            world.draw(native, camera, hidden_player, 0, include_ui=False)
            image = Image.frombytes('RGB', VIEW_SIZE, pygame.image.tobytes(native, 'RGB'))
            image = image.resize((960, 640), Image.Resampling.NEAREST)
            frames.append(annotate(image, direction, actors, starts, camera, font, small))
        sprite_colors = actor_palette(actors)
        reserved = list(dict.fromkeys(sprite_colors+[CARD_BG, INK]))
        palette = fixed_palette(frames[0], reserved)
        reserved_indices = {color: index for index, color in enumerate(reserved)}
        indexed = [encode_frame(frame, palette, reserved_indices, actors, starts,
                                direction, index*STEP_MS, camera)
                   for index, frame in enumerate(frames)]
        gif = OUT/f'world_{direction}.gif'
        indexed[0].save(gif, save_all=True, append_images=indexed[1:],
                        duration=STEP_MS, loop=0, disposal=1, optimize=False)
        frames[0].save(OUT/f'world_{direction}.png')
        with Image.open(gif) as image:
            durations = [frame.info['duration'] for frame in ImageSequence.Iterator(image)]
            assert image.n_frames == DURATION_MS//STEP_MS
            assert durations == [STEP_MS]*(DURATION_MS//STEP_MS)
            assert sum(durations) == DURATION_MS and image.info['loop'] == 0
        # Verify reserved sprite colors survive palette construction exactly.
        table = palette.getpalette()
        assert [tuple(table[index*3:index*3+3]) for index in range(len(reserved))] == reserved
        report.update(gif=gif.name, png=f'world_{direction}.png',
                      actual_frame_count=len(durations), gif_loop=0,
                      gif_frame_durations_ms=durations,
                      exact_reserved_sprite_colors=len(sprite_colors),
                      exact_opaque_sprite_pixels_preserved=True)
        (OUT/f'world_{direction}.json').write_text(json.dumps(report, indent=2)+'\n')
        return report
    finally:
        world.npcs.clear()


def capture(check_routes=False, directions=None):
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    if not check_routes:
        OUT.mkdir(parents=True, exist_ok=True)
    try:
        world = World()
        # These are transient review actors. Clear existing actor-dependent
        # drawings as well as blockers, without editing any map or story data.
        world.npcs.clear()
        world.work_fittings.clear()
        world.routine_props.clear()
        reports = [capture_direction(world, direction, check_routes)
                   for direction in (directions or VECTORS)]
        print(json.dumps(reports, indent=2))
    finally:
        pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-routes', action='store_true',
                        help='validate all routes using Caelan, without writing review media')
    parser.add_argument('--direction', choices=tuple(VECTORS),
                        help='capture one completed direction; default: all three')
    args = parser.parse_args()
    capture(args.check_routes, [args.direction] if args.direction else None)
