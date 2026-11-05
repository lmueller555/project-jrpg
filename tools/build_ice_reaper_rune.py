"""Register the authored red aether seal without synthesizing its linework.

Mechanical alpha cleanup, square registration, nearest scaling and palette
registration retain the original image-generation source unchanged. The asset
is always rendered at its final world footprint; reveal timing belongs to the
cinematic renderer, not to a resize animation.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/cinematics/ice_reaper_rune/rune_generated.png'
TARGET=ROOT/'assets/story/ice_reaper_rune'
CANVAS=512
RADIUS=216

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    TARGET.mkdir(parents=True,exist_ok=True)
    before=sha(SOURCE)
    source=Image.open(SOURCE).convert('RGBA')
    # Remove only low-opacity generated bloom. Keep the authored engraved
    # branches, fine glyphs, bright cores and disconnected accent marks.
    source.putalpha(source.getchannel('A').point(lambda a:255 if a>=96 else 0))
    bounds=source.getbbox()
    if bounds is None:raise ValueError('Empty authored rune')
    center=((bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2)
    side=max(bounds[2]-bounds[0],bounds[3]-bounds[1])
    crop=(round(center[0]-side/2),round(center[1]-side/2),
          round(center[0]+side/2),round(center[1]+side/2))
    registered=source.crop(crop).resize((2*RADIUS,2*RADIUS),Image.Resampling.NEAREST)
    alpha=registered.getchannel('A')
    registered=registered.convert('RGB').quantize(colors=128,dither=Image.Dither.NONE).convert('RGBA')
    registered.putalpha(alpha)
    output=Image.new('RGBA',(CANVAS,CANVAS))
    margin=CANVAS//2-RADIUS
    output.alpha_composite(registered,(margin,margin))
    output.save(TARGET/'rune.png',optimize=True)
    arr=np.asarray(output)
    y,x=np.indices((CANVAS,CANVAS))
    radius=np.hypot(x-CANVAS/2,y-CANVAS/2)/RADIUS
    # These masks only separate the existing drawing. They introduce no new
    # geometry or substitute procedural lines for the authored artwork.
    ranges={
      'seal':radius<=.31,
      'branches':(radius>.25)&(radius<.85),
      'rings':((radius>=.825)&(radius<.88))|(radius>=.955),
      'glyphs':(radius>=.875)&(radius<.955),
    }
    for name,region in ranges.items():
        image=Image.fromarray(np.where(region,arr[:,:,3],0).astype(np.uint8),'L')
        image.save(TARGET/f'{name}_mask.png',optimize=True)
    metadata={
      'version':1,'canvas':[CANVAS,CANVAS],'file':'rune.png',
      'center':[CANVAS/2,CANVAS/2],'outer_radius_px':RADIUS,
      'world_radius':8.2,'alpha_threshold':96,'palette_colors':128,
      'spokes':6,'spoke_start_angle_degrees':-90,
      'rings_normalized':[.845,.97],
      'glyph_band_normalized':[.875,.955],
      'central_seal_normalized_radius':.31,
      'masks':{name:f'{name}_mask.png' for name in ranges},
      'reveal_contract':'Fixed final footprint. Trace center, branching strokes, circumference and glyphs; never scale the completed drawing from the center.',
      'source_art_review':'awaiting_full_scene_review',
    }
    (TARGET/'rune.json').write_text(json.dumps(metadata,indent=2)+'\n')
    provenance={
      'version':1,'source':SOURCE.relative_to(ROOT).as_posix(),
      'source_sha256':before,'source_size':list(source.size),
      'source_content_bounds':list(bounds),'square_crop':list(crop),
      'registration_offset':[margin,margin],
      'generated_with':'image_gen',
      'operation':'Authored artwork; alpha threshold, equal-aspect square registration, nearest scaling, palette registration and masks from authored alpha only.',
      'source_unchanged':sha(SOURCE)==before,
      'exports':{p.name:sha(p) for p in sorted(TARGET.glob('*.png'))},
      'review':'awaiting_full_scene_review',
    }
    (TARGET/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({'canvas':[CANVAS,CANVAS],'outer_radius_px':RADIUS,'opaque_fraction':round(float((arr[:,:,3]>0).mean()),4),'source_unchanged':provenance['source_unchanged']}))

if __name__=='__main__':build()
