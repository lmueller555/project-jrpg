"""Build distinct held-water casting poses and synchronized gate contact art."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw
from build_eldenmere_gate import channel_assets,gate_frame,poses
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/story/venn/magicks'
SIZE=(40,48);ANCHOR=(20,38)
TIMELINE=[('raise_hand',650,4),('ease_water',1100,4),('hold_water',400,1),
          ('work_pin',1600,4),('open',1200,6),('release_water',1150,4),('finish',450,4)]
COLORS={'outline':'#1a0e16','shirt':'#fbeed0','trim':'#d3963f','tabard':'#1f5d72',
        'skin':'#e8c49d','shadow':'#573422','trousers':'#645450','boot':'#8b5531'}
def blank():return Image.new('RGBA',SIZE)
def arm(joints,cast=False):
    im=blank();d=ImageDraw.Draw(im)
    d.line(joints,fill=COLORS['outline'],width=4)
    d.line(joints,fill=COLORS['shirt'],width=2)
    x,y=joints[-1]
    d.rectangle((x,y,x+1,y+1),fill=COLORS['skin'])
    if cast:
        d.line((x+1,y,x+3,y-1),fill=COLORS['skin'])
        d.point((x+3,y+1),fill=COLORS['skin'])
    return im

def pose(idle,knee,cast_wrist,work_wrist):
    body=blank();d=ImageDraw.Draw(body)
    # Independent chest/hem, with stationary idle hands removed.
    torso=Image.new('RGBA',(24,36));td=ImageDraw.Draw(torso)
    td.rectangle((10,14,14,25),fill=COLORS['outline'])
    td.rectangle((10,15,12,23),fill=COLORS['shirt'])
    for y in range(14,25):
        for x in range(12,15):torso.putpixel((x,y),idle.getpixel((x,y)))
    td.line((11,14,13,15),fill=COLORS['trim'])
    td.line((10,20,14,20),fill=COLORS['shadow'],width=2)
    body.alpha_composite(torso,(9,8+knee))
    if knee==0:
        body.alpha_composite(idle.crop((0,26,24,36)),(8,34))
    else:
        d.polygon([(18,34+knee),(23,34+knee),(28,38),(29,41),(18,42),(15,40)],fill=COLORS['outline'])
        d.polygon([(18,35+knee),(22,35+knee),(26,38),(25,40),(18,40)],fill=COLORS['trousers'])
        d.line((24,41,30,41),fill=COLORS['boot'],width=2)
    cast=arm([(22,25+knee),(26,21),cast_wrist],True)
    work=arm([(23,25+knee),(28,28+knee//2),work_wrist])
    head=blank();head.alpha_composite(idle.crop((0,0,24,14)),(9,8+knee))
    im=blank()
    for layer in [cast,body,work,head]:im.alpha_composite(layer)
    return im,{'casting_arm':cast,'body':body,'working_arm':work,'head':head}

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    idle=Image.open(ROOT/'assets/characters/caelan/idle_right.png').convert('RGBA')
    recipe=json.loads((ROOT/'assets/source/terrain/eldenmere/gate/recipe.json').read_text())
    palette=json.loads((ROOT/'assets/terrain/eldenmere/gate/palette.json').read_text())['materials']
    parts={n:Image.open(ROOT/f'assets/source/terrain/eldenmere/gate/parts/{n}.png').convert('RGBA') for n in ['panel','post','stone','beam']}
    structure=Image.open(ROOT/'assets/source/terrain/eldenmere/gate/parts/fixed_structure.png').convert('RGBA')
    _,tiles,_=channel_assets();gate_poses=poses(recipe)['opening']
    specs={
      'raise_hand':[(0,(27,28),(25,30)),(0,(29,25),(25,30)),(0,(31,22),(25,30)),(0,(29,20),(25,30))],
      'ease_water':[(0,(29,20),(25,30)),(0,(32,19),(25,30)),(0,(32,18),(25,30)),(0,(29,20),(25,30))],
      'hold_water':[(0,(29,20),(25,30))],
      'work_pin':[(0,(29,20),(28,27)),(2,(29,20),(34,28)),(4,(29,20),(34,27)),(4,(29,20),(34,27))],
      'open':[(max(0,4-i), (29,20), (34,4+23-round(8*p['lift']/12))) for i,p in enumerate(gate_poses)],
      'release_water':[(0,(29,20),(26,29)),(0,(29,23),(25,30)),(0,(27,26),(25,30)),(0,(25,29),(25,30))],
      'finish':[(0,(25,29),(25,30))]*4}
    sheet=Image.new('RGBA',(240,len(TIMELINE)*48));layer_sheets={};animations={}
    for row,(name,duration,count) in enumerate(TIMELINE):
        frames=[]
        for i,(knee,casting,working) in enumerate(specs[name]):
            im,layers=pose(idle,knee,casting,working);rect=[i*40,row*48,40,48]
            sheet.alpha_composite(im,rect[:2])
            for layer,source in layers.items():layer_sheets.setdefault(layer,Image.new('RGBA',sheet.size)).alpha_composite(source,rect[:2])
            frames.append({'rect':rect,'casting_hand':list(casting),'working_hand':list(working),'kneel_offset':knee})
        animations[name]={'duration_ms':duration,'frames':frames}
    sheet.save(OUT/'poses.png')
    for name,im in layer_sheets.items():im.save(OUT/(name+'.png'))
    gate_sheet=Image.new('RGBA',(144,36))
    for i,p in enumerate(gate_poses):
        y=23-round(8*p['lift']/12)
        gate_sheet.alpha_composite(gate_frame(p,parts,structure,tiles['channel_05_from_n'],palette,recipe,pin_side='left',pin_y_override=y),(24*i,0))
    gate_sheet.save(OUT/'opening_gate.png')
    # Five held-water levels, six subtle shimmer phases. Every pixel remains
    # inside the existing eight-pixel channel; the gate structure occludes it.
    water_sheet=Image.new('RGBA',(48,280));w=palette['water'];earth=palette['dirt']
    for level in range(5):
        for phase in range(6):
            im=Image.new('RGBA',(8,56));d=ImageDraw.Draw(im)
            for x in range(8):
                edge=56-round((56-(25+abs(x-3.5)))*level/4)
                for y in range(56):
                    if y<edge:
                        color=w['deep'] if x in (0,7) or level and y>edge-5 else w['base']
                        if (y+phase*2)%13==0 and x in (2,3,4):color=w['flow']
                        if level and edge-2<=y<edge:color=w['glint'] if (x+phase)%3 else w['reflection']
                    else:color=earth['shadow'] if (x+y)%7 else earth['base']
                    d.point((x,y),fill=color)
            water_sheet.alpha_composite(im,(phase*8,level*56))
    water_sheet.save(OUT/'water.png')
    (OUT/'animation.json').write_text(json.dumps({'canvas':list(SIZE),'anchor':list(ANCHOR),
      'source_idle_sha256':hashlib.sha256((ROOT/'assets/characters/caelan/idle_right.png').read_bytes()).hexdigest(),
      'water_origin':[1448,620],'water_size':[8,56],'water_colors':list(w.values()),
      'sequence':[name for name,_,_ in TIMELINE],'animations':animations},indent=2)+'\n')
if __name__=='__main__':build()
