"""Capture production playback and targeted continuity comparisons.

Filmstrips and posters are decoded from the delivered MP4, so they show the
actual review video rather than a different rendering path. The path diagnostic
is explicitly a review overlay and never enters the game renderer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

from PIL import Image, ImageDraw, ImageFont

import capture_ice_reaper_opening as production

OUTPUT = ROOT/'docs/reviews/ice_reaper_continuity'
PREVIOUS = ROOT/'docs/reviews/ice_reaper_rescue'
STRIPS = {
    'rescue_filmstrip': (7.3, 8., 8.5, 8.9, 9., 9.2),
    'orbit_filmstrip': (9.5, 9.8, 10.1, 10.4, 10.7, 11.),
    'panorama_filmstrip': (17.2, 17.8, 18.4, 19., 19.6),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size=18):
    path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def video_frames(video, times, fps):
    """Decode exact numbered frames in one FFmpeg pass."""
    indices = sorted({round(time*fps) for time in times})
    expression = '+'.join(f'eq(n\\,{index})' for index in indices)
    with tempfile.TemporaryDirectory(prefix='ice-continuity-frames-') as folder:
        subprocess.run([
            'ffmpeg', '-y', '-v', 'error', '-i', str(video), '-vf',
            f'select={expression}', '-fps_mode', 'vfr',
            str(Path(folder)/'%04d.png'),
        ], check=True)
        files = sorted(Path(folder).glob('*.png'))
        if len(files) != len(indices):
            raise AssertionError('FFmpeg did not decode every requested review frame')
        return {index: Image.open(path).convert('RGB').copy()
                for index, path in zip(indices, files)}


def filmstrip(frames, times, fps, output, title):
    width, height = 480, 320
    rows = math.ceil(len(times)/3)
    sheet = Image.new('RGB', (width*3, 38+rows*(height+28)), '#142331')
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 8), title, font=font(20), fill='#f5e7c2')
    for number, time in enumerate(times):
        x, y = number%3*width, 38+number//3*(height+28)
        image = frames[round(time*fps)].resize((width, height), Image.Resampling.NEAREST)
        sheet.paste(image, (x, y+28))
        draw.text((x+9, y+4), f'{time:.2f} seconds', font=font(16), fill='#e4edf2')
    sheet.save(output, optimize=True)


def before_after(previous, current, output):
    sheet = Image.new('RGB', (960, 358), '#142331')
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate((('Previous: 8.6 seconds', previous),
                                            ('Updated: 8.6 seconds', current))):
        x = index*480
        draw.text((x+10, 9), label, font=font(), fill='#f5e7c2')
        sheet.paste(image.resize((480, 320), Image.Resampling.NEAREST), (x, 38))
    sheet.save(output, optimize=True)


def verify_opening(output):
    results = []
    for name in ('0000_brush.png', '0060_wide.png', '0252_alarm.png'):
        old, new = PREVIOUS/name, output/name
        if not old.exists() or not new.exists():
            continue
        with Image.open(old) as a, Image.open(new) as b:
            same = a.size == b.size and a.convert('RGBA').tobytes() == b.convert('RGBA').tobytes()
        results.append(dict(file=name, unchanged=same))
        if not same:
            raise AssertionError(f'The original opening composition changed: {name}')
    return results


def path_diagnostic(output):
    """Annotate the shared world-space attack line, outside normal playback."""
    import pygame
    from ice_reaper_action import IceReaperActionStage
    pygame.init()
    pygame.display.set_mode((480, 320))
    try:
        stage = IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue', strict=True)
        canvas = pygame.Surface((480, 320))
        # Immediately before impact, Caelan has cleared the target enough for
        # the prison and continued attack line to remain readable.
        time = 8.99
        stage.draw(canvas, time)
        image = Image.frombytes('RGB', canvas.get_size(), pygame.image.tobytes(canvas, 'RGB'))
        image = image.resize((960, 640), Image.Resampling.NEAREST)
        panel = Image.new('RGB', (960, 710), '#142331')
        panel.paste(image, (0, 70))
        draw = ImageDraw.Draw(panel)
        draw.text((12, 7), 'Review diagnostic — overlays are not shown in game', font=font(19), fill='#f5e7c2')
        draw.text((12, 35), 'Dashed continuation reaches Rhea if the shield does not intercept it.',
                  font=font(17), fill='#e4edf2')
        geometry = stage.attack_geometry()
        camera = stage.camera(time)
        projected = {key: camera.project(value) for key,value in geometry.items()}
        def screen(point):
            return (round(point[0]*2), round(point[1]*2)+70)
        target, shield = projected['target'], projected['shield']
        if target is None or shield is None:
            raise AssertionError('Rhea and the interception point must be visible in the diagnostic')
        a, b = screen(shield), screen(target)
        incoming = camera.project(geometry['release'].lerp(geometry['shield'], .35))
        if incoming is not None:
            p = screen(incoming)
            # Keep the explanatory heading separate from the scene overlay.
            if p[1] < 70 and a[1] != p[1]:
                fraction = (70-p[1])/(a[1]-p[1])
                p = (round(p[0]+(a[0]-p[0])*fraction), 70)
            draw.line((p, a), fill='#6fe4ff', width=3)
        for segment in range(12):
            if segment%2:
                continue
            p = tuple(round(a[i]+(b[i]-a[i])*segment/12) for i in range(2))
            q = tuple(round(a[i]+(b[i]-a[i])*(segment+1)/12) for i in range(2))
            draw.line((p,q), fill='#ffbd59', width=4)
        for point, color, label, offset in ((a,'#6fe4ff','Shield contact',(18,-45)),
                                            (b,'#ffbd59','Rhea target',(-145,26))):
            draw.ellipse((point[0]-8,point[1]-8,point[0]+8,point[1]+8), outline=color, width=3)
            location=(point[0]+offset[0],point[1]+offset[1])
            draw.text(location, label, font=font(17), fill=color, stroke_width=2, stroke_fill='#142331')
        panel.save(output/'path_diagnostic.png', optimize=True)
        return {key:list(value) for key,value in geometry.items()}
    finally:
        pygame.quit()


def review(output=OUTPUT, *, fps=60, reuse=False):
    if not reuse:
        production.capture(output, fps=fps)
    report = json.loads((output/'verification.json').read_text())
    if report['fps'] != fps or report['frames'] != round(report['duration_seconds']*fps):
        raise AssertionError('Review frame rate/count differ from the production capture')
    video = output/'preview.mp4'
    if video.stat().st_size > 11*1024*1024:
        raise AssertionError('Review MP4 exceeds the GitHub connector upload budget')
    times = sorted({8.6, 8.99, 19.3, *(time for times in STRIPS.values() for time in times)})
    frames = video_frames(video, times, fps)
    for name, times in STRIPS.items():
        filmstrip(frames, times, fps, output/f'{name}.png', name.replace('_', ' ').title())
    frames[round(8.6*fps)].save(output/'rescue_poster.png', optimize=True)
    frames[round(8.99*fps)].save(output/'impact_poster.png', optimize=True)
    frames[round(19.3*fps)].save(output/'rune_poster.png', optimize=True)
    if (PREVIOUS/'rescue_poster.png').exists():
        with Image.open(PREVIOUS/'rescue_poster.png') as previous:
            before_after(previous.convert('RGB'), frames[round(8.6*fps)], output/'rescue_comparison.png')
    evidence = dict(
        version=1, source_video_sha256=digest(video), source_fps=fps,
        opening_comparison=verify_opening(output),
        attack_geometry=path_diagnostic(output),
        filmstrips={name:list(times) for name,times in STRIPS.items()},
        note='Filmstrips and posters decode the delivered MP4; comparison is at 8.6 seconds.',
    )
    (output/'continuity_review.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(f'Continuity review: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--fps', type=int, choices=(30, 60), default=60)
    parser.add_argument('--reuse', action='store_true', help='Build comparisons from an existing completed capture')
    args = parser.parse_args()
    review(args.output.resolve(), fps=args.fps, reuse=args.reuse)
