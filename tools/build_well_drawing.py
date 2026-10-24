"""Build the visible top-winch pail and centered gardener work poses."""
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
        'shaft_center_x':40,
        'rope_origin':[40,43],'crank_pivot':[69,43],'crank_handles':handles,
        'hook_mount':[40,46],'hook_tip':[40,49],
        'loading_grip':[40,82],'parked_bucket_grip':[40,51],
        'lowered_bucket_grip':[40,92],
        'operator_position':[572,854],'loading_position':[526,892],
        'snap_pixels':31,'settle_bounce_pixels':1,
        'phases_ms':{'well_attach':1200,'well_hook':600,'well_settle':700,
                     'well_grip':500,'well_lower':3200,'well_fill':2000,
                     'well_raise':4000,'well_lock':500,'well_catch':900,
                     'well_unhook':700,'well_take':1200},
        'source':'assets/source/terrain/eldenmere/well/parts/native_structure.png',
        'bucket_owner':'gardener',
        'notes':'One pail; near-side back-facing handoff. The idle line is fully retracted with a three-pixel hook beneath the windlass. On transfer the concealed pail snaps to a fully visible parked position below the winch, settles by one pixel, and then descends with the rope. Retrieval reverses the route before the pail snaps behind her torso.'
    }
    write(OUT/'animation.json',meta)
    source=ROOT/'assets/source/characters/npcs/female_02/gardener/recipe.json'
    recipe=json.loads(source.read_text())
    if 'well_crank_left_0' not in recipe['work_poses']:recipe['status']='review'
    work=recipe['work_poses']
    obsolete=('well_attach_left_','well_reach_left_','well_take_left_',
              'well_guide_left','well_setdown_left_','well_pickup_left_')
    for name in list(work):
        if name.startswith(obsolete):del work[name]
    def add(name,direction,arms,grip=(0,18),lean=(0,0),order='after'):
        work[name]={'direction':direction,'lean':list(lean),'arms':arms,
                    'grip':list(grip),'order':order}
    # Grips are derived from the world crank registration, not eye-estimated
    # hand poses. Preserve the approved head/neck and planted boots.
    for i,(x,y) in enumerate(handles):
        hand=[486+x-560,792+y-824]
        add(f'well_crank_left_{i}','left',[[[11,16],[6,18],hand],[[13,16],[10,21],[6,20]]],hand)
        dy=int(i in (1,2,3,5,6,7))
        add(f'well_heavy_left_{i}','left',[[[11,16+dy],[6,19],hand],[[13,16+dy],[10,22],[6,21]]],hand,(-dy,dy))

    def lerp(a,b,t):return [round(a[0]+(b[0]-a[0])*t),round(a[1]+(b[1]-a[1])*t)]
    # Near-side work is back-facing. Each upper/forearm segment stays within
    # seven pixels; shoulders and the approved head/body proportions stay fixed.
    for i in range(7):
        t=i/6;grip=lerp((20,24),(12,12),t)
        left=[(8,16),lerp((7,20),(10,14),t),lerp((7,24),(10,12),t)]
        right=[(16,16),lerp((18,20),(14,14),t),grip]
        add(f'well_attach_back_{i}','back',[left,right],grip,order='before')
    for i in range(5):
        t=i/4
        left=[(8,16),lerp((10,14),(8,17),t),lerp((10,12),(8,19),t)]
        right=[(16,16),lerp((14,14),(16,17),t),lerp((14,12),(16,19),t)]
        add(f'well_release_back_{i}','back',[left,right],(12,12),order='before')
    for i in range(7):
        # Reach the handle at the same frame as the pail's foreground snap,
        # then hold it steadily until ownership transfers to the actor.
        t=min(1,i/3)
        left=[(8,16),lerp((8,17),(10,14),t),lerp((8,19),(10,12),t)]
        right=[(16,16),lerp((16,17),(14,14),t),lerp((16,19),(14,12),t)]
        add(f'well_catch_back_{i}','back',[left,right],(12,12),order='before')
    add('well_unhook_back','back',[[[8,16],[10,14],[10,12]],[[16,16],[14,14],[14,12]]],(12,12),order='before')
    full_back=recipe['carry']['full']['back']
    for i in range(7):
        t=i/6;grip=lerp((12,12),full_back['grip'],t)
        left=[(8,16),lerp((10,14),full_back['arms'][0][1],t),lerp((10,12),full_back['arms'][0][2],t)]
        right=[(16,16),lerp((14,14),full_back['arms'][1][1],t),lerp((14,12),full_back['arms'][1][2],t)]
        add(f'well_take_back_{i}','back',[left,right],grip,order='before')
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
    well_meta.update(status=status,animation='Idle water glints and a retracted center hook; the gardener pail parks visibly beneath the winch before descending',bucket_owner='gardener')
    write(OUT.parent/'well.json',well_meta)
    # Authoring registrations are checked in alongside the generated layers.
    write(SOURCE/'drawing_recipe.json',meta)
    print('Built well drawing rig and eight registered crank poses.')


if __name__=='__main__':build()
