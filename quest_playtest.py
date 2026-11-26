"""Explicit, disposable before-acceptance starts for shipped quest content."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from quests import OPENING_QUEST, MILL_QUEST, QuestLog

if TYPE_CHECKING:
    from main import Game, World


QUEST_ORDER = (OPENING_QUEST, MILL_QUEST)


@dataclass(frozen=True)
class QuestPlaytestEntry:
    id: str
    name: str
    chapter: str
    description: str


def quest_entries(quests: QuestLog | None = None) -> tuple[QuestPlaytestEntry, ...]:
    definitions = (quests if quests is not None else QuestLog()).definitions
    starts = (
        'Start at home before Serene gives Caelan his household visits.',
        'Start by Mira at her workshop, before accepting the mill outing.',
    )
    return tuple(QuestPlaytestEntry(identifier, definitions[identifier]['title'],
                                   f'{identifier} - Playable quest',
                                   description)
                 for identifier, description in zip(QUEST_ORDER, starts))


def _require(result: bool, action: str) -> None:
    if not result:
        raise ValueError(f'Could not prepare quest playtest: {action}.')


def _place_player(game: Game, world: World, point, facing: str = 'back') -> None:
    for radius in (0, 8, 16, 24, 32, 48):
        for dx, dy in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
            position = (point[0]+dx, point[1]+dy)
            if world.can_stand(position):
                game.world = world
                game.player.position.update(position)
                game.player.facing = facing
                game.player.moving = game.player.running = False
                game.player.walk_ms = 0
                if world is game.town:
                    game.exterior_position.update(position)
                return
    raise ValueError('Could not prepare quest playtest: no clear starting position.')


def _complete_objectives(game: Game, identifier: str) -> None:
    for objective in game.quests.definitions[identifier]['objectives']:
        _require(game.quests.complete_objective(identifier, objective['id']),
                 f'{identifier}/{objective["id"]}')


def _completed_opening(game: Game) -> None:
    _require(game.accept_quest(OPENING_QUEST), 'accept previous household visits')
    _complete_objectives(game, OPENING_QUEST)
    game._sync_inventory()
    _require(game.halden_visit.restore(), 'restore Halden')
    _require(game.elira_visit.restore(), 'restore Elira')
    _require(game.venn_visit.restore({
        'version': 2, 'inspected': ['pin', 'channel'], 'method': 'tools',
        'repaired': True, 'magicks_failed': False}), 'restore the repaired Venn gate')
    game.social.flags.add('CH01_MQ01_VENN_METHOD_TOOLS')
    _require(game.quests.turn_in(OPENING_QUEST, 'mother_serene'), 'report previous visits')
    game.social.flags.update({'CH01_MQ01_REPORTED', 'CH01_MQ01_COMPLETE'})
    game.opening_conclusion.restore({'version': 1, 'stage': 'done'})
    _require(game.opening_conclusion.stage == 'done', 'restore the mill handoff')
    _require(game.opening.restore({'version': 1, 'stage': 'disabled'}), 'finish the morning')
    _require(game.quests.unlock(MILL_QUEST), 'unlock the mill quest')








def prepare_quest(game: Game, identifier: str) -> None:
    """Prepare a fresh private game, never an existing or persistent journey."""
    if (not game._is_quest_playtest or game.save_store.enabled or game.audio.store.enabled
            or game.on_title):
        raise ValueError('Quest starts require a temporary playtest session.')
    if identifier not in QUEST_ORDER:
        raise ValueError(f'Unsupported quest playtest: {identifier}')
    if game.quests.to_dict() != QuestLog().to_dict():
        raise ValueError('Quest playtests must start from a fresh game.')

    if identifier == OPENING_QUEST:
        _require(game.opening.restore({'version': 1, 'stage': 'assignment'}),
                 "prepare Serene's assignment")
        _place_player(game, game._scene_by_id('sanctuary_dining'), (288, 238))
    elif identifier == MILL_QUEST:
        _completed_opening(game)
        point = game.mill_quest.bench_position
        _place_player(game, game.town, (point[0]-16, point[1]+16))
    for index, key in enumerate(QUEST_ORDER):
        expected = ('completed' if index < QUEST_ORDER.index(identifier) else
                    'available' if key == identifier else 'locked')
        _require(game.quests.status(key) == expected, f'{key} starting status')
    _require(not game.quests.states[identifier]['completed_objectives'],
             'keep the selected quest untouched')
    game._sync_inventory()
    _require(game._sync_story_party(), 'reconcile the starting party')
    game.social.blocked.clear()
    game.social.clear_pointer()
    game.quests.drain_events()
    game.quest_ui.reset()
    game.camera.reset()
    game.opening_fade = game.transfer_cooldown = 0
    game.location_seconds = 3.5
