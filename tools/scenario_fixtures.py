"""Disposable retained-system fixtures, independent of retired quest stories.

These helpers prepare completed MQ01/MQ02 facts for regional work reviews and
shared-system tests. They never complete the removed regent or festival quests.
"""
from pathlib import Path
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')


def seed_mill_completed(game):
    """Prepare the retained household/mill checkpoint, with no later story."""
    from quest_playtest import _completed_opening
    from quests import OPENING_QUEST, MILL_QUEST
    if game.quests.status(OPENING_QUEST) != 'completed':
        _completed_opening(game)
    if game.quests.status(MILL_QUEST) != 'completed':
        assert game.accept_quest(MILL_QUEST)
        for objective in game.quests.definitions[MILL_QUEST]['objectives']:
            assert game.quests.complete_objective(MILL_QUEST, objective['id'])
        assert game.quests.turn_in(MILL_QUEST, 'mira_worker')
    assert game.mill_quest.restore({
        'version': 2, 'inspected': ['mechanism', 'race', 'intake'],
        'prepared': True, 'spell_done': True, 'encouraged': True,
        'restored': True, 'verified': True, 'resolved': True,
        'warned': True, 'encounter_cleared': True, 'aftermath_done': True,
        'legacy_bypass': False, 'reported_to_halden': True, 'cups_placed': True,
    })
    assert game.opening.restore({'version': 1, 'stage': 'disabled'})
    game._sync_inventory();game._sync_story_party()
    game.world = game.town
    game.player.position.update(game.town.data['spawn'])
    game.player.facing = 'back'
    game.player.moving = game.player.running = False
    game.opening_fade = game.transfer_cooldown = 0
    game.social.cancel_script();game.social.blocked.clear()
    game.quests.drain_events();game.quest_ui.reset();game.camera.reset()
    return game


def make_game(directory=None, *, title=False, seed=False, embedded=True):
    """Create a disposable real Game; optional seed covers retained quests only."""
    import pygame
    from main import Game
    pygame.display.init();pygame.display.set_mode((960, 640))
    kwargs = {}
    if embedded:
        kwargs.update(_preview_window=pygame.Surface((960, 640)), _quest_playtest=True)
    elif directory is not None:
        kwargs.update(save_path=Path(directory)/'journey.json',
                      settings_path=Path(directory)/'settings.json')
    game = Game(window_size=(960, 640), fullscreen=False, start_on_title=title, **kwargs)
    game.audio.set_music(0);game.audio.set_effects(0)
    if seed:seed_mill_completed(game)
    return game


def place_review_actor(actor, world, position):
    """Place an explicit art-review actor without invoking any quest owner."""
    if actor not in world.npcs:world.npcs.append(actor)
    actor.position.update(position);actor.scene_id = world.data['id']
    actor.moving = False;actor.walk_ms = 0.
    actor.end_conversation()


def move_review_actor(actor, world, destination, seconds, speed=74):
    """Advance a straight, collision-checked review lane and its authored clock."""
    import pygame
    from social import facing_toward
    delta = pygame.Vector2(destination)-actor.position
    actor.moving = False
    if delta.length() < 1:return True
    budget = min(delta.length(), max(0., seconds)*speed)
    direction = delta.normalize()
    while budget > 1e-8:
        distance = min(1., budget)
        candidate = actor.position+direction*distance
        if not world.can_stand(candidate, actor.probe_size, actor):return False
        actor.position.update(candidate);actor.facing = facing_toward(direction)
        actor.moving = True;actor.walk_ms += distance/speed*1000
        budget -= distance
    return actor.position.distance_to(destination) < 1
