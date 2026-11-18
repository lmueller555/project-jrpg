"""Optional local gestures with safe standing feet and no story progression.

The overlook seat is purely a visual placement. Physical player feet remain at
the clear south approach, including in saves; seated context is validated before
the pose can be restored. Wildlife continues to own the cat and its route.
"""
import copy
import math
from pathlib import Path

import pygame
from regional_audio import Source


ROOT = Path(__file__).resolve().parent
WORLD_ID = 'auratia.overworld'
BENCH_POSITION = (1819.2, -535.2)
STAND_POSITION = (1819.2, -519.2)
SEATED_FACING = 'front'
SIT_ANCHOR = (12, 34)
INSPECT_POSITION = (-2400., 630.)
CAT_COOLDOWN = 8.
CAT_SCRIPT = 'regional_cat_greeting'
MASONRY_SCRIPT = 'regional_masonry_inspection'


def empty_state():
    return {'version': 1, 'seated': False, 'sat': False,
            'cat_greeted': False, 'masonry_read': False, 'cat_cooldown': 0.}


def valid_state(data):
    return (isinstance(data, dict) and set(data) == set(empty_state())
            and type(data['version']) is int and data['version'] == 1
            and all(type(data[key]) is bool for key in
                    ('seated', 'sat', 'cat_greeted', 'masonry_read'))
            and (not data['seated'] or data['sat'])
            and type(data['cat_cooldown']) in (int, float)
            and math.isfinite(data['cat_cooldown'])
            and 0 <= data['cat_cooldown'] <= CAT_COOLDOWN
            and (not data['cat_cooldown'] or data['cat_greeted']))


def valid_context(data, player_record):
    """A remembered seat cannot claim feet in town or elsewhere in the region."""
    if not valid_state(data):return False
    if not data['seated']:return True
    if not isinstance(player_record, dict):return False
    point = player_record.get('position')
    return (player_record.get('scene') == WORLD_ID
            and player_record.get('facing') == SEATED_FACING
            and isinstance(point, list) and len(point) == 2
            and all(type(v) in (int, float) and math.isfinite(v) for v in point)
            and math.dist(point, STAND_POSITION) < .001)


def progress_state(data):
    """Only completed gestures and seat ownership dirty the autosave signature."""
    return {key: value for key, value in data.items() if key != 'cat_cooldown'}


