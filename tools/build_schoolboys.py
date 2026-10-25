"""Register two new child designs onto the approved four-phase child poses."""
import hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from build_liam_family_front_walks import ROOT,read,write,blank,rgba

DIRECTIONS=('front','left','right','back')
SPECS={
 'finn':{'name':'Finn','age_years':6,'home':'home_a','height':22,
         'hair':['#3d2118','#785132','#a47848'],'tunic':['#9b7a49','#c3a575','#e2cca2'],
         'collar':['#455531','#6e7d43','#919b61'],'trousers':['#51413b','#746050','#9d7953'],
         'iris':'#4e7950','description':'Tousled brown hair, tan shirt, olive vest, brown trousers and boots.'},
 'rowan':{'name':'Rowan','age_years':9,'home':'home_b','height':27,
          'hair':['#222027','#38343d','#55515b'],'tunic':['#713d32','#a65b45','#cd8260'],
          'collar':['#713d32','#a65b45','#cd8260'],'trousers':['#35343b','#4b4952','#68646e'],
          'iris':'#98703a','description':'Short cropped black hair, rust tunic, charcoal trousers and brown boots.'},
}
BASE=ROOT/'assets/characters/liam'
OLD=read(BASE/'palette.json')


def registered(who,source,eyes,offset=(0,0)):
    spec=SPECS[who];height=spec['height']
    ty=lambda y:round(34+(y-34)*height/26)
    new={**OLD['materials'],**{k:spec[k] for k in ('hair','tunic','collar','trousers')}}
    general={rgba(c):rgba(new[k][i]) for k,ramp in OLD['materials'].items() if k!='hair' for i,c in enumerate(ramp)}
    hair={rgba(c):rgba(new['hair'][i]) for i,c in enumerate(OLD['materials']['hair'])}
    # Eye pixels are authored again after registration, preserving both rows.
    image=blank((24,36));semantic=blank((24,36));dx,dy=offset
    head_end=21+dy
    for y in range(36):
        sy=round(34+(y-34)*26/height)
        if not 0<=sy<36:continue
        for x in range(24):
            p=source.getpixel((x,sy))
            if not p[3]:continue
            if p==rgba(OLD['eyes']['iris']):color=rgba(spec['iris'])
            elif sy<head_end and p in hair:color=hair[p]
            elif sy>=28+dy and p in {rgba(c) for c in OLD['materials']['skin']}:
                color=rgba(new['trousers'][0 if p==rgba(OLD['materials']['skin'][1]) else 1])
            else:color=general.get(p,p)
            image.putpixel((x,y),color)
            if p in {rgba(c) for c in OLD['materials']['tunic']}:semantic.putpixel((x,y),p)
    top=image.getbbox()[1]
    # Hair silhouettes differ from Liam, while their roots stay on the head.
    design=blank((24,36));d=ImageDraw.Draw(design)
    headpixels=[(x,y) for y in range(top,min(ty(head_end),36)) for x in range(24)
                if image.getpixel((x,y)) in {rgba(c) for c in new['hair']}]
    left=min(x for x,y in headpixels);right=max(x for x,y in headpixels)
    if who=='rowan':
        for y in range(top,min(top+3,36)):
            for x in range(24):image.putpixel((x,y),(0,0,0,0))
        d.line((left+2,top,right-2,top),fill=new['outline'][0])
        d.rectangle((left+1,top+1,right-1,top+2),fill=new['hair'][1])
        d.point((left+2,top+1),fill=new['hair'][2])
        d.point((left+1,top+2),fill=new['hair'][0])
        # The 27px registration opens a one-pixel wrist in the fourth profile
        # walking pose. Restore its hand inside the retained outline pixels.
        if (image.getpixel((7,24))==rgba(new['outline'][0])
                and image.getpixel((8,25))==rgba(new['outline'][0])
                and not image.getpixel((8,24))[3]):
            d.point((8,24),fill=new['skin'][0])
    else:
        # Retain child-scale tousles but add a separate two-point cowlick.
        center=(left+right)//2
        d.line((center-2,top,center,top),fill=new['hair'][0])
        d.point((center-1,top+1),fill=new['hair'][2])
        d.point((right-1,top+2),fill=new['hair'][2])
        vest=ImageDraw.Draw(design)
        for y in range(ty(22+dy),ty(27+dy)+1):
            for x in (10+dx,14+dx):
                if 0<=x<24 and 0<=y<36 and semantic.getpixel((x,y))[3]:
                    vest.point((x,y),fill=spec['collar'][0 if x<12+dx else 1])
    face=blank((24,36));f=ImageDraw.Draw(face);eye_records=[]
    for x,y in eyes:
        ey=ty(y);f.point((x,ey),fill=OLD['eyes']['pupil']);f.point((x,ey+1),fill=spec['iris']);eye_records.append([x,ey])
    layers={'registered_body':image,'hair_and_costume':design,'eyes':face}
    merged=blank((24,36))
    for layer in layers.values():merged.alpha_composite(layer)
    return merged,layers,eye_records,ty


def export_layers(who,group,index,image,layers):
    source=ROOT/f'assets/source/characters/{who}'/group
    source.mkdir(parents=True,exist_ok=True);paths=[];combined=blank((24,36))
    for name,layer in layers.items():
        p=source/f'{index}_{name}.png';layer.save(p);paths.append(p.relative_to(ROOT).as_posix());combined.alpha_composite(layer)
    assert combined.tobytes()==image.tobytes()
    return paths


