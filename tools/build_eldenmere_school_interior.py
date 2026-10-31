"""Build a welcoming one-room village school with reusable native furnishings."""
from collections import deque
import math
from pathlib import Path

from PIL import Image,ImageDraw
from build_eldenmere_stream import read_json,write_json,rgba
from build_eldenmere_cottage_layouts import shell,source_object
from build_eldenmere_cottage_hearth import mix

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/terrain/eldenmere/school/interior'
SOURCE=ROOT/'assets/source/terrain/eldenmere/school/interior'
SIZE=(432,384)
WOOD=read_json(ROOT/'assets/terrain/eldenmere/cottage_furniture/furniture.json')['palette']


def blank(size):return Image.new('RGBA',size)
def opened(path):return Image.open(path).convert('RGBA')
def save(path,image):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path);return path.relative_to(ROOT).as_posix()


def export(name,layers):
    image=blank(next(iter(layers.values())).size);paths=[]
    for key,layer in layers.items():
        paths.append(save(SOURCE/'sprites'/name/(key+'.png'),layer));image.alpha_composite(layer)
    path=save(OUT/'sprites'/(name+'.png'),image)
    return path,image,paths


def table(name,teacher=False,festival=False):
    size=(72,48) if teacher else (64,40)
    frame=blank(size);d=ImageDraw.Draw(frame);w,h=size
    d.rectangle((3,13,w-4,h-3),fill=WOOD['outline'])
    for x in (5,w-9):
        d.rectangle((x,21,x+4,h-4),fill=WOOD['wood_shadow']);d.line((x,22,x,h-5),fill=WOOD['wood_light'])
    d.polygon(((2,8),(w-6,8),(w-2,12),(w-2,27),(5,27),(2,24)),fill=WOOD['outline'])
    d.rectangle((4,10,w-5,22),fill=WOOD['wood_base']);d.line((5,10,w-6,10),fill=WOOD['wood_worn'])
    d.polygon(((4,23),(w-4,23),(w-4,26),(6,26),(4,24)),fill=WOOD['wood_shadow'])
    for y in (14,19):d.line((6,y,w-7,y),fill=WOOD['wood_shadow'])
    for x,y in ((11,12),(35,18),(54,16)):d.line((x,y,min(x+5,w-7),y),fill=WOOD['wood_light'])
    work=blank(size);q=ImageDraw.Draw(work)
    if festival:
        q.rectangle((8,11,31,21),fill='#e1d6bc')
        for x in (10,17,24):q.line((x,13,x+4,18),fill='#ac8051');q.line((x+4,13,x,18),fill='#ac8051')
        q.rectangle((42,12,53,20),fill='#654e3c');q.rectangle((44,13,51,19),fill='#e7bb64')
        q.line((43,11,52,11),fill='#45382d');q.arc((44,7,51,14),180,360,fill='#45382d')
        q.point((47,16),fill='#fff0bd');q.rectangle((34,17,38,20),fill='#836347')
    elif teacher:
        q.polygon(((8,11),(22,12),(25,14),(28,12),(42,11),(42,23),(28,22),(25,24),(22,22),(8,23)),fill='#45382d')
        q.polygon(((10,12),(22,13),(24,15),(24,22),(21,21),(10,22)),fill='#e1d6bc')
        q.polygon(((26,15),(29,13),(40,12),(40,22),(29,21),(26,22)),fill='#d3c6a4')
        for y in (16,19):q.line((12,y,21,y),fill='#a99a7e');q.line((29,y,38,y),fill='#a99a7e')
        q.rectangle((50,17,55,22),fill='#45382d');q.rectangle((51,18,54,20),fill='#657879')
        q.line((54,18,58,10),fill='#ded1ae');q.point((58,10),fill='#fbeed0')
        q.rectangle((59,16,65,21),fill='#53696e');q.line((60,17,64,17),fill='#ded1ae')
    else:
        for x in (9,37):
            q.rectangle((x,11,x+16,21),fill='#45382d');q.rectangle((x+1,12,x+15,20),fill='#53696e')
            q.line((x+3,14,x+10,14),fill='#ded1ae');q.line((x+3,17,x+7,17),fill='#ded1ae')
            q.line((x+18,13,x+18,18),fill='#fbeed0')
        for x in (29,31,33):q.point((x,19 if x==31 else 17),fill='#b79a6c')
    return export(name,{'timber':frame,'work_on_tabletop':work})


