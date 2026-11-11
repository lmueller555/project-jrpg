"""Measure generated arm-rig atlas attachments without changing source artwork.

The base sheet preserves the previous pose layout and projected boot centers.
New skill poses use the midpoint of the two boot contacts, never silhouette
centroids. All poses use one fixed 0.225 scale, including crouches and kneels.
"""
from copy import deepcopy
import json
from pathlib import Path

from PIL import Image

from build_mira_combat import _main_component

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat/mira_arm_rig'


def attachments(cell):
    """Locate the authored lens/tool light; record explicit source coordinates."""
    bounds = cell.getbbox()
    left, top, right, bottom = bounds
    candidates = []
    for y in range(top+round((bottom-top)*.2), bottom):
        for x in range(left, left+round((right-left)*.65)):
            r, g, b, a = cell.getpixel((x,y))
            if a and g > r+20 and (b > r+15 or g > b+25):
                candidates.append((x,y))
    if not candidates:
        # Impact Bolt changes the lens to amber; use its authored bright core.
        candidates = [(x,y) for y in range(top+round((bottom-top)*.2),bottom)
                      for x in range(left,left+round((right-left)*.55))
                      if (lambda p:p[3] and p[0]>180 and p[1]>130 and p[2]<135)(cell.getpixel((x,y)))]
    if not candidates:raise ValueError('Missing visible arm-rig lens')
    edge = min(x for x,y in candidates)
    lens = [(x,y) for x,y in candidates if x <= edge+9]
    muzzle = [round(sum(point[axis] for point in lens)/len(lens)) for axis in (0,1)]
    # The activation switch sits on the dorsal cuff, slightly behind its lens.
    controller = [min(right-2,muzzle[0]+34),muzzle[1]-3]
    return {'muzzle': muzzle, 'controller': controller,
            'projector': muzzle, 'tool': muzzle}


def build():
    previous = json.loads((ROOT/'assets/source/combat/mira_redraw/registration.json').read_text())
    specification = deepcopy(previous)
    specification.update(source='base_authored.png',source_grid=[6,7],
        sources=[{'file':'base_authored.png','grid':[6,7]},
                 {'file':'skills_authored.png','grid':[8,5]}],
        registration=('Explicit projected boot contacts; retained base pose boot centers, '
                      'measured skill boot contacts; cell-local source attachments. '
                      'One fixed 0.225 native scale, no silhouette-centroid registration '
                      'and no per-pose body scaling.'))
    base = Image.open(SOURCE/'base_authored.png').convert('RGBA')
    for drawing in specification['drawings']:
        left,top,width,height = drawing['source_rect']
        cell = _main_component(base.crop((left,top,left+width,top+height)))
        drawing['source'] = 'base_authored.png'
        drawing['native_scale'] = .225
        drawing['source_foot'][1] = cell.getbbox()[3]-1
        drawing['anchors'] = attachments(cell)
    skills = Image.open(SOURCE/'skills_authored.png').convert('RGBA')
    for index in range(40):
        column,row = index%8,index//8
        left,top = round(column*skills.width/8),round(row*skills.height/5)
        right,bottom = round((column+1)*skills.width/8),round((row+1)*skills.height/5)
        cell = _main_component(skills.crop((left,top,right,bottom)))
        bounds = cell.getbbox()
        # Both planted boots are represented by their contact strip. A lower
        # crouch has shorter bounds but receives exactly the same source scale.
        points = [(x,y) for y in range(bounds[3]-12,bounds[3])
                  for x in range(bounds[0],bounds[2]) if cell.getpixel((x,y))[3]]
        foot = [round((min(x for x,y in points)+max(x for x,y in points))/2),bounds[3]-1]
        specification['drawings'].append(dict(source_cell=42+index,
            source='skills_authored.png',native_scale=.225,
            source_rect=[left,top,right-left,bottom-top],source_foot=foot,
            anchors=attachments(cell)))
    (SOURCE/'registration.json').write_text(json.dumps(specification,indent=2)+'\n')
    return specification


if __name__ == '__main__':
    print(json.dumps({'registered_drawings':len(build()['drawings'])}))
