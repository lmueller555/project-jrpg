"""Stage native regional work bodies from retained full-figure source masters.

The legacy exporter remains the authority for complete source-cell selection and
logical attachment metadata. A bounded authoring adapter captures each original
unscaled figure at registration and uniformly samples it at native2x. It does
not enlarge the exported1x sprite, synthesize limbs or write legacy banks. Runtime
activation is deliberately absent. Source/exporter hashes make this dependency
explicit; a source change requires review rather than silently changing outputs.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from hashlib import sha256
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
from unittest.mock import patch
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
ROLES={
 'grain_loader':('build_grain_loader','grain_workers/loader','loader'),
 'grain_coworker':('build_grain_coworker','grain_workers/coworker','coworker'),
 'bridge_mason':('build_bridge_mason','bridge_workers/mason','mason'),
 'bridge_tender':('build_bridge_tender','bridge_workers/tender','tender'),
}

def digest(data):return sha256(data).hexdigest()
def doc(data):return (json.dumps(data,indent=2)+'\n').encode()
def png(image):
    b=BytesIO();image.save(b,format='PNG',optimize=True);return b.getvalue()

def _native(raw,scale,kind='soles',head_aligned=False):
    native_scale=scale*2
    resized=raw.resize((round(raw.width*native_scale),round(raw.height*native_scale)),Image.Resampling.NEAREST)
    if kind=='cropped':
        soles=raw.getchannel('A').crop((0,max(0,raw.height-8),raw.width,raw.height)).getbbox()
        cx=(soles[0]+soles[2])/2
        origin=(48-round(cx*native_scale),92-resized.height)
    else:
        box=resized.getbbox()
        if box is None:raise ValueError('Empty original body')
        soles=resized.getchannel('A').crop((0,max(0,box[3]-4),resized.width,box[3])).getbbox()
        cx=round((soles[0]+soles[2]-1)/2)
        if head_aligned:
            head=resized.getchannel('A').crop((0,box[1],resized.width,min(box[3],box[1]+24))).getbbox()
            cx=round((head[0]+head[2]-1)/2)
        origin=(48-cx,94-box[3])
    occupied=resized.getbbox()
    absolute=(origin[0]+occupied[0],origin[1]+occupied[1],origin[0]+occupied[2],origin[1]+occupied[3])
    if min(absolute)<0 or absolute[2]>96 or absolute[3]>104:raise ValueError('Native complete body leaves canvas before composition: '+str(absolute))
    out=Image.new('RGBA',(96,104));out.alpha_composite(resized,origin)
    box=out.getbbox()
    if box is None or min(box)<0 or box[2]>96 or box[3]>104:raise ValueError('Native body clips')
    return out,{'source_rgba_sha256':digest(raw.tobytes()),'source_size_artwork':list(raw.size),
                'uniform_scale_to_native':native_scale,'origin_native':list(origin),
                'registration_kind':kind,'head_aligned':head_aligned}

def _module(root,name):
    if str(root/'tools') not in sys.path:sys.path.insert(0,str(root/'tools'))
    file=root/'tools'/f'{name}.py';spec=importlib.util.spec_from_file_location('_regional_native_'+name,file)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def _payload(module,role):
    result=module.build() if role in ('grain_loader','bridge_mason') else module.build_payload()
    if isinstance(result,tuple):return result[0],result[1]
    return result,json.loads(result[module.OUT/'animation.json'])

def _capture(root,role):
    name,bank,_=ROLES[role];module=_module(root,name);legacy,metadata=_payload(module,role)
    held={};records={};original_png=module.png
    def encode(image):
        item=held.get(id(image))
        if item is None:return original_png(image)
        _,native,record=item;data=png(native);records[digest(data)]=record;return data
    with ExitStack() as stack:
        stack.enter_context(patch.object(module,'png',encode))
        if role=='grain_coworker':
            original=module.registered
            def registered(source,row,col):
                logical=original(source,row,col);y0,y1=module.ROWS[row]
                raw=source.crop((round(source.width*col/4),y0,round(source.width*(col+1)/4),y1)).convert('RGBA')
                raw.putalpha(raw.getchannel('A').point(lambda v:255 if v>=128 else 0))
                native,record=_native(raw,module.SCALE)
                record.update(source_cell=[row,col],source_file='assets/source/characters/grain_workers/coworker/work_generated.png')
                held[id(logical)]=(logical,native,record);return logical
            stack.enter_context(patch.object(module,'registered',registered))
        else:
            original=module.register
            def register(raw,scale,*args,**kwargs):
                logical=original(raw,scale,*args,**kwargs)
                native,record=_native(raw,scale,'cropped' if role in ('grain_loader','bridge_mason') else 'soles',bool(kwargs.get('head_aligned',False)))
                held[id(logical)]=(logical,native,record);return logical
            stack.enter_context(patch.object(module,'register',register))
        native,native_metadata=_payload(module,role)
    if metadata!=native_metadata:raise ValueError('Logical attachment/timing metadata changed')
    def normal(payload):
        out={}
        for key,data in payload.items():
            path=Path(key)
            if not path.is_absolute():path=root/'assets/characters'/bank/path
            out[path.relative_to(root).as_posix()]=data
        return out
    return normal(legacy),normal(native),metadata,records

def refined_body(recipe,file,folder,data,trace):
    """Select a hash-pinned complete master, never transform an existing body."""
    refinement=recipe.get('refined_masters',{}).get(file)
    if refinement is None:return data,trace
    relative=Path(refinement['file']);folder=folder.resolve();target=(folder/relative).resolve()
    if relative.is_absolute() or not target.is_relative_to(folder):raise ValueError('Refined master leaves actor source')
    refined=target.read_bytes()
    if digest(refined)!=refinement['sha256']:raise ValueError('Reviewed refined master changed: '+file)
    with Image.open(BytesIO(refined)) as raw:im=raw.convert('RGBA')
    if im.size!=(96,104) or not im.getbbox() or set(im.getchannel('A').tobytes())-{0,255}:raise ValueError('Invalid complete refined master')
    return refined,{'original_registration':trace,'refined_complete_master':str(relative),'refined_master_sha256':digest(refined)}

def products(role,root=ROOT,recipe_root=None):
    recipe_root=recipe_root or root
    if role not in ROLES:raise ValueError('Role has no retained complete-body source')
    source='assets/source/characters/regional_npc_hd/'+role+'/activity_hd'
    recipe_raw=(recipe_root/source/'recipe.json').read_bytes();recipe=json.loads(recipe_raw)
    if recipe['actor_id']!=role or recipe['runtime_activation']:raise ValueError('Not a dormant scoped recipe')
    for record in recipe['dependencies']:
        if digest((root/record['file']).read_bytes())!=record['sha256']:raise ValueError('Reviewed source changed: '+record['file'])
    legacy,native,metadata,traces=_capture(root,role);bank=ROLES[role][1]
    expected={'poses/'+f['file'] for clip in metadata['sequences'].values() for f in clip['frames']}
    if set(recipe.get('refined_masters',{}))-expected:raise ValueError('Unknown refined master filename')
    pack='assets/characters/regional_npc_hd/'+role+'/activity_hd'
    output={};frames=[];native_by_legacy={};review=[]
    coworker=None
    if role=='bridge_tender':coworker=products('grain_coworker',root,recipe_root)
    for clip,sequence in metadata['sequences'].items():
        for index,frame in enumerate(sequence['frames']):
            old_path='assets/characters/'+bank+'/'+frame['file'];old=legacy[old_path]
            if (root/old_path).read_bytes()!=old:raise ValueError('Legacy bank is not reproducible: '+old_path)
            data=native[old_path];trace=traces.get(digest(data))
            if trace is None:
                if role!='bridge_tender' or clip not in ('measure_left','stretch_front'):raise ValueError('No original master registration for '+old_path)
                reused_clip='work_left' if clip=='measure_left' else 'stretch_front'
                reused=f'assets/characters/regional_npc_hd/grain_coworker/activity_hd/poses/{reused_clip}_{index}.png'
                data=coworker[reused];trace={'reuse_complete_native_body':reused,'legacy_selection':'assets/characters/grain_workers/coworker/'+reused_clip+'_'+str(index)+'.png'}
            file='poses/'+frame['file']
            data,trace=refined_body(recipe,file,recipe_root/source,data,trace)
            with Image.open(BytesIO(data)) as original:im=original.convert('RGBA')
            if im.size!=(96,104) or set(im.getchannel('A').tobytes())-{0,255}:raise ValueError('Native body shape/alpha changed')
            file='poses/'+frame['file'];output[pack+'/'+file]=data
            frames.append({'clip':clip,'index':index,'file':file,'sha256':digest(data),'logical_size':[48,52],
                           'artwork_size':[96,104],'artwork_pixels_per_world_pixel':2,
                           'draw_anchor_logical':[24,46],'logical_attachment_metadata':frame,
                           'legacy_body_sha256':digest(old),'source_registration':trace})
            native_by_legacy[digest(old)]=data
        with Image.open(BytesIO(output[pack+'/poses/'+sequence['frames'][0]['file']])) as raw:review.append((clip,raw.convert('RGBA')))
    board=Image.new('RGB',(640,32+((len(review)+4)//5)*132+104),'#e3e6da');draw=ImageDraw.Draw(board)
    draw.text((8,8),role+' / DORMANT NATIVE SOURCE BODIES / NOT GAMEPLAY',fill='#243529')
    for i,(clip,im) in enumerate(review):
        x=i%5*128+16;y=i//5*132+32;board.paste(im,(x,y),im);draw.text((i%5*128+2,y+108),clip,fill='#243529')
    with Image.open(root/'assets/characters/caelan/review_hd/idles/idle_front.png') as raw:caelan=raw.convert('RGBA')
    board.paste(caelan,(40,board.height-92),caelan);draw.text((104,board.height-65),'Approved Caelan at native2x scale',fill='#243529')
    output[pack+'/native_clip_keys.png']=png(board)
    motion_reviews=[]
    for key,clip in metadata['sequences'].items():
        views=[]
        for f in clip['frames']:
            with Image.open(BytesIO(output[pack+'/poses/'+f['file']])) as raw:body=raw.convert('RGBA')
            view=Image.new('RGB',(128,140),'#e3e6da');view.paste(body,(16,4),body)
            ImageDraw.Draw(view).text((4,116),key,fill='#243529');views.append(view)
        for slow,suffix in ((1,'normal'),(2,'half_speed')):
            b=BytesIO();durations=[max(10,round(f['duration_ms']*slow/10)*10) for f in clip['frames']]
            views[0].save(b,format='GIF',save_all=True,append_images=views[1:],duration=durations,loop=0,disposal=2)
            file='review/'+key+'_'+suffix+'.gif';data=b.getvalue();output[pack+'/'+file]=data
            motion_reviews.append({'file':file,'speed':suffix,'authored_duration_ms':sum(f['duration_ms'] for f in clip['frames'])*slow,'presentation':'Offline body-only motion review, not gameplay. PNGs remain exact color/alpha authority.'})
    manifest={'version':1,'actor_id':role,'integration_status':'staged_not_integrated','runtime_activation':False,
              'visual_approval':'pending_owner_review','artwork_pixels_per_world_pixel':2,'logical_canvas':[48,52],
              'draw_anchor_logical':[24,46],'sequences':{key:{**clip,'frames':[{**f,'file':'poses/'+f['file']} for f in clip['frames']]} for key,clip in metadata['sequences'].items()},'frames':frames,
              'source_recipe':source+'/recipe.json','source_recipe_sha256':digest(recipe_raw),
              'builder':'tools/build_regional_worker_activity_hd.py','builder_sha256':digest(Path(__file__).read_bytes()),
              'motion_reviews':motion_reviews,'dependencies':recipe['dependencies'],'activation_gates':recipe['activation_gates'],
              'canvas_geometry':'Art-only padding grows40x44 to48x52, with anchor20,38 ->24,46; body-to-ground transform and world attachment offsets are unchanged. Padding restores full source crowns instead of clipping high cells.',
              'limits':'Retained complete source bodies re-sampled uniformly at2x, or explicitly reviewed complete refined masters at the same registration. No runtime binding, prop ownership, hand metadata, timing, collision or save changes; props remain separately owned. Not a user visual approval.'}
    output[pack+'/manifest.json']=doc(manifest)
    return output

def build(role,root=ROOT,recipe_root=None,output_root=None,check=False):
    output_root=output_root or root;output=products(role,root,recipe_root);stale=[]
    for file,data in output.items():
        path=output_root/file
        if not path.is_file() or path.read_bytes()!=data:
            stale.append(file)
            if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if check and stale:raise SystemExit('Stale native work exports: '+', '.join(stale))
    print(role+': '+str(len(output))+' dormant native exports '+('verified' if check else 'built'))
    return output
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('role',choices=ROLES);p.add_argument('--check',action='store_true');a=p.parse_args();build(a.role,check=a.check)
