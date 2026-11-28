from pathlib import Path
from hashlib import sha256
import json
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;S=P.parent;ROOT=P.parents[7]
annotations={r['phase']:r for r in json.loads((P/'guide_annotations.json').read_text())}
tasks=[]
for start in(8,12,32,36):
    phases=list(range(start,start+4));atlas=Image.new('RGB',(1024,1536),'#333333');details=[]
    for cell,phase in enumerate(phases):
        im=Image.open(S/f'guide_frames/overhead_{phase:03d}_guide.png').convert('RGB');d=ImageDraw.Draw(im)
        forward='left' if phase<24 else 'right';j=annotations[phase]['joints'][forward];knee=j['knee2d'];foot=j['foot2d'];relative=phase%24
        d.ellipse((knee[0]-8,knee[1]-8,knee[0]+8,knee[1]+8),fill='#e0a83a',outline='#fff291',width=2)
        d.line([tuple(knee),tuple(foot)],fill='#32d7ed',width=3);d.ellipse((foot[0]-7,foot[1]-7,foot[0]+7,foot[1]+7),outline='#32d7ed',width=3)
        labelx=300 if forward=='left' else 10;d.line([(labelx+20,666),tuple(knee)],fill='#fff291',width=2)
        d.text((labelx,670),'FORWARD KNEE CAP',fill='#fff291');d.text((12,25),f'PHASE {phase}: TRUE VERTICAL CAMERA',fill='white');d.text((12,43),'GOLD=KNEE / CYAN=FOLDED CALF TO BOOT',fill='#32d7ed')
        if relative<=10:
            action='Rounded forward SILVER KNEE is the last/down-most part; calf and boot fold BACK under body, NO shin or brown toe below that knee.'
            d.text((12,61),'NO BOOT BELOW FORWARD KNEE',fill='#fff291')
        elif relative==11:
            action='Forward SILVER KNEE remains down-most; normal boot toe is just reaching knee level, never a long steel shin below it.'
            d.text((12,61),'BOOT TOE JUST REACHES KNEE LEVEL',fill='#fff291')
        else:
            action='Calf still folds back: normal small brown toe gradually peeks past kneecap as actualguide unfolds, with almost NO visible long shin. Bootcenter remains at/behind knee; do not extend a straight calf below it.'
            d.text((12,61),'NORMAL TOE EMERGES / CALF STILL FOLDED',fill='#fff291')
        atlas.paste(im,(cell%2*512,cell//2*768));details.append(f'Cell{cell+1}/phase{phase}: {action}')
    guide=P/f'phase_{start:02d}_{start+3:02d}_guide_atlas.png';atlas.save(guide)
    owner='anatomical LEFT leg on IMAGE RIGHT' if start<24 else 'anatomical RIGHT leg on IMAGE LEFT'
    t={'id':f'phase_{start:02d}_{start+3:02d}','output':f'phase_{start:02d}_{start+3:02d}.png','phases':phases,'grid':[2,2], 'prompt':f'''Draw FOUR COMPLETE Lucan overhead running figures as2columns2rows. Reading LEFT TO RIGHT then TOP TO BOTTOM is exact chronological phases{phases}, one60Hz tick between cells. FIRST attached actual3D pose/camera atlas is PRIMARY for each own joint/hand/foot movement; SECOND is cropped material/identity ONLY. Do not turn4 tiny increments into a whole gait cycle. Each cell is one new indivisible complete figure, never pasted/warped bodyparts.

FORWARD FOLDED CHAIN in all4 is {owner}. The GOLD guide ball is a BENT KNEE, not an ankle. CYAN line shows its calf folding BACK to the normalboot, often occluded by head/body. Follow each cell literal guide overlap, not a generic extended shin. Phase-specific rules:
'''+ '\n'.join(details)+'''

The opposite leg trails behind the red hips; only actual guide-exposed boot portions can show. TWO connected hip-knee-ankle chains and TWO real boots total, even when hidden; no thirdtoe underbelt. Never invent a long steelshin+leatherboot below the knee because a knee-shaped guide cap looks like an ankle. Real calf/boot can be hidden or overlap. Project natural actual limb lengths; no shortened anatomy, no giant bootkick, no silhouetteheight fitting.

Both own ARM chains also advance as their exact guide cell does: trace shoulder→elbow→wrist→grip, including near/far overlaps. RIGHT sword arm IMAGE LEFT; LEFT shield arm IMAGE RIGHT. No held hand/carry imposed by material crops. Sword and shield same actual sizes, grips attached. Shield UPRIGHT: ONLY narrow curved gold rim/redback sliver from90camera, never broad kiteface laidflat. Bare swept darkbrown hair CROWN AHEAD/DOWN of oxbloodhips, no upwardface/eyes or frontal breastplate. Top shoulder/torso surfaces, true90overhead upright adult runner, not prone.

Same youthful adult Lucan: polished articulated SILVERSTEEL shoulders/thighs/knees/greaves trimmedGOLD, oxblood split tabard, normal brown boots/gloves, chestmotif naturally hidden. Stable physical main-cranium and rigidpauldron size across every cell; compact passing silhouette must naturally shorten, never enlarge to contactheight. Detailed painterly cinematic art with coolmoonlight/restainedwarmrim, consistentcolors. True alpha0transparentbackground, no floor/shadow/glow/grid/text/guidecolors; generousclear margins around complete hair/swordtip/shield/exposedboots.'''}
    refs=[guide,S/'overhead_appearance_patches_v4.png'];t['references']=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest()} for p in refs];tasks.append(t)
(P/'batch_tasks.json').write_text(json.dumps(tasks,indent=2)+'\n');print(json.dumps(tasks))