class RegionalParticipation:
    def __init__(self, world):
        self.world = world
        self.sit_sprite = pygame.image.load(str(
            ROOT/'assets/characters/caelan/participation_sit_front.png')).convert_alpha()
        self._pose_player = None
        self._pose_values = {}
        self.restore()

    def restore(self, data=None):
        if data is not None and not valid_state(data):
            raise ValueError('Invalid regional participation state')
        self.release_pose()
        self.state = copy.deepcopy(empty_state() if data is None else data)

    def to_dict(self):return copy.deepcopy(self.state)

    def progress_dict(self):return progress_state(self.to_dict())

    @property
    def locks_player(self):return self.state['seated']

    def release_pose(self, game=None):
        """Release only fields this controller still owns, retaining seat state."""
        player = self._pose_player
        if player is not None and getattr(player, 'story_sprite', None) is self.sit_sprite:
            for key, value in self._pose_values.items():
                if getattr(player, key, None) is value:
                    setattr(player, key, None)
        self._pose_player = None
        self._pose_values = {}

    @staticmethod
    def _blocked_ui(game):
        return (game.on_title or game.pause.is_open or game.inventory_ui.is_open
                or game.world_map_viewer.is_open or game.map_open
                or game.quest_ui.journal_open)

    @staticmethod
    def _other_owner(game):
        return (game.combat.active or game.opening_cinematic.active
                or game.regent_arrival.active or game.social.locked
                or game.household_action or game.opening.locks_player
                or game.opening.controls_player or game.opening.in_action
                or game.mill_quest.encounter_cutscene_active)

    def can_interact(self, game):
        sprite = getattr(game.player, 'story_sprite', None)
        return (game.world is self.world and not self._blocked_ui(game)
                and not self._other_owner(game) and not game.opening_fade
                and not game.transfer_cooldown
                and (sprite is None or sprite is self.sit_sprite))

    def _clear_path(self, start, end):
        start = pygame.Vector2(start);delta = pygame.Vector2(end)-start
        steps = max(1, math.ceil(delta.length()/2))
        return all(self.world.can_stand(start+delta*(i/steps))
                   for i in range(steps+1))

    def _cat(self):return self.world.wildlife.by_id['farm_cat']

    def _cat_available(self, game):
        cat = self._cat()
        # A resting animal acknowledges the greeting without changing its route.
        # In motion it keeps its feet; the existing gardener loan gets priority.
        return (not self.state['cat_cooldown']
                and self.world.wildlife.vignette['phase'] != 'visit'
                and cat.state['mode'] in ('sleep', 'sit')
                and cat.position.distance_to(game.player.position) <= 34)

    def selected_target(self, game):
        """One deterministic selection is shared by the hint and the E action."""
        if not self.can_interact(game):return None
        if self.state['seated']:return 'stand'
        player = game.player
        if (player.position.y >= BENCH_POSITION[1]+9
                and player.position.distance_to(STAND_POSITION) <= 32
                and self._clear_path(player.position, STAND_POSITION)):
            return 'bench'
        if self._cat_available(game):return 'cat'
        crew = self.world.bridge_crew
        if (crew.stage in crew.AMBIENT
                and crew.nearby(game) is None
                and player.position.distance_to(INSPECT_POSITION) <= 28
                and self.world.can_stand(player.position)):
            return 'masonry'
        return None

    def interaction_hint(self, game):
        return {'stand': 'E: Stand up', 'bench': 'E: Sit on the overlook bench',
                'cat': 'E: Greet the farm cat',
                'masonry': 'E: Inspect the unfinished masonry'}.get(self.selected_target(game), '')

    @staticmethod
    def _stop_player(player):
        player.moving = player.running = False
        player.walk_ms = 0.

    def _bind_pose(self, game):
        player = game.player
        current = getattr(player, 'story_sprite', None)
        if current is not None and current is not self.sit_sprite:return False
        self._stop_player(player)
        self._pose_player = player
        self._pose_values = {
            'story_sprite': self.sit_sprite, 'story_draw_anchor': SIT_ANCHOR,
            'story_position': pygame.Vector2(BENCH_POSITION)+(0, 5),
            'story_sort_y': BENCH_POSITION[1]+2.}
        for key, value in self._pose_values.items():setattr(player, key, value)
        return True

    def _seated_context(self, game):
        return (game.world is self.world
                and game.player.position.distance_to(STAND_POSITION) < .001
                and game.player.facing == SEATED_FACING)

    def update(self, seconds, game):
        if self.state['seated']:
            if (not self._seated_context(game) or self._other_owner(game)
                    or not self._bind_pose(game)):
                self.stand(game)
        if not self.can_interact(game):return
        dt = min(.1, max(0., seconds)) if math.isfinite(seconds) else 0.
        self.state['cat_cooldown'] = max(0., self.state['cat_cooldown']-dt)

    def _standing_point(self, position):
        if self.world.can_stand(position):return position
        # A dynamic actor may have occupied the old approach. Resolve nearby
        # clear feet before releasing the visual; never move across a scene.
        for radius in range(4, 97, 4):
            for dx, dy in ((0, radius), (-radius, 0), (radius, 0),
                           (0, -radius), (-radius, radius), (radius, radius)):
                point = (position[0]+dx, position[1]+dy)
                if self.world.can_stand(point):return point
        return position

    def stand(self, game, *, save=True):
        seated = self.state['seated']
        original_approach = self._seated_context(game)
        sprite = getattr(game.player, 'story_sprite', None)
        owns_motion = sprite is None or sprite is self.sit_sprite
        self.state['seated'] = False
        self.release_pose(game)
        if seated:
            if original_approach:
                game.player.position.update(self._standing_point(game.player.position))
            if owns_motion:self._stop_player(game.player)
            if save:game.save_progress()
        return seated

    def cancel(self, game, *, save=True):return self.stand(game, save=save)

    def before_travel(self, game):
        self.stand(game, save=False)

    def request_movement(self, game, direction):
        if (self.state['seated'] and not self._blocked_ui(game)
                and pygame.Vector2(direction).length_squared()):
            return self.stand(game)
        return False

    def handle_event(self, game, event):
        if (not self.state['seated'] or not self.can_interact(game)
                or event.type != pygame.KEYDOWN
                or event.key not in (pygame.K_e, pygame.K_ESCAPE)):
            return False
        if not getattr(event, 'repeat', False):self.stand(game)
        return True

    def interact(self, game):
        target = self.selected_target(game)
        if target is None:return False
        if target == 'stand':return self.stand(game)
        if target == 'bench':
            # The stand point was swept for collision by selected_target.
            game.player.position.update(STAND_POSITION)
            game.player.facing = SEATED_FACING
            self.state.update(seated=True, sat=True)
            self._bind_pose(game)
            # One visible weight contact, through the shared bounded allocator.
            game.regional_audio.play(Source('participation_bench_contact', 'creak',
                'wood_contact', BENCH_POSITION, gain=.24, near=24, far=100,
                priority=2, cooldown=1.2))
            game.save_progress()
            return True
        if target == 'cat':
            cat = self._cat()
            def greet_done():
                if not self.can_interact(game) or not self._cat_available(game):return
                cat.state['facing'] = 'left' if game.player.position.x < cat.position.x else 'right'
                if cat.state['mode'] == 'sleep':
                    self.world.wildlife._mode(cat, 'stretch')
                else:
                    # Preserve the existing endpoint and return target. A brief
                    # turn, then the same owner continues the same route.
                    cat.state.update(clock=0., elapsed=7.8)
                self.state.update(cat_greeted=True, cat_cooldown=CAT_COOLDOWN)
                game.save_progress()
            return game.social.start_script(
                [{'speaker': 'caelan', 'text': 'Hello, you.'}],
                on_complete=greet_done, identifier=CAT_SCRIPT)
        crew = self.world.bridge_crew
        if crew.state['sorted'] == 3:
            text = 'The sound blocks lie apart from the cracked pieces. '
        elif crew.state['sorted']:
            text = 'The crew is sorting the loose blocks beside the work stone. '
        else:
            text = 'Loose blocks wait beside the work stone. '
        text += 'The gap in the bridge remains open.'
        def inspect_done():
            if (game.world is not self.world or
                    game.player.position.distance_to(INSPECT_POSITION) > 40):return
            if not self.state['masonry_read']:
                self.state['masonry_read'] = True
                game.save_progress()
        return game.social.start_script(
            [{'speaker': 'caelan', 'text': text}],
            on_complete=inspect_done, identifier=MASONRY_SCRIPT)
