"""Opt-in Serene story drawings; legacy actors and other scene art stay unchanged."""
from rendering import load_art

SPRITE_ROOT = 'assets/characters/named_hd/serene'
ACTION_ROOT = 'assets/characters/serene/activity_hd'
STORY_PATHS = {
    'assets/story/regent/poses/serene_seated.png': ACTION_ROOT+'/story/seated.png',
    'assets/story/regent_emergency/poses/serene_aid_left.png': ACTION_ROOT+'/story/aid_left.png',
}


def enabled(actor):
    record = getattr(actor, 'data', {})
    return (record.get('id') == 'mother_serene'
            and getattr(actor, 'sprite_root', None) == SPRITE_ROOT
            and getattr(actor, 'animation_path', None) == ACTION_ROOT+'/routines/animations.json')


def image(world, actor, path, legacy_loader):
    """Retain the logical scene canvas/anchor, preserving native buffer detail."""
    replacement = STORY_PATHS.get(path) if enabled(actor) else None
    if replacement is None:
        return legacy_loader(path)
    return load_art(world, replacement, {'artwork_pixels_per_world_pixel': 2})