def build():
    protected={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for name in ('liam','caelan','tomas') for p in (ROOT/'assets/characters'/name).rglob('*.png')}
    for who,spec in SPECS.items():
        output=ROOT/f'assets/characters/{who}';output.mkdir(parents=True,exist_ok=True)
        status=read(output/'character.json')['status'] if (output/'character.json').exists() else 'review'
        palette={**OLD,'status':status,'materials':{**OLD['materials'],**{k:spec[k] for k in ('hair','tunic','collar','trousers')}},'eyes':{'pupil':OLD['eyes']['pupil'],'iris':spec['iris']}}
        write(output/'palette.json',palette)
        for direction in DIRECTIONS:
            im=Image.open(BASE/f'idle_{direction}.png').convert('RGBA');meta=read(BASE/f'idle_{direction}.json')
            image,layers,eyes,ty=registered(who,im,meta['eyes']['top_pixels'])
            image.save(output/f'idle_{direction}.png');paths=export_layers(who,f'idle_{direction}','idle',image,layers)
            x,y,r,b=image.getbbox();assert b==35 and b-y==spec['height'],(who,direction,image.getbbox())
            write(output/f'idle_{direction}.json',{'character':who,'status':status,'animation':f'idle.{direction}','image':f'idle_{direction}.png',
                 'frame_size':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],'visible_height_px':b-y,'occupied_rect':[x,y,r-x,b-y],
                 'eyes':{'top_pixels':eyes,'height':2,'iris_offset_y':1},'layers_from_repo_root':paths,'palette':'palette.json'})
            for verb,ms in (('walk',140),('run',100)):
                source=BASE/f'{verb}_{direction}';motion=read(source/'animation.json');folder=output/f'{verb}_{direction}';folder.mkdir(parents=True,exist_ok=True)
                frames=[];records=[];sheet=blank((96,36))
                for index,record in enumerate(motion['frames'],1):
                    frame=Image.open(source/record['file']).convert('RGBA')
                    offset=record.get('upper_body_offset',[0,0])
                    motion_eyes=record.get('eyes',[[x+offset[0],y+offset[1]] for x,y in meta['eyes']['top_pixels']])
                    image,layers,eyes,ty=registered(who,frame,motion_eyes,offset)
                    assert image.getbbox()[0]>0 and image.getbbox()[2]<24 and image.getbbox()[3]<=35,(who,verb,direction,index,image.getbbox())
                    assert set(image.getchannel('A').tobytes())=={0,255}
                    filename=f'frame_{index:02}.png';image.save(folder/filename);sheet.alpha_composite(image,((index-1)*24,0));frames.append(image)
                    paths=export_layers(who,f'{verb}_{direction}',f'frame_{index:02}',image,layers)
                    dx,dy=record.get('upper_body_offset',[0,0]);bob=ty(9+dy)-ty(9)
                    records.append({'file':filename,'duration_ms':ms,'phase':record.get('phase',str(index)),
                        'upper_body_offset':[dx,bob],'shoulder_offset':[dx,bob],'airborne':record.get('airborne',False),
                        'eyes':eyes,'layers_from_repo_root':paths})
                assert len({f.tobytes() for f in frames})==4,(who,verb,direction)
                sheet.save(folder/'spritesheet.png')
                write(folder/'animation.json',{'character':who,'animation':f'{verb}.{direction}','status':status,'frame_count':4,'frame_size':[24,36],
                     'draw_anchor':[12,30],'foot_anchor':[12,34],'loop':True,'duration_ms':ms*4,'image':'spritesheet.png','frames':records})
                write(folder/'recipe.json',{'source_animation':(source/'animation.json').relative_to(ROOT).as_posix(),
                     'child_visible_height_px':spec['height'],'registration':'Nearest-neighbor height registration anchored at native foot row34; authored child face/hair/vest details',
                     'source_motion':'Approved shared four-phase child walk/run, preserving arm counterstride and head/shoulder bob.'})
        write(output/'character.json',{'id':who,'name':spec['name'],'age_years':spec['age_years'],'home':spec['home'],
             'frame_size':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],'visible_height_px':spec['height'],'status':status,'design':spec['description']})
        write(ROOT/f'assets/source/characters/{who}/recipe.json',{'id':who,'spec':spec,'registration_source':'assets/characters/liam',
             'source_height_px':26,'target_height_px':spec['height'],'foot_baseline':34,'approved_png_sha256':protected})
        (output/'README.md').write_text(f"# {spec['name']} — {status}\n\n{spec['age_years']} years old; {spec['height']} visible pixels in a 24×36 frame.\n{spec['description']} Home: `{spec['home']}`.\n\nFour directional idles and four-pose walks (140ms) and runs (100ms) preserve\nthe approved shared child gait, with new hair, clothing and eye details.\nRun poses retain bent elbows, stride extension, lean and flight.\nBuild with `python tools/build_schoolboys.py`. Source layers and recipes live\nunder `assets/source/characters/{who}` and reconstruct each export.\n")
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in protected.items())
    print('Built Finn and Rowan: four-direction idles, walks and runs; existing art unchanged.')


if __name__=='__main__':build()
