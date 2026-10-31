"""Replay catalogue: metadata, minimal prerequisites and bounded production cues.

The UI never knows quest internals. Each entry prepares a fresh, non-persistent
Game and delegates animation, dialogue and effects to its existing controller.
Only the setup is manufactured; no story lines or animation clocks are copied.
"""
from dataclasses import dataclass
from functools import partial
from typing import Callable

import pygame

from quests import OPENING_QUEST, MILL_QUEST, REGENT_QUEST, LANTERN_QUEST


DIALOGUE_CONTROLS = 'Space / E / click: dialogue · Esc: Gallery'
AUTOMATIC_CONTROLS = 'Plays automatically · Esc: Gallery'


class GalleryPlayback:
    """A preview boundary around a production controller, not a scene engine."""
    def __init__(self, game):
        self.game = game
        self.finished = False
        self.elapsed = 0.
        self.error = None
        self.hold_seconds = .65
        self._predicate = lambda: False
        self._drive = lambda: None
        self._done = False
        self._settled = 0.

    @property
    def settling(self):return self._done

    def done(self):
        self._done = True
        return True

    def watch(self, predicate, drive=None):
        self._predicate = predicate
        if drive is not None:self._drive = drive

    def update(self, seconds=0.):
        if self.finished:return
        self.elapsed += max(0., seconds)
        if self._done or self._predicate():
            self._done = True
            self._settled += max(0., seconds)
            # Let the final restored pose/prop read before returning to the list.
            if self._settled >= self.hold_seconds:self.finished = True
        else:self._drive()


@dataclass(frozen=True)
class GalleryEntry:
    id: str
    name: str
    chapter: str
    description: str
    thumbnail: str
    controls: str
    fixture: Callable

    def start(self, game):
        # Callers must create an isolated Game. This is a second safety boundary
        # in addition to Game's disabled preview SaveStore and save guard.
        if not getattr(game, '_is_gallery_preview', False) or game.save_store.enabled:
            raise ValueError('Cutscene previews require an isolated, non-persistent Game')
        playback = GalleryPlayback(game)
        game.on_title = False
        game.opening_fade = game.transfer_cooldown = 0.
        self.fixture(game, playback)
        game.quests.drain_events();game.quest_ui.reset()
        game.camera.reset()
        return playback


def _station(game, world, position, facing='back'):
    game.world = world
    game.player.position.update(position)
    game.player.facing = facing
    game.player.moving = game.player.running = False
    game.social.blocked.clear()
    game.opening_fade = game.transfer_cooldown = 0.


def _complete_objectives(game, quest, identifiers):
    for identifier in identifiers:
        if not game.quests.complete_objective(quest, identifier):
            raise ValueError(f'Gallery prerequisite could not complete {quest}/{identifier}')


def _households(game, completed=('halden', 'elira', 'venn')):
    if not game.accept_quest(OPENING_QUEST):raise ValueError('Cannot prepare opening quest')
    _complete_objectives(game, OPENING_QUEST, completed)
    game._sync_inventory()
    game.halden_visit.restore();game.elira_visit.restore();game.venn_visit.restore()


def _mill_available(game):
    _households(game)
    if not game.quests.turn_in(OPENING_QUEST, 'mother_serene'):raise ValueError('Cannot finish opening quest')
    game.quests.unlock(MILL_QUEST)
    game.opening_conclusion.restore({'version': 1, 'stage': 'done'})
    game.opening.restore({'version': 1, 'stage': 'disabled'})


def _mill_checkpoint(game, stage):
    """Use current v2 facts, including the finished encounter for intake scenes."""
    _mill_available(game)
    game.accept_quest(MILL_QUEST)
    objectives = ['meet_mira', 'diagnose_mill', 'prepare_journey']
    facts = dict(version=2, inspected=['mechanism', 'race'], prepared=False,
                 spell_done=False, encouraged=False, restored=False, verified=False,
                 resolved=False, warned=True, encounter_cleared=False,
                 aftermath_done=False, legacy_bypass=False)
    if stage != 'encounter':
        objectives += ['secure_trail', 'reach_intake']
        facts.update(inspected=['mechanism', 'race', 'intake'], encounter_cleared=True,
                     aftermath_done=True)
    if stage in ('spell', 'repair', 'completed'):
        objectives.append('prepare_intake');facts['prepared'] = True
    if stage in ('repair', 'completed'):
        objectives.append('small_spell');facts.update(spell_done=True, encouraged=True)
    if stage == 'completed':
        objectives += ['repair_intake', 'verify_mill', 'report']
        facts.update(restored=True, verified=True, resolved=True)
    _complete_objectives(game, MILL_QUEST, objectives)
    if stage == 'completed':
        if not game.quests.turn_in(MILL_QUEST, 'mira_worker'):raise ValueError('Cannot finish mill quest')
        game.quests.unlock(REGENT_QUEST)
    if not game.mill_quest.restore(facts):raise ValueError('Invalid mill preview checkpoint')


