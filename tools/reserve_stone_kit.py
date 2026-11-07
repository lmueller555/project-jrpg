"""Source-derived native pixel modules for the regional Sanctuary.

Masonry, slate, carved windows and timber are sampled from approved Eldenmere
packs. Natural rock pieces come from the native regional polish pack. Geometry
assembles small reusable modules; no old Sanctuary painting is read.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'assets/terrain/elden_vale_sanctuary_kit'
SOURCE_BUILDING = 'assets/terrain/eldenmere/sanctuary/closed.png'
SOURCE_WALLS = ['assets/terrain/eldenmere/terraces/tiles/wall_front_0%d.png'%i for i in range(3)]
SOURCE_RIDGE = 'assets/terrain/overworld/elden_vale/polish/props/ridge.png'
SOURCE_ROCK = 'assets/terrain/overworld/elden_vale/polish/props/rock_outcrop.png'
SOURCE_STONES = 'assets/terrain/overworld/elden_vale/polish/props/river_rocks.png'
SOURCE_RAILS = ['assets/terrain/eldenmere/garden_fence/modules/'+part+'/module.png'
                for part in ('e_a','w_a')]
SOURCE_PAVING = 'assets/terrain/eldenmere/sanctuary_charm/props/flagstones.png'
CROPS = [
    {'path': SOURCE_BUILDING, 'crop': [78,84,102,108], 'purpose': 'slate roof material'},
    {'path': SOURCE_BUILDING, 'crop': [32,146,58,182], 'purpose': 'carved arched window'},
    {'path': SOURCE_BUILDING, 'crop': [118,156,150,198], 'purpose': 'timber door and frame'},
    {'path': SOURCE_BUILDING, 'crop': [39,56,54,72], 'purpose': 'small bell'},
    *[{'path': path, 'crop': [0,7,24,24], 'purpose': 'limestone masonry material'} for path in SOURCE_WALLS],
    {'path': SOURCE_RIDGE, 'crop': [0,0,96,64], 'purpose': 'natural rock surface'},
    {'path': SOURCE_RIDGE, 'crop': [24,20,48,44], 'purpose': 'cave limestone face material'},
    {'path': SOURCE_RIDGE, 'crop': [48,16,72,40], 'purpose': 'cave limestone face material'},
    {'path': SOURCE_ROCK, 'crop': [0,0,64,36], 'purpose': 'natural limestone outcrop'},
    {'path': SOURCE_STONES, 'crop': [0,0,36,20], 'purpose': 'small natural stones'},
    {'path': SOURCE_PAVING, 'crop': [0,0,32,16], 'purpose': 'horizontal cloister floor paving'},
    *[{'path': path, 'crop': [10,14,14,32], 'purpose': 'keeper rail native post'}
      for path in SOURCE_RAILS],
]


def opened(path):
    with Image.open(ROOT/path) as source:
        return source.convert('RGBA')


def texture(size, pieces, *, offset=(0,0)):
    result = Image.new('RGBA', size)
    for y in range(-offset[1], size[1], pieces[0].height):
        for x in range(-offset[0], size[0], pieces[0].width):
            image = pieces[(x//pieces[0].width+y//pieces[0].height)%len(pieces)]
            result.alpha_composite(image, (x,y))
    return result


def masked_texture(size, pieces, points, *, openings=()):
    result = texture(size,pieces)
    mask = Image.new('L',size)
    draw = ImageDraw.Draw(mask)
    draw.polygon(points,fill=255)
    for opening in openings:draw.polygon(opening,fill=0)
    result.putalpha(mask)
    result.paste((0,0,0,0),mask=ImageOps.invert(mask))
    return result


def shaded(image, factor):
    """Retain source pixel texture while placing it in architectural shade."""
    result=image.convert('RGB').point(lambda value:round(value*factor))
    result.putalpha(image.getchannel('A'))
    return result


def outlined(draw, points, dark='#444942', light='#c6c3aa', width=1):
    draw.line(points,fill=dark,width=width)


def make_kit():
    building = opened(SOURCE_BUILDING)
    masonry = [opened(path).crop((0,7,24,24)) for path in SOURCE_WALLS]
    # Light limestone remains in the approved warm/cool pixel ramps.
    roof = [building.crop((78,84,102,108))]
    images = {}

    hall = Image.new('RGBA',(288,216))
    walls = texture((240,108),masonry)
    hall.alpha_composite(walls,(24,96))
    d = ImageDraw.Draw(hall)
    d.rectangle((24,96,263,203),outline='#666c60',width=2)
    d.rectangle((24,194,263,203),fill='#666d61')
    # The foundation is sourced from the same pixel masonry material.
    hall.alpha_composite(texture((240,17),masonry),(24,190))
    d = ImageDraw.Draw(hall)
    d.line((24,190,263,190),fill='#d2ccb0',width=2)
    d.line((24,206,263,206),fill='#414b42',width=2)
    roof_points=[(8,109),(28,64),(114,64),(144,38),(174,64),(260,64),(280,109),(280,116),(8,116)]
    hall.alpha_composite(masked_texture(hall.size,roof,roof_points))
    d=ImageDraw.Draw(hall)
    d.line(roof_points+[roof_points[0]],fill='#454a42',width=3)
    d.line((12,108,276,108),fill='#afa483',width=2)
    d.line((14,113,274,113),fill='#4b4b3e',width=3)
    d.line((29,65,113,65,144,39,174,65,258,65),fill='#a8b4a5',width=2)
    # Stone central gable sits above the long limestone front, with a rose light.
    gable=[(108,116),(108,99),(144,69),(180,99),(180,116)]
    hall.alpha_composite(masked_texture(hall.size,masonry,gable))
    d=ImageDraw.Draw(hall)
    d.line((106,101,144,66,182,101),fill='#4f5950',width=4)
    d.line((108,98,144,66,180,98),fill='#cdc7ac',width=2)
    d.ellipse((132,91,155,114),fill='#666c60',outline='#d2c7a9',width=3)
    d.ellipse((137,96,150,109),fill='#253b3c')
    d.line((144,97,144,108),fill='#ac9b6d')
    d.line((138,103,149,103),fill='#ac9b6d')
    window=building.crop((32,146,58,182))
    window_mask=Image.new('L',window.size)
    ImageDraw.Draw(window_mask).polygon([(0,35),(0,12),(3,5),(8,0),(18,0),(23,5),(25,12),(25,35)],fill=255)
    window.putalpha(window_mask)
    for x in (48,86,176,214):hall.alpha_composite(window,(x,136))
    # New tall stone entrance keeps the ordinary native door width.
    portal=masked_texture((48,60),masonry,[(0,59),(0,22),(4,12),(12,4),(24,0),(36,4),(44,12),(47,22),(47,59)])
    hall.alpha_composite(portal,(120,150))
    door=building.crop((118,156,150,198))
    hall.alpha_composite(door,(128,168))
    d=ImageDraw.Draw(hall)
    d.rectangle((128,207,159,211),fill='#b4b29b')
    d.line((128,211,159,211),fill='#505c50')
    # Small bell tower is modular limestone, not the household silhouette.
    tower=Image.new('RGBA',(48,90))
    tower.alpha_composite(texture((32,64),masonry),(8,26))
    td=ImageDraw.Draw(tower)
    td.rectangle((8,26,39,89),outline='#5e695b',width=2)
    td.rectangle((15,43,32,70),fill='#263930')
    td.polygon([(15,43),(19,37),(28,37),(32,43)],fill='#263930')
    tower.alpha_composite(building.crop((39,56,54,72)),(17,48))
    tower.alpha_composite(masked_texture(tower.size,roof,[(0,29),(24,0),(47,29),(47,34),(0,34)]))
    td=ImageDraw.Draw(tower)
    td.line((0,31,24,1,47,31),fill='#d1c7a8',width=2)
    td.line((0,34,47,34),fill='#505849',width=2)
    hall.alpha_composite(tower,(120,0))
    images['hall']=hall

    # Three 64px-clear bays; all scenery pieces are individually placeable.
    floor=Image.new('RGBA',(240,72),masonry[1].getpixel((12,10)))
    paving=opened(SOURCE_PAVING)
    for y in range(0,72,16):
        for x in range(-16 if y//16%2 else 0,240,32):
            floor.alpha_composite(paving,(x,y))
    # Covered walkway: dark recesses preserve the open arches' silhouette.
    # Light stone columns remain individual foreground objects over this floor.
    images['cloister_floor']=shaded(floor,.60)
    images['cloister_back_wall']=shaded(texture((240,24),masonry),.48)
    roof_points=[(0,38),(12,6),(228,6),(239,38),(239,53),(0,53)]
    cloister_roof=masked_texture((240,72),roof,roof_points)
    rd=ImageDraw.Draw(cloister_roof)
    rd.line(roof_points+[roof_points[0]],fill='#4c5649',width=2)
    rd.line((2,49,237,49),fill='#b4ab8c',width=2)
    images['cloister_roof']=cloister_roof
    column=texture((12,72),masonry)
    cd=ImageDraw.Draw(column)
    cd.rectangle((0,0,11,5),fill='#c8c5aa',outline='#707867')
    cd.rectangle((0,65,11,71),fill='#b3b79c',outline='#67705f')
    cd.line((1,6,1,64),fill='#d1c9ac')
    cd.line((10,6,10,64),fill='#626d5a')
    images['cloister_column']=column
    archbar=Image.new('RGBA',(240,48))
    archbar.alpha_composite(texture((240,48),masonry))
    amask=Image.new('L',(240,48),255)
    ad=ImageDraw.Draw(amask)
    for left in (12,88,164):
        ad.polygon([(left,48),(left,29),(left+4,19),(left+12,10),(left+24,5),(left+40,5),
                    (left+52,10),(left+60,19),(left+64,29),(left+64,48)],fill=0)
    archbar.putalpha(amask)
    archbar.paste((0,0,0,0),mask=ImageOps.invert(amask))
    images['cloister_arches']=archbar

    # Reusable entrance arch: 48px clear opening and two24px piers.
    outer=[(0,95),(0,42),(4,24),(16,8),(32,0),(64,0),(80,8),(92,24),(95,42),(95,95)]
    opening=[(24,96),(24,42),(28,30),(36,20),(48,16),(60,20),(68,30),(72,42),(72,96)]
    arch=masked_texture((96,96),masonry,outer,openings=[opening])
    ad=ImageDraw.Draw(arch)
    ad.line(outer+[outer[0]],fill='#57624f',width=2)
    ad.line(opening,fill='#d8cfb3',width=2)
    for x in (0,72):
        ad.rectangle((x,88,x+23,95),fill='#788369',outline='#4e5c49')
        ad.line((x+1,87,x+22,87),fill='#d0c8a8')
    for points in (((47,0),(47,16)),((18,8),(35,21)),((5,25),(27,33)),((76,8),(61,21)),((91,25),(70,33))):
        ad.line(points,fill='#606f58',width=1)
    images['entrance_arch']=arch

    ridge=opened(SOURCE_RIDGE)
    rock=opened(SOURCE_ROCK)
    images['ridge']=ridge
    images['rock_outcrop']=rock
    images['small_rocks']=opened(SOURCE_STONES)
    # The cave's irregular arch is assembled from small natural rock samples.
    cave=Image.new('RGBA',(160,128))
    cd=ImageDraw.Draw(cave)
    cd.polygon([(26,122),(19,87),(23,46),(42,25),(67,14),(96,19),(125,32),(141,66),(145,121)],fill='#3c493c')
    cd.polygon([(45,126),(45,75),(51,55),(66,43),(84,41),(103,50),(115,72),(115,126)],fill='#18251f')
    cd.polygon([(52,126),(52,83),(59,65),(74,54),(92,55),(107,72),(109,126)],fill='#101a17')
    # Overlay full source ridges, then clear the mouth through the surface mask.
    rock_material=[ridge.crop((24,20,48,44)),ridge.crop((48,16,72,40))]
    outer_cave=[(14,127),(8,92),(18,48),(40,24),(68,12),(98,16),(134,47),(152,90),(148,127)]
    mouth_polygon=[(47,128),(47,78),(53,59),(65,47),(82,43),(100,49),(112,65),(114,128)]
    rim=masked_texture(cave.size,rock_material,outer_cave,openings=[mouth_polygon])
    rim.alpha_composite(ridge,(0,24))
    rim.alpha_composite(ImageOps.mirror(ridge),(64,31))
    rim.alpha_composite(rock,(38,0))
    rim.alpha_composite(ImageOps.mirror(rock),(12,83))
    rim.alpha_composite(rock,(88,86))
    mouth=Image.new('L',rim.size,255)
    md=ImageDraw.Draw(mouth)
    md.polygon([(47,128),(47,78),(53,59),(65,47),(82,43),(100,49),(112,65),(114,128)],fill=0)
    rim.putalpha(Image.composite(rim.getchannel('A'),Image.new('L',rim.size),mouth))
    cave.alpha_composite(rim)
    cd=ImageDraw.Draw(cave)
    cd.line((48,123,48,80,54,61,66,49,83,45,99,51,110,67,112,123),fill='#737b65',width=2)
    cd.line((54,122,54,84,61,67,74,57,91,58,105,75,107,122),fill='#344437',width=2)
    images['cave']=cave
    keeper_rail=Image.new('RGBA',(72,48))
    for x,path in zip((4,64),SOURCE_RAILS):
        keeper_rail.alpha_composite(opened(path).crop((10,14,14,32)),(x,14))
    kd=ImageDraw.Draw(keeper_rail)
    rope=[(7,18),(15,21),(26,24),(36,25),(46,24),(57,21),(65,18)]
    kd.line(rope,fill='#655d43',width=3)
    kd.line([(x,y-1) for x,y in rope],fill='#d7c493',width=1)
    kd.line(rope,fill='#a69468',width=1)
    kd.ellipse((4,16,8,20),outline='#d4bb81')
    kd.ellipse((63,16,67,20),outline='#d4bb81')
    images['cave_keeper_rail']=keeper_rail

    marker=texture((18,28),masonry)
    mmask=Image.new('L',marker.size)
    ImageDraw.Draw(mmask).polygon([(1,27),(1,6),(5,1),(12,1),(16,6),(16,27)],fill=255)
    marker.putalpha(mmask)
    md=ImageDraw.Draw(marker)
    md.line((5,9,12,9),fill='#777d68');md.line((5,12,11,12),fill='#777d68')
    md.line((5,15,12,15),fill='#777d68')
    images['memorial_marker']=marker
    board=Image.new('RGBA',(32,30))
    bd=ImageDraw.Draw(board)
    bd.rectangle((4,15,7,29),fill='#665b3f');bd.rectangle((25,15,28,29),fill='#665b3f')
    bd.rectangle((0,0,31,20),fill='#685c3f',outline='#424c37')
    bd.rectangle((3,3,28,17),fill='#d0c8a5',outline='#a79a75')
    for y,w in ((6,18),(9,21),(12,15)):bd.line((6,y,w,y),fill='#887a56')
    images['survey_board']=board
    stake=Image.new('RGBA',(8,26));sd=ImageDraw.Draw(stake)
    sd.rectangle((3,0,5,25),fill='#8c744b');sd.line((3,0,3,25),fill='#c6b477')
    sd.polygon([(5,1),(7,4),(5,8)],fill='#c9b483')
    images['survey_stake']=stake
    basin=Image.new('RGBA',(48,34));bd=ImageDraw.Draw(basin)
    bd.ellipse((3,10,44,32),fill='#5f705d')
    bd.ellipse((1,2,46,27),fill='#858e74',outline='#4d6553',width=2)
    bd.ellipse((5,4,42,23),fill='#c9c4a5',outline='#a0a58a',width=2)
    bd.ellipse((10,8,37,20),fill='#466f70',outline='#6e9a91',width=2)
    bd.line((14,11,25,11),fill='#bfd6b5')
    images['basin']=basin

    sources=sorted({record['path'] for record in CROPS})
    metadata={
        'version':1,'tile_size':24,'authoring':'native_modular_source_assembly',
        'shade_factors':{'cloister_floor':.60,'cloister_back_wall':.48},
        'source_crops':CROPS,
        'source_sha256':{path:sha256((ROOT/path).read_bytes()).hexdigest() for path in sources},
        'modules':{
            'hall':{'size':[288,216],'ground_rect':[24,120,240,84],
                    'door_anchor':[144,210],'door_clearance':[128,174,32,42]},
            'cloister':{'size':[240,120],'column_x':[0,76,152,228],
                        'column_position_y':44,'back_wall_rect':[0,48,240,12],
                        'column_ground_rects':[[x,100,12,12] for x in (0,76,152,228)],
                        'bay_centers':[[44,92],[120,92],[196,92]]},
            'entrance_arch':{'size':[96,96],'ground_rects':[[0,80,24,16],[72,80,24,16]],
                             'opening':[24,40,48,56],'anchor':[48,96]},
            'cave':{'size':[160,128],'mouth_rect':[47,78,67,50],'anchor':[80,116]},
            'cave_keeper_rail':{'size':[72,48],'ground_rect':[0,30,72,12]},
        }}
    return images, metadata


def products():
    images,metadata=make_kit()
    result={}
    for name,image in images.items():
        body=BytesIO();image.save(body,format='PNG');result[name+'.png']=body.getvalue()
    result['kit.json']=(json.dumps(metadata,indent=2)+'\n').encode()
    return result


def build(check=False):
    exports=products()
    if check:
        for name,data in exports.items():
            if not (OUTPUT/name).is_file() or (OUTPUT/name).read_bytes()!=data:
                raise ValueError('Stale Sanctuary modular kit: '+name)
    else:
        OUTPUT.mkdir(parents=True,exist_ok=True)
        for name,data in exports.items():(OUTPUT/name).write_bytes(data)
    print(('Verified' if check else 'Exported')+' source-derived Sanctuary stone kit')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