def board():
    frame=blank((144,48));d=ImageDraw.Draw(frame)
    d.rectangle((2,2,141,43),fill=WOOD['outline']);d.rectangle((4,4,139,41),fill=WOOD['wood_base'])
    d.rectangle((7,6,136,37),fill='#354d48');d.line((7,6,136,6),fill='#223a35')
    d.rectangle((4,40,139,44),fill=WOOD['wood_light']);d.line((4,40,139,40),fill=WOOD['wood_worn'])
    chalk=blank(frame.size);d=ImageDraw.Draw(chalk)
    # Uneven, readable chalk glyphs instead of font rendering at sprite scale.
    glyphs={'A':[(0,6,0,2),(0,2,2,0),(2,0,4,2),(4,2,4,6),(0,3,4,3)],
            'B':[(0,0,0,6),(0,0,3,0),(3,0,4,1),(4,1,3,3),(0,3,3,3),(3,3,4,4),(4,4,3,6),(0,6,3,6)],
            'C':[(4,0,1,0),(1,0,0,1),(0,1,0,5),(0,5,1,6),(1,6,4,6)]}
    for i,c in enumerate('ABC'):
        for x,y,xx,yy in glyphs[c]:d.line((15+i*12+x,12+y,15+i*12+xx,12+yy),fill='#ded1ae')
    for i in range(5):d.line((69+i*7,12,69+i*7,18),fill='#ded1ae')
    d.line((67,19,100,11),fill='#ded1ae')
    d.line((15,27,62,27),fill='#889e91');d.line((73,27,119,27),fill='#889e91')
    for x in (18,27,36):d.rectangle((x,25,x+3,28),fill='#ded1ae')
    d.line((115,41,121,41),fill='#fbeed0');d.rectangle((125,40,132,42),fill='#654e3c')
    return export('writing_board',{'wooden_frame':frame,'chalk_exercise':chalk})


def village_map():
    # Retain the furnishing ID and footprint used by classroom approaches.
    # The small prop and the inspectable original share one approved geography.
    im=opened(ROOT/'assets/world/auratia/wall_map.png')
    assert im.size==(42,40),im.size
    return export('village_map',{'auratia_world_map':im})


def bookcase():
    im=blank((48,72));d=ImageDraw.Draw(im)
    d.rectangle((4,8,43,66),fill=WOOD['outline']);d.rectangle((6,10,41,63),fill=WOOD['wood_shadow'])
    for y in (11,29,47,62):
        d.rectangle((5,y,42,y+3),fill=WOOD['wood_base']);d.line((6,y,41,y),fill=WOOD['wood_light'])
    colors=('#7b9065','#53696e','#a08158','#bcae91','#836347')
    for row,top in enumerate((15,33,51)):
        for col,x in enumerate(range(8,39,6)):
            high=10 if (row+col)%3 else 8
            d.rectangle((x,top+11-high,x+4,top+11),fill=colors[(row+col)%len(colors)])
            d.line((x,top+11-high,x,top+11),fill='#45382d');d.point((x+2,top+9),fill='#ded1ae')
    d.line((7,66,41,66),fill=WOOD['wood_worn'])
    return export('bookshelf',{'shelves_and_treasured_books':im})


def bench():
    im=blank((72,32));d=ImageDraw.Draw(im)
    d.rectangle((6,11,65,17),fill=WOOD['outline']);d.rectangle((8,12,63,15),fill=WOOD['wood_base'])
    d.line((8,12,63,12),fill=WOOD['wood_worn'])
    for x in (9,59):d.rectangle((x,17,x+3,27),fill=WOOD['wood_shadow'])
    d.rectangle((14,10,28,14),fill='#7b9065');d.line((15,11,27,11),fill='#a1ae83')
    d.rectangle((46,8,59,12),fill='#d3c6a4');d.line((47,9,57,9),fill='#53696e')
    return export('reading_bench',{'worn_bench_and_reading_books':im})


