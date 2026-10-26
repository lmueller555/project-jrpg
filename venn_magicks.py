"""Authored pose and held-water frames for the practical irrigation spell."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ART='assets/story/venn/magicks/'
class VennMagicks:
    def __init__(self,world):
        self.data=json.loads((ROOT/ART/'animation.json').read_text())
        self.sequence=self.data['sequence']
        sheet=world.image(ART+'poses.png')
        self.poses={name:[sheet.subsurface(f['rect']).copy() for f in record['frames']]
                    for name,record in self.data['animations'].items()}
        water=world.image(ART+'water.png')
        self.water=[[water.subsurface((phase*8,level*56,8,56)).copy() for phase in range(6)] for level in range(5)]
        gate=world.image(ART+'opening_gate.png')
        self.opening=[gate.subsurface((i*24,0,24,36)).copy() for i in range(6)]
        self.colors={tuple(bytes.fromhex(c[1:])) for c in self.data['water_colors']}
    def duration(self,phase):return self.data['animations'][phase]['duration_ms']/1000
    def index(self,phase,seconds):return min(len(self.poses[phase])-1,int(seconds/self.duration(phase)*len(self.poses[phase])))
    def pose(self,phase,seconds):return self.poses[phase][self.index(phase,seconds)]
    def amount(self,phase,seconds):
        if phase=='raise_hand' or phase=='finish':return 0
        if phase=='ease_water':return min(1,seconds/self.duration(phase))
        if phase=='release_water':return max(0,1-seconds/self.duration(phase))
        return 1
    def overlay_gate(self,gate,amount,phase):
        effect=self.water[round(4*amount)][phase]
        # Replace only water-colored pixels, preserving wood, iron and stone.
        for y in range(36):
            for x in range(8):
                if gate.get_at((8+x,y))[:3] in self.colors:gate.set_at((8+x,y),effect.get_at((x,y+16)))
        return effect
