"""Build GUIDE-ONLY annotated complete linked poses for ImageGen authoring.

No pixels from this helper are final character artwork. Physical pose/camera
comes from the parent-authored3D guide; labels separate a projecting knee from
the calf that folds back to an occluded boot. Whole-character final art must be
ImageGen authored. Existing master/prompt inputs are never overwritten.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from hashlib import sha256
import argparse,json,shutil
BASE=Path(__file__).resolve().parents[2]
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
META={r['index']:r for r in json.loads((BASE/'guides/overhead/metadata_even_000_048.json').read_text())}
SOURCE_APPEARANCE=BASE/'batches/overhead_000_015_pose_retry'


def guide_cell(phase):
    raw=BASE/'guides/overhead'/f'guide_{phase:03d}.png'
    # One identical crop/uniform scale for all rough mannequins. It enlarges
    # the construction guide, never normalizes individual pose bounds.
    crop=(60,270,450,660);scale=1.25;origin=(12,110)
    sample=Image.open(raw).convert('RGB').crop(crop)
    sample=sample.resize(tuple(round(v*scale) for v in sample.size),Image.Resampling.LANCZOS)
    im=Image.new('RGB',(512,768),(153,153,153));im.paste(sample,origin)
    d=ImageDraw.Draw(im);m=META[phase]['landmarks_guide']
    def point(xy):return (origin[0]+(xy[0]-crop[0])*scale,origin[1]+(xy[1]-crop[1])*scale)
    d.text((10,12),f'PHASE {phase}/48 — GUIDE ONLY',font=FONT,fill='white')
    for side,color in [('R','#ff5858'),('L','#00dddd')]:
        hip=point(m[side+'hip']);knee=point(m[side+'knee']);foot=point(m[side+'foot'])
        d.line([hip,knee,foot],fill=color,width=4)
        for name,xy,rad,dx,dy in [('KNEE',knee,11,-100 if side=='R' else 12,20),('BOOT',foot,8,-100 if side=='R' else 12,-25)]:
            x,y=xy;d.ellipse((x-rad,y-rad,x+rad,y+rad),outline=color,width=3)
            tx=max(5,min(410,x+dx));ty=y+dy;d.text((tx,ty),f'{side} {name}',font=FONT,fill=color)
            d.line((tx+37,ty+9,x,y),fill=color,width=1)
    d.text((12,672),'KNEE may project DOWN;',font=FONT,fill='white')
    d.text((12,694),'CALF folds UP to labelled BOOT.',font=FONT,fill='white')
    return im,raw


def prepare(start,stop,name):
    folder=BASE/'batches'/name;folder.mkdir(exist_ok=True)
    for final in ['master.png','generation.json','prompt.txt']:
        if (folder/final).exists():raise ValueError('Refusing to replace retained authoring input '+str(folder/final))
    phases=list(range(start,stop));count=len(phases)
    if count!=16:raise ValueError('This helper prepares16-frame4×4 sheets')
    canvas=Image.new('RGB',(1024,1536));records=[];details=[]
    for n,phase in enumerate(phases):
        im,raw=guide_cell(phase);im=im.resize((256,384),Image.Resampling.LANCZOS);x=n%4*256;y=n//4*384;canvas.paste(im,(x,y));m=META[phase]['landmarks_guide'];head=m['head'][1]
        records.append({'sample_index':phase,'gait_frame':phase,'cell':[x,y,x+256,y+384],
          'view_elevation':90.,'view_azimuth':0.,'guide':str(raw.relative_to(BASE)),
          'guide_sha256':sha256(raw.read_bytes()).hexdigest(),
          'guide_construction':'Fixed crop[60,270,450,660], uniform1.25 guide scale, colored linked-chain knee/boot diagnostic, then uniform0.5 whole-cell sampling. Guide pixels never exported.',
          'physical_guide_landmarks':m})
        def pos(side):
            dy=m[side+'foot'][1]-head
            return ('DOWN/front' if dy>8 else 'UP/back' if dy< -8 else 'near the head center')
        details.append(f'row{n//4+1} column{n%4+1}, phase{phase}: RIGHT/imageLEFT boot {pos("R")}; LEFT/imageRIGHT boot {pos("L")}. Follow each labelled knee→boot fold; knee position is NOT boot position.')
    canvas.save(folder/'camera_pose_guide.png')
    for f in ['approved_phase_reference.png','angle_model_reference.png']:shutil.copyfile(SOURCE_APPEARANCE/f,folder/f)
    (folder/'reference_manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    prompt='''Draw SIXTEEN COMPLETE Iselin running animation drawings in a strict4-COLUMN by4-ROW sheet, reading order, genuinely TRANSPARENT alphaZERO background and gutters. No labels, guide marks, shadows, boxes, white fill or baked checkerboard. All sixteen use the SAME TRUE90DEGREE straight-down overhead view; running toward IMAGE BOTTOM. FACE naturally hidden behind crown, no frontal portrait. Same adult head/neck/shoulder/body physical dimensions in every drawing; never fit occupied figure height to a cell.
REFERENCE1 is the primary actual complete3D linked pose guide. Its colored lines and KNEE/BOOT markers explain anatomy ONLY: RED=anatomicalRIGHT/imageLEFT, CYAN=anatomicalLEFT/imageRIGHT. No red/cyan/text in final painting; final trousers and boots are gray. Reference2 is ONLY the cropped approved overhead head/hair/braid. Reference3 is ONLY blue/silver coat material. Construct every entire body afresh from its individual guide; don't invent a fixed extended-leg body from an appearance reference.
These are16consecutive60Hz phases of a48frame800ms run. Preserve individual phase order and continuous joint paths:
'''+ '\n'.join(details)+'''
CRITICAL FOLDED-LEG RULE: The knee can project DOWN in front of the crown while its calf folds BACK UP to a boot behind/ABOVE the head center. Follow the labelled hip→KNEE→BOOT chain. Do NOT mistake a forward knee stub for a straight shin/boot. When both BOOT markers lie on the imageTOP side of head center, neither foot may hang extended below the crown; let head/coat naturally occlude the folded calf/boot. A visible projecting knee is correct, but it is not a boot. Contact0RIGHT/imageLEFT boot leads with LEFT/imageRIGHT arm forward; contact24LEFT/imageRIGHT boot leads with RIGHT/imageLEFT arm forward. BOTH connected arm chains and BOTH connected leg chains must progress through contact, passing, recovery and exchange. No16copies of one extended shin, wiggle then snap, duplicate limb or amputated torso. Complete fresh figures, no pasted cutout parts/warped frontal bodies/crossfades.
Iselin's mantle stays anatomicalRIGHT/imageLEFT. ONE thick FORWARD braid roots at anatomicalLEFT/imageRIGHT pearl/silver temple clasp and shoulder, never a rear-center ponytail. Loose long white/silver hair, mantle and coat stream behind/up-image and LEFT in stable world wind. Continuous lively waves and delayed heavy-braid bending with stable roots; no row-boundary reset. Royal deep blue/navy coat/mantle, fine silver embroidery, lining and clasps, gray trousers, plain gray leather boots/simple silver bands. Exact head/material reference identity and palette, no violet cast, nighttime regrade or invented boot embroidery. Refined detailed painterly cinematic style, thin dark silhouette edge, correct natural occlusion. Every full flowing silhouette clear of cell edges. Full alphaZERO background and clear gutters; no haze/vignette/checkerboard.'''
    (folder/'prompt.txt').write_text(prompt)
    print(folder)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--start',type=int,required=True);parser.add_argument('--stop',type=int,required=True);parser.add_argument('--name',required=True);a=parser.parse_args();prepare(a.start,a.stop,a.name)
