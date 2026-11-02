"""Offline native part-authoring for the cinematic clerk, never imagegen.

Retained clerk pixels supply his profile, moss coat, ledger, hand and materials.
Unseen rear/overhead silhouettes are explicitly reconstructed at native size.
Original generations, idle/read exports, portraits and Aldric are read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from .build_regent_arrival_actors import cell, foot_center
except ImportError:
    from build_regent_arrival_actors import cell, foot_center


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/regent_arrival/actors'
OUT = SOURCE/'clerk_walk'
REVIEW = ROOT/'docs/reviews/regent_crossroads'
SIZE = (80, 96)
ANCHOR = (40, 92)
STRIDE = 30
PHASES = ('near_contact', 'near_down', 'near_passing', 'near_up',
          'far_contact', 'far_down', 'far_passing', 'far_up')
BOB = (0, 1, 0, -1, 0, 1, 0, -1)
FOOT_X = (-7.5, -3.75, 0., 3.75, 7.5, 6., 0., -6.)
FOOT_FLOOR = (92, 92, 92, 92, 92, 89, 89, 90)
FOOT_ANGLE = (-7, 0, 0, 7, 16, 24, 8, -7)
ARM_SWING = (-.24, -.18, 0., .18, .24, .18, 0., -.18)
LEG_LENGTHS = (16.5, 16.)
FREE_ARM_LENGTHS = (math.hypot(1, 12), math.hypot(2, 10))
HELD_ARM_LENGTHS = (math.hypot(3, 12), 11.)
VIEWS = {'side': 0., 'quarter': math.pi/4, 'back': math.pi/2}
LOOPS = {'walk_left': 'side', 'walk_left_back': 'quarter', 'walk_back': 'back'}
# These are clerk-only masks, not a recolored Aldric body or overworld sprite.
MASKS = {
    'head': ((0, 0), (79, 0), (79, 29), (0, 29)),
    'torso': ((36, 28), (43, 27), (48, 31), (48, 48), (44, 52),
              (35, 51), (34, 34)),
    'front_coat': ((32, 48), (36, 48), (38, 73), (32, 73), (29, 70), (30, 60)),
    'back_coat': ((41, 49), (50, 49), (51, 59), (55, 70), (52, 73),
                  (43, 74), (41, 62)),
    'ledger_arm': ((46, 30), (51, 31), (54, 39), (56, 51), (55, 55),
                   (48, 55), (47, 46)),
    'ledger': ((43, 48), (49, 48), (51, 52), (51, 61), (44, 60)),
    'ledger_hand': ((50, 53), (55, 53), (55, 58), (53, 61), (48, 60), (47, 57)),
    'free_upper': ((32, 31), (36, 33), (36, 43), (34, 47), (29, 46), (30, 37)),
    'free_forearm': ((29, 43), (34, 43), (33, 54), (28, 55), (27, 52)),
    'free_hand': ((28, 53), (32, 54), (32, 59), (30, 61), (27, 59), (27, 55)),
    'boot': ((36, 82), (41, 82), (42, 90), (39, 91), (27, 91),
             (27, 88), (32, 86), (35, 85)),
}
MATERIALS = {'moss': (42, 32, 54, 72), 'sleeve': (48, 35, 53, 47),
             'trousers': (37, 74, 41, 83), 'leather': (35, 86, 40, 90),
             'book': (44, 49, 49, 58), 'hair': (33, 15, 46, 28),
             'skin': (48, 54, 55, 60)}
LAYER_ORDER = ('far_thigh', 'far_shin', 'far_boot', 'free_upper',
               'free_forearm', 'free_hand', 'near_thigh', 'near_shin',
               'near_boot', 'coat', 'torso', 'head', 'ledger_arm',
               'ledger', 'ledger_hand')


def blank(size=SIZE):
    return Image.new('RGBA', size)


def encoded(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2)+'\n').encode()


def references():
    """Reproduce the two existing registrations without reading a new export."""
    with Image.open(SOURCE/'travelers_generated.png') as sheet:
        frames = [cell(sheet.convert('RGBA'), column, 3,
                       row_bounds=[0, 325, 635, 948, 1282]) for column in (0, 1)]
    bounds = frames[0].getbbox()
    scale = 77/(bounds[3]-bounds[1])
    result = []
    for frame in frames:
        box = frame.getbbox()
        fx, fy = foot_center(frame)
        crop = frame.crop(box)
        crop = crop.resize((round(crop.width*scale), round(crop.height*scale)),
                           Image.Resampling.NEAREST)
        image = blank()
        image.alpha_composite(crop, (round(40-(fx-box[0])*scale),
                                     92-round((fy-box[1])*scale)))
        result.append(image)
    return tuple(result)


def polygon_part(reference, polygon):
    mask = Image.new('L', SIZE)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    image = blank()
    image.paste(reference, mask=mask)
    return image


def translated(image, x=0, y=0):
    result = blank(image.size)
    result.alpha_composite(image, (x, y))
    return result


def rigid(image, source_root, source_end, target_root, target_end):
    """Native nearest rotation about joints: never stretch a limb."""
    delta = (math.atan2(target_end[1]-target_root[1], target_end[0]-target_root[0])
             -math.atan2(source_end[1]-source_root[1], source_end[0]-source_root[0]))
    c, s = math.cos(delta), math.sin(delta)
    sx, sy = source_root
    tx, ty = target_root
    return image.transform(SIZE, Image.Transform.AFFINE,
                           (c, s, sx-c*tx-s*ty, -s, c, sy+s*tx-c*ty),
                           Image.Resampling.NEAREST)


def two_bone(root, end, lengths):
    dx, dy = end[0]-root[0], end[1]-root[1]
    distance = math.hypot(dx, dy)
    upper, lower = lengths
    if not abs(upper-lower) < distance <= upper+lower:
        raise ValueError(f'Clerk endpoint outside fixed limb reach: {root}, {end}')
    along = (upper*upper-lower*lower+distance*distance)/(2*distance)
    height = math.sqrt(max(0., upper*upper-along*along))
    return (root[0]+dx*along/distance-dy*height/distance,
            root[1]+dy*along/distance+dx*height/distance)


def project(point, yaw, lane=0.):
    """Yaw the sagittal gait into a shallow ground plane, not a flat flip.

    The clerk's anatomical left hand/leg is near in profile, but becomes the
    LEFT side in a back view. Ledger ownership therefore never swaps hands.
    Joint lengths are measured in the unprojected anatomical plane; projected
    bones naturally foreshorten. The exporter never performs this operation.
    """
    forward = point[0]-40
    return (40+math.cos(yaw)*forward+math.sin(yaw)*lane,
            point[1]+math.sin(yaw)*(forward*.22-1.65))


def material_pixel(reference, material, u, v):
    left, top, right, bottom = MATERIALS[material]
    x = left+max(0, min(right-left-1, round(u*(right-left-1))))
    y = top+max(0, min(bottom-top-1, round(v*(bottom-top-1))))
    pixel = reference.getpixel((x, y))

    def valid(p):
        r, g, b, a = p
        if not a:
            return False
        if material in ('moss', 'sleeve'):
            return g >= 36 and g >= r*.84 and g >= b*1.12
        if material == 'hair':
            return 35 <= r < 125 and g < 80 and g < r*.78
        if material == 'skin':
            return r > 110 and r > g*1.25 and g > b*1.2
        if material == 'book':
            return r < 160 and g < 110
        return True

    if not valid(pixel):
        # Use the nearest actual pixel of the requested clerk material where
        # the reference patch contains a hand, face, ledger or transparent air.
        candidates = ((px, py) for py in range(top, bottom) for px in range(left, right)
                      if valid(reference.getpixel((px, py))))
        px, py = min(candidates, key=lambda p: (p[0]-x)**2+(p[1]-y)**2)
        pixel = reference.getpixel((px, py))
    return pixel


def textured_polygon(reference, points, material, size=SIZE, outline=True):
    result = blank(size)
    points = [(round(x), round(y)) for x, y in points]
    mask = Image.new('L', size)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    left, top, right, bottom = mask.getbbox()
    pixels, alpha = result.load(), mask.load()
    for y in range(top, bottom):
        for x in range(left, right):
            if alpha[x, y]:
                pixels[x, y] = material_pixel(reference, material,
                    (x-left)/max(1, right-left-1), (y-top)/max(1, bottom-top-1))
    if outline:
        # A retained dark garment/boot edge, not a new black cartoon outline.
        edge = reference.getpixel((54, 48) if material in ('moss', 'sleeve') else (38, 90))
        ImageDraw.Draw(result).line(points+[points[0]], fill=edge, width=1)
    return result


def segment(reference, a, b, widths, material):
    """Paint the actual joint-to-joint native silhouette with clerk materials."""
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    nx, ny = dy/length, -dx/length
    wa, wb = widths
    points = ((a[0]+nx*wa, a[1]+ny*wa), (b[0]+nx*wb, b[1]+ny*wb),
              (b[0]-nx*wb, b[1]-ny*wb), (a[0]-nx*wa, a[1]-ny*wa))
    result = textured_polygon(reference, points, material)
    draw = ImageDraw.Draw(result)
    draw.ellipse((round(b[0]-wb+1), round(b[1]-wb+1),
                  round(b[0]+wb-1), round(b[1]+wb-1)),
                 fill=material_pixel(reference, material, .45, .8))
    return result


def parts(reference):
    result = {name: polygon_part(reference, points) for name, points in MASKS.items()}
    # The free hand originally covers a tiny part of the hem. Reconstruct only
    # that cloth; neither the reference nor its old runtime PNG is repainted.
    for name in ('front_coat', 'back_coat'):
        image = result[name]
        for y in range(53, 63):
            for x in range(27, 56):
                p = image.getpixel((x, y))
                if p[3] and p[0] > p[1]*1.3 and p[0] > 80:
                    image.putpixel((x, y), material_pixel(reference, 'moss', (x-29)/26, (y-53)/10))
    # The closed cover continues underneath the retained fingers. Author that
    # hidden contact surface explicitly, so the auditable book layer contains
    # book material, not a second hand pasted into the prop.
    for y in range(48, 62):
        for x in range(43, 52):
            p = result['ledger'].getpixel((x, y))
            if p[3] and p[0] > 160:
                result['ledger'].putpixel((x, y), material_pixel(reference, 'book', (x-43)/9, (y-48)/14))
    return result


def reconstructed_body(reference, view):
    """Explicit clerk back silhouettes; no borrowed Aldric head, coat or strap."""
    quarter = view == 'quarter'
    if quarter:
        torso_points = ((36, 29), (42, 28), (47, 31), (49, 37),
                         (47, 52), (34, 52), (33, 36))
        coat_points = ((34, 49), (47, 49), (49, 60), (52, 72),
                       (43, 74), (39, 68), (36, 74), (30, 71), (32, 59))
        head_points = ((35, 15), (41, 15), (45, 17), (47, 21),
                       (46, 26), (43, 29), (37, 29), (34, 26),
                       (32, 24), (32, 19))
    else:
        torso_points = ((35, 29), (44, 29), (49, 33), (49, 39),
                         (47, 52), (32, 52), (30, 36), (32, 32))
        coat_points = ((32, 49), (47, 49), (49, 60), (51, 72),
                       (42, 74), (40, 68), (38, 74), (29, 72), (31, 59))
        head_points = ((35, 15), (42, 15), (46, 18), (47, 23),
                       (45, 27), (43, 29), (35, 28), (32, 24),
                       (32, 20), (33, 17))
    torso = textured_polygon(reference, torso_points, 'moss')
    coat = textured_polygon(reference, coat_points, 'moss')
    head = textured_polygon(reference, head_points, 'hair', outline=False)
    skin = reference.getpixel((38, 25))
    hair_dark = reference.getpixel((44, 20))
    hair_light = reference.getpixel((40, 17))
    collar = reference.getpixel((39, 28))
    draw = ImageDraw.Draw(head)
    draw.line(((37, 16), (35, 17)), fill=hair_light)
    draw.line(((43, 18), (44, 20)), fill=hair_dark)
    draw.line(((36, 26), (39, 28), (43, 27)), fill=hair_dark)
    if quarter:
        draw.rectangle((33, 23, 35, 25), fill=skin)
        draw.point((34, 24), fill=reference.getpixel((36, 24)))
    # Narrow nape and cream collar. Never paint a face on the direct back.
    draw.line(((38, 28), (42, 28)), fill=skin)
    td = ImageDraw.Draw(torso)
    td.line(((35, 30), (39, 32), (44, 30)), fill=collar)
    td.line(((33, 35), (40, 37), (47, 35)), fill=reference.getpixel((43, 68)))
    td.line(((40, 37), (40, 49)), fill=reference.getpixel((54, 46)))
    td.line(((33, 50), (46, 50)), fill=reference.getpixel((38, 50)), width=2)
    cd = ImageDraw.Draw(coat)
    cd.line(((40, 53), (40, 65), (38, 72)), fill=reference.getpixel((34, 62)))
    cd.line(((43, 58), (46, 69)), fill=reference.getpixel((48, 67)))
    cd.line(((33, 71), (36, 72)), fill=reference.getpixel((51, 72)))
    return {'head': head, 'torso': torso, 'coat': coat}


def foot_pose(reference, layers, phase, view, idle=False):
    yaw = VIEWS[view]
    if view == 'side':
        source = layers['boot']
        root = (38, 85)
    else:
        points = (((37, 82), (42, 82), (43, 90), (41, 91),
                   (34, 91), (33, 89), (36, 87)) if view == 'quarter' else
                  ((37, 82), (42, 82), (43, 90), (42, 91),
                   (36, 91), (36, 86)))
        source = textured_polygon(reference, points, 'leather')
        root = (40, 87 if idle else 85)
    angle = math.radians(0 if idle else FOOT_ANGLE[phase])
    x = 40 if idle else 40+FOOT_X[phase]
    image = rigid(source, root, (root[0], root[1]+1), (x, 85),
                  (x+math.sin(angle), 85+math.cos(angle)))
    floor = 92 if idle else FOOT_FLOOR[phase]
    dy = floor-image.getbbox()[3]
    image = translated(image, y=dy)
    # Leg IK is solved before yaw. Project the whole shoe about its ankle;
    # this registration, not a foot-pixel centroid, is the animated root.
    ankle = (x, 85.+dy)
    return image, ankle, yaw


def projected_boot(image, ankle, target, yaw):
    # Rear footprints were authored as rear silhouettes above. Only translate
    # those native cells into their projected joint registration here.
    return translated(image, round(target[0]-ankle[0]), round(target[1]-ankle[1]))


def free_arm(reference, layers, index, bob, yaw, idle=False):
    angle = 0. if idle else ARM_SWING[index]
    shoulder = (33., 33.+bob)
    upper, lower = FREE_ARM_LENGTHS
    elbow = (shoulder[0]+math.sin(angle)*upper,
             shoulder[1]+math.cos(angle)*upper)
    wrist = (elbow[0]+math.sin(angle-.14)*lower,
             elbow[1]+math.cos(angle-.14)*lower)
    anatomical = dict(shoulder=shoulder, elbow=elbow, wrist=wrist)
    screen = {key: project(point, yaw, 9.) for key, point in anatomical.items()}
    if yaw == 0:
        upper_image = rigid(layers['free_upper'], (33, 33), (32, 45), screen['shoulder'], screen['elbow'])
        forearm = rigid(layers['free_forearm'], (32, 45), (30, 55), screen['elbow'], screen['wrist'])
        hand = rigid(layers['free_hand'], (30, 55), (30, 56), screen['wrist'],
                     (screen['wrist'][0]+math.sin(angle-.14),
                      screen['wrist'][1]+math.cos(angle-.14)))
    else:
        upper_image = segment(reference, screen['shoulder'], screen['elbow'], (2.4, 2.0), 'sleeve')
        forearm = segment(reference, screen['elbow'], screen['wrist'], (2.0, 1.7), 'sleeve')
        wx, wy = screen['wrist']
        hand = textured_polygon(reference, ((wx-1, wy), (wx+1, wy),
                    (wx+2, wy+3), (wx, wy+5), (wx-1, wy+3)),
                    'skin', outline=False)
    return {'free_upper': upper_image, 'free_forearm': forearm, 'free_hand': hand}, {
        'anatomical': anatomical, 'screen': screen, 'hand': 'right', 'role': 'free'}


def held_arm(reference, layers, bob, yaw):
    anatomical = {'shoulder': (48., 33.+bob), 'elbow': (51., 45.+bob),
                  'wrist': (51., 56.+bob), 'grip': (51., 57.+bob)}
    screen = {key: project(point, yaw, -9.) for key, point in anatomical.items()}
    if yaw == 0:
        drawing = {key: translated(layers[key], y=bob)
                   for key in ('ledger_arm', 'ledger', 'ledger_hand')}
    else:
        sleeve = segment(reference, screen['shoulder'], screen['elbow'], (2.9, 2.2), 'sleeve')
        sleeve.alpha_composite(segment(reference, screen['elbow'], screen['wrist'], (2.2, 1.8), 'sleeve'))
        gx, gy = screen['grip']
        ledger = textured_polygon(reference, ((gx-7, gy-10), (gx-1, gy-12),
                         (gx+1, gy+2), (gx-6, gy+2)), 'book')
        ld = ImageDraw.Draw(ledger)
        ld.line(((round(gx-1), round(gy-10)), (round(gx), round(gy+1))),
                fill=reference.getpixel((48, 53)))
        ld.line(((round(gx-6), round(gy-8)), (round(gx-5), round(gy+1))),
                fill=reference.getpixel((44, 50)))
        hand = textured_polygon(reference, ((gx-1, gy-2), (gx+1, gy-2),
                  (gx+2, gy), (gx+1, gy+2), (gx-1, gy+3), (gx-2, gy+1)),
                  'skin', outline=False)
        drawing = {'ledger_arm': sleeve, 'ledger': ledger, 'ledger_hand': hand}
    return drawing, {'anatomical': anatomical, 'screen': screen, 'hand': 'left',
                     'role': 'ledger', 'attachment': 'grip remains inside book and hand alpha'}


def coat_pose(layers, index, bob, view):
    source = layers['coat'] if view != 'side' else blank()
    if view == 'side':
        source.alpha_composite(layers['front_coat'])
        source.alpha_composite(layers['back_coat'])
    result = blank()
    sway = (0, 0, 1, 1, 0, 0, -1, -1)[index]
    for y in range(48, 76):
        result.alpha_composite(source.crop((0, y, 80, y+1)),
                               (sway if y >= 63 else 0, y+bob))
    return result


def authored_frame(reference, source_parts, index, view='side', idle=False):
    yaw = VIEWS[view]
    bob = 0 if idle else BOB[index]
    layers = source_parts if view == 'side' else {**source_parts, **reconstructed_body(reference, view)}
    drawing, records = {}, {}
    for near in (False, True):
        key = 'near' if near else 'far'
        phase = index if near else (index+4)%8
        shoe, ankle, _ = foot_pose(reference, layers, phase, view, idle)
        hip = (41. if near else 39., 55.+bob)
        knee = two_bone(hip, ankle, LEG_LENGTHS)
        anatomical = dict(hip=hip, knee=knee, ankle=ankle)
        screen = {name: project(point, yaw, -4. if near else 4.)
                  for name, point in anatomical.items()}
        if idle:
            # Static feet have no sagittal stride/depth offset: both soles
            # share the native standing floor, matching the retained 77px body.
            screen = {name: (point[0], anatomical[name][1]) for name, point in screen.items()}
        shoe = projected_boot(shoe, ankle, screen['ankle'], yaw)
        drawing[key+'_thigh'] = segment(reference, screen['hip'], screen['knee'], (2.9, 2.3), 'trousers')
        drawing[key+'_shin'] = segment(reference, screen['knee'], screen['ankle'], (2.3, 2.0), 'leather')
        drawing[key+'_boot'] = shoe
        records[key+'_leg'] = {'handed_side': 'left' if near else 'right',
            'anatomical': anatomical, 'screen': screen, 'planted': idle or phase <= 4,
            'foot_bounds': list(shoe.getbbox())}
    arm, records['free_arm'] = free_arm(reference, layers, index, bob, yaw, idle)
    drawing.update(arm)
    arm, records['ledger_arm'] = held_arm(reference, layers, bob, yaw)
    drawing.update(arm)
    drawing.update(coat=coat_pose(layers, 0 if idle else index, bob, view),
                   torso=translated(layers['torso'], y=bob), head=translated(layers['head'], y=bob))
    image = blank()
    # In a rear view both hands lie beside the back silhouette, so their small
    # visible ends must not disappear beneath the coat. The ledger stays left.
    order = LAYER_ORDER if view == 'side' else tuple(
        key for key in LAYER_ORDER if not key.startswith('free_'))+('free_upper', 'free_forearm', 'free_hand')
    for key in order:
        image.alpha_composite(drawing[key])
    filename = (f'walk_{index}.png' if view == 'side' else
                f'walk_left_back_{index}.png' if view == 'quarter' else f'walk_back_{index}.png')
    return image, {'file': filename, 'phase': 'idle' if idle else PHASES[index], 'duration_ms': 125,
        'body_offset': [0, bob], 'yaw_radians': yaw, 'layer_order': list(order), **records}, drawing


def aerial_pose(reference, oblique=False):
    """Native 48x64 high-camera silhouette, not a scaled upright/chibi body."""
    size = (48, 64)
    result = blank(size)
    if oblique:
        coat_points = ((20, 23), (27, 22), (31, 26), (30, 34), (32, 45),
                       (25, 46), (23, 43), (20, 46), (17, 44), (18, 34), (17, 28))
        head_points = ((21, 12), (26, 11), (30, 14), (30, 18),
                       (27, 22), (22, 22), (19, 19), (19, 15))
        boots = (((20, 43), (23, 43), (23, 54), (21, 55), (18, 55), (19, 51)),
                 ((26, 43), (29, 43), (30, 54), (29, 55), (26, 55)))
        book_points = ((14, 34), (18, 33), (20, 43), (15, 44))
        hands = ((18, 40, 20, 43), (30, 36, 32, 39))
        collar_line, belt, seam = ((20, 23), (24, 25), (28, 23)), 34, 37
    else:
        coat_points = ((18, 36), (22, 33), (27, 33), (31, 36),
                       (30, 42), (29, 49), (25, 50), (24, 48), (19, 49), (17, 42))
        head_points = ((21, 28), (26, 27), (29, 30), (29, 34),
                       (26, 37), (21, 37), (18, 34), (18, 31))
        boots = (((20, 47), (23, 47), (23, 54), (22, 55), (19, 55)),
                 ((26, 47), (29, 47), (29, 55), (26, 55)))
        book_points = ((13, 42), (17, 41), (19, 50), (14, 51))
        hands = ((17, 46, 19, 49), (30, 42, 32, 44))
        collar_line, belt, seam = ((19, 36), (24, 38), (29, 36)), 44, 46
    for points in boots:
        result.alpha_composite(textured_polygon(reference, points, 'leather', size))
    result.alpha_composite(textured_polygon(reference, coat_points, 'moss', size))
    draw = ImageDraw.Draw(result)
    draw.line(collar_line, fill=reference.getpixel((39, 28)))
    draw.line(((19, belt), (29, belt)), fill=reference.getpixel((38, 50)))
    draw.line(((24, seam), (24, 47 if oblique else 49)), fill=reference.getpixel((34, 62)))
    result.alpha_composite(textured_polygon(reference, book_points, 'book', size))
    for rectangle in hands:
        left, top, right, bottom = rectangle
        result.alpha_composite(textured_polygon(reference,
            ((left, top), (right-1, top), (right, bottom-1),
             (right-1, bottom), (left, bottom)), 'skin', size, outline=False))
    result.alpha_composite(textured_polygon(reference, head_points, 'hair', size, outline=False))
    draw = ImageDraw.Draw(result)
    x, y = (22, 13) if oblique else (22, 29)
    draw.line(((x, y), (x-2, y+2), (x-2, y+4)), fill=reference.getpixel((38, 16)))
    draw.line(((x+4, y+1), (x+5, y+4), (x+3, y+7)), fill=reference.getpixel((44, 20)))
    if oblique:
        draw.point((20, 20), fill=reference.getpixel((38, 25)))
    return result


def protected_inputs():
    path = OUT/'protected_originals.json'
    if path.exists():
        return json.loads(path.read_text())
    # Capture trusted, already-verified export hashes BEFORE adding new clerk
    # cells. Subsequent rebuilds use this immutable snapshot, not new manifests.
    protected = {}
    for story in ('regent_arrival', 'regent_aerial'):
        directory = ROOT/'assets/story'/story/'actors'
        provenance = json.loads((directory/'provenance.json').read_text())
        for name, sha in provenance['exports'].items():
            if name.endswith('.png'):
                protected[(directory/name).relative_to(ROOT).as_posix()] = sha
    for directory in (SOURCE, ROOT/'assets/source/cinematics/regent_aerial/actors'):
        for source in directory.glob('*_generated.png'):
            protected[source.relative_to(ROOT).as_posix()] = digest(source.read_bytes())
    # Protect Aldric's art, not his metadata: the parent must separately allow
    # this newly authored clerk in Aldric's older non-side-asset hash guard.
    for source in sorted((SOURCE/'aldric_side_walk').rglob('*.png')):
        if source.is_file():
            protected[source.relative_to(ROOT).as_posix()] = digest(source.read_bytes())
    return dict(sorted(protected.items()))


def strip(images):
    images = tuple(images)
    width, height = images[0].size
    result = blank((width*len(images), height))
    for i, image in enumerate(images):
        result.alpha_composite(image, (i*width, 0))
    return result


def review_frames(frames):
    board = Image.new('RGB', (8*166, 3*220), '#27342e')
    draw = ImageDraw.Draw(board)
    for row, (view, images) in enumerate(frames.items()):
        for i, image in enumerate(images):
            large = image.resize((160, 192), Image.Resampling.NEAREST)
            board.paste(large, (i*166+3, row*220+5), large)
            draw.text((i*166+4, row*220+199), f'{view} / {PHASES[i]}', fill='#efdec4')
    return board


def review_gif(frames):
    previews = []
    for index in range(8):
        board = Image.new('RGB', (720, 305), '#27342e')
        draw = ImageDraw.Draw(board)
        for column, (view, images) in enumerate(frames.items()):
            image = images[index].resize((240, 288), Image.Resampling.NEAREST)
            board.paste(image, (column*240, 0), image)
            draw.text((column*240+10, 290), f'{view}: {PHASES[index]}', fill='#efdec4')
        previews.append(board)
    stream = io.BytesIO()
    previews[0].save(stream, format='GIF', save_all=True, append_images=previews[1:],
                    duration=[120, 130]*4, loop=0, disposal=2, optimize=False)
    return stream.getvalue()


def build():
    reference, reading = references()
    protected = protected_inputs()
    for name, sha in protected.items():
        if digest((ROOT/name).read_bytes()) != sha:
            raise ValueError('Protected original actor asset changed: '+name)
    source_parts = parts(reference)
    outputs = {OUT/'protected_originals.json': json_bytes(protected),
               OUT/'reference.png': encoded(reference), OUT/'parts.png': encoded(strip(source_parts.values())),
               OUT/'parts.json': json_bytes({'canvas': list(SIZE), 'parts': list(source_parts),
                    'masks': MASKS, 'material_bounds': MATERIALS,
                    'notes': 'Clerk-specific retained pixel masks; hand-occluded hem cloth and ledger cover reconstructed.'})}
    frames, loops = {}, {}
    for loop, view in LOOPS.items():
        authored = [authored_frame(reference, source_parts, i, view) for i in range(8)]
        images = [item[0] for item in authored]
        frames[view] = images
        outputs[OUT/(view+'_walk.png')] = encoded(strip(images))
        layer_paths = {}
        for layer in LAYER_ORDER:
            name = f'{view}_layers/{layer}.png'
            outputs[OUT/name] = encoded(strip(item[2][layer] for item in authored))
            layer_paths[layer] = name
        loops[loop] = {'view': view, 'sheet': view+'_walk.png', 'stride_pixels': STRIDE,
                       'layers': layer_paths, 'frames': [item[1] for item in authored]}
    poses = {}
    for pose, view in (('turn_left_back', 'quarter'), ('stand_back', 'back')):
        image, record, _ = authored_frame(reference, source_parts, 0, view, idle=True)
        outputs[OUT/(pose+'.png')] = encoded(image)
        poses[pose] = {'file': pose+'.png', 'view': view, 'joints': record}
    poses['stand_left_back'] = poses['turn_left_back']
    aerial = {}
    for pose, oblique in (('overhead', False), ('oblique', True)):
        image = aerial_pose(reference, oblique)
        name = 'aerial_'+pose+'.png'
        outputs[OUT/name] = encoded(image)
        aerial[pose] = {'file': name, 'canvas': [48, 64], 'anchor': [24, 56],
                        'facing': 'northwest' if oblique else 'north'}
    metadata = {'version': 1, 'canvas': list(SIZE), 'anchor': list(ANCHOR),
        'reference_height': 77, 'authoring': 'offline native part-authored; no imagegen tool used',
        'authoring_tool': 'tools/build_regent_clerk_walk.py',
        'authoring_tool_sha256': digest(Path(__file__).read_bytes()),
        'appearance_source': (SOURCE/'travelers_generated.png').relative_to(ROOT).as_posix(),
        'appearance_source_sha256': digest((SOURCE/'travelers_generated.png').read_bytes()),
        'reference_pixels_sha256': digest(reference.tobytes()),
        'reading_pixels_sha256': digest(reading.tobytes()),
        'registration': 'fixed [40,92] ground root; no per-frame crop, rescale or foot recentering',
        'limb_lengths': {'leg': LEG_LENGTHS, 'free_arm': FREE_ARM_LENGTHS, 'ledger_arm': HELD_ARM_LENGTHS},
        'projection': 'x=40+cos(yaw)*(x-40)+sin(yaw)*lane; y=y+sin(yaw)*((x-40)*0.22-1.65); idle legs keep native y',
        'ledger_ownership': 'anatomical left hand / left hip; near in profile, left in back/overhead',
        'reconstruction': 'New rear hair/nape, moss coat yoke/vent, rear boots and foreshortened aerial silhouettes; retained clerk materials only.',
        'loops': loops, 'poses': poses, 'aerial': aerial,
        'protected_originals': 'protected_originals.json'}
    outputs[OUT/'clerk_walk.json'] = json_bytes(metadata)
    outputs[REVIEW/'clerk_reference.png'] = encoded(reference_board())
    outputs[REVIEW/'clerk_frames.png'] = encoded(review_frames(frames))
    outputs[REVIEW/'clerk_walk.gif'] = review_gif(frames)
    turns = [reference, frames['side'][2]]+[Image.open(io.BytesIO(outputs[OUT/(pose+'.png')])).convert('RGBA')
                                                for pose in ('turn_left_back', 'stand_back')]
    board = Image.new('RGB', (4*240, 310), '#27342e')
    for i, (image, label) in enumerate(zip(turns, ('Retained idle', 'Native side / passing',
                                                   'Turn / rear quarter', 'Static back'))):
        large = image.resize((240, 288), Image.Resampling.NEAREST)
        board.paste(large, (i*240, 0), large)
        ImageDraw.Draw(board).text((i*240+8, 291), label, fill='#efdec4')
    outputs[REVIEW/'clerk_turns.png'] = encoded(board)
    board = Image.new('RGB', (740, 285), '#27342e')
    for i, (pose, record) in enumerate(aerial.items()):
        image = Image.open(io.BytesIO(outputs[OUT/record['file']])).convert('RGBA')
        board.paste(image, (i*260+10, 185), image)
        large = image.resize((192, 256), Image.Resampling.NEAREST)
        board.paste(large, (i*260+65, 0), large)
        ImageDraw.Draw(board).text((i*260+7, 266), 'Native 1x / '+pose+' 4x', fill='#efdec4')
        # Existing aerial adults are read-only scale/style comparisons, not
        # appearance parts. The clerk silhouette above is authored at 1x.
        comparison = ROOT/'assets/story/regent_aerial/actors/aldric'/(pose+'.png')
        with Image.open(comparison) as original:
            original = original.convert('RGBA')
            board.paste(original, (535+i*95, 95), original)
    draw = ImageDraw.Draw(board)
    draw.text((530, 55), 'Existing Aldric / scale only', fill='#efdec4')
    draw.text((535, 165), 'overhead', fill='#efdec4')
    draw.text((630, 165), 'oblique', fill='#efdec4')
    outputs[REVIEW/'clerk_aerial.png'] = encoded(board)
    return outputs


def reference_board():
    board = Image.new('RGB', (840, 535), '#27342e')
    draw = ImageDraw.Draw(board)
    for column, (label, image) in enumerate(zip(('Retained stand / coordinates',
                                                'Retained read (unchanged)'), references())):
        x0, y0 = column*420+15, 25
        large = image.resize((400, 480), Image.Resampling.NEAREST)
        board.paste(large, (x0, y0), large)
        draw.text((x0, 6), label, fill='#efdec4')
        if column == 0:
            for x in range(20, 61, 5):
                draw.line((x0+x*5, y0, x0+x*5, y0+480), fill='#546154')
                draw.text((x0+x*5, 510), str(x), fill='#efdec4')
            for y in range(10, 96, 5):
                draw.line((x0+115, y0+y*5, x0+285, y0+y*5), fill='#546154')
                draw.text((x0+290, y0+y*5), str(y), fill='#efdec4')
    return board


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--reference-only', action='store_true')
    args = parser.parse_args()
    outputs = ({REVIEW/'clerk_reference.png': encoded(reference_board())}
               if args.reference_only else build())
    write_outputs(outputs, check=args.check)
    print(('Verified' if args.check else 'Authored')+
          f' {len(outputs)} native clerk sources/reviews (originals preserved)')


def write_outputs(outputs, check=False):
    for path, content in outputs.items():
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise SystemExit('Clerk authoring output differs: '+str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


if __name__ == '__main__':
    main()