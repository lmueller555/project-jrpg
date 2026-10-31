"""Register existing game materials into the bridge crew's fixed prop canvases.

Inputs are read-only. Crops and nearest-neighbour exports preserve hard pixels;
small edge masks register the existing shading to the controller's grips.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/characters/bridge_workers'
SOURCE=ROOT/'assets/source/characters/bridge_workers'
REGION='assets/terrain/overworld/elden_vale/polish/props/'
SOURCES={
    'bench':REGION+'bench.png',
    'barrier':REGION+'fence_h.png',
    'stone':REGION+'bridge_rubble.png',
    'wood':'assets/terrain/eldenmere/workshop/props/workbench.png',
    'kettle':'assets/terrain/eldenmere/sanctuary_interior/props/kettle.png',
    'cup':'assets/story/sanctuary_opening/poses/cup.png',
}


def build_props():
    originals={key:Image.open(ROOT/path).convert('RGBA') for key,path in SOURCES.items()}
    def crop(key,box,size):return originals[key].crop(box).resize(size,Image.Resampling.NEAREST)
    props={
        'bench':crop('bench',(3,0,33,18),(26,12)),
        'barrier':crop('barrier',(2,0,46,18),(38,19)),
        'kettle':originals['kettle'].resize((12,12),Image.Resampling.NEAREST),
        'cup':originals['cup'].copy(),
    }
    # The uppermost intact masonry piece has the same lit top, neutral face and
    # dark right edge as the bridge debris. The grip keeps its original 12x9 box.
    stone=crop('stone',(13,0,20,10),(12,9))
    mask=Image.new('L',(12,9));d=ImageDraw.Draw(mask)
    d.polygon([(3,0),(8,0),(10,2),(11,6),(9,8),(2,8),(0,5),(1,2)],fill=255)
    stone.putalpha(mask);props['stone']=stone
    # Native workshop grain supplies a worn plank surface. A chamfer, upper
    # lip and shaded lower edge give the shallow tray a distinct thickness.
    tray=crop('wood',(10,2,22,14),(24,8))
    mask=Image.new('L',(24,8));d=ImageDraw.Draw(mask)
    d.polygon([(2,0),(21,0),(23,2),(23,5),(21,7),(2,7),(0,5),(0,2)],fill=255)
    tray.putalpha(mask);d=ImageDraw.Draw(tray)
    d.line([(2,0),(21,0),(22,1)],fill='#b09872')
    d.line([(1,2),(1,5),(3,6),(20,6),(22,5)],fill='#493d2c')
    d.line([(3,1),(20,1)],fill='#8b7252')
    d.point((4,4),fill='#b09872');d.point((18,3),fill='#5b4631')
    props['tray']=tray
    for name in ('keep_mark','reject_mark'):
        image=Image.new('RGBA',(13,10))
        image.alpha_composite(crop('barrier',(2,2,7,18),(3,8)),(5,2))
        board=crop('wood',(10,2,22,14),(13,6))
        mask=Image.new('L',(13,6));d=ImageDraw.Draw(mask)
        d.polygon([(1,0),(11,0),(12,1),(12,4),(10,5),(0,5),(0,1)],fill=255)
        board.putalpha(mask);image.alpha_composite(board,(0,0));d=ImageDraw.Draw(image)
        d.line([(1,0),(10,0)],fill='#b09872');d.line([(1,5),(10,5)],fill='#493d2c')
        if name=='keep_mark':d.line([(3,2),(5,4),(9,1)],fill='#e0d5ac')
        else:
            d.line([(4,1),(8,4)],fill='#382f26');d.line([(8,1),(4,4)],fill='#382f26')
        props[name]=image
    # Retain the tool's contact extent, with a bevel on its metal head and a
    # worn timber handle sampled from the same workshop material vocabulary.
    tool=Image.new('RGBA',(13,5));d=ImageDraw.Draw(tool)
    d.line([(1,3),(10,3)],fill='#493d2c',width=2)
    d.line([(1,2),(9,2)],fill='#a08764')
    d.polygon([(10,0),(12,0),(12,4),(9,4),(9,1)],fill='#454c47')
    d.line([(10,0),(12,0)],fill='#b2b6a5');d.line([(10,1),(10,3)],fill='#818b82')
    props['tool']=tool
    for name,image in props.items():image.save(OUT/(name+'.png'))
    manifest={'status':'review','method':'existing art crops, nearest-neighbour registration and material-matched edge finishing',
        'sources':{key:{'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()} for key,path in SOURCES.items()},
        'crops':{'bench':[3,0,33,18],'barrier':[2,0,46,18],'stone':[13,0,20,10],'wood':[10,2,22,14]},
        'dimensions':{key:list(image.size) for key,image in props.items()},
        'preserved':'runtime positions, anchors, collision, actor art and surrounding scenery'}
    (SOURCE/'props_export.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':build_props()
