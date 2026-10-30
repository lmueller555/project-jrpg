"""Walk review captures through the game's real interior doors."""
from collections import deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def travel_to(capture, destination):
    """Use live player movement and door entry, without relocating the party."""
    game = capture.g
    while game.world is not destination:
        origin = game.world
        queue = deque([(origin, None)])
        seen = {origin.path}
        first = None
        while queue:
            world, first_edge = queue.popleft()
            if world is destination:
                first = first_edge
                break
            for door in world.doors:
                other = game._load_scene(ROOT/door.data['destination'])
                if other.path in seen:
                    continue
                seen.add(other.path)
                queue.append((other, first_edge or (door, other)))
        assert first is not None, ('No door route', origin.data['id'], destination.data['id'])
        door, other = first
        capture.walk(door.data['anchor'], next_scene=other.data['id'])
        assert game.world is other, ('Door did not transfer', door.data['id'])
        if hasattr(capture, 'room_transitions'):
            capture.room_transitions.append(dict(origin=origin.data['id'],
                                                destination=other.data['id'],
                                                door=door.data['id']))
