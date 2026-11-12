"""Explicit, disposable before-acceptance starts for shipped quest content."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from post_battle import battle_reward_definition
from quests import OPENING_QUEST, MILL_QUEST, REGENT_QUEST, LANTERN_QUEST, QuestLog

if TYPE_CHECKING:
    from main import Game, World


QUEST_ORDER = (OPENING_QUEST, MILL_QUEST, REGENT_QUEST, LANTERN_QUEST)
SKIPPED_MQ03_XP = 5500  # Total cave allowance, including its authored bosses.
EARLY_PARTY = ('caelan', 'mira')


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
        'Start with the regent arrival, before Serene assigns the visit. '
        'In development: the quest ending is not implemented.',
        'Start at home before Tomas invites Caelan to the lantern preparations. '
        'Uses a test-only completed visit to reach this independently playable quest.',
    )
    return tuple(QuestPlaytestEntry(identifier, definitions[identifier]['title'],
                                   f'{identifier} - '+('In development' if identifier == REGENT_QUEST
                                                       else 'Playable quest'),
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


def _completed_mill(game: Game) -> None:
    _completed_opening(game)
    _require(game.accept_quest(MILL_QUEST), 'accept the previous mill outing')
    _require(game.quests.complete_objective(MILL_QUEST, 'meet_mira'), 'meet Mira')
    _require(game._sync_story_party(), 'recruit Mira for the previous outing')
    _require(game.acquire_weapon('caelan', 'caelan_gearblade'), 'receive the first gearblade')
    reward = battle_reward_definition('mill')
    _require(game.award_battle_rewards('mq02:ridgeback_tusker', reward['drops']),
             'record the required riverbank victory')
    members = ['caelan', 'mira']
    plan = game.character_progression.preview(
        reward['xp'], members, {key: game.party.characters[key].current_hp for key in members})
    _require(game.character_progression.apply(plan), 'restore required encounter EXP')
    for objective in game.quests.definitions[MILL_QUEST]['objectives'][1:]:
        _require(game.quests.complete_objective(MILL_QUEST, objective['id']),
                 f'previous mill/{objective["id"]}')
    _require(game.quests.turn_in(MILL_QUEST, 'mira_worker'), 'finish the previous mill outing')
    _require(game.mill_quest.restore({
        'version': 2, 'inspected': ['mechanism', 'race', 'intake'],
        'prepared': True, 'spell_done': True, 'encouraged': True,
        'restored': True, 'verified': True, 'resolved': True,
        'warned': True, 'encounter_cleared': True, 'aftermath_done': True,
        'legacy_bypass': False, 'reported_to_halden': True, 'cups_placed': True,
    }), 'restore the completed modern mill and table setting')
    game.social.flags.update({'CH01_MQ02_ENCOUNTER_CLEARED', 'CH01_MQ02_SMALL_MAGICK',
                              'CH01_MQ02_MILL_RESTORED', 'CH01_MQ02_COMPLETE'})
    _require(game._sync_story_party(), "finish Mira's previous outing")
    if game.quests.status(REGENT_QUEST) == 'locked':
        _require(game.quests.unlock(REGENT_QUEST), 'unlock the regent quest')


def _completed_cave(game: Game) -> None:
    """Seed the canonical completed-cave route without stacking boss EXP.

    The two optional focuses are included in this later-story test checkpoint;
    optional treasure containers remain untouched. No live combat is settled.
    """
    from elemental_bosses import REGISTRY
    owner = game.character_abilities
    _require(owner.learn_ability('caelan', 'aqua_edge'), 'restore Aqua Edge discovery')
    _require(game.cave_lesson.restore({'version': 1, 'resonance_seen': True,
                                     'battle_cleared': True, 'deferred': False}),
             'restore the completed bat lesson')
    state = game.elemental_bosses.to_dict()
    for enemy_id, entry in REGISTRY.items():
        _require(game.award_battle_rewards(entry['receipt'], {entry['item']: 1}),
                 f'restore {enemy_id} focus receipt')
        _require(owner.grant_gem(entry['gem']), f'install {entry["gem"]} focus')
        _require(owner.learn_ability('caelan', entry['skill']), f'learn {entry["skill"]}')
        state['bosses'][enemy_id].update(discovered=True, intro_seen=True,
                                       defeated=True, pending_acquisition=False)
        state['victory_order'].append(enemy_id)
    _require(game.elemental_bosses.restore(state), 'acknowledge previous focus installations')
    reward = battle_reward_definition('cave_boss')
    _require(game.award_battle_rewards('boss:vespermaw', reward['drops']),
             'restore Vespermaw reward receipt')
    _require(game.sanctuary_boss.restore({'version': 1, 'defeated': True,
                                       'intro_seen': True, 'pending': None}),
             'restore defeated Vespermaw')
    _require(owner.set_active_gem('water'), 'select the Blue focus')
    from sanctuary_arrival_party import REQUIRED as rescue_party
    _require(game.party.active_ids == rescue_party, 'restore the acknowledged cave rescue formation')
    plan = game.character_progression.preview(
        SKIPPED_MQ03_XP, rescue_party,
        {key: game.party.characters[key].current_hp for key in rescue_party})
    _require(game.character_progression.apply(plan), 'grant skipped MQ03 cave EXP')


def _completed_visit(game: Game) -> None:
    _completed_mill(game)
    _require(game.regent_arrival.restore({'version': 1, 'state': 'seen'}),
             'restore the previous arrival')
    _require(game.accept_quest(REGENT_QUEST), 'prepare the test-only completed visit')
    objectives = game.quests.definitions[REGENT_QUEST]['objectives']
    for objective in objectives[:-1]:
        _require(game.quests.complete_objective(REGENT_QUEST, objective['id']),
                 f'previous visit/{objective["id"]}')
    _require(game.regent_quest.restore({'version': 3, 'stage': 'sanctuary_arrival_pending'}),
             'restore the previous Sanctuary response')
    # Apply its acknowledged consequences, without running the arrival movie in
    # a later-quest fixture. Lucan shares the same cave allowance as the others.
    _require(game.sanctuary_arrival.restore({'version': 1, 'beat': 7,
                                          'completed': True, 'cave_entered': True}),
             'restore the previous Sanctuary rescue handoff')
    _require(game._sync_story_party(), 'restore the cave rescue trio')
    _completed_cave(game)
    _require(game.quests.complete_objective(REGENT_QUEST, objectives[-1]['id']),
             'finish the previous Sanctuary response')
    _require(game.quests.turn_in(REGENT_QUEST, 'mother_serene'), 'close the test-only visit')
    _require(game.regent_quest.restore({'version': 3, 'stage': 'done'}),
             'restore the supported completed-visit setup')
    _require(game._sync_story_party(), 'finish Lucan’s temporary rescue outing')
    game.social.flags.add('CH01_MQ03_COMPLETE')
    if game.quests.status(LANTERN_QUEST) == 'locked':
        _require(game.quests.unlock(LANTERN_QUEST), 'unlock the lantern quest')
    _require(game.lantern_quest.restore(), 'prepare the lantern invitation')


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
    elif identifier == REGENT_QUEST:
        _completed_mill(game)
        _require(game.regent_quest.restore(), 'prepare the visiting party')
        _place_player(game, game._scene_by_id('sanctuary_dining'), (252, 224))
        _require(game.regent_arrival.request(), "queue the regent's opening arrival")
    else:
        _completed_visit(game)
        _place_player(game, game.lantern_quest.invitation_world,
                      game.lantern_quest.points['invitation'])

    for index, key in enumerate(QUEST_ORDER):
        expected = ('completed' if index < QUEST_ORDER.index(identifier) else
                    'available' if key == identifier else 'locked')
        _require(game.quests.status(key) == expected, f'{key} starting status')
    _require(not game.quests.states[identifier]['completed_objectives'],
             'keep the selected quest untouched')
    game._sync_inventory()
    _require(game._sync_story_party(), 'reconcile the starting party')
    if QUEST_ORDER.index(identifier) >= QUEST_ORDER.index(REGENT_QUEST):
        # The completed outing recruited Mira. In a playtest she is usable even
        # when the tester heads straight to the cave before MQ03's rejoin prose.
        # The normal story handoff can still require her for the Sanctuary trip.
        _require(game.party.set_available('mira', True), 'make previously recruited Mira available')
        _require(game.party.select(EARLY_PARTY), 'restore the earlier combat party')
        for key in EARLY_PARTY:game.party.characters[key].recover()
    game.social.blocked.clear()
    game.social.clear_pointer()
    game.quests.drain_events()
    game.quest_ui.reset()
    game.camera.reset()
    game.opening_fade = game.transfer_cooldown = 0
    game.location_seconds = 3.5
    if identifier == REGENT_QUEST:
        _require(game.regent_arrival.maybe_start(), 'start the regent arrival')
