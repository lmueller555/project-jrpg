"""Adapt staged signature assets into explicit live regional bindings.

The source asset schema never becomes a runtime props registry implicitly.
Contact clipping consumes authored solid geometry, never artwork alpha as collision.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops
ROOT=Path(__file__).resolve().parents[1]
SIGNATURE=ROOT/'assets/terrain/overworld/elden_vale/signature_landscape_hd/manifest.json'
RECIPE=ROOT/'assets/source/maps/overworld/elden_vale/recipe.json'


def support_rectangles(recipe,plan):
    solids=[]
    for group in recipe['setpieces']:
        for prop in group.get('props',[]):
            if prop['id'] in plan['existing_supports']:
                x,y=[round(v*24) for v in prop['tile_position']];w,h=prop['solid']
                solids.append((x-w//2,y-h//2,w,h))
    if len(solids)!=len(plan['existing_supports']):raise ValueError('Unknown landmark support')
    ox,oy=plan['master_origin_logical']
    # This contact is the approved source study under the regional rendition's
    # explicitly authored X/Y projection, not a sprite-derived solid rectangle.
    x,y,w,h=ox+356*384/784,oy+504*.5,72*384/784,20*.5
    if not any(fx<=x and fy<=y and x+w<=fx+fw and y+h<=fy+fh for fx,fy,fw,fh in solids):
        raise ValueError('Regional skull contact leaves existing solid ridge')
    return solids


def regional_bindings(products, depend, png_bytes):
    depend(SIGNATURE);depend(RECIPE);depend(Path(__file__))
    assets=json.loads(SIGNATURE.read_text())['assets']
    recipe=json.loads(RECIPE.read_text());plan=recipe.get('signature_landscape',{})
    if not plan:return {},{}
    folder=ROOT/'assets/maps/overworld/elden_vale/hd_integration/signature'
    landmarks={};props={}
    def export(name,image,**metadata):
        path=folder/(name+'.png');products[path]=png_bytes(image)
        return {'image':path.relative_to(ROOT).as_posix(),'logical_size':[image.width//2,image.height//2],
                'artwork_pixels_per_world_pixel':2,'collision':'none','interaction_cues':False,**metadata}
    master=Image.open(ROOT/assets['antlers_regional']['image']).convert('RGBA')
    depend(ROOT/assets['antlers_regional']['image'])
    pieces=[('regional_beam_left',(0,0,260,380)),('regional_beam_central',(260,0,508,380)),
            ('regional_beam_right',(508,0,768,380)),('regional_skull_raised',(0,380,768,528)),
            ('regional_skull_contact',(0,500,768,528))]
    # Lower terrestrial fringe embeds in the already solid ridge. Preserve the
    # authored jaw/teeth polygon; it may overhang, but is never a new ground wall.
    origin=plan['master_origin_logical']
    solids=support_rectangles(recipe,plan)
    contact=Image.new('L',master.size);draw=ImageDraw.Draw(contact)
    for x,y,w,h in solids:
        draw.rectangle((round((x-origin[0])*2),round((y-origin[1])*2),round((x+w-origin[0])*2)-1,round((y+h-origin[1])*2)-1),fill=255)
    bone=Image.new('L',master.size);bone_draw=ImageDraw.Draw(bone)
    polygon=plan['bone_polygon_source_artwork']
    bone_draw.polygon([(round(x*768/1568),round((760+y)*528/1056)) for x,y in polygon],fill=255)
    solid=contact.copy()
    contact=ImageChops.lighter(contact,bone)
    # Hand-registered uneven embedding edge avoids a horizontal crop scar across
    # weathered roots. Only terrestrial fringe changes, never the jaw polygon.
    edge=plan['embedding_edge_artwork']
    embedding=Image.new('L',master.size)
    ImageDraw.Draw(embedding).polygon([(0,0),(master.width,0),*reversed([tuple(p) for p in edge])],fill=255)
    embedded_alpha=ImageChops.multiply(master.getchannel('A'),ImageChops.lighter(embedding,contact))
    master.putalpha(embedded_alpha)
    ground_coverage=solid.copy()
    ImageDraw.Draw(ground_coverage).rectangle((0,0,master.width,499),fill=0)
    for name,box in pieces:
        image=master.crop(box)
        if name.endswith('raised'):
            image.putalpha(ImageChops.multiply(image.getchannel('A'),ImageChops.invert(ground_coverage.crop(box))))
        if name.endswith('contact'):
            image.putalpha(ImageChops.multiply(image.getchannel('A'),solid.crop(box)))
        record=export(name,image,assembly_position_artwork=list(box[:2]))
        if not name.endswith('contact'):
            maskpath=folder/(name+'_mask.png');products[maskpath]=png_bytes(image.getchannel('A'))
            record['occlusion_mask']=maskpath.relative_to(ROOT).as_posix()
        landmarks[name]=record
    # These are explicit prop adaptations at the existing regional feet. The
    # physical rectangles remain owned by the original setpiece records.
    for key,source_name in plan.get('prop_assets',{}).items():
        asset=assets[source_name];depend(ROOT/asset['image'])
        raw=Image.open(ROOT/asset['image']).convert('RGBA')
        # Uniformly fit a donor into the established regional ridge canvas.
        canvas=Image.new('RGBA',(192,128));factor=min(192/raw.width,128/raw.height)
        size=tuple(round(value*factor) for value in raw.size)
        fitted=raw.resize(size,Image.Resampling.NEAREST)
        canvas.alpha_composite(fitted,((192-size[0])//2,128-size[1]))
        props[key]=export(key,canvas,foot_anchor=[48,64],
                          collision='existing regional geometry; never derived from image alpha')
    miniature=assets['sanctuary_miniature'];depend(ROOT/miniature['image'])
    props['ridge_sanctuary']={**miniature,'artwork_pixels_per_world_pixel':2,'foot_anchor':[48,78],
                              'collision':'existing Sanctuary entry contract; image is not a trigger','interaction_cues':False}
    return landmarks,props
