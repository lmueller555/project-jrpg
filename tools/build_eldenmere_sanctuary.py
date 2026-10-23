"""Export a native sanctuary and replace its town placeholder for appearance review."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import nearest
import build_eldenmere_town as town
from build_eldenmere_blockout import geometry

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary'
OUTPUT=ROOT/'assets/terrain/eldenmere/sanctuary'
BASE=ROOT/'assets/maps/eldenmere/terrain_foundation'


def contains(rect,x,y):
    return rect[0]<=x<rect[2] and rect[1]<=y<rect[3]


def material(pixel,x,y,recipe,palette):
    r,g,b,_=pixel;landmarks=recipe['source_landmarks'];outline=[recipe['outline']]
    if max(r,g,b)<70:return outline
    if contains(landmarks['bell'],x,y):return outline+list(recipe['bronze'].values())
    if g>r+3 and g>b+8:return outline+list(palette['grass'].values())
    if contains(landmarks['lantern'],x,y):return outline+list(palette['iron'].values())+[palette['plaster']['light']]
    if any(contains(rect,x,y) for rect in landmarks['windows']) and b>r+5 and g>r+5:
        return outline+list(palette['glass'].values())
    if contains(landmarks['chimney'],x,y) or y>=1005:
        return outline+list(palette['stone'].values())+list(palette['grass'].values())
    if y<748 and (b>r+4 or g>r+4):return outline+list(palette['roof'].values())
    if r>150 and g>130 and b>90 and r-g<40 and g-b<70:
        return outline+list(palette['plaster'].values())
    if r>=g+8 and r>=b+12:return outline+list(palette['wood'].values())
    if y>=748 and max(r,g,b)-min(r,g,b)<25:
        return outline+list(palette['iron'].values())+list(palette['stone'].values())
    return outline+list(palette['stone'].values())+list(palette['roof'].values())


def export_native(recipe):
    reference=town.opened(SOURCE/recipe['source'])
    palette=read_json(ROOT/recipe['palette_source'])['materials']
    result=Image.new('RGBA',tuple(recipe['frame_size']));components=[]
    for band in recipe['bands']:
        left,top,right,bottom=band['crop'];w,h=band['sample_size']
        sample=reference.crop(band['crop']).resize((w,h),Image.Resampling.NEAREST)
        part=Image.new('RGBA',(w,h))
        for y in range(h):
            for x in range(w):
                pixel=sample.getpixel((x,y))
                if pixel[3]<recipe['alpha_threshold']:continue
                sx=left+(x+.5)*(right-left)/w;sy=top+(y+.5)*(bottom-top)/h
                colors=[rgba(c) for c in material(pixel,sx,sy,recipe,palette)]
                part.putpixel((x,y),nearest(pixel[:3],colors))
        part.save(SOURCE/'parts'/f"{band['id']}.png")
        result.alpha_composite(part,tuple(band['position']))
        components.append({**band,'image':f"../../../source/terrain/eldenmere/sanctuary/parts/{band['id']}.png"})
    result.save(SOURCE/'parts/exterior_native.png');result.save(OUTPUT/'closed.png')
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':{**palette,'outline':{'base':recipe['outline']},'bronze':recipe['bronze']}})
    return result,components


def build():
    recipe=read_json(SOURCE/'recipe.json')
    for path in (SOURCE/'parts',OUTPUT/'scene_frames'):
        path.mkdir(parents=True,exist_ok=True)
    sanctuary,components=export_native(recipe)
    plan=read_json(BASE/'adapted_plan.json');geo=geometry(plan)
    foundation_recipe=read_json(ROOT/'assets/source/maps/eldenmere/terrain_foundation/recipe.json')
    foundation=read_json(BASE/'scene.json')
    buildings=town.building_assets(foundation_recipe,plan)
    existing=next(r for r in buildings if r['id']=='sanctuary')
    gx,gy,gw,gh=recipe['ground_rect'];x,y=recipe['town_ground_position'];position=[x-gx,y-gy]
    assert existing['ground_rect_pixels']==[x,y,gw,gh]
    existing.update(position=position,prefab_size=recipe['frame_size'],frames=[sanctuary],placeholder=False,
                    pack=str(OUTPUT.relative_to(ROOT)),door_centre=[position[0]+recipe['door_rect'][0]+16,position[1]+recipe['door_rect'][1]+42])
    grass=town.opened(BASE/'layers/grass.png')
    base=grass.copy();base.alpha_composite(town.opened(BASE/'layers/paths.png'))
    masonry=town.opened(BASE/'layers/masonry.png')
    water,water_tiles=town.stream_tiles(geo);channels=town.channels(plan,geo);bridges=town.bridge_assets(plan)
    # Static sanctuary review; the surrounding town retains the original water/smoke clock.
    environment=town.render_environment(0,base,grass,masonry,water,water_tiles,channels,buildings,bridges)
    native=town.with_actor(environment,bridges,foundation_recipe['main_hero_foot'])
    native.save(OUTPUT/'town_native.png')
    # A scale view moves the one player actor to the sanctuary entrance.
    scale_native=town.with_actor(environment,bridges,recipe['hero_foot'],recipe['hero_facing'])
    scale_native.save(OUTPUT/'scene_frames/frame_01.png')
    crop=scale_native.crop(town.box(recipe['review_crop']))
    crop.save(OUTPUT/'entrance_native.png')
    board=Image.new('RGB',(crop.width*4,crop.height*4+112),'#e8edf2')
    d=ImageDraw.Draw(board);d.fontmode='1'
    d.text((24,14),f"ELDENMERE / sanctuary exterior / {recipe['status']}",font=town.font(27,True),fill='#243529')
    d.text((24,52),'8 x 5 ground footprint / Caelan at the entrance / native art enlarged 4x',font=town.font(20),fill='#53696e')
    board.paste(enlarged(crop,4),(0,84))
    d.text((24,board.height-24),'Appearance review: closed doors, still bell and lantern; smoke and animated layers follow approval.',font=town.font(18),fill='#53696e')
    board.save(OUTPUT/'sanctuary_review.png')
    sprite_board=Image.new('RGB',(1120,1060),'#e8edf2');d=ImageDraw.Draw(sprite_board);d.fontmode='1'
    d.text((24,16),f"Sanctuary / {recipe['status']} / 216 x 216 drawing frame",font=town.font(25,True),fill='#243529')
    cell=Image.new('RGBA',(216,228),'#c5c2b4');cell.alpha_composite(sanctuary)
    hero=town.opened(ROOT/'assets/characters/caelan/idle_front.png');cell.alpha_composite(hero,(122,192))
    sprite_board.paste(enlarged(cell.convert('RGB'),4),(128,90))
    d.text((24,1020),'192 x 120 ground / 32px door opening / paired doors / 3 windows / bronze bell',font=town.font(21),fill='#53696e')
    sprite_board.save(OUTPUT/'exterior_review.png')
    overview=enlarged(native,2);town_board=Image.new('RGB',(overview.width,overview.height+96),'#e8edf2');d=ImageDraw.Draw(town_board);d.fontmode='1'
    d.text((24,16),f"ELDENMERE / sanctuary placed in town / {recipe['status']}",font=town.font(28,True),fill='#243529')
    d.text((24,54),'Sanctuary exterior replaces its measured placeholder. Mira workshop remains pending.',font=town.font(20),fill='#53696e')
    town_board.paste(overview,(0,96));town_board.save(OUTPUT/'town_review.png')
    # Check the true native threshold using the already verified 24x12 planning probe.
    allowed=town.opened(BASE/'navigation/allowed_routes.png').convert('L')
    blocked=town.opened(BASE/'navigation/blocking.png').convert('L')
    foot=recipe['hero_foot'];probe=[foot[0]-12,foot[1]-6,24,12]
    assert not blocked.crop(town.box(probe)).getbbox(),'Native doorway approach blocked'
    assert allowed.getpixel(tuple(foot)), 'Door approach leaves planned route'
    reached=town.opened(BASE/'navigation/reachable_centres.png').convert('L')
    assert reached.getpixel(tuple(foot)), 'Native threshold is not reachable from courtyard'
    write_json(OUTPUT/'sanctuary.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'prefab_size':recipe['frame_size'],'ground_rect':recipe['ground_rect'],'ground_tiles':recipe['ground_tiles'],
        'image':'closed.png','components':components,'door':{'rect':recipe['door_rect'],'clear_width':32,'state':'closed','animated':False},
        'bell':{'state':'still','animated':False},'lantern':{'lit':False,'animated':False},'chimney_smoke_included':False,
        'palette':'palette.json','position':position,'ground_position':[x,y],
        'door_world_rect':[position[0]+recipe['door_rect'][0],position[1]+recipe['door_rect'][1],32,42],
        'character':{'image':'assets/characters/caelan/idle_front.png','foot':foot,'anchor':[12,30],'probe_size':[24,12]},
        'review_crop':recipe['review_crop'],'review_scale':4,'source_recipe':'../../../source/terrain/eldenmere/sanctuary/recipe.json',
        'base_town':'assets/maps/eldenmere/terrain_foundation/scene.json','engine_collision_implemented':False,
        'door_interaction_implemented':False,'interior_transition_implemented':False,
        'purpose':'Static closed-door appearance review before adding sanctuary animation layers.'})
    print('Built native 8x5 sanctuary, entrance review with Caelan, standalone sprite and updated town still.')


if __name__=='__main__':build()
