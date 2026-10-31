"""A repeatable, player-confirmed rest at Caelan's sanctuary bed."""
import json
from pathlib import Path

from social import foot_gap


ROOT = Path(__file__).resolve().parent


class BedRest:
    def __init__(self, game):
        self.game = game
        self.data = json.loads((ROOT/'assets/story/bed_rest.json').read_text(encoding='utf-8'))

    def nearby(self):
        game = self.game
        if (game.on_title or game.opening_cinematic.active or game.combat.active
                or game.pause.is_open or game.inventory_ui.is_open
                or game.world_map_viewer.is_open or game.map_open
                or game.quest_ui.journal_open or game.social.locked
                or game.household_action or game.opening.locks_player
                or game.opening.stage not in ('disabled', 'explore', 'assignment', 'done')
                or game.transfer_cooldown or game.opening_fade
                or game.world.data['id'] != self.data['scene']):
            return False
        bed = next((entity for entity in game.world.entities
                    if entity['id'] == self.data['entity']), None)
        probe = game.world.probe_rect(game.player.position)
        # The headboard backs onto the wall display. Its inspection approach
        # belongs to the family drawing; resting uses the sides and foot.
        return bool(bed is not None and game.world.can_stand(game.player.position)
                    and probe.bottom > bed['rect'].top
                    and foot_gap(probe, bed['rect'])
                    <= self.data['interaction_radius'])

    def interaction_hint(self):
        return 'E: rest' if self.nearby() else ''

    def interact(self):
        if not self.nearby():return False
        return self.game.social.start_choice(
            self.data['offer'], self.data['choices'], self._choose,
            identifier='bed_rest_offer', prompt=self.data['prompt'])

    def _choose(self, action):
        # Live dialogue permits walking away. Recheck the actual bed and scene
        # after SocialSystem clears the choice, before applying any recovery.
        if action != 'rest' or not self.nearby():return
        game = self.game
        # The progression registry holds the persistent character resources;
        # encounter-only guests already start each battle fully recovered.
        for attributes in game.lattice_progression.attributes.values():
            attributes.recover()
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game.opening_fade = .65
        game.social.start_script(self.data['complete'], identifier='bed_rest_complete')
        game.save_progress()
