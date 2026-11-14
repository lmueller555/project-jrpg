"""Author Aldric's native side walk; never modify the original generations.

This is an offline, part-based pixel-art authoring step, not an imagegen export
or a runtime puppet. The retained standing art supplies the face, clothing,
sleeves, hands and boot textures. Explicit joint poses supply eight coherent
steps. The arrival exporter subsequently copies the already registered cells.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

try:
    from .build_regent_arrival_actors import cell, foot_center
except ImportError:
    from build_regent_arrival_actors import cell, foot_center


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/regent_arrival/actors'
OUT = SOURCE/'aldric_side_walk'
REVIEW = ROOT/'docs/reviews/aldric_side_walk'
SIZE = (80, 96)
ANCHOR = (40, 92)
STRIDE = 32
PHASES = ('near_contact', 'near_down', 'near_passing', 'near_up',
          'far_contact', 'far_down', 'far_passing', 'far_up')
BOB = (0, 1, 0, -1, 0, 1, 0, -1)
FOOT_X = (-8, -4, 0, 4, 8, 7, 0, -6)
FOOT_FLOOR = (92, 92, 92, 92, 92, 89, 89, 90)
FOOT_ANGLE = (-8, 0, 0, 6, 16, 24, 8, -8)
ARM_SWING = (.30, .22, 0., -.22, -.30, -.22, 0., .22)
LEG_LENGTHS = (17., 17.)
ARM_LENGTHS = (math.hypot(3, 11), 10.)


def blank():
    return Image.new('RGBA', SIZE)


def encoded(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def registered(source, reference_height):
    """Use the retained export grid once; never recenter an animated foot."""
    scale = 80/reference_height
    fx, fy = foot_center(source)
    box = source.getbbox()
    crop = source.crop(box)
    crop = crop.resize((round(crop.width*scale), round(crop.height*scale)),
                       Image.Resampling.NEAREST)
    output = blank()
    output.alpha_composite(crop, (round(40-(fx-box[0])*scale),
                                 92-round((fy-box[1])*scale)))
    return output


def references():
    sheet = Image.open(SOURCE/'travelers_generated.png').convert('RGBA')
    bounds = [0, 325, 635, 948, 1282]
    standing = ImageOps.mirror(cell(sheet, 0, 0, row_bounds=bounds))
    box = standing.getbbox()
    height = box[3]-box[1]
    old = []
    for column, row, mirror in ((3, 0, True), (0, 1, False),
                                (1, 1, False), (2, 1, False)):
        image = cell(sheet, column, row, row_bounds=bounds)
        old.append(registered(ImageOps.mirror(image) if mirror else image, height))
    return registered(standing, height), old


def polygon_part(source, polygon):
    mask = Image.new('L', SIZE)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    output = blank()
    output.paste(source, mask=mask)
    return output


def translated(image, x=0, y=0):
    output = blank()
    output.alpha_composite(image, (x, y))
    return output


def rigid(image, source_root, source_end, target_root, target_end):
    """Rotate native pixels about a joint without stretching a limb."""
    source_angle = math.atan2(source_end[1]-source_root[1], source_end[0]-source_root[0])
    target_angle = math.atan2(target_end[1]-target_root[1], target_end[0]-target_root[0])
    angle = target_angle-source_angle
    c, s = math.cos(angle), math.sin(angle)
    tx, ty = target_root
    sx, sy = source_root
    return image.transform(SIZE, Image.Transform.AFFINE,
                           (c, s, sx-c*tx-s*ty, -s, c, sy+s*tx-c*ty),
                           Image.Resampling.NEAREST)


def shaded(image, palette):
    colors = {p[:3] for p in image.get_flattened_data() if p[3]}
    lookup = {p: min(palette, key=lambda q:
              sum((a*.78-b)**2 for a, b in zip(p, q))) for p in colors}
    result = blank()
    result.putdata([(*lookup[p[:3]], 255) if p[3] else (0, 0, 0, 0)
                    for p in image.get_flattened_data()])
    return result


def two_bone(root, end, lengths):
    """A left-facing knee flexes forward; both bone lengths remain fixed."""
    dx, dy = end[0]-root[0], end[1]-root[1]
    distance = math.hypot(dx, dy)
    upper, lower = lengths
    if not abs(upper-lower) < distance <= upper+lower:
        raise ValueError(f'Foot outside leg reach: {root}, {end}')
    along = (upper*upper-lower*lower+distance*distance)/(2*distance)
    height = math.sqrt(max(0., upper*upper-along*along))
    return (root[0]+dx*along/distance-dy*height/distance,
            root[1]+dy*along/distance+dx*height/distance)


def textured_bone(source, a, b, widths, texture_bounds):
    """Pose a trouser/boot silhouette using its retained native material."""
    output = blank()
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    nx, ny = dy/length, -dx/length
    wa, wb = widths
    silhouette = Image.new('L', SIZE)
    draw = ImageDraw.Draw(silhouette)
    draw.polygon([(round(x), round(y)) for x, y in
                  ((a[0]+nx*wa, a[1]+ny*wa), (b[0]+nx*wb, b[1]+ny*wb),
                   (b[0]-nx*wb, b[1]-ny*wb), (a[0]-nx*wa, a[1]-ny*wa))], fill=255)
    draw.ellipse((round(b[0]-wb), round(b[1]-wb),
                  round(b[0]+wb), round(b[1]+wb)), fill=255)
    left, top, right, bottom = texture_bounds
    pixels, mask = output.load(), silhouette.load()
    for y in range(SIZE[1]):
        for x in range(SIZE[0]):
            if not mask[x, y]:
                continue
            t = max(0., min(1., ((x-a[0])*dx+(y-a[1])*dy)/(length*length)))
            width = wa+(wb-wa)*t
            side = ((x-a[0])*nx+(y-a[1])*ny)/max(1., width)
            sx = max(left, min(right-1, round(left+(side+1)*.5*(right-left-1))))
            sy = max(top, min(bottom-1, round(top+t*(bottom-top-1))))
            pixel = source.getpixel((sx, sy))
            pixels[x, y] = pixel if pixel[3] else (44, 32, 25, 255)
            if abs(side) > .84:
                pixels[x, y] = (28, 23, 22, 255)
    return output


def parts(reference):
    """Explicit appearance masks, all in the same native pelvis registration."""
    result = {
        'head': polygon_part(reference, ((0, 0), (79, 0), (79, 29), (0, 29))),
        'torso': polygon_part(reference, ((35, 28), (43, 27), (47, 32), (46, 44),
                                          (46, 51), (33, 52), (32, 35))),
        'front_coat': polygon_part(reference, ((33, 48), (36, 48), (33, 75),
                                               (29, 73), (30, 64))),
        'back_coat': polygon_part(reference, ((39, 49), (46, 49), (48, 61),
                                              (54, 73), (41, 76), (40, 62))),
        'pouch': polygon_part(reference, ((43, 45), (47, 45), (47, 54), (43, 55))),
        'upper_arm': polygon_part(reference, ((44, 31), (49, 32), (51, 39),
                                              (51, 46), (46, 46), (44, 38))),
        'forearm': polygon_part(reference, ((46, 43), (51, 43), (51, 54), (46, 54))),
        'hand': polygon_part(reference, ((46, 54), (50, 53), (51, 57),
                                         (49, 60), (46, 60), (45, 57))),
        'foot': polygon_part(reference, ((34, 84), (40, 84), (40, 91),
                                         (27, 91), (27, 89), (31, 88))),
    }
    # Restore the small cloth patch originally hidden by the resting hand.
    # This belongs to this new authored source, never the retained PNG.
    coat = result['back_coat']
    cloth_mask = Image.new('L', SIZE)
    ImageDraw.Draw(cloth_mask).polygon(((39, 49), (46, 49), (48, 61),
                                       (54, 73), (41, 76), (40, 62)), fill=255)
    for y in range(53, 64):
        for x in range(42, 52):
            if not cloth_mask.getpixel((x, y)):
                continue
            p = coat.getpixel((x, y))
            if not p[3] or (p[0] > p[2]*1.4 and p[0] > 80):
                coat.putpixel((x, y), reference.getpixel((44, 64+y%5)))
    return result


def foot_pose(foot, phase):
    theta = math.radians(FOOT_ANGLE[phase])
    ankle = (40+FOOT_X[phase], 86.)
    image = rigid(foot, (36, 86), (36, 87), ankle,
                  (ankle[0]+math.sin(theta), ankle[1]+math.cos(theta)))
    dy = FOOT_FLOOR[phase]-image.getbbox()[3]
    image = translated(image, y=dy)
    return image, (ankle[0], ankle[1]+dy)


def arm_pose(layers, phase, near, bob):
    angle = ARM_SWING[phase]*(1 if near else -1)
    shoulder = (46. if near else 34., 33.+bob)
    upper, lower = ARM_LENGTHS
    elbow = (shoulder[0]+math.sin(angle)*upper,
             shoulder[1]+math.cos(angle)*upper)
    wrist = (elbow[0]+math.sin(angle-.18)*lower,
             elbow[1]+math.cos(angle-.18)*lower)
    image = rigid(layers['upper_arm'], (46, 33), (49, 44), shoulder, elbow)
    image.alpha_composite(rigid(layers['forearm'], (49, 44), (49, 54), elbow, wrist))
    image.alpha_composite(rigid(layers['hand'], (49, 54), (49, 55), wrist,
                                (wrist[0]+math.sin(angle-.18), wrist[1]+math.cos(angle-.18))))
    return image, dict(shoulder=shoulder, elbow=elbow, wrist=wrist)


def coat_pose(layer, phase, bob, front=False):
    output = blank()
    # Cloth follows the previous step, by at most one native pixel at the hem.
    sway = (0, 0, 1, 1, 0, 0, -1, -1)[phase]
    if front:
        sway = -sway
    for y in range(48, 77):
        dx = sway if y >= 63 else 0
        output.alpha_composite(layer.crop((0, y, 80, y+1)), (dx, y+bob))
    return output


def authored_frame(reference, layers, palette, index):
    bob = BOB[index]
    drawing, info = {}, {}
    for near in (False, True):
        name = 'near' if near else 'far'
        phase = index if near else (index+4)%8
        shoe, ankle = foot_pose(layers['foot'], phase)
        hip = (41. if near else 39., 55.+bob)
        knee = two_bone(hip, ankle, LEG_LENGTHS)
        leg = textured_bone(reference, hip, knee, (3.5, 2.5), (34, 56, 40, 73))
        leg.alpha_composite(textured_bone(reference, knee, ankle, (2.5, 2.5), (32, 74, 40, 88)))
        leg.alpha_composite(shoe)
        arm, joints = arm_pose(layers, index, near, bob)
        drawing[name+'_leg'] = leg if near else shaded(leg, palette)
        drawing[name+'_arm'] = arm if near else shaded(arm, palette)
        info[name+'_leg'] = dict(hip=hip, knee=knee, ankle=ankle,
                                 planted=phase <= 4, foot_bounds=list(shoe.getbbox()))
        info[name+'_arm'] = joints
    image = blank()
    for name in ('far_arm', 'far_leg', 'near_leg'):
        image.alpha_composite(drawing[name])
    image.alpha_composite(coat_pose(layers['front_coat'], index, bob, front=True))
    image.alpha_composite(coat_pose(layers['back_coat'], index, bob))
    image.alpha_composite(translated(layers['torso'], y=bob))
    image.alpha_composite(translated(layers['pouch'], y=bob))
    image.alpha_composite(drawing['near_arm'])
    image.alpha_composite(translated(layers['head'], y=bob))
    return image, dict(file=f'walk_{index}.png', phase=PHASES[index], duration_ms=125,
                      body_offset=[0, bob], **info)


def protected_inputs():
    path = OUT/'side_walk.json'
    if path.exists():
        # The approved clerk extension owns its new manifest/locomotion only;
        # original clerk idle/read/portrait pixels remain protected here.
        return {name:sha for name,sha in json.loads(path.read_text())['protected_sha256'].items()
                if name!='assets/story/regent_arrival/actors/clerk/animation.json'}
    inputs = list(SOURCE.glob('*_generated.png'))
    for path in (ROOT/'assets/story/regent_arrival/actors').rglob('*'):
        if not path.is_file() or path.name == 'provenance.json':
            continue
        if path.parent.name == 'aldric' and (path.name == 'animation.json' or
                (path.stem.startswith('walk_') and path.stem[5:].isdigit())):
            continue
        if path.parent.name == 'clerk' and path.name not in ('stand_left.png','read_left.png'):
            continue
        inputs.append(path)
    return {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(inputs)}


def build():
    reference, old = references()
    palette = sorted({p[:3] for p in reference.get_flattened_data() if p[3]})
    layers = parts(reference)
    frames, records = zip(*(authored_frame(reference, layers, palette, i) for i in range(8)))
    sheet = Image.new('RGBA', (SIZE[0]*8, SIZE[1]))
    for i, frame in enumerate(frames):
        sheet.alpha_composite(frame, (i*SIZE[0], 0))
    protected = protected_inputs()
    for name, sha in protected.items():
        if digest((ROOT/name).read_bytes()) != sha:
            raise ValueError('Protected original or non-side-walk asset changed: '+name)
    metadata = dict(version=1, canvas=list(SIZE), anchor=list(ANCHOR),
                    sheet='side_walk.png', stride_pixels=STRIDE,
                    authoring='offline native pixel parts and explicit fixed-length joint poses',
                    authoring_tool='tools/build_aldric_side_walk.py',
                    authoring_tool_sha256=digest(Path(__file__).read_bytes()),
                    appearance_source='assets/source/cinematics/regent_arrival/actors/travelers_generated.png',
                    appearance_source_sha256=digest((SOURCE/'travelers_generated.png').read_bytes()),
                    reference_pixels_sha256=digest(reference.tobytes()),
                    leg_lengths=list(LEG_LENGTHS), arm_lengths=list(ARM_LENGTHS),
                    registration='fixed pelvis/root x=40 and supporting floor y=92; no per-frame recentering',
                    frames=records, protected_sha256=protected)
    outputs = {OUT/'side_walk.png': encoded(sheet),
               OUT/'side_walk.json': (json.dumps(metadata, indent=2)+'\n').encode()}
    # Review-only images are deliberately separate from runtime actor inputs.
    board = Image.new('RGB', (8*170, 2*220), '#26352e')
    draw = ImageDraw.Draw(board)
    for row, images in enumerate((old, frames)):
        for i, image in enumerate(images):
            large = image.resize((160, 192), Image.Resampling.NEAREST)
            board.paste(large, (i*170+5, row*220+5), large)
            text = 'Previous '+str(i) if row == 0 else PHASES[i]
            draw.text((i*170+5, row*220+202), text, fill='#f1e7c8')
    outputs[REVIEW/'frames.png'] = encoded(board)
    previews = []
    for frame in frames:
        canvas = Image.new('RGBA', SIZE, '#26352e')
        canvas.alpha_composite(frame)
        previews.append(canvas.convert('RGB').resize((240, 288), Image.Resampling.NEAREST))
    stream = io.BytesIO()
    # GIF stores centiseconds, not125ms. Alternate120/130 to retain a1s loop.
    previews[0].save(stream, format='GIF', save_all=True, append_images=previews[1:],
                     duration=[120,130]*4, loop=0, disposal=2, optimize=False)
    outputs[REVIEW/'walk.gif'] = stream.getvalue()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_bytes() != content:
                raise SystemExit('Side-walk authoring output differs: '+str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    print(('Verified' if args.check else 'Authored')+' eight registered Aldric side-walk poses')


if __name__ == '__main__':
    main()