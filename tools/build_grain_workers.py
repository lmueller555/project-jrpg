"""Export farm work poses from approved layered villagers, not flattened warps.

Generated pose_reference.png guides grips and weight; approved appearance parts
retain the exact palette, head and foot registration. Outputs are new assets.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/characters/grain_workers'


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    for role, variant in [('loader','male_02'), ('coworker','male_03')]:
        source = ROOT/f'assets/source/characters/npcs/{variant}/walk_front/parts'
        palette = json.loads((ROOT/f'assets/characters/npcs/{variant}/palette.json').read_text())['material_overrides']
        def body(phase=None, crouch=0):
            image = Image.new('RGBA',(40,44))
            for part in ['idle_legs' if phase is None else f'frame_{phase+1:02}_legs','waist','shirt','head']:
                layer = Image.open(source/f'{part}.png').convert('RGBA')
                image.alpha_composite(layer,(8, 4+(crouch if part in ('head','shirt') else 0)))
            return image
        def arms(image, hands):
            d=ImageDraw.Draw(image)
            for shoulder,hand in zip([(15,21),(24,21)], hands):
                elbow=(shoulder[0]+(-2 if shoulder[0]<20 else 2),round((21+hand[1])/2))
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
            'assist': ([(25,27),(31,27)],1),
            'assist_low': ([(25,35),(31,35)],3),
            'stretch': ([(14,29),(24,22)],0),
        }
        for name,(hands,crouch) in poses.items():
            for phase in range(4 if name=='carry' else 2):
                image=body(phase if name=='carry' else None,crouch)
                animated=[(x,y+(phase%2 if name=='work' else 0)) for x,y in hands]
                arms(image,animated)
                image.save(OUT/f'{role}_{name}_{phase}.png')
    sack=Image.new('RGBA',(12,12));d=ImageDraw.Draw(sack)
    d.polygon([(3,0),(8,0),(8,3),(10,5),(11,9),(9,11),(2,11),(0,9),(1,5),(4,3)],fill='#56422d')
    d.polygon([(4,1),(7,1),(6,4),(9,6),(9,9),(7,10),(2,9),(2,6),(5,4)],fill='#b99a6d')
    d.line([(3,6),(3,8),(6,9)],fill='#d1b486',width=1)
    d.line([(3,3),(8,3)],fill='#84512e',width=1)
    sack.save(OUT/'sack.png')
    cloth=Image.new('RGBA',(18,8));d=ImageDraw.Draw(cloth)
    d.polygon([(2,0),(15,0),(17,6),(13,7),(9,6),(4,7),(0,6)],fill='#536569')
    d.line([(3,1),(14,1),(16,5)],fill='#9aa49a',width=1)
    d.line([(4,2),(3,6)],fill='#6f8580',width=2)
    cloth.save(OUT/'cover.png')
    (OUT/'art.json').write_text(json.dumps({'status':'review','anchor':[20,38], 'canvas':[40,44],
        'source':'assets/source/characters/grain_workers/pose_reference.png',
        'appearance':'approved male_02 and male_03 walk_front parts',
        'grip_offsets':{'lift':[0,-3],'carry':[0,-11],'place':[10,-9]},
        'roles':['loader','coworker']},indent=2)+'\n')

if __name__=='__main__':build()
