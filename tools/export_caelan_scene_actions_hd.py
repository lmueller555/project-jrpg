"""Export complete drawn Caelan scene poses at 2×; never assemble body parts.

Only technical alpha isolation, uniform per-sheet sampling, translation, one-pixel
contour inking and separately owned prop/FX composition happen here. Logical
scene geometry, timings and ownership cues remain in the scene controllers.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
from tools.caelan_outline import apply_outline
SOURCE=ROOT/'assets/source/characters/caelan/scene_actions_hd'
INPUTS=SOURCE/'inputs'
DIRECTIONS=('front','back','left','right')
META={'artwork_pixels_per_world_pixel':2,'anchor_space':'logical','contact_space':'logical'}

def encoded(im):
    f=BytesIO();im.save(f,format='PNG',optimize=True);return f.getvalue()
def blank(size=(24,36)):return Image.new('RGBA',tuple(v*2 for v in size))
def paste(dest,im,point):dest.alpha_composite(im,tuple(round(v*2) for v in point))
def old(name):return Image.open(INPUTS/name).convert('RGBA')
def metadata(name):return json.loads((INPUTS/name).read_text())
def doubled(im):return im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST)
@lru_cache(None)
def native_prop(path):
    """Keep held and deposited objects on the same registered presentation bank."""
    town=json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
    record=town.get('art_replacements',{}).get(path)
    if isinstance(record,dict):
        return Image.open(ROOT/record['file']).convert('RGBA')
    return doubled(Image.open(ROOT/path).convert('RGBA'))
def padded(body,size=(40,48),offset=(8,8)):
    im=blank(size);paste(im,body,offset);return im

# Sheet-level physical scales, calibrated against the approved 48×72 idles.
# Crouches and seated keys retain their head size rather than filling the canvas.
SHEETS={'cup_pass':(2,2,.105),'lift_back':(2,2,.12),'hold':(2,2,.12),'crouch_give':(4,2,.16),
        'seated_eat':(4,2,.14),'cup_work':(4,2,.16),
        'cast_wake':(4,2,.16),'sleep_rescue':(4,2,.16),'carry':(4,4,.215)}
@lru_cache(None)
def drawing(name,index):
    cols,rows,scale=SHEETS[name];im=Image.open(SOURCE/(name+'.png')).convert('RGBA')
    x,y=index%cols,index//cols
    cell=_main_component(im.crop((round(x*im.width/cols),round(y*im.height/rows),round((x+1)*im.width/cols),round((y+1)*im.height/rows))))
    if name=='cup_work' and index<4:scale=.14
    if name=='sleep_rescue' and index==0:scale=.13
    box=cell.getbbox();crop=cell.crop(box)
    crop=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
    canvas=blank();dx=round(24-crop.width/2);dy=69-crop.height
    if name=='sleep_rescue' and index==0:dy=2
    if dx<0 or dy<0:raise ValueError(('Drawing clips',name,index,crop.size))
    canvas.alpha_composite(crop,(dx,dy));return apply_outline(canvas)
def action_frame(i):
    if i<4:return drawing('cast_wake',4) if i==2 else drawing('hold',i)
    if i<12:return drawing('crouch_give',i-4)
    if i<20:return drawing('seated_eat',i-12)
    if i<24:return drawing('cup_pass',i-20)
    if i<28:return drawing('cup_work',i-20)
    return drawing('sleep_rescue',2) if i==31 else drawing('cast_wake',i-28)
def idle(d):return Image.open(ROOT/f'assets/characters/caelan/review_hd/idles/idle_{d}.png').convert('RGBA')
def walk(d,phase):
    # Approved travel remains immutable; sample its complete authored frames.
    folder=ROOT/f'assets/characters/caelan/review_hd/walk_{d}'
    data=json.loads((folder/'animation.json').read_text())
    return Image.open(folder/data['frames'][phase*4]['file']).convert('RGBA')
def carry(d,phase):return drawing('carry',DIRECTIONS.index(d)*4+phase)

def products():
    native_prop.cache_clear()
    result={};records=[]
    def export(path,im,anchor=(12,30)):
        raw=encoded(im);result[path]=raw
        records.append(dict(file=path,logical_size=[im.width//2,im.height//2],canvas=list(im.size),draw_anchor=list(anchor),output_sha256=sha256(raw).hexdigest(),**META))
    def document(path,data):result[path]=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode()
    def info(data):
        data=dict(data);data.update(META)
        data['appearance_source']='assets/source/characters/caelan/scene_actions_hd'
        data.update(canvas_space='logical',rect_space='artwork',frame_size_space='logical')
        if 'frame_size' in data:data['artwork_frame_size']=[v*2 for v in data['frame_size']]
        for key in ('appearance_source_sha256','appearance_registration','outline','arm_lengths','preserved_source_regions'):
            data.pop(key,None)
        return data
    folder='assets/story/sanctuary_opening/poses'
    export(folder+'/caelan_seated.png',action_frame(13));export(folder+'/caelan_seated_glance.png',action_frame(14))
    sleep=drawing('sleep_rescue',0);export(folder+'/caelan_sleep_head.png',sleep)
    sit=[idle('right'),action_frame(15),action_frame(14),action_frame(13)]
    for p,im in enumerate(sit):
        export(f'{folder}/caelan_sit/frame_{p+1:02}.png',im)
        export(f'{folder}/caelan_stand/frame_{4-p:02}.png',im)
    for name,start,wrists in [('caelan_eat',16,((17,23),(18,18),(18,15),(18,22))),('caelan_seated_cup',20,((15,18),(19,19),(19,21),(17,24)))]:
        data=info(metadata(f'{folder}/{name}/animation.json'))
        for p,rec in enumerate(data['frames']):
            export(f'{folder}/{name}/frame_{p+1:02}.png',action_frame(start+p));rec['wrist']=list(wrists[p])
        document(f'{folder}/{name}/animation.json',data)
    for name in ('caelan_sit','caelan_stand'):
        document(f'{folder}/{name}/animation.json',info(metadata(f'{folder}/{name}/animation.json')))
    for p,im in enumerate([sleep,drawing('sleep_rescue',1),action_frame(15),idle('front')]):export(f'{folder}/wake_up/frame_{p+1:02}.png',im)
    document(folder+'/wake_up/animation.json',info(metadata(folder+'/wake_up/animation.json')))
    recipe=info(metadata(folder+'/recipe.json'));recipe['notes']='Complete 2× drawn Caelan poses; logical positions, ownership and action cues retained.'
    recipe['source_png_sha256']={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in (ROOT/'assets/characters/caelan/review_hd/idles').glob('*.png')}
    document(folder+'/recipe.json',recipe)
    export('assets/characters/caelan/participation_sit_front.png',action_frame(12),anchor=(12,34))
    document('assets/source/characters/caelan/participation_sit/recipe.json',dict(output='assets/characters/caelan/participation_sit_front.png',logical_size=[24,36],draw_anchor=[12,34],seat_contact=[12,25],method='Complete drawn seated-front key.',**META))
    bag=native_prop('assets/story/halden/sack.png')
    def carrying(body,d,drop=0):
        im=padded(body,(32,40),(4,4));point={'front':(8,17),'back':(8,17),'left':(2,16),'right':(14,16)}[d];point=(point[0],point[1]+drop)
        if d=='back':
            behind=blank((32,40));paste(behind,bag,point);behind.alpha_composite(im);return behind
        paste(im,bag,point)
        # Only the existing drawn palms occlude the held sack; no replacement limbs.
        palms=blank()
        boxes={'front':(6,18,18,26),'left':(1,18,12,26),'right':(13,18,24,26)}
        x1,y1,x2,y2=(v*2 for v in boxes[d])
        for y in range(y1,y2):
            for x in range(x1,x2):
                r,g,b,a=body.getpixel((x,y))
                if a and r>=170 and g>=110 and b>=75 and r>g*1.1 and b>g*.5:palms.putpixel((x,y),(r,g,b,a))
        paste(im,palms,(4,4));return im
    folder='assets/story/halden/caelan'
    for i,d in enumerate(DIRECTIONS):
        export(f'{folder}/hold_{d}.png',carrying(action_frame(i),d),anchor=(16,34))
        for p in range(4):
            export(f'{folder}/carry_{d}_{p}.png',carrying(carry(d,p),d),anchor=(16,34))
            body=(drawing('lift_back',p) if d=='back' else action_frame(4+i) if p<2 else action_frame(i))
            export(f'{folder}/lift_{d}_{p}.png',padded(body,(32,40),(4,4)) if p<2 else carrying(body,d,1 if p==2 else 0),anchor=(16,34))
    folder='assets/story/venn/caelan'
    for i,d in enumerate(DIRECTIONS):export(f'{folder}/give_{d}.png',padded(action_frame(8+i)),anchor=(20,38))
    for mode in ('hands','tools'):
        for p,i in enumerate((24,25,26,27)):
            im=padded(action_frame(i))
            if mode=='tools':im.alpha_composite(doubled(old(f'tool_{p}.png')))
            export(f'{folder}/{mode}_{p}.png',im,anchor=(20,38))
    def spell_atlas(folder):
        data=info(metadata(folder+'/animation.json'));data['layer_order']=['body','energy']
        existing=old(folder+'/energy.png');body=blank(existing.size);energy=blank(existing.size)
        for animation in data['animations'].values():
            for rec in animation['frames']:
                x,y,w,h=rec['rect'];angle=rec['angle_degrees'];index=28 if angle>=65 else 29 if angle>=15 else 30
                native=idle('right') if angle==90 else action_frame(index)
                palm=(11,24) if angle==90 else (19,18) if index==29 else (22,13) if index==30 else (14,24)
                paste(body,padded(native),(x,y))
                fx=existing.crop((x,y,x+w,y+h));previous=rec.get('casting_hand',[22,27]);destination=(palm[0]+8,palm[1]+8)
                shifted=blank((w,h));paste(shifted,doubled(fx),(destination[0]-previous[0],destination[1]-previous[1]));paste(energy,shifted,(x,y))
                rec['casting_hand']=list(destination);rec['appearance_source_cell']=index if angle!=90 else None
                rec.pop('joints',None);rec['rect']=[v*2 for v in rec['rect']]
        im=body.copy();im.alpha_composite(energy)
        for name,image in [('poses',im),('body',body),('energy',energy)]:export(folder+'/'+name+'.png',image,anchor=(20,38))
        data.pop('source_body',None);data.pop('source_idle_sha256',None)
        document(folder+'/animation.json',data)
    spell_atlas('assets/story/venn/magicks');spell_atlas('assets/story/mill/poses')
    folder='assets/story/lantern/poses';data=info(metadata(folder+'/caelan.json'));frame_layer=doubled(old(folder+'/caelan_frame.png'));body=Image.new('RGBA',frame_layer.size)
    for action,frames in data['actions'].items():
        choices=(24,25,26,26,27) if action=='work' else (24,25,26,27)
        for p,rec in enumerate(frames):
            x,y,w,h=rec['rect'];paste(body,padded(action_frame(choices[p])),(x,y));rec['rect']=[v*2 for v in rec['rect']];rec.pop('joints',None);rec['appearance_source_cell']=choices[p]
    im=body.copy();im.alpha_composite(frame_layer)
    export(folder+'/caelan.png',im,anchor=(20,38));export(folder+'/caelan_body.png',body,anchor=(20,38));export(folder+'/caelan_frame.png',frame_layer,anchor=(20,38))
    data['layers'].pop('working_arm',None)
    for key in ('source','source_idle','source_sha256','head_pixels_preserved_above_y','lower_body_preserved_from_y'):data.pop(key,None)
    document(folder+'/caelan.json',data)
    folder='assets/story/elira';lantern=native_prop('assets/terrain/eldenmere/elira_interior/sprites/lantern_unlit.png')
    def lantern_canvas(body,origin=None,behind=False):
        im=blank((40,64));pos=(8+(origin or (18,2))[0],24+(origin or (18,2))[1])
        if origin is not None and behind:paste(im,lantern,pos)
        paste(im,body,(8,24))
        if origin is not None and not behind:paste(im,lantern,pos)
        return im
    for i,d in enumerate(DIRECTIONS):
        origin={'front':(12,0),'back':(12,0),'left':(-5,0),'right':(16,0)}[d]
        export(f'{folder}/hold_{d}.png',lantern_canvas(action_frame(i),origin,d=='back'),anchor=(20,54))
        export(f'{folder}/give_{d}.png',lantern_canvas(action_frame(8+i)),anchor=(20,54))
        for p in range(4):export(f'{folder}/carry_{d}_{p}.png',lantern_canvas(carry(d,p),origin,d=='back'),anchor=(20,54))
    reach=[idle('back'),action_frame(1),drawing('sleep_rescue',3),action_frame(31)]
    take=[action_frame(31),drawing('sleep_rescue',3),action_frame(1),action_frame(1)]
    for p in range(4):
        f=p/3
        export(f'{folder}/reach_{p}.png',lantern_canvas(reach[p]),anchor=(20,54))
        export(f'{folder}/take_{p}.png',lantern_canvas(take[p],(round(6+6*f),round(-19+19*f)),True),anchor=(20,54))
        export(f'{folder}/step_{p}.png',lantern_canvas(walk('back',p)),anchor=(20,54))
        export(f'{folder}/down_{p}.png',lantern_canvas(carry('back',p),(12,0),True),anchor=(20,54))
        export(f'{folder}/place_{p}.png',lantern_canvas(action_frame(0),(round(18-8*f),round(2+6*f))),anchor=(20,54))
        export(f'{folder}/place_empty_{p}.png',lantern_canvas(action_frame(0)),anchor=(20,54))
    for p in range(4):export(f'assets/story/sanctuary_rescue/actions/row_5_{p}.png',padded(drawing('sleep_rescue',4+p),(40,40),(8,0)),anchor=(20,34))
    sources=[dict(file=str(p.relative_to(ROOT)),sha256=sha256(p.read_bytes()).hexdigest()) for p in SOURCE.glob('*.png') if not p.name.startswith(('intent_','reference_'))]
    town=json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text());prop_sources=[]
    for path in ('assets/story/halden/sack.png','assets/terrain/eldenmere/elira_interior/sprites/lantern_unlit.png'):
        replacement=town.get('art_replacements',{}).get(path)
        if isinstance(replacement,dict):
            p=ROOT/replacement['file'];prop_sources.append({'file':replacement['file'],'sha256':sha256(p.read_bytes()).hexdigest()})
    document('assets/characters/caelan/scene_actions.json',dict(version=1,status='integrated',builder='tools/export_caelan_scene_actions_hd.py',sources=sources,prop_sources=prop_sources,outputs=records,**META))
    rescue=json.loads((SOURCE/'rescue_input.json').read_text());rescue['actors']['caelan']['poses']['assist'].update(META)
    document('assets/story/sanctuary_rescue/art.json',rescue)
    return result

def build(check=False):
    output=products();changed=[]
    for name,raw in output.items():
        p=ROOT/name
        if not p.exists() or p.read_bytes()!=raw:
            changed.append(name)
            if not check:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    if check and changed:raise SystemExit('Stale scene exports: '+', '.join(changed))
    return output
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} scene exports')
