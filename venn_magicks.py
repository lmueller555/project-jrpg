"""Pose-only animation for Caelan's unsuccessful irrigation spell."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
ART = 'assets/story/venn/magicks/'

class VennMagicks:
    def __init__(self, world):
        self.data = json.loads((ROOT/ART/'animation.json').read_text())
        self.sequence = self.data['sequence']
        sheet = world.image(ART+'poses.png')
        self.poses = {name: [sheet.subsurface(f['rect']).copy() for f in record['frames']]
                      for name, record in self.data['animations'].items()}

    def duration(self, phase):return self.data['animations'][phase]['duration_ms']/1000
    def index(self, phase, seconds):
        return min(len(self.poses[phase])-1, max(0, int(seconds/self.duration(phase)*len(self.poses[phase]))))
    def pose(self, phase, seconds):return self.poses[phase][self.index(phase, seconds)]
