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
    from build_bridge_props import build_props
    build_props()
    (OUT/'art.json').write_text(json.dumps({'status':'review','anchor':[20,38], 'canvas':[40,44],
        'appearance':'approved male_01 and male_03 layered front walks',
        'pose_reference':'assets/source/characters/grain_workers/pose_reference.png',
        'roles':['mason','tender']},indent=2)+'\n')

if __name__=='__main__':build()
