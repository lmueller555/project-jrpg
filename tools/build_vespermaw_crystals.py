"""Author large, wall-embedded elemental lenses for the confluence chamber.

The same retained native modules appear in exploration and the low battle view.
No actor, interface, counter hint or combat state is baked into this pack.
"""
from io import BytesIO
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/terrain/limestone_cave/elemental_crystals'
PALETTES = {
    'fire': ['#421f29','#772d34','#ad3e37','#db5d3d','#f18b50','#ffc17a','#ffe5ae'],
    'ice': ['#35415f','#596d8b','#849db6','#a8c8d7','#cce4e8','#e5f2ef','#fcfff8'],
    'water': ['#142e57','#204978','#286b9f','#388fc1','#60b8d9','#9bdeee','#ddf7f5'],
}

def encoded(image):
    output=BytesIO();image.save(output,format='PNG');return output.getvalue()

def drawing(element, level):
    image=Image.new('RGBA',(64,76));d=ImageDraw.Draw(image)
    # Broken bedrock collar seats the lens inside a wall rather than on a floor.
    d.polygon(((10,17),(25,6),(41,8),(55,22),(56,55),(47,70),(30,75),(12,68),(5,48)),fill='#282a31')
    d.polygon(((9,29),(17,17),(29,12),(43,17),(53,31),(49,61),(36,71),(18,65),(10,49)),fill='#59584e',outline='#777361')
    for poly, color in [(((10,27),(18,17),(16,37),(8,45)),'#86816a'),(((46,18),(54,28),(50,47),(44,37)),'#3a3b37'),(((14,61),(30,71),(19,68),(9,56)),'#3b3e39')]:
        d.polygon(poly,fill=color)
    colors=[]
    for color in PALETTES[element]:
        rgb=tuple(int(color[i:i+2],16) for i in (1,3,5))
        gain=.59+.41*level/7
        colors.append(tuple(round(c*gain) for c in rgb))
    if element=='fire':
        outer=((16,58),(12,39),(21,23),(27,31),(33,12),(42,29),(47,25),(51,48),(43,67),(28,70))
        facets=[(((16,58),(21,29),(28,45),(28,70)),1),(((21,29),(33,12),(34,43),(28,45)),3),(((33,12),(42,29),(34,43)),5),(((42,29),(47,25),(46,49),(34,43)),2),(((34,43),(46,49),(43,67),(28,70)),3),(((28,45),(34,43),(35,62),(28,70)),5)]
        seams=[((21,29),(28,45),(28,65)),((33,18),(34,43),(43,57))]
    elif element=='ice':
        outer=((14,31),(23,15),(37,10),(49,27),(50,50),(39,67),(25,70),(14,55))
        facets=[(((14,31),(23,15),(26,37),(14,55)),2),(((23,15),(37,10),(35,34),(26,37)),5),(((37,10),(49,27),(35,34)),3),(((35,34),(49,27),(50,50),(39,49)),2),(((26,37),(35,34),(39,49),(25,70)),4),(((14,55),(26,37),(25,70)),1),(((39,49),(50,50),(39,67),(25,70)),3)]
        seams=[((23,18),(26,37),(22,59)),((38,16),(35,34),(43,44))]
    else:
        outer=((17,25),(29,11),(41,15),(50,31),(49,52),(39,68),(26,71),(14,59),(12,42))
        facets=[(((17,25),(29,11),(30,32),(21,43),(12,42)),3),(((29,11),(41,15),(40,35),(30,32)),5),(((41,15),(50,31),(40,35)),2),(((40,35),(50,31),(49,52),(37,51)),3),(((21,43),(30,32),(37,51),(26,71)),2),(((12,42),(21,43),(26,71),(14,59)),1),(((37,51),(49,52),(39,68),(26,71)),4)]
        seams=[((28,17),(30,32),(21,43),(24,60)),((42,24),(40,35),(44,47))]
    d.polygon(outer,fill=colors[0],outline='#111d29')
    for points,color in facets:d.polygon(points,fill=colors[color])
    for points in seams:d.line(points,fill=colors[6],width=1)
    # Narrow stepped glints maintain facet planes instead of a white fill flash.
    for x,y in ((26,24),(36,31),(28,53),(40,56)):
        d.line((x,y,x+2,y-2),fill=colors[5],width=1)
    d.line((17,59,26,70,37,68),fill=colors[1],width=2)
    for x,y in ((9,21),(52,58),(17,70),(47,13)):
        d.line((x,y,x-3,y+4),fill='#999077',width=1)
    return image

def products():
    out={};modules={}
    for element in PALETTES:
        frames=[]
        for level in range(8):
            path=OUT/f'{element}_{level:02}.png';out[path]=encoded(drawing(element,level));frames.append(path.relative_to(ROOT).as_posix())
        modules[element]={'frames':frames,'anchor':[32,72],'emission_origin':[32,44],
            'element':element,'size':[64,76],'frame_duration_ms':160,'reduced_motion_frame':4,
            'color':{'fire':[255,105,62],'ice':[180,226,245],'water':[65,153,234]}[element],
            'core_components':[[13,12,39,59]],'footprints':[]}
    manifest={'version':1,'kind':'embedded_elemental_lenses','modules':modules,
              'design':'Large irregular elemental lenses seated in fractured limestone; Fire jagged, Ice faceted, Water flowing.',
              'build':'tools/build_vespermaw_crystals.py'}
    out[OUT/'assets.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for path,raw in products().items():
        if args.check:assert path.exists() and path.read_bytes()==raw,path
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
