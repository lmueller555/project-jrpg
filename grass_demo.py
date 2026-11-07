"""Native grass demonstration world; existing game maps remain independent."""
from main import World


class GrassDemoWorld(World):
    def location(self, position):
        nearest = min(self.data.get('landmarks', []),
                      key=lambda record: (record['position'][0]-position[0])**2
                                         +(record['position'][1]-position[1])**2,
                      default=None)
        return nearest['name'] if nearest is not None else self.data['name']