def _regent_checkpoint(game, stage):
    from regent_quest import OBJECTIVES, PREFIX
    _mill_checkpoint(game, 'completed')
    # Subsequent present-day scenes take place after the standalone arrival.
    game.regent_arrival.restore({'version': 1, 'state': 'seen'})
    game.accept_quest(REGENT_QUEST)
    _complete_objectives(game, REGENT_QUEST, OBJECTIVES[:PREFIX[stage]])
    if stage == 'done':
        if not game.quests.turn_in(REGENT_QUEST, 'mother_serene'):raise ValueError('Cannot finish regent quest')
        game.quests.unlock(LANTERN_QUEST)
    if not game.regent_quest.restore({'version': 1, 'stage': stage}):raise ValueError('Invalid regent checkpoint')


def _lantern_checkpoint(game, stage, world, position):
    from lantern_quest import OBJECTIVES, PREFIX
    _regent_checkpoint(game, 'done')
    game.accept_quest(LANTERN_QUEST)
    _complete_objectives(game, LANTERN_QUEST, OBJECTIVES[:PREFIX[stage]])
    _station(game, world, position)
    if not game.lantern_quest.restore({'version': 1, 'stage': stage}):raise ValueError('Invalid lantern checkpoint')


def _opening_film(game, playback):
    playback.hold_seconds = 0.
    game.opening_audio.set_paused(True)
    game.opening_cinematic.start(playback.done)
    game.music.play('opening_leitmotif', fade_ms=0)


def _morning(game, playback, breakfast=False):
    if breakfast:
        game.opening.restore({'version': 1, 'stage': 'explore'})
        _station(game, game._scene_by_id('sanctuary_dining'), (132, 240))
        if not game.opening._start_breakfast():raise ValueError('Cannot start breakfast')
        playback.watch(lambda: game.opening.stage == 'assignment' and not game.social.active)
    else:
        game.opening.start_new_game()
        playback.watch(lambda: game.opening.stage == 'explore' and not game.social.active)


def _halden_visit(game, playback, sack=False):
    game.accept_quest(OPENING_QUEST)
    controller = game.halden_visit
    _station(game, controller.home, (128, 292) if sack else (192, 200))
    controller.restore()
    if sack:
        if not game.deliver_quest_item(OPENING_QUEST, 'halden', 'halden'):
            raise ValueError('Cannot prepare Halden medicine')
        if not controller.interact():raise ValueError('Cannot start Tomas’s sack carry')
        playback.watch(lambda: 1 in controller.stored and controller.tomas_job is None)
    else:
        if not controller.try_conversation(controller.halden):raise ValueError('Cannot start Halden arrival')
        playback.watch(lambda: controller.medicine and controller.action is None and not game.social.active)


def _halden_arrival(game, playback):
    _households(game)
    controller = game.opening_conclusion
    _station(game, controller.hall, (184, 258))
    controller._place(controller.serene, controller.hall, (184, 230))
    controller.serene.select_step('move_to_hall_table', position=(184, 230), scene_id='sanctuary_hall')
    controller.reported()
    playback.watch(lambda: controller.stage == 'done' and not game.social.active)


def _venn(game, playback, method):
    from venn_visit import PIN_APPROACH
    _households(game, ('halden',))
    if not game.deliver_quest_item(OPENING_QUEST, 'venn', 'venn'):raise ValueError('Cannot prepare Venn delivery')
    controller = game.venn_visit
    controller.inspected = {'pin', 'channel'}
    _station(game, game.town, PIN_APPROACH, 'right')
    if not controller._select_method(method):raise ValueError('Cannot start gate repair')
    playback.watch(lambda: controller.repaired and controller.action is None and not game.social.active)


def _elira(game, playback, placement=False):
    from elira_visit import STOOL_APPROACH, TABLE_APPROACH
    _households(game, ('halden',))
    if not game.deliver_quest_item(OPENING_QUEST, 'elira', 'elira'):raise ValueError('Cannot prepare Elira delivery')
    controller = game.elira_visit
    _station(game, controller.home, TABLE_APPROACH if placement else STOOL_APPROACH)
    controller.restore({'version': 1, 'lantern': 'carried' if placement else 'shelf'})
    if not controller.interact():raise ValueError('Cannot start memorial lantern action')
    playback.watch(lambda: controller.action is None and controller.lantern == ('table' if placement else 'carried'))


