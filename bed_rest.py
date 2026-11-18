"""Repeatable, confirmed party recovery at authored beds and visitor care."""
import json
from pathlib import Path

from social import foot_gap


ROOT = Path(__file__).resolve().parent


class BedRest:
    def __init__(self, game):
        self.game = game
        self.data = json.loads((ROOT/'assets/story/bed_rest.json').read_text(encoding='utf-8'))
        self.relief = json.loads((ROOT/'assets/story/sanctuary_relief.json').read_text(encoding='utf-8'))
        self.last_error = ''

    def available(self, profile):
        """Shared live-play gates; a dialogue callback must pass these again."""
        game = self.game
        if (game.on_title or game.opening_cinematic.active or game.combat.active
                or game.pause.is_open or game.inventory_ui.is_open
                or getattr(getattr(game, 'party_ui', None), 'is_open', False)
                or game.world_map_viewer.is_open or game.map_open
                or game.quest_ui.journal_open or game.social.locked
                or game.household_action or game.opening.locks_player
                or game.opening.stage not in ('disabled', 'explore', 'assignment', 'done')
                or game.transfer_cooldown or game.opening_fade
                or game.world.data['id'] != profile['scene']):
            return False
        return game.world.can_stand(game.player.position)

    def _profile(self):
        return (self.relief['bed'] if self.game.world.data['id'] == self.relief['bed']['scene']
                else self.data)

    def _near_bed(self, profile):
        if not self.available(profile):return False
        game = self.game
        bed = next((entity for entity in game.world.entities
                    if entity['id'] == profile['entity']), None)
        probe = game.world.probe_rect(game.player.position)
        # The headboard backs onto the wall display. Its inspection approach
        # belongs to the family drawing; resting uses the sides and foot.
        return bool(bed is not None and game.world.can_stand(game.player.position)
                    and probe.bottom > bed['rect'].top
                    and foot_gap(probe, bed['rect'])
                    <= profile['interaction_radius'])

    def nearby(self):return self._near_bed(self._profile())

    def interaction_hint(self):
        return 'E: rest' if self.nearby() else ''

    def interact(self):
        profile = self._profile()
        if not self._near_bed(profile):return False
        return self._offer(profile, lambda:self._near_bed(profile))

    def offer_relief(self, can_rest=None, *, attendant=False):
        """Offer the visitor bed through its attendant's independently checked range."""
        profile = self.relief['attendant_rest'] if attendant else self.relief['bed']
        validator = can_rest or (lambda:self._near_bed(self.relief['bed']))
        if not self.available(profile) or not validator():return False
        return self._offer(profile, validator)

    def _offer(self, profile, validator, *, retry=False):
        if not self.available(profile) or not validator():return False
        identifier = profile.get('identifier', 'bed_rest')
        lines = profile.get('retry_lines', profile['offer']) if retry else profile['offer']
        choices = ([{'text':'Retry', 'action':'rest'}, {'text':'Not now', 'action':'leave'}]
                   if retry else profile['choices'])
        return self.game.social.start_choice(
            lines, choices, lambda action:self._choose(action, profile, validator),
            identifier=identifier+('_retry' if retry else '_offer'),
            prompt='Your rest could not be saved. Try again?' if retry else profile['prompt'])

    def _choose(self, action, profile=None, validator=None):
        # Live dialogue permits walking away. Recheck the actual bed and scene
        # after SocialSystem clears the choice, before applying any recovery.
        profile = profile or self.data
        validator = validator or (lambda:self._near_bed(profile))
        if action != 'rest' or not self.available(profile) or not validator():return
        game = self.game
        # Rest recovers the travelling roster, including available reserves.
        # Characters who are elsewhere retain their resources until they return.
        party=getattr(game,'party',None)
        resources={'caelan':game.attributes}
        if party is not None:
            resources.update({identifier:party.characters[identifier]
                              for identifier in party.available_ids})
        before = [(attributes, attributes.current_hp, attributes.current_mp)
                  for attributes in resources.values()]
        for attributes in resources.values():
            attributes.recover()
        store = getattr(game, 'save_store', None)
        if store is not None and store.enabled and not game.save_progress():
            for attributes, hp, mp in before:attributes.set_current(hp=hp, mp=mp)
            self.last_error = game.save_error or 'Your rest could not be saved.'
            self._offer(profile, validator, retry=True)
            return
        self.last_error = ''
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game.opening_fade = .65
        game.social.start_script(profile['complete'],
                                 identifier=profile.get('identifier', 'bed_rest')+'_complete')