def wall_details():
    pegs=blank((24,48));d=ImageDraw.Draw(pegs)
    d.line((5,4,20,4),fill=WOOD['wood_light'],width=2)
    for x in (7,13,19):
        d.point((x,6),fill='#45382d');d.line((x,6,x,9),fill='#737e7a')
    d.polygon(((6,9),(3,12),(5,22),(11,22),(11,12),(8,9)),fill='#7b9065')
    d.polygon(((16,9),(12,12),(14,27),(20,27),(21,12),(18,9)),fill='#53696e')
    d.line((7,11,7,21),fill='#566b50');d.line((17,11,17,26),fill='#354d48')
    export('coat_pegs',{'peg_rail_and_small_coats':pegs})
    art=blank((16,30));d=ImageDraw.Draw(art)
    for top in (1,16):
        d.rectangle((1,top,13,top+12),fill='#e1d6bc');d.point((7,top),fill='#836347')
    d.line((3,9,3,6,7,3,11,6,11,10),fill='#a08158');d.line((3,10,11,10),fill='#a08158')
    d.line((4,24,10,24,11,26),fill='#53696e');d.point((3,23),fill='#53696e');d.line((6,25,6,27),fill='#53696e')
    export('child_drawings',{'houses_and_dog_sketches':art})


def object_record(identifier,path,pos,size,foot,access,sort=None):
    return {'id':identifier,'position':list(pos),'frame_size':list(size),'image_from_repo_root':path,
            'floor_rect':foot,'sort_y':(0 if foot is None else foot[1]+foot[3]) if sort is None else sort,'access':list(access)}


