"""Export complete authored right-walk drawings; no limb rig or live activation."""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
from tools.caelan_outline import apply_outline

SOURCE=ROOT/'assets/source/characters/caelan/walk_right_hd_review'
OUT=ROOT/'assets/characters/caelan/review_hd/walk_right'
REVIEW=ROOT/'docs/reviews/caelan_right_walk_hd'
SCALE=.124
SEQUENCE=[(name,i) for name in ('A','B','C2','D') for i in range(4)]
# D's last pose reversed its arm identity. Use the separately authored contact
# key for the short final approach; retain D's rejected pose as source history.
SEQUENCE[-1]=('keys',0)
SEQUENCE[11]=('C3',3)


def build():
    OUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    frames=[];records=[];sources={}
    for index,(name,cell) in enumerate(SEQUENCE):
        path=SOURCE/(name+'.png');sources[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        atlas=Image.open(path).convert('RGBA');w,h=atlas.width//2,atlas.height//2
        rect=(cell%2*w,cell//2*h,(cell%2+1)*w,(cell//2+1)*h)
        drawing=_main_component(atlas.crop(rect));bounds=drawing.getbbox()
        # These source batches were audited on the same crown/neck/belt grid.
        # Uniform density applies to every whole drawing; NEVER use foot height
        # or occupied height as a per-pose normalization/scale measurement.
        head=drawing.crop((0,0,w,203)).getbbox();head_center=(head[0]+head[2])/2
        origin=(round(22+(bounds[0]-head_center)*SCALE),
                round(24+(bounds[1]-211)*SCALE))
        crop=drawing.crop(bounds);size=(round(crop.width*SCALE),round(crop.height*SCALE))
        if min(origin)<1 or origin[0]+size[0]>47 or origin[1]+size[1]>71:
            raise ValueError(('Clipped complete pose',index+1,size,origin))
        frame=Image.new('RGBA',(48,72));frame.alpha_composite(crop.resize(size,Image.Resampling.NEAREST),origin)
        frames.append(frame)
        records.append({'file':f'frame_{index+1:02}.png','duration_ms':35,'source':path.name,
            'cell':list(rect),'source_bounds':list(bounds),'source_head_bounds':list(head),
            'source_neck_reference_y':211,'source_belt_reference_y':315,
            'uniform_scale':SCALE,'origin':list(origin),'sampled_size':list(size),
            'support_leg':'right_near' if index<8 else 'left_far',
            'swing_leg':'left_far' if index<8 else 'right_near',
            'phase':('contact' if index in (0,8) else 'passing' if index in (4,12)
                     else 'recovery' if index in (6,7,14,15) else 'transition')})
    idle_path=ROOT/'assets/characters/caelan/review_hd/idles/idle_right.png'
    idle=Image.open(idle_path).convert('RGBA')
    palette=Image.new('P',(1,1))
    palette_data=json.loads((SOURCE/'palette.json').read_text())['rgb']
    palette.putpalette(palette_data+[0]*(768-len(palette_data)))
    exported=[]
    ground_windows=[(24,48),(20,42),(20,42),(16,38),(14,32),(12,31),(8,24),(0,20)]
    ground_windows+= [(24,48),(20,42),(20,42),(15,38),(14,32),(11,31),(0,24),(0,22)]
    for record,frame,window in zip(records,frames,ground_windows):
        alpha=frame.getchannel('A')
        frame=frame.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE).convert('RGBA')
        frame.putalpha(alpha);frame=apply_outline(frame)
        # Audited support-foot windows identify actual sole pixels, not an
        # occupied-height scale or a bounding-box center used to build motion.
        sole=[(x,y) for y in range(65,72) for x in range(*window) if frame.getpixel((x,y))[3]]
        ground=max(y for x,y in sole);contact=[x for x,y in sole if y==ground]
        record['support_ground_interval']=[min(contact),ground,max(contact)]
        record['head_crown_y']=frame.crop((0,0,48,24)).getbbox()[1]
        record['support_window']=list(window)
        frame.save(OUT/record['file']);exported.append(frame)
    protected=json.loads((SOURCE/'protected_frames.json').read_text())
    for file,digest in protected.items():
        if hashlib.sha256((OUT/file).read_bytes()).hexdigest()!=digest:
            raise ValueError(('Frame12 correction changed a protected frame',file))
    if len({im.tobytes() for im in exported})!=16:raise ValueError('Duplicate native poses')
    sheet=Image.new('RGBA',(48*16,72))
    for i,frame in enumerate(exported):sheet.alpha_composite(frame,(48*i,0))
    sheet.save(OUT/'spritesheet.png')
    manifest={'version':1,'character':'caelan','animation':'walk.right','status':'approved',
        'design_status':'approved','artwork_status':'approved',
        'runtime_integration':False,'artwork_pixels_per_world_pixel':2,'frame_size':[48,72],
        'logical_size':[24,36],'draw_anchor':[24,60],'foot_anchor':[24,68],
        'cycle_ms':560,'loop':True,'source_scale':SCALE,'frames':records,
        'source_hashes':sources,'palette_sha256':hashlib.sha256((SOURCE/'palette.json').read_bytes()).hexdigest(),
        'approved_idle_sha256':hashlib.sha256(idle_path.read_bytes()).hexdigest(),
        'processing':'Whole-character drawings, uniform sampling, head/neck registration, shared palette and contour; no detached limb transforms.'}
    (OUT/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (SOURCE/'registration.json').write_text(json.dumps(manifest,indent=2)+'\n')
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
    board=Image.new('RGB',(864,1304),'#303940');d=ImageDraw.Draw(board)
    d.text((16,12),'CAELAN | RIGHT WALK | 16 COMPLETE DRAWN POSES',font=font,fill='#edf0e9')
    for i,frame in enumerate(exported):
        pos=(12+i%4*216,44+i//4*312)
        big=frame.resize((192,288),Image.Resampling.NEAREST);board.paste(big,pos,big)
        d.text((pos[0],pos[1]+288),f'{i+1:02}  {records[i]["phase"]}',font=small,fill='#d4dbdf')
    board.save(REVIEW/'frames.png')
    preview=[]
    for tick in range(32):
        image=Image.new('RGB',(680,490),'#303940');d=ImageDraw.Draw(image)
        for phase,x,label in ((tick%16,16,'Normal | 560 ms cycle'),
                              ((tick//2)%16,240,'Half speed'),(None,464,'Approved idle')):
            frame=idle if phase is None else exported[phase]
            d.text((x,12),label,font=font,fill='#edf0e9')
            d.line((x+8,330,x+190,330),fill='#58646c')
            big=frame.resize((192,288),Image.Resampling.NEAREST);image.paste(big,(x,48),big)
            image.paste(frame,(x+72,400),frame)
            if phase is not None:d.text((x+20,350),f'Frame {phase+1:02} / 16',font=small,fill='#d4dbdf')
        d.text((16,378),'Bottom row: normal 960 x 640 viewport size',font=small,fill='#b9c8ce')
        preview.append(image)
    # One review palette: GIF conversion does not recolor each temporal frame.
    packed=Image.new('RGB',(680*8,490*4))
    for i,image in enumerate(preview):packed.paste(image,(i%8*680,i//8*490))
    gif_palette=packed.quantize(colors=256,dither=Image.Dither.NONE)
    gif_frames=[im.quantize(palette=gif_palette,dither=Image.Dither.NONE) for im in preview]
    gif_frames[0].save(REVIEW/'preview.gif',save_all=True,append_images=gif_frames[1:],
                       duration=[30,40]*16,loop=0,disposal=2,optimize=False)
    print('Exported 16 approved frames, 560ms cadence; runtime activation remains pending.')


if __name__=='__main__':build()