def _mill_action(game, playback, action):
    _mill_checkpoint(game, action)
    controller = game.mill_quest
    key = {'prepare': 'bypass', 'spell': 'spell', 'repair': 'lever'}[action]
    _station(game, controller.upstream, controller.points[key], 'right')
    # Same authored stations used by the real alignment controller, without a
    # preceding walk through the quest. The action itself still performs checks.
    controller._place_mira(controller.upstream, controller.layout['mira_'+key])
    spoken = {'prepare': 'prepare', 'spell': 'spell_intro', 'repair': 'repair'}[action]
    if not controller._speak(spoken, lambda: controller._start_action(action)):
        raise ValueError('Cannot start intake scene')
    fact = {'prepare': 'prepared', 'spell': 'encouraged', 'repair': 'restored'}[action]
    playback.watch(lambda: getattr(controller, fact) and controller.action is None and not game.social.active)


def _mill_encounter(game, playback):
    _mill_checkpoint(game, 'encounter')
    controller = game.mill_quest
    _station(game, controller.upstream, controller.upstream.data['spawn'])
    controller._place_mira(controller.upstream, game.player.position+(24, 8))
    if not controller.begin_encounter(playback.done):raise ValueError('Cannot start millrace encounter')


def _arrival(game, playback):
    playback.hold_seconds = 0.
    _mill_checkpoint(game, 'completed')
    preferred = game.mill_quest.points['halden_resolution']
    clear = next((pygame.Vector2(preferred)+offset
                  for offset in ((0, 0), (0, 12), (12, 0), (-12, 0), (0, -12), (24, 0))
                  if game.town.can_stand(pygame.Vector2(preferred)+offset)), None)
    if clear is None:raise ValueError('No clear arrival witness station')
    _station(game, game.town, clear)
    # Request exactly the production pending->active arrival boundary.
    if not game.regent_arrival.request() or not game.regent_arrival.maybe_start():
        raise ValueError('Cannot start Aldric arrival')
    playback.watch(lambda: game.regent_arrival.arrival_complete and not game.regent_arrival.active)


def _cart(game, playback):
    _regent_checkpoint(game, 'dispute')
    controller = game.regent_quest
    _station(game, game.town, (610, 548))
    # Reconstruct the authored stations around the actual preview witness.
    controller.restore({'version': 1, 'stage': 'dispute'})
    def drive():
        if controller.stage == 'dispute' and not game.social.active:controller.interact()
    playback.watch(lambda: controller.stage == 'escorting' and controller._delivery_done, drive)
    drive()


def _lantern(game, playback, segment):
    controller = game.lantern_quest
    configs = {
        'frame': ('workshop', 'frame_ready', game.town, controller.points['workshop']),
        'collect': ('collecting_route', 'materials_collected', game.town, controller.rest_points['collection']),
        'homecoming': ('materials_collected', 'materials_home', controller.liam_home, controller.rest_points['home']),
        'paper': ('rested', 'paper_tried', controller.liam_home, controller.rest_points['home']),
        'finish': ('home_rejoined', 'lantern_finished', controller.liam_home, controller.finish_points['home']),
        'putaway': ('homeward', 'done', controller.liam_home, controller.finish_points['home']),
    }
    start, end, world, point = configs[segment]
    _lantern_checkpoint(game, start, world, point)
    def drive():
        if controller.stage != end and not game.social.active and controller.action is None:
            controller.interact()
    playback.watch(lambda: controller.stage == end and controller.action is None and not game.social.active, drive)
    drive()


def _bridge_tea(game, playback):
    world = game.overworld_world
    _station(game, world, (-2376, 642))
    controller = world.bridge_crew
    controller.restore({'sorted': 3, 'tea_beat': 0, 'request_read': False, 'greeted': []})
    if not game.overworld_travel.interact():raise ValueError('Cannot start the bridge tea break')
    def drive():
        if controller.stage in ('request', 'exchange') and not game.social.active:
            game.overworld_travel.interact()
    playback.watch(lambda: controller.state['tea_beat'] == 5 and not game.social.active, drive)


def _grain_extra(game, playback):
    from grain_farm import MILL_FLAG
    _mill_checkpoint(game, 'completed')
    game.social.flags.add(MILL_FLAG)
    world = game.overworld_world
    _station(game, world, (-870, 203))
    controller = world.grain_farm
    controller.restore({'loaded': 2, 'exchange_read': False, 'scene_done': False, 'greeted': []})
    # The finite loading and the coworker's circuit are prerequisite work. Both
    # workers begin at their real waiting stations; the exchange and cooperative
    # lowering that follow are entirely driven by GrainFarm.
    controller.coworker_stop = 6
    controller._stage('ready')
    if not game.overworld_travel.interact():raise ValueError('Cannot start the grain exchange')
    playback.watch(lambda: controller.state['scene_done'] and not game.social.active)


def _entry(identifier, name, chapter, description, fixture, automatic=False):
    return GalleryEntry(identifier, name, chapter, description,
                        f'assets/ui/gallery/{identifier}.png',
                        AUTOMATIC_CONTROLS if automatic else DIALOGUE_CONTROLS, fixture)


