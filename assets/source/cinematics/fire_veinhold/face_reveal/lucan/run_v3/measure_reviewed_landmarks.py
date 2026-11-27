"""Retain actual selected-artwork observations, separate from authoring guides.

The image-derived checks use their own independently reviewed regions. These
annotations document visible knees and boot edges; they do not move pixels,
infer hidden anatomy, or prescribe future gait targets.
"""
from hashlib import sha256
from pathlib import Path
import json
import tempfile
import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
BANK = ROOT/'assets/story/fire_veinhold_opening/shot07/characters/lucan'
OUTPUT = Path(tempfile.gettempdir())/'lucan_run_v3_landmarks'
# Identity windows selected by viewing the actual rendered boot contours.
WINDOWS = {
    0: {'right':[290,820,380,985], 'left':[380,650,450,790]},
    7: {'right':[280,800,380,985], 'left':[380,680,455,820]},
    8: {'right':[270,800,380,985], 'left':[380,650,470,840]},
    9: {'right':[280,800,385,985], 'left':[380,690,460,850]},
    10:{'right':[250,700,370,985], 'left':[380,650,475,865]},
    11:{'right':[250,680,365,930], 'left':[370,650,465,890]},
    12:{'right':[270,680,350,850], 'left':[345,700,440,890]},
    13:{'right':[230,620,340,850], 'left':[370,740,480,945]},
    14:{'right':[230,620,340,850], 'left':[370,740,480,960]},
    15:{'right':[250,600,370,810], 'left':[370,790,480,985]},
    16:{'right':[230,600,370,810], 'left':[370,790,480,985]},
    17:{'right':[230,600,370,810], 'left':[370,790,480,985]},
    18:{'right':[275,630,360,810], 'left':[370,790,480,985]},
    24:{'right':[270,650,345,780], 'left':[380,820,480,985]},
    27:{'right':[280,680,350,825], 'left':[370,810,480,985]},
    34:{'right':[250,600,365,840], 'left':[370,790,480,985]},
    35:{'right':[250,600,365,840], 'left':[370,790,480,985]},
    36:{'right':[250,600,365,840], 'left':[370,790,480,985]},
    37:{'right':[250,620,360,820], 'left':[370,790,480,985]},
    38:{'right':[250,620,365,850], 'left':[370,700,485,935]},
    39:{'right':[250,650,360,920], 'left':[370,650,480,920]},
    40:{'right':[250,700,365,960], 'left':[375,630,480,850]},
    41:{'right':[250,760,365,985], 'left':[375,630,480,850]},
    42:{'right':[260,800,390,985], 'left':[380,620,480,850]},
}
MANUAL_KNEE = {(15,'right'):[313,633]}
# These rear/oblique plates do not expose a reliable center in the actual view.
UNANNOTATED_KNEES = {(0,'left'), (24,'right'), (13,'right'), (14,'right'),
    (16,'right'), (17,'right'), (18,'right'), (36,'left')}

def measure():
    OUTPUT.mkdir(exist_ok=True)
    records, tiles = [], []
    for frame, windows in WINDOWS.items():
        path = BANK/f'frame_{frame:02}.png'
        image = Image.open(path).convert('RGBA')
        pixels = np.asarray(image)
        gray = cv2.cvtColor(pixels[:,:,:3],cv2.COLOR_RGB2GRAY)[540:740,270:480]
        circles = cv2.HoughCircles(cv2.GaussianBlur(gray,(5,5),1),
            cv2.HOUGH_GRADIENT,1,35,param1=100,param2=30,minRadius=20,maxRadius=45)
        choices = [] if circles is None else circles[0]+[270,540,0]
        canvas = Image.new('RGB',image.size,'#152235')
        canvas.paste(image,mask=image.getchannel('A'))
        pen = ImageDraw.Draw(canvas)
        limbs = {}
        for side, region in windows.items():
            x1,y1,x2,y2 = region
            ys,xs = np.where(pixels[y1:y2,x1:x2,3]>128)
            if not len(ys):
                raise ValueError(f'Missing observed boot {frame}:{side}')
            bottom = int(ys.max())
            point = [round(float(xs[ys>=bottom-2].mean()+x1),2),bottom+y1]
            if point[1]>=y2-1:
                raise ValueError(f'Observed boot touches review crop: {frame}:{side}')
            candidates = [c for c in choices if (c[0]<380)==(side=='right')]
            knee = MANUAL_KNEE.get((frame,side))
            method = 'Manual visible kneecap-center observation' if knee else 'Circular plate-edge proposal, visually reviewed'
            if knee is None and candidates and (frame,side) not in UNANNOTATED_KNEES:
                knee = [round(float(v),2) for v in candidates[0][:2]]
            limbs['anatomical_'+side] = {
                'visible_kneecap_center':knee, 'knee_uncertainty_pixels':8,
                'knee_method':method if knee else 'No reliable center annotated for this oblique/partially hidden plate; inspect the full connected chain.',
                'visible_boot_distal_edge':point, 'boot_uncertainty_pixels':3,
                'boot_measurement_roi':region,
                'ankle_joint':None,
                'ankle_visibility':'Anatomical joint is hidden by greave/boot shaft. Visible calf and boot continuity was reviewed; no hidden joint is invented.',
                'heel_contact':None,
                'heel_visibility':'Rear heel contact is obscured in this frontal view. The visible distal sole edge is recorded; no ground-plane contact is inferred.'}
            color = '#ffad42' if side=='right' else '#50d8ff'
            pen.rectangle(region,outline=color,width=2)
            for label, value in [('knee',knee),('boot',point)]:
                if value:
                    x,y = value
                    pen.ellipse((x-5,y-5,x+5,y+5),outline=color,width=2)
                    pen.text((x+8,y-7),side+' '+label,fill=color)
        pen.text((20,15),f'Actual selected artwork {frame:02}; exported pixels',fill='white')
        canvas.save(OUTPUT/f'frame_{frame:02}.png')
        tiles.append((frame,canvas.crop((220,440,540,1024))))
        records.append({'frame':frame,'png':path.relative_to(ROOT).as_posix(),
            'png_sha256':sha256(path.read_bytes()).hexdigest(),'limbs':limbs})
    result = {
        'units':'Exported 768x1024 artwork pixels before cinematic projection.',
        'purpose':'Actual selected-artwork observations, not authoring targets or a source of generated limb coordinates.',
        'method':'Opaque alpha >128 distal boot edge in visually selected anatomical ROIs; visible kneecap plate observations with explicit uncertainty. Hidden ankle/heel joints are not inferred.',
        'review_limit':'Connected anatomy was reviewed in the actual selected drawings. These observations and a cropped frontal billboard shot do not prove3D foot locking at4m/s.',
        'frames':records}
    (HERE/'reviewed_landmarks.json').write_text(json.dumps(result,indent=2)+'\n')
    sheet = Image.new('RGB',(320*6,614*((len(tiles)+5)//6)),'#152235')
    pen = ImageDraw.Draw(sheet)
    for index,(frame,tile) in enumerate(tiles):
        x,y = (index%6)*320,(index//6)*614
        sheet.paste(tile,(x,y))
        pen.text((x+5,y+586),str(frame),fill='white')
    sheet.save(OUTPUT/'actual_knee_boot_observations.jpg')
    print('Retained actual selected knee/boot observations for',len(records),'frames in',OUTPUT)

if __name__ == '__main__':
    measure()
