"""Export bridge work poses from approved layered villagers, not flattened warps.

Generated pose_reference.png guides grips and weight; approved appearance parts
retain the exact palette, head and foot registration. Outputs are new assets.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/characters/bridge_workers'


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    for role, variant in [('mason','male_01'), ('tender','male_03')]:
        source = ROOT/f'assets/source/characters/npcs/{variant}/walk_front/parts'
        palette_data = json.loads((ROOT/f'assets/characters/npcs/{variant}/palette.json').read_text())
        palette = palette_data.get('material_overrides', palette_data.get('materials'))
        def body(phase=None, crouch=0):
            image = Image.new('RGBA',(40,44))
            for part in ['idle_legs' if phase is None else f'frame_{phase+1:02}_legs','waist','shirt','head']:
                layer = Image.open(source/f'{part}.png').convert('RGBA')
                image.alpha_composite(layer,(8, 4+(crouch if part in ('head','shirt') else 0)))
            return image
        def arms(image, hands, crouch=0):
            d=ImageDraw.Draw(image)
            for shoulder,hand in zip([(15,21+crouch),(24,21+crouch)], hands):
                elbow=(shoulder[0]+(-2 if shoulder[0]<20 else 2),round((shoulder[1]+hand[1])/2))
                d.line([shoulder,elbow,hand],fill='#1a0e16',width=4)
                d.line([shoulder,elbow],fill=palette['shirt']['base'],width=3)
                d.line([elbow,hand],fill='#eda052',width=2)
                d.point(hand,fill='#e8c49d')
        poses={
            'lift': ([(15,35),(24,35)],3),
            'carry': ([(15,27),(24,27)],0),
            'look': ([(15,27),(24,27)],2),
            'cover': ([(15,29),(24,29)],2),
            'place': ([(25,29),(33,29)],2),
            'work': ([(25,27),(31,27)],0),
            'assist': ([(30,27),(34,27)],1),
            'assist_low': ([(30,35),(34,35)],3),
            'stretch': ([(14,29),(24,22)],0),
            'cup': ([(18,26),(24,29)],0),
            'offer': ([(7,26),(13,26)],0),
            'receive': ([(27,26),(31,26)],0),
            'drink': ([(18,19),(22,19)],5),
            'sit': ([(15,30),(24,30)],5),
            'measure': ([(10,28),(30,28)],2),
        }
        for name,(hands,crouch) in poses.items():
            for phase in range(4 if name in ('carry','cup') else 2):
                image=body(phase if name in ('carry','cup') else None,crouch)
                animated=[(x,y+(phase%2 if name=='work' else 0)) for x,y in hands]
                arms(image,animated,crouch)
                if name in ('sit','drink'):
                    image.paste((0,0,0,0),(10,31,30,44))
                    d=ImageDraw.Draw(image)
                    d.rectangle((14,31,25,34),fill=palette['trousers']['base'] if 'trousers' in palette else '#665039')
                    d.rectangle((14,34,17,38),fill='#594333');d.rectangle((23,34,26,38),fill='#594333')
                    d.rectangle((13,38,18,39),fill='#251e20');d.rectangle((23,38,28,39),fill='#251e20')
                image.save(OUT/f'{role}_{name}_{phase}.png')
    shapes = {
        'stone': ((12,9), [('polygon', [(0,3),(3,0),(9,1),(11,5),(9,8),(1,8)], '#666960'), ('line',[(2,3),(8,2),(10,5)], '#b1afa0')]),
        'cup': ((6,6), [('rectangle',(0,0,4,4),'#d3b98a'),('rectangle',(4,1,5,3),'#a18966'),('line',[(1,0),(3,0)],'#493e32')]),
        'kettle': ((12,12), [('ellipse',(1,3,10,11),'#4b5559'),('arc',(3,0,9,8),'#9d9f8c'),('line',[(9,7),(11,3)],'#4b5559')]),
        'bench': ((26,12), [('rectangle',(3,5,5,11),'#4b382a'),('rectangle',(20,5,22,11),'#4b382a'),('rectangle',(0,0,25,4),'#a08251'),('line',[(1,0),(24,0)],'#c9ac71')]),
        'tray': ((24,8), [('rectangle',(0,0,23,7),'#56432d'),('rectangle',(2,1,21,5),'#ab8c59')]),
        'tool': ((13,5), [('line',[(1,3),(11,3)],'#b29264'),('rectangle',(9,0,12,4),'#8e9695')]),
        'barrier': ((38,19), [('rectangle',(3,0,5,18),'#695038'),('rectangle',(32,0,34,18),'#695038'),('rectangle',(0,2,37,5),'#b39b68'),('line',[(5,8),(31,8)],'#b4a77d')]),
    }
    for name,(size,marks) in shapes.items():
        image=Image.new('RGBA',size);d=ImageDraw.Draw(image)
        for kind,coords,color in marks:
            if kind=='arc':d.arc(coords,180,360,fill=color,width=1)
            elif kind=='line':d.line(coords,fill=color,width=1)
            else:getattr(d,kind)(coords,fill=color)
        image.save(OUT/(name+'.png'))
    (OUT/'art.json').write_text(json.dumps({'status':'review','anchor':[20,38], 'canvas':[40,44],
        'appearance':'approved male_01 and male_03 layered front walks',
        'pose_reference':'assets/source/characters/grain_workers/pose_reference.png',
        'roles':['mason','tender']},indent=2)+'\n')

if __name__=='__main__':build()
