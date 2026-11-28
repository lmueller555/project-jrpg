from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;ROOT=P.parents[7]
tasks=[]
for phase in(8,32):
    owner='LEFT leg on IMAGE RIGHT' if phase==8 else 'RIGHT leg on IMAGE LEFT'
    t={'id':f'passing_key_{phase:02d}','output':f'passing_key_{phase:02d}.png','phase':phase,'prompt':f'''Paint ONE complete Lucan running figure in the EXACT TRUE VERTICAL camera and anatomical projection in FIRST attached actual3D guide. SECOND supplies cropped material/identity ONLY. Phase{phase} compact passing/recovery, NOT contact. The first guide gold ball is a BENT KNEE, never an ankle. Cyan shows its CALF FOLDING BACK to a boot mostly OCCLUDED by head/body. Guide colors and text must not appear in finished art.

CRITICAL FORWARD LEG: {owner} has the forward/down projected SILVER KNEE CAP. Its calf folds BACK UNDER/BEHIND the torso: NO LONG SHIN and NO BROWN BOOT may protrude BELOW this forward kneecap. The down-most part of that chain is rounded steel kneecap. Normal boot is hidden by head/torso; do not invent a visible foot to show it. Trace hip→forward knee→folded calf→occluded boot exactly as guide. Opposite leg trails behind red hips; only its boot portion actually peeking past cloth in guide can show. Exactly TWO connected hip-knee-ankle chains and TWO actual boots, even when occluded. No obsolete third toe underbelt.

True90degree overhead: bare swept darkbrown hair CROWN AHEAD/DOWN of red hips; no face/eyes looking up or frontal breastplate. TOPS of shoulders/torso, naturally foreshortened adult upright runner, not prone. Same physical head/shoulders and real limb lengths; do not fit silhouetteheight. RIGHT sword arm IMAGE LEFT and LEFT shield arm IMAGE RIGHT, both full connected shoulder-elbow-wrist chains and attached glove/grip. Shield hangs UPRIGHT: ONLY thin curved golden rim with tiny red back sliver, never broad flat kite face. Normal-sized sword/shield naturally foreshortened.

Young adult Lucan, detailed painterly cinematic knight, polished articulated SILVERSTEEL/GOLD shoulders/thighs/knees/greaves, oxblood split tabard, normal brown leather gloves/boots. Pale chestmotif naturally occluded. Cool moonlit silver with restrained warmrim, no redesign. One indivisible newly drawn COMPLETE figure, not assembled/warped parts. Entire hair/swordtip/shield/visible boots within generous TRANSPARENT margins. True alpha0 background, no floor/shadow/glow/grid/text.'''}
    refs=[P/f'guide_{phase:02d}.png',P.parent/'overhead_appearance_patches_v4.png']
    t['references']=[{'path':q.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(q.read_bytes()).hexdigest()} for q in refs];tasks.append(t)
(P/'key_tasks.json').write_text(json.dumps(tasks,indent=2)+'\n')
print(json.dumps(tasks))
