"""Repeatable inspection of the live well, without manipulating its operation."""
from copy import deepcopy
import json
from pathlib import Path

from object_cues import ObjectCues
from social import facing_toward


ROOT = Path(__file__).resolve().parent
INSPECTION = 'assets/story/well/inspection.json'


class WellExamination:
    """Use the reachable physical rim and existing scripted dialogue UI.

    This interaction reads a snapshot. The gardener/controller still own all
    work, pail transfers and water; closing or cancelling prose has no callback.
    """
    def __init__(self, game):
        self.game = game
        self.data = json.loads((ROOT/INSPECTION).read_text(encoding='utf-8'))

    def _enabled(self):
        game = self.game
        if (game.world is not game.town or getattr(game.world, 'well', None) is None
                or game.on_title or getattr(game, 'game_over', False)
                or not getattr(game, '_music_focused', True)
                or getattr(game, '_is_gallery_preview', False)
                or getattr(game, 'on_gallery', False)
                or getattr(game, 'gallery_session', None) is not None
                or getattr(game, 'on_quest_playtest', False)
                or getattr(game, 'quest_playtest_session', None) is not None
                or game.social.locked or game.map_open
                or game.quest_ui.journal_open or game.household_action
                or game.transfer_cooldown or game.opening_fade
                or game.opening.locks_player
                or game.opening.stage not in ('disabled', 'explore', 'assignment', 'done')):
            return False
        for owner in ('pause', 'inventory_ui', 'services', 'party_ui',
                      'world_map_viewer', 'save_menu', 'status_ui'):
            if getattr(getattr(game, owner, None), 'is_open', False):return False
        for owner in ('combat', 'opening_cinematic', 'mill_gift', 'regent_arrival',
                      'sanctuary_arrival', 'sanctuary_rescue'):
            if getattr(getattr(game, owner, None), 'active', False):return False
        if getattr(getattr(game, 'regent_arrival', None), 'state', None) == 'pending':
            return False
        for owner in ('mill_quest', 'regent_quest', 'lantern_quest'):
            if getattr(getattr(game, owner, None), 'locks_player', False):return False
        return True

    def _contact(self):
        if not self._enabled():return None
        world, player = self.game.world, self.game.player
        if not world.can_stand(player.position):return None
        # The physical support, not transparent artwork/canopy padding, owns
        # distance and facing. Its boundary is approached from walkable ground.
        boundary = world.well.presentation.base['geometry']['ground_rect_world_logical']
        closest = ObjectCues.nearest_boundary(player.position, boundary)
        delta = closest-player.position
        if (not delta.length_squared() or delta.length() > self.data['reach_logical']
                or player.facing != facing_toward(delta)
                or not ObjectCues.clear_approach(world, player.position, closest)):
            return None
        return closest

    def available(self):
        return self._contact() is not None

    def interaction_hint(self):
        return 'E: Examine well' if self.available() else ''

    def description_key(self):
        """Snapshot-based prose; completed work elsewhere leaves an idle well."""
        well = self.game.town.well
        state = well.snapshot()
        capacity = well.model.contract['pail']['capacity_units']
        if state.pail_owner == 'well' and state.water_units == capacity:
            return 'filled'
        return 'working' if well.owner is not None else 'idle'

    def interact(self):
        if not self.available():return False
        key = self.description_key()
        if not self.game.social.start_script(
                deepcopy(self.data['descriptions'][key]),
                identifier='well_examine_'+key):
            return False
        self.game.player.moving = False
        self.game.player.running = False
        self.game._mouse_held = False
        self.game.social.clear_pointer()
        return True
