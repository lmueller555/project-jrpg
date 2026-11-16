"""Native terrain composition shared by Eldenmere town and upstream exports."""
from functools import lru_cache
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFilter
from tools.build_world_water_hd import clipped, compose_water, depth_control, load
ROOT=Path(__file__).resolve().parents[1]
@lru_cache(None)
def image(path):return load(ROOT/path)
def read(path):return json.loads((ROOT/path).read_text())
OFFSETS=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
def mask_for(cells,x,y):
    bits=0
    for i,(dx,dy) in enumerate(OFFSETS):
        if (x+dx,y+dy) in cells and (not(dx and dy) or ((x+dx,y) in cells and (x,y+dy) in cells)):bits|=1<<i
    return bits

class Materials:
    def __init__(self):
        self.ground_pack='assets/terrain/eldenmere/grass_dirt_hd/'
        gm=read(self.ground_pack+'tileset.json')
        self.grass=[image(self.ground_pack+p) for p in gm['materials']['grass']]
        self.dirt={r['mask']:image(self.ground_pack+r['file']) for r in gm['tiles']}
        self.water_pack='assets/terrain/water_hd/'
        wm=read(self.water_pack+'tileset.json')
        self.surfaces={(r['depth'],r['arrangement'],r['texture_phase']):r for r in wm['water_surfaces'] if r['family']=='temperate'}
        self.channels=read('assets/terrain/eldenmere/waterworks_hd/tileset.json')
        self.channel_routes={r['id']:r for r in self.channels['channel_routes'] if r['style']=='maintained'}
    def ground(self,size,dirt_cells):
        out=Image.new('RGBA',tuple(v*2 for v in size))
        for y in range((size[1]+23)//24):
            for x in range((size[0]+23)//24):
                out.alpha_composite(self.grass[(x//3+y//4)%4],(x*48,y*48))
                if (x,y) in dirt_cells:out.alpha_composite(self.dirt[mask_for(dirt_cells,x,y)],(x*48,y*48))
        return out
    @lru_cache(None)
    def water_tile(self,mask,xphase,yphase,arrangement,tick,direction):
        spatial=xphase+2*yphase
        def surface(depth):return image(self.water_pack+self.surfaces[depth,arrangement,spatial]['frames'][tick]['file'])
        water_mask=Image.open(ROOT/(self.water_pack+f'masks/water_{mask:03}.png')).convert('L')
        tile=compose_water(surface('shallow'),surface('deep'),water_mask,depth_control(water_mask))
        current=image(self.water_pack+f'currents/straight_{direction}/frame_{tick:02}.png')
        tile.alpha_composite(clipped(current,water_mask))
        tile.alpha_composite(image(self.water_pack+f'banks/grass/{arrangement}/mask_{mask:03}.png'))
        return tile
    def water(self,cells,tick,direction='S'):
        # Cell records are cropped by callers into small visible chunks.
        return [(self.water_tile(mask_for(cells,x,y),x%2,y%2,(x//3+y//3)%2,tick,direction),(x*48,y*48)) for x,y in sorted(cells) if x>=0 and y>=0]
    def channel(self,route,tick,mode='full'):
        if route=='return_w':route='outlet_w'
        if route not in self.channel_routes:raise ValueError('Unknown channel port binding: '+route)
        r=self.channel_routes[route];pack='assets/terrain/eldenmere/waterworks_hd/'
        if mode=='full':return image(pack+r['frames'][tick])
        # Keep banks dry except for the existing narrow trickle; no navigation change.
        bank=image(pack+r['bank']).copy();mask=Image.open(ROOT/(pack+r['water_mask'])).convert('L')
        bank.alpha_composite(clipped(image(pack+r['frames'][tick]),mask.filter(ImageFilter.MinFilter(9))))
        return bank
    def spillway(self,tick,mode='full'):
        pack='assets/terrain/eldenmere/waterworks_hd/spillways/maintained/'
        full=image(pack+f'frame_{tick:02}.png')
        if mode=='full':return full
        mask=Image.open(ROOT/(pack+'water_mask.png')).convert('L')
        bank=image(pack+'structure.png').copy()
        bank.alpha_composite(clipped(full,mask.filter(ImageFilter.MinFilter(9))))
        return bank
    def paving(self,size,world=(0,0)):
        pattern=image('assets/terrain/eldenmere/stone_paving_hd/surface/pattern_96.png');out=Image.new('RGBA',size)
        ox,oy=world
        for y in range(-oy*2%96-96,size[1],96):
            for x in range(-ox*2%96-96,size[0],96):out.alpha_composite(pattern,(x,y))
        return out
