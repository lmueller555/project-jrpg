"""Native grass demonstration world; existing game maps remain independent."""
from pathlib import Path

from interactive_grass import InteractiveGrass
from main import ROOT, World, read_json


class GrassDemoWorld(World):
    def __init__(self, path, image_cache=None):
        super().__init__(path, image_cache)
        data = self.data['grass']
        manifest_path = Path(data['manifest'])
        if not manifest_path.is_absolute():manifest_path = ROOT/manifest_path
        self.grass = InteractiveGrass(read_json(manifest_path), data['instances'], self.image)
        self.entities.extend(self.grass.entity_records)
        self.reduced_motion = False

    def location(self, position):
        nearest = min(self.data.get('landmarks', []),
                      key=lambda record: (record['position'][0]-position[0])**2
                                         +(record['position'][1]-position[1])**2,
                      default=None)
        return nearest['name'] if nearest is not None else self.data['name']

    def update_grass(self, seconds, player, party_actors=(), *, reduced_motion=False):
        self.reduced_motion = bool(reduced_motion)
        self.grass.update(seconds, (player, *self.npcs, *party_actors),
                          reduced_motion=self.reduced_motion)

    def draw(self, target, camera, player, elapsed_ms, include_ui=True, party_actors=()):
        if self.grass.enabled:
            return super().draw(target, camera, player, elapsed_ms, include_ui,
                                party_actors=party_actors)
        original = self.entities
        try:
            self.entities = [record for record in original if 'grass_instance' not in record]
            return super().draw(target, camera, player, elapsed_ms, include_ui,
                                party_actors=party_actors)
        finally:self.entities = original
