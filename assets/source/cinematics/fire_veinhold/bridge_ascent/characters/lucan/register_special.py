"""Observed whole-pose seam repairs, with actual cranium registration.

The cranium template locates a complete figure; all physical density choices
come from separately inspected rigid head/pauldron widths. No limb transforms.
"""
from pathlib import Path
from hashlib import sha256
import json
import cv2,numpy as np
from PIL import Image
S=Path(__file__).resolve().parent;ROOT=S.parents[6]

def head_location(image):
    template=Image.open(S/'registered_front_cranium_reference.png').convert('RGB')
    template=cv2.cvtColor(np.array(template),cv2.COLOR_RGB2GRAY)
    gray=cv2.cvtColor(np.array(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    best=None
    for scale in np.linspace(.65,1.25,61):
        sample=cv2.resize(template,None,fx=scale,fy=scale)
        response=cv2.matchTemplate(gray[:min(400,image.height//2),140:390],sample,cv2.TM_CCOEFF_NORMED)
        _,score,_,point=cv2.minMaxLoc(response)
        if best is None or score>best['score']:
            best={'point':[140+point[0]+sample.shape[1]/2+.5*scale,point[1]+sample.shape[0]/2+17*scale],
                  'score':score,'template_scale_for_location_only':float(scale)}
    return best

def apply():
    from register_banks import export,OUT
    guide={r['index']:r for r in json.loads((S/'guide_frames/transition_guide_targets.json').read_text())}
    records=[]
    specs=[(36,'transition_036_039b.png',[0,0,512,768],1.15)]
    for i in range(37,40):specs.append((i,'transition_037_039c.png',[(i-37)*512,0,(i-36)*512,1024],270/266))
    for start,name,scale in ((40,'transition_040_043_closed.png',1.14),(44,'transition_044_047_closed.png',270/246),
                             ):
        for cell,index in enumerate(range(start,start+4)):
            specs.append((index,name,[cell%2*512,cell//2*768,(cell%2+1)*512,(cell//2+1)*768],scale))
    specs += [(48,'transition_048_051b.png',[0,0,512,768],270/254),(49,'transition_048_051b.png',[512,0,1024,768],270/249),(50,'transition_050_model_join.png',[0,0,1024,1536],270/545),(51,'transition_051_contact_armor.png',[0,0,1024,1536],.52)]
    for index,name,box,scale in specs:
        source=S/name;image=Image.open(source).convert('RGBA').crop(box)
        if index>=48:
            point={48:[275,175],49:[268,180],50:[529,303],51:[512,512]}[index]
            observed={'point':point,'method':'Manually observed whole cranium center; raw source pixel grid.'}
        else:
            observed=head_location(image)
        # The template control uses an actual whole head at37. The moderately
        # more elevated masters expose the crown about6sourcepixels farther
        # below its ellipse center; this offset was checked against source
        # outline grids (40/44) and does not change any body-part pixels.
        point=observed['point'][:]
        if index<48 and not 37<=index<=39:point[1]-=6
        target=[v*2 for v in guide[index]['guide_landmark_targets']['head_centre']]
        origin=[target[a]-point[a]*scale for a in(0,1)]
        record={'kind':'transition','index':index,'gait_frame':index%48,'source':source.relative_to(ROOT).as_posix(),
            'source_sha256':sha256(source.read_bytes()).hexdigest(),'cell':box,'scale':scale,'origin':origin,'alpha_floor':16,
            'head_location_match':observed,'observed_whole_cranium_centre':point,'guide_head_centre':target,
            'rigid_registration':{'main_cranium_source_band':[120,140],'main_pauldron_pair_source_band':[250,285]},
            'method':'Uniform completefigure sampling from inspected rigid cranium/pauldron widths; actual whole-cranium center registers to projected3Dhead center. Template locates only, never determines density.'}
        path=OUT/f'transition_{index:03d}.png';export(record).save(path);record['output_sha256']=sha256(path.read_bytes()).hexdigest();records.append(record)
    (S/'special_registration.json').write_text(json.dumps(records,indent=2)+'\n')
    return records
