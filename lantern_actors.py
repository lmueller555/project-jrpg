"""Temporary directional support for the existing school residents.

The teacher and five other pupils begin as stationary home actors. This helper
borrows those exact objects for a quest-scoped preparation session; it does not
create a second teacher, alter their home records, or install a daily schedule.
"""
import json
from pathlib import Path
from types import MethodType


ROOT = Path(__file__).resolve().parent
DIRECTIONS = ('front', 'left', 'right', 'back')
_MISSING = object()


def _request_conversation(actor, facing):
    actor.conversation_ready = True
    actor.conversation_facing = facing
    actor.moving = False


def _end_conversation(actor):
    actor.conversation_ready = False


class ResidentPose:
    """Call ``sync`` after movement/placement; ``release`` restores home art.

    The actor's normal position remains authoritative for rendering, doors and
    collision. Stationary actors have a stored Rect, so it must be refreshed
    alongside their position rather than leaving a blocker in the old room.
    """

    FIELDS = ('probe_size', 'opens_doors', 'facing', 'moving', 'walk_ms',
              'scene_id', 'sort_y', 'story_sprite', 'story_draw_anchor',
              'conversation_ready', 'conversation_facing',
              'request_conversation', 'end_conversation')

    def __init__(self, actor, world):
        self.actor = actor
        self.original = {key: actor.__dict__.get(key, _MISSING) for key in self.FIELDS}
        root = actor.data.get('sprite_root', f"assets/characters/{actor.data['id']}")
        self.idles = {direction: world.image(f'{root}/idle_{direction}.png')
                      for direction in DIRECTIONS}
        self.walks = {}
        for direction in DIRECTIONS:
            folder = f'{root}/walk_{direction}'
            meta = json.loads((ROOT/folder/'animation.json').read_text())
            self.walks[direction] = [(world.image(f"{folder}/{frame['file']}"),
                                      frame['duration_ms']) for frame in meta['frames']]
        actor.probe_size = tuple(actor.data['probe_size'])
        actor.opens_doors = True
        actor.facing = 'right' if actor.data['id'] == 'liam_mother' else 'front'
        actor.moving = False;actor.walk_ms = 0.;actor.sort_y = None
        actor.scene_id = world.data['id']
        actor.conversation_ready = False;actor.conversation_facing = actor.facing
        actor.request_conversation = MethodType(_request_conversation, actor)
        actor.end_conversation = MethodType(_end_conversation, actor)
        self.released = False
        self.sync()

    def sync(self):
        if self.released:return
        actor = self.actor
        facing = actor.conversation_facing if actor.conversation_ready else actor.facing
        image = self.idles[facing]
        if actor.moving and not actor.conversation_ready:
            frames = self.walks[facing]
            time = actor.walk_ms % sum(duration for _, duration in frames)
            for frame, duration in frames:
                if time < duration:
                    image = frame;break
                time -= duration
        actor.story_sprite = image
        actor.story_draw_anchor = tuple(actor.draw_anchor)
        width, height = actor.probe_size
        actor.blocker.update(round(actor.position.x)-width//2,
                             round(actor.position.y)-height//2, width, height)

    def release(self):
        if self.released:return
        actor = self.actor
        for key, value in self.original.items():
            if value is _MISSING:
                if key in actor.__dict__:delattr(actor, key)
            else:setattr(actor, key, value)
        # The controller returns the same actor home before releasing support.
        width, height = actor.data['probe_size']
        actor.blocker.update(round(actor.position.x)-width//2,
                             round(actor.position.y)-height//2, width, height)
        self.released = True
