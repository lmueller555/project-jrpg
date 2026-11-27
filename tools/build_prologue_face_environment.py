"""Bake the frontal performance from painted sources and the runtime camera.

This is offline planar environment projection. It never constructs character
anatomy. Complete authored figures are composited offline, so both presentation
modes stream one bounded native bank rather than caching all source drawings.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import inspect
import json
import math
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cinematic_face_reveal import (CinematicFaceReveal, DEFAULT_CAMERA, FACE_SCENE,
                                   camera_at, performance_signature, project_world)
from cinematic_bridge_run import CinematicBridgeRun
from cinematic_perspective import _png_size

SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/face_reveal/environment'
OUTPUT = ROOT/'assets/story/fire_veinhold_opening/shot07/environment'
REVIEW = ROOT/'docs/reviews/veinhold_motion_continuity'
APPROACH_SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/continuation/materials/frozen_bridge_final.png'
WIDTH, HEIGHT, FPS, COUNT = 960, 640, 60, 301
PROOFS = (0, 45, 90, 180, 300)
GEOMETRY = {
    'bridge_width_metres':14., 'bridge_length_metres':299.0819285747636,
    'deck_texture_repeat_metres':4., 'rail_repeat_metres':4.,
    'rail_height_metres':1.2, 'backdrop_horizon_fraction':.89,
    'backdrop_pixels_per_radian':750.,
    'mainland_approach_metres':100., 'mainland_approach_end_width_metres':6.,
    'approach_material_source_crop':[720,450,850,490],
    'projection':'World-ray intersections with fixed deck and rail planes; '
                 'one angular sky/coast painting at effectively distant depth.',
}


def _json(data):
    return (json.dumps(data, indent=2)+'\n').encode()


def _png(image):
    stream = BytesIO()
    image.save(stream, format='PNG', compress_level=6)
    return stream.getvalue()


def _entry(data):
    return {'sha256':sha256(data).hexdigest(), 'bytes':len(data)}


def _projection_fingerprint():
    return sha256((inspect.getsource(camera_at)+inspect.getsource(project_world)
                   +json.dumps(DEFAULT_CAMERA, sort_keys=True)).encode()).hexdigest()


def _pyramid(path, *, alpha=False, box=None):
    image = Image.open(path).convert('RGBA' if alpha else 'RGB')
    if box is not None:
        image = image.crop(tuple(box))
    # Straight-alpha input is converted before sampling so transparent edge RGB
    # cannot create a bright fringe on receding steel bars.
    if alpha:
        image = image.convert('RGBa')
    images = []
    while True:
        images.append(np.asarray(image, dtype=np.float32)/255.)
        if min(image.size) <= 8:
            break
        image = image.resize((max(1,image.width//2), max(1,image.height//2)),
                             Image.Resampling.LANCZOS)
    return images


def _bilinear(image, u, v, *, wrap=False):
    height, width = image.shape[:2]
    if wrap:
        u, v = u % width, v % height
    else:
        u, v = np.clip(u, 0, width-1), np.clip(v, 0, height-1)
    x0, y0 = np.floor(u).astype(np.int32), np.floor(v).astype(np.int32)
    x1, y1 = x0+1, y0+1
    if wrap:
        x1 %= width; y1 %= height
    else:
        x1 = np.minimum(x1,width-1); y1 = np.minimum(y1,height-1)
    dx, dy = (u-x0)[:,None], (v-y0)[:,None]
    return ((image[y0,x0]*(1-dx)+image[y0,x1]*dx)*(1-dy)
            +(image[y1,x0]*(1-dx)+image[y1,x1]*dx)*dy)


def _surface_samples(pyramid, u, v, footprint, *, wrap=False):
    # Select a whole-source mip by projected texel footprint. This prevents
    # subpixel rivets and joints sparkling near the bridge's vanishing point.
    lod = np.clip(np.log2(np.maximum(footprint,1.)),0,len(pyramid)-1)
    levels = np.floor(lod).astype(np.int32)
    result = np.zeros((len(u),pyramid[0].shape[2]), dtype=np.float32)
    for level in np.unique(levels):
        selected = levels == level
        texture = pyramid[int(level)]
        sx = texture.shape[1]/pyramid[0].shape[1]
        sy = texture.shape[0]/pyramid[0].shape[0]
        sampled = _bilinear(texture,u[selected]*sx,v[selected]*sy,wrap=wrap)
        next_level = min(int(level)+1,len(pyramid)-1)
        if next_level != level:
            coarser = pyramid[next_level]
            nx,ny = coarser.shape[1]/pyramid[0].shape[1],coarser.shape[0]/pyramid[0].shape[0]
            second = _bilinear(coarser,u[selected]*nx,v[selected]*ny,wrap=wrap)
            blend = (lod[selected]-level)[:,None]
            sampled = sampled*(1-blend)+second*blend
        result[selected] = sampled
    return result


class PaintedBridge:
    def __init__(self):
        self.backdrop = np.asarray(Image.open(SOURCE/'backdrop_generated.png').convert('RGB'),
                                   dtype=np.float32)/255.
        self.deck = _pyramid(SOURCE/'deck_generated.png')
        self.approach = _pyramid(APPROACH_SOURCE,box=GEOMETRY['approach_material_source_crop'])
        self.rail = _pyramid(SOURCE/'rail_generated.png',alpha=True)
        yy,xx = np.mgrid[0:HEIGHT,0:WIDTH].astype(np.float32)
        self.horizontal = (480.-xx)/DEFAULT_CAMERA['focal_pixels']
        self.vertical = (320.-yy)/DEFAULT_CAMERA['focal_pixels']

    def render(self, index):
        camera = camera_at(index/FPS)
        pitch = camera['pitch_radians']
        along = -math.cos(pitch)+self.vertical*math.sin(pitch)
        vertical = math.sin(pitch)+self.vertical*math.cos(pitch)
        yaw = np.arctan2(self.horizontal,-along)
        elevation = np.arctan2(vertical,np.sqrt(along*along+self.horizontal*self.horizontal))
        density = GEOMETRY['backdrop_pixels_per_radian']
        u = self.backdrop.shape[1]/2-yaw*density
        v = self.backdrop.shape[0]*GEOMETRY['backdrop_horizon_fraction']-elevation*density
        frame = _bilinear(self.backdrop,u.ravel(),v.ravel()).reshape(HEIGHT,WIDTH,3)

        # The bridge deck is one fixed, horizontal world plane. Travel changes
        # which world texels are visible; it never slides the mountains or sky.
        with np.errstate(divide='ignore',invalid='ignore'):
            distance = -camera['position'][2]/vertical
        world_x = self.horizontal*distance
        world_y = camera['position'][1]+along*distance
        # A finite masonry approach joins the metal deck to the painted
        # mainland road. Its material is an unoccluded crop of the previously
        # approved frozen-bridge landing, not a second independently moving
        # mountain plate. It tapers into the existing distant coastal saddle.
        approach_length = GEOMETRY['mainland_approach_metres']
        width = (GEOMETRY['bridge_width_metres']+(world_y/approach_length)
                 *(GEOMETRY['bridge_width_metres']-GEOMETRY['mainland_approach_end_width_metres']))
        on_approach = ((distance > 0)&(vertical < 0)&(world_y < 0)&(world_y >= -approach_length)
                       &(np.abs(world_x) <= width/2))
        if np.any(on_approach):
            height,texture_width = self.approach[0].shape[:2]
            u = world_x[on_approach]/4.*texture_width
            v = world_y[on_approach]/4.*height
            footprint = distance[on_approach]/camera['focal_pixels']*texture_width/4.
            frame[on_approach] = _surface_samples(self.approach,u,v,footprint,wrap=True)
        valid = ((distance > 0)&(vertical < 0)&(np.abs(world_x) <= GEOMETRY['bridge_width_metres']/2)
                 &(world_y >= 0)&(world_y <= GEOMETRY['bridge_length_metres']))
        if np.any(valid):
            height,width = self.deck[0].shape[:2]
            repeat = GEOMETRY['deck_texture_repeat_metres']
            u = (world_x[valid]/repeat)*width
            v = (world_y[valid]/repeat)*height
            # Pixel footprint grows with distance and the ground's grazing angle.
            footprint = (distance[valid]/camera['focal_pixels']*width/repeat
                         /np.maximum(np.abs(vertical[valid]),.04))
            frame[valid] = _surface_samples(self.deck,u,v,footprint,wrap=True)

        for side in (-1.,1.):
            # A vertical painted railing plane at each physical deck edge.
            # Ray intersections naturally clip the near plane and resolve the
            # panel's transparent X-brace gaps against deck and distant coast.
            with np.errstate(divide='ignore',invalid='ignore'):
                distance = side*GEOMETRY['bridge_width_metres']/2/self.horizontal
            world_y = camera['position'][1]+along*distance
            world_z = camera['position'][2]+vertical*distance
            valid = ((distance > 0)&(world_y >= 0)&(world_y <= GEOMETRY['bridge_length_metres'])
                     &(world_z >= 0)&(world_z <= GEOMETRY['rail_height_metres']))
            if not np.any(valid):
                continue
            height,width = self.rail[0].shape[:2]
            u = ((world_y[valid]/GEOMETRY['rail_repeat_metres'])%1)*width
            v = (1-world_z[valid]/GEOMETRY['rail_height_metres'])*(height-1)
            footprint = distance[valid]/camera['focal_pixels']*width/GEOMETRY['rail_repeat_metres']
            pixels = _surface_samples(self.rail,u,v,footprint)
            frame[valid] = pixels[:,:3]+frame[valid]*(1-pixels[:,3:4])
        return Image.fromarray(np.clip(np.rint(frame*255),0,255).astype(np.uint8)),camera


def _sources():
    paths = [Path(__file__), SOURCE/'generation.json',APPROACH_SOURCE, FACE_SCENE,
             ROOT/'cinematic_face_reveal.py', ROOT/'cinematic_bridge_run.py',
             ROOT/'cinematic_perspective.py']
    paths += sorted(SOURCE.glob('*_generated.png'))+sorted(SOURCE.glob('*_prompt.txt'))
    paths += sorted((OUTPUT.parent/'characters').glob('*/*.json'))
    paths += sorted((OUTPUT.parent/'characters').glob('*/*.png'))
    return {path.relative_to(ROOT).as_posix():_entry(path.read_bytes()) for path in paths}


def _camera_metadata():
    return [{'index':index, 'time_seconds':index/FPS, 'camera':camera_at(index/FPS),
             'bridge':{'width_metres':14., 'rail_height_metres':1.2,
                       'mainland_landing':[0.,0.,0.]}} for index in range(COUNT)]


@contextmanager
def _compositor(metadata):
    """Use the production drawing path without reading previously baked pixels.

    A tiny temporary clear bank supplies validated camera metadata while the
    replacement reel is being built. This avoids both a stale-camera bootstrap
    and compositing characters twice when the build is run again.
    """
    import pygame
    scene = json.loads(FACE_SCENE.read_text())
    if scene.get('camera') != DEFAULT_CAMERA or not scene.get('baked_characters'):
        raise ValueError('Production performance must use the shared camera and baked figures')
    initialized = pygame.display.get_init()
    if not initialized:
        pygame.display.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1,1))
    owner = None
    with tempfile.TemporaryDirectory(prefix='.face-bake-', dir=OUTPUT.parent) as name:
        temporary = Path(name)
        clear_path = temporary/'clear.png'
        clear_path.write_bytes(_png(Image.new('RGBA', (WIDTH,HEIGHT))))
        (temporary/'cameras.json').write_bytes(_json(metadata))
        segment = {'duration_ms':5000, 'frames':['clear.png']*COUNT,
                   'alarm_frames':['clear.png']*COUNT, 'metadata_path':'cameras.json'}
        (temporary/'manifest.json').write_bytes(_json({
            'version':1, 'width':WIDTH, 'height':HEIGHT, 'fps':FPS,
            'segments':{'face_reveal':segment, 'face_reveal_reduced':deepcopy(segment)}}))
        for actor in scene['actors']:
            actor['animation'] = os.path.relpath(FACE_SCENE.parent/actor['animation'], temporary)
        scene['environment'] = 'manifest.json'
        (temporary/'scene.json').write_bytes(_json(scene))
        try:
            owner = CinematicFaceReveal(temporary/'scene.json', allowed_root=OUTPUT.parent,
                                        cache_size=144, baked_characters=False)
            yield owner
        finally:
            if owner is not None:
                owner.close()
            if not initialized:
                pygame.display.quit()


def bake(*, proof=False, check=False):
    import pygame
    renderer = PaintedBridge()
    REVIEW.mkdir(parents=True,exist_ok=True)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    indices = PROOFS if proof else range(COUNT)
    outputs,metadata,proofs = {},_camera_metadata(),[]
    with _compositor(metadata) as owner:
        for index in indices:
            image,camera = renderer.render(index)
            surface = pygame.image.frombytes(image.tobytes(), image.size, 'RGB')
            owner.draw_unbaked(surface, owner.samples(index/FPS))
            image = Image.frombytes('RGB', (WIDTH,HEIGHT), pygame.image.tobytes(surface, 'RGB'))
            payload = _png(image)
            filename = f'frame_{index:04d}.png'
            path = OUTPUT/filename
            if check:
                if path.read_bytes() != payload or _png_size(path) != (WIDTH,HEIGHT):
                    raise ValueError(f'Stale frontal performance {index}')
            elif not proof:
                path.write_bytes(payload)
            outputs[filename] = _entry(payload)
            if index in PROOFS:
                proofs.append((index,image))
                if not check:
                    image.save(REVIEW/f'performance_{index:04d}.png')
    if proof:
        sheet = Image.new('RGB',(960*3,670*2),'#101821')
        draw = ImageDraw.Draw(sheet)
        for position,(index,image) in enumerate(proofs):
            x,y=(position%3)*960,(position//3)*670
            sheet.paste(image,(x,y));draw.text((x+10,y+645),f'{index:03d} / {index/FPS:.2f}s',fill='white')
        sheet.resize((1440,670),Image.Resampling.LANCZOS).save(REVIEW/'performance_contact.jpg',quality=92)
        print('Five native performance proofs ready.')
        return
    clear = _png(Image.new('RGBA',(WIDTH,HEIGHT)))
    paths = [f'frame_{index:04d}.png' for index in range(COUNT)]
    segment = {'duration_ms':5000,'frames':paths,'alarm_frames':['clear.png']*COUNT,
               'metadata_path':'cameras.json'}
    manifest = {'version':1,'width':WIDTH,'height':HEIGHT,'fps':FPS,'baked_characters':True,
                'performance_signature':performance_signature(FACE_SCENE),
                'segments':{'face_reveal':segment,'face_reveal_reduced':dict(segment)}}
    contents = {'clear.png':clear,'cameras.json':_json(metadata),'manifest.json':_json(manifest)}
    for name,payload in contents.items():
        if check:
            if (OUTPUT/name).read_bytes() != payload:
                raise ValueError('Stale frontal environment metadata: '+name)
        else:
            (OUTPUT/name).write_bytes(payload)
        outputs[name] = _entry(payload)
    recipe = {'version':1,'command':'python tools/build_prologue_face_environment.py',
              'render_size':[WIDTH,HEIGHT],'fps':FPS,'samples':COUNT,'duration_seconds':5,
              'projection_helper_sha256':_projection_fingerprint(),
              'compositor_sha256':sha256((inspect.getsource(CinematicFaceReveal.samples)
                  +inspect.getsource(CinematicFaceReveal.draw_unbaked)
                  +inspect.getsource(CinematicBridgeRun._whole_drawing)).encode()).hexdigest(),
              'construction':'Native full frames composite complete authored drawings over freshly projected scenery; no limb transforms or temporal interpolation.',
              'camera':DEFAULT_CAMERA,'geometry':GEOMETRY,
              'sources':_sources(),'outputs':outputs,
              'reduced_motion':'Shares all301 views because the down-tilt is the essential face reveal; no optional camera shake.'}
    recipe_path = SOURCE/'performance_recipe.json'
    if check:
        if json.loads(recipe_path.read_text()) != recipe:
            raise ValueError('Stale frontal environment export recipe')
        print('301 native full-performance frames and both camera manifests reproduce exactly.')
    else:
        recipe_path.write_bytes(_json(recipe))
        print('Baked301 native full-performance frames for both presentation modes.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof',action='store_true')
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    if args.proof and args.check:
        parser.error('--proof and --check are separate modes')
    bake(proof=args.proof,check=args.check)
