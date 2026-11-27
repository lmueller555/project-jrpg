"""Offline source landmark audit; never draws or deforms production anatomy.

Requires opencv-python-headless and numpy in the authoring environment only.
The production exporter consumes recorded coordinates with Pillow, not cv2.
"""
from pathlib import Path
import json
import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / 'appearance_contact.png'

def measure():
    original = cv2.imread(str(REFERENCE))
    patches = {'eyes': (480,105,140,65,551,141),
               'neck': (500,225,110,60,555,247),
               'belt': (520,500,80,90,554,544)}
    ranges = {'eyes': (70,250), 'neck': (180,400), 'belt': (420,700)}
    records=[]
    for path in sorted((HERE/'frames').glob('frame_*.png')):
        image=cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        gray=cv2.cvtColor(image[:,:,:3],cv2.COLOR_BGR2GRAY)
        landmarks={};scores={};matching_scales={}
        for name,(x,y,w,h,cx,cy) in patches.items():
            template=cv2.cvtColor(original[y:y+h,x:x+w],cv2.COLOR_BGR2GRAY)
            best=-1;match=None;top,bottom=ranges[name]
            region=gray[top:bottom,380:720]
            for s in np.linspace(.85,1.2,36):
                sampled=cv2.resize(template,None,fx=float(s),fy=float(s))
                result=cv2.matchTemplate(region,sampled,cv2.TM_CCOEFF_NORMED)
                _,score,_,point=cv2.minMaxLoc(result)
                if score > best:
                    best=score
                    match=[380+point[0]+(cx-x)*s,top+point[1]+(cy-y)*s]
                    matching_scales[name]=float(s)
            landmarks[name]=[round(float(v),3) for v in match]
            scores[name]=round(float(best),5)
        records.append({'frame':int(path.stem.split('_')[-1]),
            'source':path.relative_to(HERE.parent).as_posix(),
            'landmarks':landmarks,'landmark_match_scores':scores,
            'template_match_scales':matching_scales})
    (HERE/'measured_landmarks.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Measured',len(records),'whole-drawing sources; no pixel changes.')
    return records

if __name__=='__main__':measure()
