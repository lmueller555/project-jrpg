"""Register authored worn-rig exploration and cinematic drawings, without repainting."""
from pathlib import Path
from statistics import median
import hashlib,json,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
SOURCE=ROOT/'assets/source/characters/mira/arm_rig'
OUT=ROOT/'assets/characters/mira'

def cells(name,columns,rows):
    sheet=Image.open(SOURCE/name).convert('RGBA');result=[]
    for i in range(columns*rows):
        x,y=i%columns,i//columns
        box=(round(x*sheet.width/columns),round(y*sheet.height/rows),round((x+1)*sheet.width/columns),round((y+1)*sheet.height/rows))
        cell=_main_component(sheet.crop(box));bounds=cell.getbbox()
        contacts=[(xx,yy) for yy in range(bounds[3]-35,bounds[3]) for xx in range(bounds[0],bounds[2]) if cell.getpixel((xx,yy))[3]]
        foot=((min(x for x,y in contacts)+max(x for x,y in contacts))/2,bounds[3]-1)
        result.append((cell,bounds,foot,box))
    return result

def frame(record,scale,canvas,anchor):
    cell,bounds,foot,_=record
    crop=cell.crop(bounds)
    cut=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
    image=Image.new('RGBA',canvas)
    position=(round(anchor[0]-(foot[0]-bounds[0])*scale),round(anchor[1]-(foot[1]-bounds[1])*scale))
    image.alpha_composite(cut,position)
    b=image.getbbox()
    if not b or position[0]<0 or position[1]<0 or position[0]+cut.width>canvas[0] or position[1]+cut.height>canvas[1]:raise ValueError(('clipped',b,canvas,position))
    return image

