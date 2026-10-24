"""Register moving well parts and gardener poses against the approved artwork.

The original well exports remain intact. This adds an interaction rig; the
runtime shares its phase clock with the gardener rather than looping a GIF.
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
    original=Image.open(OUT.parent/'structure.png').convert('RGBA')
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
        'rope_origin':[40,43],'crank_pivot':[69,43],'crank_handles':handles,
        'idle_bucket_grip':[40,49],'lowered_bucket_grip':[40,73],
        'raised_bucket_grip':[40,43],'pour_bucket_grip':[73,73],
        'pail_grip_world':[563,878], 'operator_position':[572,854],
        'pail_position':[576,884],
        'phases_ms':{'well_setdown':1000,'well_grip':500,'well_lower':3200,
                     'well_fill':2000,'well_raise':4000,'well_lock':500,
                     'well_guide':1500,'well_pour':3000,'well_reset':2000,
                     'well_pickup':1000},
        'source':'assets/terrain/eldenmere/well/structure.png',
        'notes':'Two buckets; portable pail fills only during the transfer. Shared actor clock.'
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
    add('well_guide_left',[[[11,16],[5,16],[-5,12]],[[13,16],[8,21],[3,18]]])
    for i in range(5):
        x=round(5-6*i/4)
        add(f'well_setdown_left_{i}',[[[11,16],[6,21],[x,24]],[[13,16],[11,22],[7,24]]],(x,24),(-int(i>1),int(i>1)))
        x=round(-1+6*i/4);y=round(24-5*i/4)
        add(f'well_pickup_left_{i}',[[[11,16],[7,20],[x,y]],[[13,16],[11,22],[x+2,y+2]]],(x,y),(-int(i<2),int(i<2)))
    if json.loads(source.read_text())!=recipe:write(source,recipe)
    gardener.build()
    # Authoring registrations are checked in alongside the generated layers.
    write(SOURCE/'drawing_recipe.json',meta)
    print('Built well drawing rig and eight registered crank poses.')


if __name__=='__main__':build()
