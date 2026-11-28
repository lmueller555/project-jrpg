"""Annotate preserved real3D guides to distinguish knee from folded calf/boot.

These images are construction references only. No generated figure is altered.
"""
from pathlib import Path
from hashlib import sha256
import ast,math,json
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent;ROOT=HERE.parents[7]
tree=ast.parse((SOURCE/'render_pose_guides.py').read_text());ns={'math':math}
exec(compile(ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in('hermite','curve','foot_at','knee_at')],type_ignores=[]),'unchanged_3d_guide_functions','exec'),ns)
records=[]
for phase in list(range(8,16))+list(range(32,40)):
    source=SOURCE/f'guide_frames/overhead_{phase:03d}_guide.png'
    image=Image.open(source).convert('RGB');d=ImageDraw.Draw(image)
    recoil=-.012*math.cos(4*math.pi*(phase/60)/.8);hip_z=.95+recoil
    points={}
    for side,offset in((1,0),(-1,.4)):
        y,z=ns['foot_at'](phase/60+offset);hip=(side*.11,0,hip_z);foot=(side*.13,y,z);knee=ns['knee_at'](hip,foot)
        def projected(point):return[256-250*point[0],480+250*point[1]]
        points['right' if side==1 else 'left']={'foot3d':foot,'knee3d':knee,'foot2d':projected(foot),'knee2d':projected(knee)}
    forward='left' if phase<24 else 'right';knee=points[forward]['knee2d'];foot=points[forward]['foot2d']
    d.ellipse((knee[0]-9,knee[1]-9,knee[0]+9,knee[1]+9),fill='#e0a83a',outline='#fff291',width=2)
    d.line([tuple(knee),tuple(foot)],fill='#32d7ed',width=3)
    d.ellipse((foot[0]-7,foot[1]-7,foot[0]+7,foot[1]+7),outline='#32d7ed',width=3)
    labelx=300 if forward=='left' else 10
    d.line([(labelx+20,666),tuple(knee)],fill='#fff291',width=2)
    d.text((labelx,670),'FORWARD KNEE CAP',fill='#fff291')
    d.text((labelx,686),'NO SHIN/BOOT BELOW',fill='#fff291')
    d.text((12,25),f'PHASE {phase}: EXACT VERTICAL CAMERA',fill='white')
    d.text((12,43),'CYAN: CALF FOLDS BACK TO HIDDEN BOOT',fill='#32d7ed')
    d.text((12,61),'GOLD BALL = KNEE, NOT AN ANKLE',fill='#fff291')
    output=HERE/f'guide_{phase:02d}.png';image.save(output)
    records.append({'phase':phase,'source':source.relative_to(ROOT).as_posix(),'source_sha256':sha256(source.read_bytes()).hexdigest(),'output':output.name,'output_sha256':sha256(output.read_bytes()).hexdigest(),'purpose':'construction_reference_only; original3Drender unchanged','joints':points})
(HERE/'guide_annotations.json').write_text(json.dumps(records,indent=2)+'\n')
print('Annotated16existingreal3Dguides; no original sources changed')
