"""Export complete left-run drawings with approved runtime metadata; selection remains in the registry."""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_mira_combat import _main_component
from tools.caelan_outline import apply_outline

SOURCE = ROOT / 'assets/source/characters/caelan/run_left_hd_review'
OUT = ROOT / 'assets/characters/caelan/review_hd/run_left'
REVIEW = ROOT / 'docs/reviews/caelan_left_run_hd'
SCALE = .12
# Whole-body crown/neck/belt registration; no foot-height normalization.
VERTICAL = [5, 5, 3, 3, 5, 4, 4, 5, 5, 5, 4, 4, 5, 4, 4, 5]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    for path, expected in json.loads((SOURCE / 'protected_references.json').read_text()).items():
        assert digest(ROOT / path) == expected, path
    protected_frames = json.loads((SOURCE / 'revision_2/protected_frames.json').read_text())
    for filename, expected in protected_frames.items():
        assert digest(SOURCE / 'revision_2/before' / filename) == expected, filename
    palette_path = ROOT / 'assets/source/characters/caelan/walk_right_hd_review/palette.json'
    palette = Image.new('P', (1, 1))
    colors = json.loads(palette_path.read_text())['rgb']
    palette.putpalette(colors + [0] * (768 - len(colors)))
    frames, records, hashes = [], [], {}
    # Left arm/leg are near; right arm/leg are far throughout this view.
    # Reflected guides are shifted eight poses to retain right-first contact.
    phases = ['contact', 'compression', 'support', 'late_support', 'toe_off',
              'flight', 'descending_flight', 'touchdown'] * 2
    support = ['right', 'right', 'right', 'right', 'right_toe', None, None, 'left',
               'left', 'left', 'left', 'left', 'left_toe', None, None, 'right']
    for batch in 'ABCD':
        path = SOURCE / f'{batch}.png'
        hashes[path.name] = digest(path)
        hashes[f'guide_{batch}.png'] = digest(SOURCE / f'guide_{batch}.png')
        atlas = Image.open(path).convert('RGBA')
        w, h = atlas.width // 2, atlas.height // 2
        for cell in range(4):
            rect = (cell % 2*w, cell // 2*h, (cell % 2+1)*w, (cell // 2+1)*h)
            source_name = path.name
            repair_cell = {0: 0, 1: 1, 8: 2, 9: 3}.get(len(frames))
            if repair_cell is not None:
                source_name = 'revision_2/folded_leg_correction.png'
                repair_path = SOURCE / source_name
                hashes[source_name] = digest(repair_path)
                repaired = Image.open(repair_path).convert('RGBA')
                w, h = repaired.width // 2, repaired.height // 2
                rect = (repair_cell % 2*w, repair_cell // 2*h,
                        (repair_cell % 2+1)*w, (repair_cell // 2+1)*h)
                drawing = _main_component(repaired.crop(rect))
            else:
                drawing = _main_component(atlas.crop(rect))
            bounds = drawing.getbbox()
            head = drawing.crop((0, 0, w, 190)).getbbox()
            center = (head[0] + head[2]) / 2
            # One uniform sampling density, translation from cranial center.
            # Registration uses head/neck/belt landmarks, never boot height.
            origin = (round(28 + (bounds[0]-center)*SCALE), round(VERTICAL[len(frames)]+bounds[1]*SCALE))
            size = (round((bounds[2]-bounds[0])*SCALE), round((bounds[3]-bounds[1])*SCALE))
            assert origin[0] > 0 and origin[1] > 0
            assert origin[0]+size[0] < 56 and origin[1]+size[1] < 76
            frame = Image.new('RGBA', (56, 76))
            frame.alpha_composite(drawing.crop(bounds).resize(size, Image.Resampling.NEAREST), origin)
            alpha = frame.getchannel('A')
            frame = frame.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE).convert('RGBA')
            frame.putalpha(alpha)
            frame = apply_outline(frame)
            index = len(frames)
            filename = f'frame_{index+1:02}.png'
            if repair_cell is not None:
                # Restore the exact same phase's upper artwork after a complete
                # generated redraw. No limb rotations, offsets or phase mixing.
                preserved = Image.open(SOURCE / 'revision_2/before' / filename).convert('RGBA')
                frame.paste(preserved.crop((0, 0, 56, 48)), (0, 0))
                assert frame.crop((0, 0, 56, 48)).tobytes() == preserved.crop((0, 0, 56, 48)).tobytes()
            support_span = None
            if support[index] is not None:
                sole_y = frame.getbbox()[3] - 1
                sole_x = [x for x in range(56) if frame.getpixel((x, sole_y))[3]]
                # On these audited support poses the opposite boot is raised.
                # This measures the visible sole, never positions/scales the art.
                support_span = [min(sole_x), sole_y, max(sole_x)]
            frame.save(OUT / filename)
            if repair_cell is None:
                assert digest(OUT / filename) == protected_frames[filename], filename
            frames.append(frame)
            records.append(dict(file=filename, duration_ms=25, source=source_name,
                cell=list(rect), alpha_cutoff=128, source_bounds=list(bounds), source_head_bounds=list(head),
                uniform_scale=SCALE, origin=list(origin), sampled_size=list(size),
                phase=phases[index], support_leg=support[index],
                support_ground_interval=support_span,
                vertical_registration_offset=VERTICAL[index],
                source_neck_reference_y=205, source_belt_reference_y=310,
                reflected_motion_guide=f'guide_{batch}.png', guide_cell=cell,
                approved_right_reference_frame=(index+8)%16+1,
                repair_window=([0, 48, 56, 76] if repair_cell is not None else None),
                preserved_upper_sha256=(hashlib.sha256(preserved.crop((0, 0, 56, 48)).tobytes()).hexdigest()
                    if repair_cell is not None else None),
                head_crown_y=frame.crop((0, 0, 56, 24)).getbbox()[1]))
    sheet = Image.new('RGBA', (56*16, 76))
    for i, frame in enumerate(frames):
        sheet.alpha_composite(frame, (i*56, 0))
    sheet.save(OUT / 'spritesheet.png')
    manifest = dict(version=1, character='caelan', animation='run.left', status='approved',
        design_status='approved', artwork_status='approved', runtime_integration=True,
        artwork_pixels_per_world_pixel=2, frame_size=[56, 76], logical_size=[28, 38],
        draw_anchor=[28, 64], foot_anchor=[28, 72], cycle_ms=400, loop=True,
        source_hashes=hashes, palette_sha256=digest(palette_path), frames=records,
        revision=2,
        processing='Complete generated drawings; uniform nearest sampling, cranial horizontal registration, recorded whole-body vertical registration, shared palette and contour. Frames1/2/9/10 retain exact same-phase upper rows0:48 after full-pose leg redraw. No limb transforms.')
    (OUT / 'animation.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (SOURCE / 'registration.json').write_text(json.dumps(manifest, indent=2)+'\n')
    idle = Image.open(ROOT / 'assets/characters/caelan/review_hd/idles/idle_left.png').convert('RGBA')
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    board = Image.new('RGB', (992, 1368), '#303940')
    d = ImageDraw.Draw(board)
    d.text((16, 12), 'CAELAN | LEFT RUN | 16 COMPLETE DRAWN POSES', font=font, fill='#edf0e9')
    for i, frame in enumerate(frames):
        x, y = 12+i%4*248, 44+i//4*328
        big = frame.resize((224, 304), Image.Resampling.NEAREST)
        board.paste(big, (x, y), big)
        d.text((x, y+304), f'{i+1:02}  {records[i]["phase"]}', font=small, fill='#d4dbdf')
    board.save(REVIEW / 'frames.png')
    board.save(REVIEW / 'frames_v2.png')
    preview = []
    for tick in range(32):
        im = Image.new('RGB', (800, 490), '#303940')
        d = ImageDraw.Draw(im)
        for phase, x, label in ((tick%16, 16, 'Normal | 400 ms cycle'),
                                 ((tick//2)%16, 280, 'Half speed'), (None, 552, 'Approved idle')):
            frame = idle if phase is None else frames[phase]
            d.text((x, 12), label, font=font, fill='#edf0e9')
            d.line((x+8, 332, x+222, 332), fill='#58646c')
            big = frame.resize((frame.width*4, frame.height*4), Image.Resampling.NEAREST)
            im.paste(big, (x+16 if phase is None else x, 48 if phase is None else 32), big)
            im.paste(frame, (x+88 if phase is None else x+84, 400 if phase is None else 396), frame)
            if phase is not None:
                d.text((x+20, 350), f'Frame {phase+1:02} / 16', font=small, fill='#d4dbdf')
        d.text((16, 378), 'Bottom row: native artwork size in the 2x viewport', font=small, fill='#b9c8ce')
        preview.append(im)
    packed = Image.new('RGB', (800*8, 490*4))
    for i, im in enumerate(preview):
        packed.paste(im, (i%8*800, i//8*490))
    gif_palette = packed.quantize(colors=256, dither=Image.Dither.NONE)
    gif_frames = [im.quantize(palette=gif_palette, dither=Image.Dither.NONE) for im in preview]
    gif_frames[0].save(REVIEW / 'preview.gif', save_all=True, append_images=gif_frames[1:],
        duration=[20, 30]*16, loop=0, disposal=2, optimize=False)
    (REVIEW / 'preview_v2.gif').write_bytes((REVIEW / 'preview.gif').read_bytes())
    comparison = Image.new('RGB', (720, 760), '#303940')
    cd = ImageDraw.Draw(comparison)
    cd.text((16, 12), 'FOLDED LEG REPAIR | Previous / Revised | Same movement phase', font=font, fill='#edf0e9')
    for row, index in enumerate((0, 1, 8, 9)):
        old = Image.open(SOURCE / 'revision_2/before' / f'frame_{index+1:02}.png').convert('RGBA')
        for column, frame in enumerate((old, frames[index])):
            x, y = 100+column*340, 48+row*176
            lower = frame.crop((0, 40, 56, 76)).resize((224, 144), Image.Resampling.NEAREST)
            comparison.paste(lower, (x, y), lower)
            cd.text((x, y+144), f'Frame {index+1:02} | {"Previous" if column == 0 else "Revised"}', font=small, fill='#d4dbdf')
    comparison.save(REVIEW / 'folded_leg_comparison_v2.png')
    print('Exported left-run bank: 16 frames / 400ms; integrated registry retained.')


if __name__ == '__main__':
    build()
