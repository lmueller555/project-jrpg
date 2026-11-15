"""Export authored whole front/rear cycles without procedural posing or activation."""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_mira_combat import _main_component
from tools.caelan_outline import apply_outline

# Density of the 5x native review guide, adjusted for the generated atlas canvas.
UPPER_CONFIGS={'front':{'A_initial':(.14,160,23),'B':(.118,205,24),
    'C_initial':(.118,205,24),'D_initial':(.118,198,24),'D':(.135,177,24)},
    'back':{'A':(.128,195,25),'B':(.128,195,25),
    'C_initial':(.128,190,25),'D':(.128,195,25)}}

def sample_upper(source,direction,name,cell,palette):
    scale,neck,target=UPPER_CONFIGS[direction][name]
    atlas=Image.open(source/(name+'.png')).convert('RGBA');w,h=atlas.width//2,atlas.height//2
    drawing=_main_component(atlas.crop((cell%2*w,cell//2*h,(cell%2+1)*w,(cell//2+1)*h)))
    bounds=drawing.getbbox();head=drawing.crop((0,0,w,neck-5)).getbbox();center=(head[0]+head[2])/2
    origin=(round(24+(bounds[0]-center)*scale),round(target+(bounds[1]-neck)*scale))
    crop=drawing.crop(bounds);size=tuple(round(v*scale) for v in crop.size)
    frame=Image.new('RGBA',(48,72));frame.alpha_composite(crop.resize(size,Image.Resampling.NEAREST),origin)
    alpha=frame.getchannel('A');frame=frame.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE).convert('RGBA');frame.putalpha(alpha)
    return apply_outline(frame),{'source_cell':[cell%2*w,cell//2*h,(cell%2+1)*w,(cell//2+1)*h],
        'source_bounds':list(bounds),'source_head_bounds':list(head),
        'source_neck_reference_y':neck,'uniform_scale':scale,'origin':list(origin),
        'sampled_size':list(size),'source':name+'.png'}


def build(direction):
    if direction=='back':
        from tools.export_caelan_back_walk_hd_v2 import build as build_back
        frames,records=build_back()
        render_review(direction,frames,records,ROOT/'docs/reviews/caelan_back_walk_hd',
                      ROOT/'assets/characters/caelan/review_hd/idles/idle_back.png')
        return
    source=ROOT/f'assets/source/characters/caelan/walk_{direction}_hd_review'
    bank=ROOT/f'assets/characters/caelan/review_hd/walk_{direction}'
    review=ROOT/f'docs/reviews/caelan_{direction}_walk_hd'
    bank.mkdir(parents=True,exist_ok=True);review.mkdir(parents=True,exist_ok=True)
    path=source/'leg_revision.png';atlas=Image.open(path).convert('RGBA')
    palette_path=ROOT/'assets/source/characters/caelan/walk_right_hd_review/palette.json'
    palette=Image.new('P',(1,1));rgb=json.loads(palette_path.read_text())['rgb'];palette.putpalette(rgb+[0]*(768-len(rgb)))
    guide_ratio=atlas.width/1536
    scale=1/(5*guide_ratio)
    neck=132*guide_ratio
    plan=json.loads((source/'leg_plan.json').read_text())
    hashes={path.name:hashlib.sha256(path.read_bytes()).hexdigest(),
            'leg_plan.json':hashlib.sha256((source/'leg_plan.json').read_bytes()).hexdigest()}
    frames=[];records=[]
    for i in range(16):
        active=atlas;active_path=path;grid=4;cell=i
        scale=1/(5*guide_ratio);neck=132*guide_ratio;target_neck=24
        if direction=='front' and i==11:cell=12
        if direction=='back' and i==10:cell=11
        if direction=='back' and i==11:cell=10
        repair_cell=({12:2}.get(i) if direction=='front' else {2:1,9:3}.get(i))
        if repair_cell is not None:
            active_path=source/'join_revision.png';active=Image.open(active_path).convert('RGBA')
            grid=2;cell=repair_cell
            scale=.1225 if direction=='front' else .119
            neck=223 if direction=='front' else 225
            target_neck=25
        hashes[active_path.name]=hashlib.sha256(active_path.read_bytes()).hexdigest()
        rect=(cell%grid*active.width//grid,cell//grid*active.height//grid,(cell%grid+1)*active.width//grid,(cell//grid+1)*active.height//grid)
        drawing=active.crop(rect)
        threshold=128
        drawing.putalpha(drawing.getchannel('A').point(lambda a:255 if a>=threshold else 0))
        drawing=_main_component(drawing);bounds=drawing.getbbox()
        head=drawing.crop((0,0,drawing.width,neck-5)).getbbox();center=(head[0]+head[2])/2
        origin=(round(24+(bounds[0]-center)*scale),round(target_neck+(bounds[1]-neck)*scale))
        crop=drawing.crop(bounds);size=tuple(round(v*scale) for v in crop.size)
        if min(origin)<1 or origin[0]+size[0]>47 or origin[1]+size[1]>71:
            raise ValueError(('Pose clips margin',direction,i+1,bounds,origin,size))
        frame=Image.new('RGBA',(48,72));frame.alpha_composite(crop.resize(size,Image.Resampling.NEAREST),origin)
        alpha=frame.getchannel('A');frame=frame.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE).convert('RGBA');frame.putalpha(alpha);frame=apply_outline(frame)
        name,cell=plan['upper_sources'][i]
        upper,upper_registration=sample_upper(source,direction,name,cell,palette)
        # After a complete authored redraw, retain the established upper body,
        # following the documented regional-preservation workflow (no limb rig).
        frame.paste(upper.crop((0,0,48,48)),(0,0))
        if direction=='front' and i==13:
            # Select this complete authored contact-approach pose, rather than
            # retaining a prematurely lifted boot from the transition atlas.
            frame=upper.copy()
        snapshot=source/'upper_snapshot'/f'frame_{i+1:02}.png'
        if upper.tobytes()!=Image.open(snapshot).convert('RGBA').tobytes():
            raise ValueError(('Upper snapshot provenance changed',direction,i+1))
        hashes[name+'.png']=hashlib.sha256((source/(name+'.png')).read_bytes()).hexdigest()
        frame.save(bank/f'frame_{i+1:02}.png');frames.append(frame)
        feet=[]
        for lo,hi in ((17,23),(27,32)):
            pixels=[(x,y) for x in range(lo,hi) for y in range(52,72) if frame.getpixel((x,y))[3]]
            y=max(y for x,y in pixels);feet.append([lo,hi,y])
        records.append({'file':f'frame_{i+1:02}.png','rect':[i*48,0,48,72],'duration_ms':35,
            'source':active_path.name,'source_cell':list(rect),'source_bounds':list(bounds),
            'source_head_bounds':list(head),'source_neck_reference_y':neck,'source_belt_reference_y':319 if repair_cell is not None else 202*guide_ratio,
            'uniform_scale':scale,'protected_upper_source':[name,cell],'upper_registration':upper_registration,
            'upper_sha256':hashlib.sha256(upper.crop((0,0,48,48)).tobytes()).hexdigest(),'origin':list(origin),'sampled_size':list(size),
            'head_crown_y':frame.crop((0,0,48,24)).getbbox()[1],
            'boot_observation_windows':feet,
            'phase':('contact' if i in (0,8) else 'passing' if i in (4,12) else 'transition')})
        if direction=='front' and i==13:
            records[-1].update(upper_registration)
            records[-1]['complete_pose_override']=True
            records[-1]['source_belt_reference_y']=246
    if len({f.tobytes() for f in frames})!=16:raise ValueError('Duplicate frames')
    sheet=Image.new('RGBA',(768,72))
    for i,frame in enumerate(frames):sheet.alpha_composite(frame,(i*48,0))
    sheet.save(bank/'spritesheet.png')
    idle_path=ROOT/f'assets/characters/caelan/review_hd/idles/idle_{direction}.png';idle=Image.open(idle_path).convert('RGBA')
    data={'version':1,'character':'caelan','animation':f'walk.{direction}','status':'approved',
        'design_status':'approved','artwork_status':'approved','runtime_integration':True,
        'frame_size':[48,72],'logical_size':[24,36],'draw_anchor':[24,60],'foot_anchor':[24,68],
        'artwork_pixels_per_world_pixel':2,'cycle_ms':560,'loop':True,'source_scale':'Uniform per authored atlas; see frame records',
        'source_hashes':hashes,'protected_region':[0,0,48,48],
        'approved_idle_sha256':hashlib.sha256(idle_path.read_bytes()).hexdigest(),
        'palette_sha256':hashlib.sha256(palette_path.read_bytes()).hexdigest(),
        'alpha_threshold':threshold,'frames':records,
        'processing':'Complete authored drawings; hard alpha, uniform nearest-neighbor sampling, head/neck registration, shared material palette and contour. Upper rows0:48 retain the sampled whole-pose snapshots after complete leg redraws. No detached limb transforms or idle warping.'}
    (bank/'animation.json').write_text(json.dumps(data,indent=2)+'\n');(source/'registration.json').write_text(json.dumps(data,indent=2)+'\n')
    render_review(direction,frames,records,review,idle_path)
    print(direction,'crowns',[r['head_crown_y'] for r in records],'boots',[r['boot_observation_windows'] for r in records])

def render_review(direction,frames,records,review,idle_path):
    idle=Image.open(idle_path).convert('RGBA')
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
    board=Image.new('RGB',(864,1304),'#303940');draw=ImageDraw.Draw(board)
    draw.text((16,12),f'CAELAN | {direction.upper()} WALK | 16 DRAWN POSES',font=font,fill='#edf0e9')
    for i,frame in enumerate(frames):
        pos=(12+i%4*216,44+i//4*312);big=frame.resize((192,288),Image.Resampling.NEAREST);board.paste(big,pos,big)
        draw.text((pos[0],pos[1]+288),f'{i+1:02}  {records[i]["phase"]}',font=small,fill='#d4dbdf')
    board.save(review/'frames.png')
    previews=[]
    for tick in range(32):
        image=Image.new('RGB',(680,490),'#303940');draw=ImageDraw.Draw(image)
        for phase,x,label in ((tick%16,16,'Normal | 560 ms cycle'),((tick//2)%16,240,'Half speed'),(None,464,'Approved idle')):
            frame=idle if phase is None else frames[phase]
            draw.text((x,12),label,font=font,fill='#edf0e9');big=frame.resize((192,288),Image.Resampling.NEAREST);image.paste(big,(x,48),big);image.paste(frame,(x+72,400),frame)
            if phase is not None:draw.text((x+20,350),f'Frame {phase+1:02} / 16',font=small,fill='#d4dbdf')
        draw.text((16,378),'Bottom row: normal 960 x 640 viewport size',font=small,fill='#b9c8ce');previews.append(image)
    packed=Image.new('RGB',(680*8,490*4))
    for i,frame in enumerate(previews):packed.paste(frame,(i%8*680,i//8*490))
    gif_palette=packed.quantize(colors=256,dither=Image.Dither.NONE)
    indexed=[f.quantize(palette=gif_palette,dither=Image.Dither.NONE) for f in previews]
    indexed[0].save(review/'preview.gif',save_all=True,append_images=indexed[1:],duration=[30,40]*16,loop=0,disposal=2,optimize=False)
    if direction=='back':
        board.save(review/'frames_v2.png')
        (review/'preview_v2.gif').write_bytes((review/'preview.gif').read_bytes())

if __name__=='__main__':
    for direction in ('front','back'):build(direction)
