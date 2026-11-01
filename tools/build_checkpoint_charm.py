"""Register complete generated checkpoint poses; never reshape body parts."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/characters/checkpoint_charm'
TARGET = ROOT/'assets/characters/checkpoint_charm'
CANVAS = (40, 44)
ANCHOR = (20, 38)
SCALE = 36/225
ROWS = ((0, 250), (250, 490), (490, 730), (730, 985), (985, 1228), (1228, 1536))
DIRECTIONS = ('front', 'back', 'left', 'right')


def png(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def json_bytes(value):return (json.dumps(value, indent=2)+'\n').encode()
def sha(value):return hashlib.sha256(value).hexdigest()


def register(sheet, column, row):
    top, bottom = ROWS[row]
    left, right = column*256, (column+1)*256
    cell = sheet.crop((left, top, right, bottom)).convert('RGBA')
    # Drop semitransparent generation residue without recoloring the art.
    cell.putalpha(cell.getchannel('A').point(lambda n: 255 if n >= 128 else 0))
    box = cell.getbbox()
    if box is None:raise ValueError('Empty checkpoint guard cell')
    feet = cell.crop((box[0], max(box[1],box[3]-14), box[2], box[3])).getbbox()
    if feet is None:raise ValueError('Missing checkpoint boot contact')
    foot_x = box[0]+(feet[0]+feet[2])/2
    pose = cell.crop(box)
    size = (round(pose.width*SCALE),round(pose.height*SCALE))
    pose = pose.resize(size,Image.Resampling.NEAREST)
    point = (round(ANCHOR[0]-(foot_x-box[0])*SCALE),ANCHOR[1]-size[1])
    if min(point)<0 or point[0]+size[0]>CANVAS[0]:
        raise ValueError('Checkpoint pose leaves its common canvas')
    output = Image.new('RGBA',CANVAS)
    output.alpha_composite(pose,point)
    return output,{'source_cell':[left,top,right,bottom],
                   'alpha_bounds':list(box),'registration':list(point),'scale':SCALE}


def build_outputs():
    sheet = Image.open(SOURCE/'poses_generated.png').convert('RGBA')
    if sheet.size != (1024,1536):raise ValueError('Unexpected checkpoint source dimensions')
    outputs, clips, registrations, images = {}, {}, {}, {}
    board = Image.new('RGB',(640,6*196),'#203b33')
    draw = ImageDraw.Draw(board)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',11)
    for row in range(6):
        for column in range(4):
            prefix = 'walk_'+DIRECTIONS[row] if row<4 else ('sit' if row==4 else 'check_right')
            name = prefix+'_'+str(column)
            image,registration = register(sheet,column,row)
            images[name] = image
            outputs[TARGET/(name+'.png')] = png(image)
            registrations[name] = registration
            expanded = image.resize((160,176),Image.Resampling.NEAREST)
            board.paste(expanded,(column*160,row*196),expanded)
            draw.text((column*160+4,row*196+178),name,font=font,fill='#e2e7db')
    def frame(name,duration):return {'file':name+'.png','duration_ms':duration}
    for direction in DIRECTIONS:
        clips['walk_'+direction] = {'loop':True,'frames':[frame('walk_'+direction+'_'+str(i),160) for i in range(4)]}
    clips['sit_down_front'] = {'loop':False,'frames':[frame('sit_0',260),frame('sit_1',280),frame('sit_2',300)]}
    clips['sit_front'] = {'loop':True,'frames':[frame('sit_2',950),frame('sit_3',950)]}
    clips['stand_up_front'] = {'loop':False,'frames':[frame('sit_2',240),frame('sit_1',280),frame('sit_0',260)]}
    clips['check_right'] = {'loop':False,'frames':[frame('check_right_0',450),frame('check_right_1',700),frame('check_right_2',700),frame('check_right_3',450)]}
    outputs[TARGET/'animation.json'] = json_bytes({'version':1,'id':'checkpoint_charm',
        'canvas':list(CANVAS),'anchor':list(ANCHOR),'draw_anchor':list(ANCHOR),'clips':clips,
        'equipment':{'helmet':'closed silver visor','tabard':'navy and gold','shield_arm':'physical left'}})
    outputs[SOURCE/'native_review.png'] = png(board)
    outputs[TARGET/'provenance.json'] = json_bytes({'version':1,
        'exporter':'tools/build_checkpoint_charm.py',
        'sources':{'assets/source/characters/checkpoint_charm/poses_generated.png':sha((SOURCE/'poses_generated.png').read_bytes())},
        'registrations':registrations,
        'exports':{str(p.relative_to(ROOT)):sha(data) for p,data in outputs.items()},
        'notes':['Twenty-four complete generated body poses; no body-part transforms or runtime mirroring.',
                 'Every exported pose uses the same uniform nearest-neighbor scale.',
                 'Seated poses articulate hips and knees; standing height is never compressed.',
                 'The physical-left shield and existing closed-helmet portrait identity are retained.']})
    return outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    outputs=build_outputs()
    if args.check:
        bad=[str(p.relative_to(ROOT)) for p,data in outputs.items() if not p.exists() or p.read_bytes()!=data]
        if bad:raise SystemExit('Checkpoint exports differ: '+', '.join(bad))
        print(f'Verified {len(outputs)} checkpoint guard sprite/provenance exports')
    else:
        for path,data in outputs.items():
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        print(f'Exported {len(outputs)} checkpoint guard sprite/provenance files')


if __name__=='__main__':main()