def build():
    OUT.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
    layout={'floor_tiles':[16,12],'supports':[24,138,288,402],
            'window_positions':[[48,30],[300,30]],'partition':None}
    floor,walls,fixtures,partition,structure=shell(layout,[204,360,24,8])
    # Preserve the approved shell materials, without resizing native floor tiles.
    layers={'floor':floor,'walls':walls,'fixtures':fixtures}
    for name,im in layers.items():save(OUT/(name+'.png'),im);save(SOURCE/'shell'/(name+'.png'),im)
    save(OUT/'structure.png',structure)
    assets={}
    for name,creator in [('pupil_desk',lambda:table('pupil_desk')),('teacher_desk',lambda:table('teacher_desk',True)),
                         ('festival_corner',lambda:table('festival_corner',festival=True)),('writing_board',board),
                         ('village_map',village_map),('bookshelf',bookcase),('reading_bench',bench)]:assets[name]=creator()
    wall_details();objects=[]
    def new(identifier,asset,pos,foot,access,sort=None):
        path,im,_=assets[asset];objects.append(object_record(identifier,path,pos,im.size,foot,access,sort))
    new('writing_board','writing_board',(144,27),None,(216,100),0)
    new('village_map','village_map',(96,28),None,(108,94),0)
    new('teacher_desk','teacher_desk',(104,102),[106,124,68,18],(140,154))
    teacher=source_object({'id':'teacher_chair','pack':'cottage_furniture','sprite':'chair_down','position':[128,72],'access':[184,108]});objects.append(teacher)
    for i,(x,y) in enumerate(((76,164),(280,164),(76,256)),1):
        new(f'pupil_desk_{i}','pupil_desk',(x,y),[x+2,y+18,60,20],(x+32,y-12))
        for seat,dx in enumerate((4,36)):
            cx=x+dx;cy=y+26;access=[x-10,cy+32] if seat==0 else [x+78,cy+32]
            objects.append(source_object({'id':f'pupil_chair_{(i-1)*2+seat+1}','pack':'cottage_furniture','sprite':'chair_up','position':[cx,cy],'access':access}))
    new('bookshelf','bookshelf',(352,108),[356,166,40,16],(374,194))
    new('festival_corner','festival_corner',(286,260),[288,278,60,20],(318,246))
    new('reading_bench','reading_bench',(286,312),[292,329,60,10],(320,350))
    for name,pos,access in [('coat_pegs',(20,270),(48,298)),('child_drawings',(336,35),(346,110))]:
        im=opened(OUT/'sprites'/f'{name}.png');objects.append(object_record(name,(OUT/'sprites'/f'{name}.png').relative_to(ROOT).as_posix(),pos,im.size,None,access,0))
    objects.append({'id':'hearth','position':[350,24],'frame_size':[48,72],
                    'floor_rect':[352,72,44,20],'sort_y':92,'access':[374,104],
                    'image_from_repo_root':'assets/terrain/eldenmere/cottage_hearth/frames/frame_01.png'})
    # Native-color daylight bands follow the panes; hearth shimmer stays subtle.
    wood=list(read_json(ROOT/'assets/source/terrain/eldenmere/cottage_interior/recipe.json')['palette']['wood'].values())
    base_colors=[rgba(c) for c in wood]
    daylight=read_json(ROOT/'assets/terrain/eldenmere/cottage_interior/palette.json')['daylight']
    day_strength=(0,0,1,1,2,2,1,1,0)
    fire=read_json(ROOT/'assets/source/terrain/eldenmere/cottage_hearth/recipe.json')
    daymask=Image.new('L',SIZE);d=ImageDraw.Draw(daymask)
    for wx in (48,300):
        d.polygon(((wx+7,76),(wx+28,76),(wx+47,120),(wx+18,120)),fill=255)
        d.line((wx+18,77,wx+35,118),fill=0,width=2)
    save(OUT/'daylight_mask.png',daymask)
    for tick in range(36):
        overlay=blank(SIZE);strength=day_strength[tick//2%9]
        for y in range(76,121):
            for x in range(24,408):
                if daymask.getpixel((x,y)):
                    pixel=floor.getpixel((x,y))
                    if pixel in base_colors:
                        overlay.putpixel((x,y),rgba(list(daylight[strength].values())[base_colors.index(pixel)]))
        # The same two-strength warm pool as the cottage hearth, not sparkles.
        for x in range(352,398):
            for y in range(92,113):
                distance=((x-374)/23)**2+((y-100)/11)**2
                if distance<=1:
                    base=floor.getpixel((x,y))
                    overlay.putpixel((x,y),mix(base,rgba(fire['glow_color']),fire['glow_strengths'][tick%4]*(1 if distance<.45 else .5)))
        save(OUT/'lighting'/f'frame_{tick+1:02}.png',overlay)
        save(SOURCE/'lighting'/f'frame_{tick+1:02}.png',overlay)
    status=read_json(OUT/'room.json')['status'] if (OUT/'room.json').exists() else 'review'
    meta={'id':'school','name':'Eldenmere schoolroom','status':status,'floor_tiles':[16,12],'room_size':list(SIZE),
          'floor_rect':[24,72,384,288],'entry_rect':[204,360,24,8],'partition_rect':None,'objects':objects,
          'teacher_role':'liam_mother','seat_count':6,'pupil_desk_count':3,'central_aisle':[192,96,60,258],
          'lighting_frame_count':36,'lighting_frame_duration_ms':300,'npcs':[],
          'world_map_display':{'entity_id':'village_map','position':[108,94],'radius':22,
                               'label':'Examine Auratia’s world map'},
          'notes':'Welcoming school with room for six children. Teacher and pupil action schedules are a later stage.'}
    write_json(OUT/'room.json',meta)
    write_json(SOURCE/'recipe.json',{'id':'eldenmere.school.interior','status':status,'native_tile_size':24,
        'room_size':list(SIZE),'floor_rect':meta['floor_rect'],'shell_source':'assets/terrain/eldenmere/cottage_interior',
        'furniture_palette':'assets/terrain/eldenmere/cottage_furniture/furniture.json','objects':objects,
        'world_map_display':meta['world_map_display'],
        'features':['six pupil seats','three slate desks','teacher book and ink','chalk counting lesson','Auratia world map with polar regions','child house and dog drawings','shared worn books','festival paper patterns and lantern']})
    # Validate every destination with the same 24x12 floor probe as the game.
    blocked=Image.new('L',SIZE,255);blocked.paste(0,(24,72,408,360))
    for obj in objects:
        if obj.get('floor_rect'):
            x,y,w,h=obj['floor_rect'];blocked.paste(255,(x,y,x+w,y+h))
    def valid(point):
        x,y=point
        return not blocked.crop((x-12,y-6,x+12,y+6)).getbbox()
    visited={(216,342)};queue=deque(visited)
    while queue:
        x,y=queue.popleft()
        for q in ((x-2,y),(x+2,y),(x,y-2),(x,y+2)):
            if q not in visited and 36<=q[0]<=396 and 78<=q[1]<=354 and valid(q):visited.add(q);queue.append(q)
    missing=[(o['id'],o['access']) for o in objects if tuple(o['access']) not in visited]
    assert not missing,missing
    save(OUT/'collision_review.png',blocked)
    assembled=structure.copy();assembled.alpha_composite(opened(OUT/'lighting/frame_01.png'))
    for obj in sorted(objects,key=lambda o:o['sort_y']):assembled.alpha_composite(opened(ROOT/obj['image_from_repo_root']),tuple(obj['position']))
    save(OUT/'assembled.png',assembled);save(OUT/'assembled_enlarged.png',assembled.resize((864,768),Image.Resampling.NEAREST))
    print(f'Built 16x12 schoolroom, three shared desks/six seats; {len(objects)} object approaches reachable.')


if __name__=='__main__':build()