def build():
    source=cells('exploration_authored.png',6,6)
    scale=30/median(r[1][3]-r[1][1] for r in source[:20])
    exports=[]
    def export(path,index,canvas=(32,36),anchor=(16,34),amount=scale):
        image=frame(source[index],amount,canvas,anchor);image.save(ROOT/path,optimize=True)
        exports.append(dict(file=path,source_cell=index,source='exploration_authored.png',scale=amount,anchor=list(anchor)))
        return image
    for index,direction in enumerate(('front','back','left','right')):
        export(f'assets/characters/mira/idle_{direction}.png',index)
        board=Image.new('RGBA',(128,36))
        for phase in range(4):
            image=export(f'assets/characters/mira/walk_{direction}/frame_{phase+1:02}.png',4+index*4+phase)
            board.alpha_composite(image,(phase*32,0))
        board.save(OUT/f'walk_{direction}/spritesheet.png')
        p=OUT/f'walk_{direction}/animation.json';data=json.loads(p.read_text());data.update(frame_size=[32,36],foot_anchor=[16,34]);
        for phase,f in enumerate(data['frames']):f['rect']=[phase*32,0,32,36]
        data['source']='assets/source/characters/mira/arm_rig/exploration_authored.png';p.write_text(json.dumps(data,indent=2)+'\n')
    meta=json.loads((OUT/'idle_front.json').read_text());meta.update(frame_size=[32,36],rect=[0,0,32,36],foot_anchor=[16,34]);(OUT/'idle_front.json').write_text(json.dumps(meta,indent=2)+'\n')
    meta=json.loads((OUT/'work_bench/animation.json').read_text());meta.update(frame_size=[32,36],foot_anchor=[16,34],draw_anchor=[16,30]);(OUT/'work_bench/animation.json').write_text(json.dumps(meta,indent=2)+'\n')
    names=['rest','inspect','reach','wrench_high','wrench_mid','wrench_pull','withdraw','test_a','test_b']
    for i,name in enumerate(names):export(f'assets/characters/mira/work_bench/{name}.png',20+i)
    board=Image.new('RGBA',(32*len(names),36))
    for i,name in enumerate(names):board.alpha_composite(Image.open(OUT/f'work_bench/{name}.png'),(i*32,0))
    board.save(OUT/'work_bench/spritesheet.png');board.resize((board.width*4,144),Image.Resampling.NEAREST).save(OUT/'work_bench/poses_review.png')
    cinema=cells('cinematic_authored.png',8,4)
    cs=84/median(r[1][3]-r[1][1] for r in cinema[8:16])
    views=('front','front_right','right','rear_right','rear','rear_left','left','front_left')
    for folder in sorted((ROOT/'assets/story').rglob('mira')):
        if not folder.is_dir() or 'ice_reaper' not in folder.as_posix():continue
        manifest=folder/'animation.json'
        if not manifest.exists():continue
        data=json.loads(manifest.read_text());canvas=tuple(data['canvas']);anchor=tuple(data['anchor'])
        if canvas!=(128,128):continue
        for key,animation in data['animations'].items():
            view=next((v for v in sorted(views,key=len,reverse=True) if key.endswith(v)),'left');v=views.index(view)
            for i,f in enumerate(animation['frames']):
                if key.startswith(('load','loading')):index=16+i%8
                elif key.startswith(('raise','fire')):index=24+min(7,round(i*7/max(1,len(animation['frames'])-1)))
                elif key.startswith(('ready','stand')):index=8+v
                else:index=v
                if key=='loading_detail':
                    index=18+i%4
                    cell,bounds,_,_=cinema[index]
                    crop=cell.crop((bounds[0],round(bounds[1]+(bounds[3]-bounds[1])*.35),bounds[2],round(bounds[1]+(bounds[3]-bounds[1])*.7)))
                    image=Image.new('RGBA',canvas);cut=crop.resize((112,64),Image.Resampling.NEAREST);image.alpha_composite(cut,(8,32))
                else:image=frame(cinema[index],cs,canvas,anchor)
                colors=[(x,y) for y in range(image.height) for x in range(image.width)
                        if (lambda c:c[3] and c[1]>c[0]+20 and c[2]>c[0]+25)(image.getpixel((x,y)))]
                f['emitter']=[round(sum(a[i] for a in colors)/len(colors)) for i in (0,1)] if colors else [64,60]
                image.save(folder/f['file'],optimize=True)
                exports.append(dict(file=(folder/f['file']).relative_to(ROOT).as_posix(),source='cinematic_authored.png',source_cell=index,scale=cs,anchor=list(anchor)))
        data['source']='assets/source/characters/mira/arm_rig/cinematic_authored.png'
        data['source_sha256']=hashlib.sha256((SOURCE/'cinematic_authored.png').read_bytes()).hexdigest()
        data['sources']=[{'file':data['source'],'sha256':data['source_sha256']}]
        records=[{**r,'sha256':hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()} for r in exports if Path(r['file']).parent==folder.relative_to(ROOT)]
        (folder/'provenance.json').write_text(json.dumps(dict(version=1,generated_with='image_gen',frames=records,sources=data['sources']),indent=2)+'\n')
        data['worn_rig_source']='assets/source/characters/mira/arm_rig/cinematic_authored.png'
        manifest.write_text(json.dumps(data,indent=2)+'\n')
    # The lift joins the existing scene's registered low and raised endpoints.
    folder=ROOT/'assets/story/mira_prefire_aim'
    for i in range(4):
        image=(Image.open(ROOT/'assets/story/ice_reaper_rescue/actors/mira/load_08.png').convert('RGBA') if i==0 else Image.open(ROOT/'assets/story/ice_reaper_continuity/actors/mira/aim_front_01.png').convert('RGBA') if i==3 else frame(cinema[24+i],cs,(128,128),(64,116)))
        image.save(folder/f'raise_{i+1:02}.png',optimize=True)
    data=json.loads((folder/'animation.json').read_text())
    data['source']='assets/source/characters/mira/arm_rig/cinematic_authored.png'
    data['source_sha256']=hashlib.sha256((SOURCE/'cinematic_authored.png').read_bytes()).hexdigest()
    data['endpoints']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'assets/story/ice_reaper_rescue/actors/mira/load_08.png',ROOT/'assets/story/ice_reaper_continuity/actors/mira/aim_front_01.png')}
    (folder/'animation.json').write_text(json.dumps(data,indent=2)+'\n')
    # Regenerate contact sheets from current runtime frames, never old equipment.
    for folder in (OUT/'work_bench',*(ROOT/'assets/story').rglob('mira')):
        if not folder.is_dir() or not (folder/'animation.json').exists():continue
        data=json.loads((folder/'animation.json').read_text());files=list(dict.fromkeys(f['file'] for a in data.get('animations',{}).values() for f in a['frames']))
        if not files:continue
        w,h=Image.open(folder/files[0]).size;sheet=Image.new('RGBA',(w*8,h*((len(files)+7)//8)))
        for i,file in enumerate(files):sheet.alpha_composite(Image.open(folder/file).convert('RGBA'),((i%8)*w,(i//8)*h))
        if (folder/'contact_sheet.png').exists():sheet.save(folder/'contact_sheet.png')
    board=Image.new('RGBA',(32*5,36*4))
    for row,direction in enumerate(('front','back','left','right')):
        files=[OUT/f'idle_{direction}.png']+[OUT/f'walk_{direction}/frame_{i:02}.png' for i in range(1,5)]
        frames=[Image.open(p).convert('RGBA') for p in files]
        for col,image in enumerate(frames):board.alpha_composite(image,(col*32,row*36))
        frames[1].save(OUT/f'walk_{direction}/walk_{direction}_preview.gif',save_all=True,append_images=frames[2:],duration=140,loop=0,disposal=2)
        for name in ('frames_review.png','shared_motion_comparison.gif'):
            p=OUT/f'walk_{direction}'/name
            if p.exists():p.unlink()
    board.save(OUT/'walk_directions.png');board.resize((board.width*4,board.height*4),Image.Resampling.NEAREST).save(OUT/'walk_directions_review.png')
    for name in ('idle_front_review.png','walk_directions_review.gif','scale_comparison.png'):
        p=OUT/name
        if p.exists():p.unlink()
    data=dict(version=1,arm='anatomical_left',equipment='external worn cuff over intact limb',exports=exports,
              sources=[dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(SOURCE.glob('*_authored.png'))])
    (SOURCE/'registration.json').write_text(json.dumps(data,indent=2)+'\n')
    return data
if __name__=='__main__':print(json.dumps({'exported_frames':len(build()['exports'])}))