GALLERY_ENTRIES = (
    _entry('later_journey', 'A Light in the Distance', 'Prologue',
           'Caelan and Mira share a quiet moment later in their journey.', _opening_film, True),
    _entry('morning_wake', 'Morning Bells', 'A Day Like Any Other',
           'A knock at the sanctuary bedroom wakes Caelan.', partial(_morning, breakfast=False)),
    _entry('morning_breakfast', 'Breakfast at the Sanctuary', 'A Day Like Any Other',
           'Join Tomas and Mother Serene for the opening morning meal.', partial(_morning, breakfast=True)),
    _entry('halden_medicine', 'Medicine for Halden', 'A Day Like Any Other',
           'Visit Halden with Tomas and pass along Serene’s medicine.', partial(_halden_visit, sack=False)),
    _entry('tomas_sack', 'Tomas Lends a Hand', 'A Day Like Any Other',
           'Tomas lifts, carries and stores one grain sack on the dry pallet.', partial(_halden_visit, sack=True), True),
    _entry('elira_lantern_retrieval', 'The Memorial Lantern', 'A Day Like Any Other',
           'Caelan climbs the stool to retrieve Elira’s lantern.', partial(_elira, placement=False), True),
    _entry('elira_lantern_placement', 'A Lantern Remembered', 'A Day Like Any Other',
           'Set the memorial lantern carefully on Elira’s table.', partial(_elira, placement=True), True),
    _entry('venn_failed_spell', 'A Spell That Will Not Take', 'A Day Like Any Other',
           'A failed spell gives way to a practical repair at the Venn channel.', partial(_venn, method='magicks')),
    _entry('venn_gate_repair', 'Borrowed Tools', 'A Day Like Any Other',
           'Free the gate pin, clear the twigs and restore the channel.', partial(_venn, method='tools'), True),
    _entry('halden_arrival', 'Trouble at the Mill', 'A Day Like Any Other',
           'Halden enters the sanctuary with news of the stopped mill.', _halden_arrival),
    _entry('millrace_threat', 'A Boar by the Millrace', 'Mira’s Mill Quest',
           'The camera reveals the threat and returns for Mira’s warning. Ends before combat.', _mill_encounter),
    _entry('mill_bypass', 'Make Room for the Water', 'Mira’s Mill Quest',
           'Caelan and Mira set the intake bypass together.', partial(_mill_action, action='prepare')),
    _entry('mill_small_spell', 'A Smaller Magical Success', 'Mira’s Mill Quest',
           'Move a little still water and hear Mira’s encouragement.', partial(_mill_action, action='spell')),
    _entry('mill_repair', 'Freeing the Intake', 'Mira’s Mill Quest',
           'A lever, a haul rope and two pairs of hands restore the mill.', partial(_mill_action, action='repair')),
    _entry('regent_arrival', 'Aldric’s Relief Caravan', 'The Regent’s Road',
           'The present-day caravan reaches Eldenmere after the mill is restored.', _arrival),
    _entry('regent_cart_release', 'The Road Crew’s Cart', 'The Regent’s Road',
           'Witness the dispute and Mr. Venn hauling the released cart away.', _cart),
    _entry('lantern_frame', 'A Frame of His Own', 'Liam’s First Lantern',
           'Try the design, assemble the tower frame and help Liam lift it.', partial(_lantern, segment='frame')),
    _entry('lantern_collect', 'Gathering the Materials', 'Liam’s First Lantern',
           'Liam collects the frame and paper from Mira’s workbench.', partial(_lantern, segment='collect')),
    _entry('lantern_homecoming', 'A Place at the Table', 'Liam’s First Lantern',
           'Bring the lantern materials home and set them down safely.', partial(_lantern, segment='homecoming')),
    _entry('lantern_paper_practice', 'The First Paper Window', 'Liam’s First Lantern',
           'Liam tries his first paper design at the family table.', partial(_lantern, segment='paper')),
    _entry('lantern_finishing', 'Finishing Liam’s Lantern', 'Liam’s First Lantern',
           'Choose the design, fit and fasten the covering, then lift the finished lantern.', partial(_lantern, segment='finish')),
    _entry('lantern_putaway', 'Safe Until Tomorrow', 'Liam’s First Lantern',
           'Put the finished lantern away and say goodbye for the afternoon.', partial(_lantern, segment='putaway')),
    _entry('grain_extra_sack', 'One Sack Too Many', 'Elden Vale',
           'A quiet disagreement by the grain cart ends with a shared lift.', _grain_extra),
    _entry('bridge_tea', 'Tea by the Broken Bridge', 'Elden Vale',
           'The repair crew sets down a cup, steadies a tray and takes a short break.', _bridge_tea),
)

GALLERY_BY_ID = {entry.id: entry for entry in GALLERY_ENTRIES}
