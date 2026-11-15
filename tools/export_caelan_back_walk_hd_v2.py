"""Rebuild the rear gait from coupled whole poses; preserve only the old head."""
from pathlib import Path
import hashlib
import json
from PIL import Image
from tools.build_mira_combat import _main_component
from tools.caelan_outline import apply_outline

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/caelan/walk_back_hd_review'
BANK=ROOT/'assets/characters/caelan/review_hd/walk_back'
SCALE=.128
# Complete-pose selections and scoped join redraws in actual motion order.
PLAN=[(0,None),(1,None),(2,('joins_A',0)),(3,('final_joins',0)),
      (3,('joins_A',1)),(4,('joins_A',2)),(7,('joins_A',3)),(7,('final_joins',1)),
      (8,None),(9,None),(10,('joins_B',0)),(11,None),
      (12,None),(13,None),(14,('joins_B',1)),(15,('joins_B',2))]
REPAIR_GRIDS={'joins_A':(.121,225,24,215),'joins_B':(.121,225,24,215),
              'final_joins':(.106,235,23,225)}

def build():
    palette_path=ROOT/'assets/source/characters/caelan/walk_right_hd_review/palette.json'
    palette=Image.new('P',(1,1));rgb=json.loads(palette_path.read_text())['rgb'];palette.putpalette(rgb+[0]*(768-len(rgb)))
    frames=[];records=[];hashes={}
    for slot,(i,repair) in enumerate(PLAN):
        name='ABCD'[i//4];cell=i%4;path=SOURCE/'revision_2'/(name+'.png')
        hashes[str(path.relative_to(SOURCE))]=hashlib.sha256(path.read_bytes()).hexdigest()
        atlas=Image.open(path).convert('RGBA');w,h=atlas.width//2,atlas.height//2
        rect=(cell%2*w,cell//2*h,(cell%2+1)*w,(cell//2+1)*h)
        drawing=_main_component(atlas.crop(rect));bounds=drawing.getbbox()
        head=drawing.crop((0,0,w,183)).getbbox();center=(head[0]+head[2])/2
        # One density/neck grid; neither boot nor occupied height normalizes a pose.
        origin=(round(24+(bounds[0]-center)*SCALE),round(23+(bounds[1]-188)*SCALE))
        crop=drawing.crop(bounds);size=tuple(round(v*SCALE) for v in crop.size)
        frame=Image.new('RGBA',(48,72));frame.alpha_composite(crop.resize(size,Image.Resampling.NEAREST),origin)
        alpha=frame.getchannel('A');frame=frame.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE).convert('RGBA');frame.putalpha(alpha);frame=apply_outline(frame)
        old_path=SOURCE/'revision_2/before'/f'frame_{i+1:02}.png'
        old=Image.open(old_path).convert('RGBA');frame.paste(old.crop((0,0,48,24)),(0,0))
        hashes[str(old_path.relative_to(SOURCE))]=hashlib.sha256(old_path.read_bytes()).hexdigest()
        base=frame.copy()
        repair_registration=None
        if repair:
            repair_name,repair_cell=repair;repair_path=SOURCE/'revision_2'/(repair_name+'.png')
            hashes[str(repair_path.relative_to(SOURCE))]=hashlib.sha256(repair_path.read_bytes()).hexdigest()
            master=Image.open(repair_path).convert('RGBA');rw,rh=master.width//2,master.height//2
            repair_rect=(repair_cell%2*rw,repair_cell//2*rh,(repair_cell%2+1)*rw,(repair_cell//2+1)*rh)
            rscale,rneck,rtarget,rhead=REPAIR_GRIDS[repair_name]
            art=_main_component(master.crop(repair_rect));rb=art.getbbox();rh_bounds=art.crop((0,0,rw,rhead)).getbbox()
            rcenter=(rh_bounds[0]+rh_bounds[2])/2
            ro=(round(24+(rb[0]-rcenter)*rscale),round(rtarget+(rb[1]-rneck)*rscale))
            rc=art.crop(rb);rs=tuple(round(v*rscale) for v in rc.size)
            revised=Image.new('RGBA',(48,72));revised.alpha_composite(rc.resize(rs,Image.Resampling.NEAREST),ro)
            ra=revised.getchannel('A');revised=revised.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE).convert('RGBA');revised.putalpha(ra)
            frame=apply_outline(revised);frame.paste(base.crop((0,0,48,48)),(0,0))
            repair_registration={'source':str(repair_path.relative_to(SOURCE)),'cell':list(repair_rect),
                'bounds':list(rb),'head_bounds':list(rh_bounds),'scale':rscale,'neck_reference_y':rneck,'target_neck_y':rtarget,
                'origin':list(ro),'sampled_size':list(rs),'protected_upper_sha256':hashlib.sha256(base.crop((0,0,48,48)).tobytes()).hexdigest()}
        coupled_path=SOURCE/'revision_2/coupled_before_joins'/f'frame_{i+1:02}.png'
        hashes[str(coupled_path.relative_to(SOURCE))]=hashlib.sha256(coupled_path.read_bytes()).hexdigest()
        if base.tobytes()!=Image.open(coupled_path).convert('RGBA').tobytes():
            raise ValueError(('Coupled pose snapshot changed',i+1))
        left,top,right,bottom=frame.getbbox()
        if min(left,top)<1 or right>=48 or bottom>=72:raise ValueError(('Clipped',i+1,frame.getbbox()))
        frame.save(BANK/f'frame_{slot+1:02}.png');frames.append(frame)
        windows=[]
        for lo,hi in ((17,23),(27,32)):
            y=max(y for x in range(lo,hi) for y in range(52,72) if frame.getpixel((x,y))[3]);windows.append([lo,hi,y])
        phase='contact' if slot in (0,8) else 'passing' if slot in (4,12) else 'transition'
        records.append({'file':f'frame_{slot+1:02}.png','rect':[slot*48,0,48,72],'duration_ms':35,
            'source':str(path.relative_to(SOURCE)),'source_cell':list(rect),'source_bounds':list(bounds),
            'source_head_bounds':list(head),'source_neck_reference_y':188,'source_belt_reference_y':273,
            'uniform_scale':SCALE,'origin':list(origin),'sampled_size':list(size),'phase':phase,
            'head_crown_y':frame.crop((0,0,48,24)).getbbox()[1],
            'protected_head_source':str(old_path.relative_to(SOURCE)),
            'head_sha256':hashlib.sha256(old.crop((0,0,48,24)).tobytes()).hexdigest(),
            'boot_observation_windows':windows,'leg_join_repair':repair_registration,
            'coupled_reference':str(coupled_path.relative_to(SOURCE)),
            'support_leg':'right' if slot<8 else 'left',
            'swing_leg':'left' if slot<8 else 'right',
            'arm_plan':'right arm trails toward neutral; left arm swings toward camera' if slot<8 else
                       'left arm trails toward neutral; right arm swings toward camera'})
    if len({f.tobytes() for f in frames})!=16:raise ValueError('Duplicate poses')
    sheet=Image.new('RGBA',(768,72))
    for i,frame in enumerate(frames):sheet.alpha_composite(frame,(i*48,0))
    sheet.save(BANK/'spritesheet.png')
    idle_path=ROOT/'assets/characters/caelan/review_hd/idles/idle_back.png'
    data={'version':2,'character':'caelan','animation':'walk.back','status':'review','design_status':'approved',
        'artwork_status':'review','runtime_integration':False,'frame_size':[48,72],'logical_size':[24,36],
        'draw_anchor':[24,60],'foot_anchor':[24,68],'artwork_pixels_per_world_pixel':2,'cycle_ms':560,'loop':True,
        'source_scale':SCALE,'source_hashes':hashes,'protected_region':[0,0,48,24],
        'approved_idle_sha256':hashlib.sha256(idle_path.read_bytes()).hexdigest(),
        'palette_sha256':hashlib.sha256(palette_path.read_bytes()).hexdigest(),'alpha_threshold':128,'frames':records,
        'processing':'Whole authored coupled arm/leg poses; uniform density and neck registration, shared palette and contour. Original head rows0:24 retained. Core shoulders, arms, torso and legs are coupled complete drawings; scoped leg-join redraws protect their same-phase upper48 rows. No limb rigs or independent arm/leg phase assembly.'}
    (BANK/'animation.json').write_text(json.dumps(data,indent=2)+'\n')
    (SOURCE/'registration.json').write_text(json.dumps(data,indent=2)+'\n')
    (SOURCE/'revision_2/registration.json').write_text(json.dumps(data,indent=2)+'\n')
    print('Rear v2 boot observations:',[r['boot_observation_windows'] for r in records])
    return frames,records
