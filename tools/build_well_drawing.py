"""Register moving well parts and gardener poses against the approved artwork.

The approved source remains intact. The idle well now has a bare rope hook;
one gardener-owned pail moves between her hands and that hook.
"""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw
import build_gardener as gardener

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/terrain/eldenmere/well/drawing'
SOURCE=ROOT/'assets/source/terrain/eldenmere/well'


def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    original=Image.open(SOURCE/'parts/native_structure.png').convert('RGBA')
    fixed=original.copy();d=ImageDraw.Draw(fixed)
    # Remove the old rope and pail within the shaft only. Reconstruct the dark
    # shaft and its water from registered neighboring material pixels.
    d.rectangle((37,47,42,59),fill='#34362f')
    d.rectangle((32,59,44,71),fill='#34362f')
    for y in range(65,72):
        for x in range(32,45):
            c=original.getpixel((x-8,y))
            if c[3]:fixed.putpixel((x,y),c)
    # The windlass itself is retained; its rope wrap gets an animated texture.
    # Only the old exposed crank is cleared, outside the right-hand timber.
    d.rectangle((69,40,83,51),fill=(0,0,0,0))
    fixed.save(OUT/'fixed.png')
    rim=Image.new('RGBA',original.size)
    # Front lip hides rope and bucket while they are inside the shaft.
    for y in range(62,96):
        for x in range(84):
            if y>=72 or (x<22 and y>=63) or (x>56 and y>=63):
                rim.putpixel((x,y),fixed.getpixel((x,y)))
    rim.save(OUT/'front_rim.png')
    # Six-pixel crank handle travel is deliberately legible at native scale.
    handles=[[round(74+3*math.cos(i*math.tau/8)),round(46+3*math.sin(i*math.tau/8))] for i in range(8)]
    status=json.loads((SOURCE/'drawing_recipe.json').read_text())['status'] if (SOURCE/'drawing_recipe.json').exists() else 'review'
    meta={
        'status':status,'position':[486,792],'canvas_size':[112,112],
        'fixed':'fixed.png','front_rim':'front_rim.png',
        'rope_origin':[54,43],'crank_pivot':[69,43],'crank_handles':handles,
        'hook_grip':[54,50],'lowered_bucket_grip':[54,74],
        'operator_position':[572,854],'hook_position':[558,862],
        'phases_ms':{'well_attach':1800,'well_secure':600,'well_grip':500,
                     'well_lower':3200,'well_fill':2000,'well_raise':4000,
                     'well_lock':500,'well_take_hold':1400,
                     'well_unhook':700,'well_take':1400},
        'source':'assets/source/terrain/eldenmere/well/parts/native_structure.png',
        'bucket_owner':'gardener',
        'notes':'One pail. Held throughout attaching/removing; rope moves vertically only. No lateral bucket transfer.'
    }
    write(OUT/'animation.json',meta)
    source=ROOT/'assets/source/characters/npcs/female_02/gardener/recipe.json'
    recipe=json.loads(source.read_text())
    if 'well_crank_left_0' not in recipe['work_poses']:recipe['status']='review'
    work=recipe['work_poses']
    def add(name,arms,grip=(0,18),lean=(0,0)):
        work[name]={'direction':'left','lean':list(lean),'arms':arms,'grip':list(grip),'order':'after'}
    # Grips are derived from the world crank registration, not eye-estimated
    # hand poses. Preserve the approved head/neck and planted boots.
    for i,(x,y) in enumerate(handles):
        hand=[486+x-560,792+y-824]
        add(f'well_crank_left_{i}',[[[11,16],[6,18],hand],[[13,16],[10,21],[6,20]]],hand)
        dy=int(i in (1,2,3,5,6,7))
        add(f'well_heavy_left_{i}',[[[11,16+dy],[6,19],hand],[[13,16+dy],[10,22],[6,21]]],hand,(-dy,dy))
    # Local grip at the parked hook: world hook minus body top-left. Both hands
    # meet the handle before detaching; the bucket then follows those hands.
    hook=[meta['position'][i]+meta['hook_grip'][i]-meta['hook_position'][i]+(12,30)[i] for i in range(2)]
    for mode,start,end in (('attach',(5,24),hook),('reach',(5,24),hook),('take',hook,(5,19))):
        for i in range(7):
            t=i/6;x=round(start[0]+(end[0]-start[0])*t);y=round(start[1]+(end[1]-start[1])*t)
            add(f'well_{mode}_left_{i}',[[[11,16],[4,17],[x,y]],[[13,16],[7,20],[x+2,y+2]]],(x,y))
    if json.loads(source.read_text())!=recipe:write(source,recipe)
    gardener.build()
    # Export the same bucketless idle into terrain/runtime map art, so the map
    # and compiler cannot reintroduce a second, permanent bucket.
    import os,sys
    os.environ.setdefault('SDL_VIDEODRIVER','dummy')
    os.environ.setdefault('SDL_AUDIODRIVER','dummy')
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
    sys.path.insert(0,str(ROOT))
    import pygame
    from well_routine import DrawingWell
    pygame.init();pygame.display.set_mode((1,1))
    class Art:
        def image(self,path):return pygame.image.load(str(ROOT/path)).convert_alpha()
    rig=DrawingWell(Art())
    for phase in range(6):
        surface=rig.sprite(phase*200).subsurface((0,0,84,96))
        pygame.image.save(surface,str(OUT.parent/f'frames/frame_{phase+1:02}.png'))
        if phase==0:pygame.image.save(surface,str(OUT.parent/'structure.png'))
    pygame.quit()
    water_mask=Image.new('L',(84,96))
    for x in (*range(29,35),*range(43,49)):water_mask.putpixel((x,69),255)
    water_mask.save(SOURCE/'parts/water_mask.png')
    idle=Image.open(OUT.parent/'structure.png').convert('RGBA')
    background=Image.new('RGBA',idle.size,'#e8edf2');background.alpha_composite(idle)
    background.convert('RGB').resize((504,576),Image.Resampling.NEAREST).save(OUT.parent/'well_review.png')
    well_meta=json.loads((OUT.parent/'well.json').read_text())
    well_meta.update(status=status,animation='Idle water glints and bare hook; gardener attaches her own pail when drawing water',bucket_owner='gardener')
    write(OUT.parent/'well.json',well_meta)
    # Authoring registrations are checked in alongside the generated layers.
    write(SOURCE/'drawing_recipe.json',meta)
    print('Built well drawing rig and eight registered crank poses.')


if __name__=='__main__':build()
