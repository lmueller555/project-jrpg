"""Build the compact upstream millrace scene from approved Eldenmere terrain.

Ground grass, dirt transitions, water banks/animation and trees are exact native
approved assets. The intake props use their wood/iron/stone and water palettes.
Only this new scene and the town's reversible-link metadata are authored here.
"""
from pathlib import Path
from random import Random
import json, math
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'assets/maps/eldenmere/upstream'
ART=ROOT/'assets/story/mill'
PROPS=ART/'props'
SIZE=(768,576);TILE=24

def read(p):return json.loads((ROOT/p).read_text())
def load(p):return Image.open(ROOT/p).convert('RGBA')
def rel(p):return p.relative_to(ROOT).as_posix()
def save(im,p):p.parent.mkdir(parents=True,exist_ok=True);im.save(p);return rel(p)
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def mask_for(cells,x,y):
    offsets=[(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]
    bits=0
    for i,(dx,dy) in enumerate(offsets):
        if (x+dx,y+dy) not in cells:continue
        if dx and dy and ((x+dx,y) not in cells or (x,y+dy) not in cells):continue
        bits|=1<<i
    return bits

PAL=read('assets/terrain/eldenmere/irrigation/palette.json')['materials']
GATE=read('assets/terrain/eldenmere/gate/palette.json')['materials']
W=PAL['water'];D=PAL['dirt'];WOOD=GATE['wood'];IRON=GATE['iron'];STONE=GATE['stone']

def native_props():
    PROPS.mkdir(parents=True,exist_ok=True)
    result=[]
    def record(name,pos,states,sort_y,**extra):
        paths={}
        for state,im in states.items():paths[state]=save(im,PROPS/f'{name}_{state}.png')
        result.append({'id':name,'scene':'upstream','position':list(pos),'sort_y':sort_y,'states':paths,**extra})
    def screen(progress=0,prepared=False):
        im=Image.new('RGBA',(96,84));d=ImageDraw.Draw(im)
        # Two dry stone abutments and an iron intake screen over the existing race.
        for x in (12,46):
            d.rectangle((x,2,x+10,60),fill=STONE['shadow'])
            for y in range(3,61,8):
                d.rectangle((x+1,y,x+9,y+5),fill=STONE['base'])
                d.line((x+1,y,x+9,y),fill=STONE.get('cap',STONE['base']))
        lift=round(12*progress)
        d.rectangle((23,10-lift,45,44-lift),fill=IRON['shadow'])
        for x in range(25,45,4):d.line((x,12-lift,x,43-lift),fill=IRON['base'])
        d.line((23,10-lift,45,10-lift),fill=IRON['light'],width=2)
        d.line((23,43-lift,45,43-lift),fill=IRON['base'],width=2)
        d.rectangle((5,52,49,56),fill=WOOD['shadow']);d.line((6,52,48,52),fill=WOOD['light'])
        if progress<1:
            # The branch is physically drawn west onto the dry bank during repair.
            dx=round(-20*progress);dy=round(19*progress)
            pts=[(12+dx,13+dy),(28+dx,29+dy),(54+dx,32+dy),(68+dx,42+dy)]
            d.line(pts,fill=WOOD['shadow'],width=9)
            d.line(pts,fill=WOOD['base'],width=5)
            d.line([(13+dx,12+dy),(29+dx,27+dy),(55+dx,30+dy)],fill=WOOD['light'])
            d.line((29+dx,28+dy,31+dx,8+dy),fill=WOOD['shadow'],width=4)
            d.line((31+dx,9+dy,32+dx,3+dy),fill=WOOD['base'],width=2)
            d.ellipse((63+dx,37+dy,70+dx,44+dy),fill=WOOD['light'],outline=WOOD['shadow'])
        else:
            d.line((2,65,34,74,57,73),fill=WOOD['shadow'],width=8)
            d.line((2,64,34,72,57,71),fill=WOOD['base'],width=4)
            d.line((28,70,24,59),fill=WOOD['shadow'],width=3)
        # Rope already secured around the limb after the bypass is isolated.
        if prepared or progress:
            d.line((12,55,29-round(20*progress),28+round(19*progress)),fill='#d8c39c')
        return im
    moving=[save(screen(i/5,True),PROPS/f'intake_move_{i}.png') for i in range(6)]
    record('intake_screen',(492,184),{'blocked':screen(),'prepared':screen(0,True),'cleared':screen(1,True),'restored':screen(1,True)},264,moving_frames=moving)
    def bypass(closed):
        im=Image.new('RGBA',(54,38));d=ImageDraw.Draw(im)
        d.rectangle((30,0,45,37),fill=WOOD['shadow']);d.rectangle((32,1,43,36),fill=WOOD['base'])
        for y in (5,21):d.line((31,y,44,y),fill=IRON['shadow'],width=2)
        d.line((16,18,36,18),fill=IRON['base'],width=2)
        d.ellipse((10,12,22,24),outline=IRON['shadow'],width=3)
        d.ellipse((12,14,20,22),outline=IRON['light'])
        if closed:d.line((16,12,16,24),fill=WOOD['light'],width=2)
        else:d.line((10,18,22,18),fill=WOOD['light'],width=2)
        d.ellipse((15,17,17,19),fill=IRON['light'])
        return im
    record('bypass',(482,260),{'blocked':bypass(False),'prepared':bypass(True),'cleared':bypass(True),'restored':bypass(False)},298)
    def pool(t):
        im=Image.new('RGBA',(54,36));d=ImageDraw.Draw(im)
        d.rectangle((0,0,29,31),fill=STONE['shadow'])
        d.rectangle((1,1,28,29),fill=STONE['base'])
        d.rectangle((4,4,24,26),fill=D['shadow'])
        d.rectangle((6,6,22,24),fill=D['edge'])
        # Inspection catch lies at world (502,340), reachable from the south.
        d.rectangle((7,22,11,27),fill=IRON['shadow'])
        d.line((8,23,8,26),fill=IRON['light'])
        # The adjacent stone trough drains into the existing race at x536.
        d.rectangle((26,16,52,25),fill=STONE['shadow'])
        d.rectangle((27,17,53,23),fill=D['shadow'])
        d.line((27,17,51,17),fill=STONE.get('cap',STONE['base']))
        height=round(19*(1-t))
        if height:
            d.rectangle((6,8+19-height,22,26),fill=W['base'])
            d.line((7,8+19-height,21,8+19-height),fill=W['glint'])
            d.line((9,11+19-height,14,min(26,11+19-height)),fill=W['reflection'])
        if 0<t<1:
            # A compact moving stream, no flash-only success or new water source.
            end=27+round(t*25)
            d.line((22,19,28,20,end,20),fill=W['flow'],width=2)
            d.point((end,20),fill=W['glint'])
        if t>=1:
            d.line((30,21,51,21),fill=W['deep'])
        return im
    spell=[save(pool(i/5),PROPS/f'pool_spell_{i}.png') for i in range(6)]
    record('inspection_pool',(494,316),{'blocked':pool(0),'prepared':pool(0),'cleared':pool(1),'restored':pool(1)},350,animation=spell)
    def lever(up):
        im=Image.new('RGBA',(60,42));d=ImageDraw.Draw(im)
        d.rectangle((28,16,43,38),fill=STONE['shadow'])
        d.rectangle((30,17,41,36),fill=STONE['base'])
        pivot=(34,18);grip=(12,16 if up else 29)
        d.line((*grip,*pivot,52,10 if up else 4),fill=WOOD['shadow'],width=5)
        d.line((*grip,*pivot,52,10 if up else 4),fill=WOOD['light'],width=2)
        d.rectangle((10,grip[1]-1,15,grip[1]+1),fill=IRON['shadow'])
        d.ellipse((31,15,37,21),fill=IRON['base']);d.point((34,18),fill=IRON['light'])
        d.line((52,8,53,-1),fill='#d8c39c')
        return im
    record('lever',(486,358),{'blocked':lever(True),'prepared':lever(True),'cleared':lever(False),'restored':lever(False)},399)
    # The running main stream is never replaced. Only this small millrace changes.
    def race(phase,full):
        im=Image.new('RGBA',(24,408));d=ImageDraw.Draw(im)
        d.rectangle((6,0,17,407),fill=D['shadow'])
        d.line((5,0,5,407),fill=D['edge']);d.line((18,0,18,407),fill=D['edge'])
        a,b=(8,15) if full else (11,12)
        d.rectangle((a,0,b,407),fill=W['base'])
        for y in range(phase*2,408,18):d.line((max(a,10),y,min(b,13),y),fill=W['reflection'])
        return im
    flowing=[save(race(i,True),PROPS/f'race_flow_{i}.png') for i in range(6)]
    record('millrace_flow',(528,168),{'blocked':race(0,False),'prepared':race(0,False),'cleared':race(0,False),'restored':race(0,True)},-9999,restored_frames=flowing)
    return result


def build_scene():
    MAP.mkdir(parents=True,exist_ok=True)
    rng=Random(1729)
    grassmeta=read('assets/terrain/eldenmere/grass_dirt/tileset.json')
    grass=[load('assets/terrain/eldenmere/grass_dirt/'+p) for p in grassmeta['grass']['images']]
    dirt=load('assets/terrain/eldenmere/grass_dirt/'+grassmeta['image'])
    stream=read('assets/terrain/eldenmere/stream/tileset.json')
    banks=load('assets/terrain/eldenmere/stream/'+stream['banks'])
    water=[load('assets/terrain/eldenmere/stream/'+f['image']) for f in stream['frames'][:6]]
    dirtcells={(x,y) for x in range(6,9) for y in range(9,24)}
    dirtcells|={(x,y) for x in range(8,20) for y in range(12,15)}
    dirtcells|={(x,y) for x in range(17,22) for y in range(9,19)}
    streamcells={(x,y) for x in range(-1,33) for y in range(4,7)}
    streamcells|={(x,3) for x in list(range(4,9))+list(range(16,20))}
    streamcells|={(x,7) for x in list(range(2,5))+list(range(13,16))+list(range(25,28))}
    base=Image.new('RGBA',SIZE)
    for y in range(24):
        for x in range(32):base.alpha_composite(grass[rng.randrange(len(grass))],(x*24,y*24))
    for x,y in sorted(dirtcells):
        mask=mask_for(dirtcells,x,y);idx=grassmeta['lookup_256'][mask];rect=grassmeta['tiles'][idx]['rect']
        base.alpha_composite(dirt.crop((rect[0],rect[1],rect[0]+24,rect[1]+24)),(24*x,24*y))
    tree=load('assets/terrain/eldenmere/foliage/tree/idle.png')
    shrub=load('assets/terrain/eldenmere/foliage/shrub/idle.png')
    treepos=[(-24,-40),(48,-42),(134,-50),(228,-36),(322,-48),(420,-44),(522,-44),(620,-46),(708,-42),
             (-38,142),(-22,260),(-28,376),(10,470),(80,410),(242,424),(300,410),(600,164),(660,202),(624,326),(684,414),(550,458),(36,300),(28,396),(350,446),(430,438),(654,440),(706,454)]
    collision=Image.new('RGB',SIZE,'black');c=ImageDraw.Draw(collision)
    c.rectangle((0,0,767,15),fill='white');c.rectangle((0,0,15,575),fill='white');c.rectangle((752,0,767,575),fill='white');c.rectangle((0,560,767,575),fill='white')
    for x,y in streamcells:c.rectangle((24*x,24*y,24*x+23,24*y+23),fill='white')
    c.rectangle((532,168,547,575),fill='white')
    # Permanent stone/control footprints; state changes never mutate navigation.
    for rect in [(504,184,551,265),(516,260,527,298),(494,316,523,347),(516,358,547,399)]:c.rectangle(rect,fill='white')
    # Trees are depth-sorted entities so their canopies occlude, not their full art.
    entities=[]
    for i,(x,y) in enumerate(treepos):
        entities.append({'id':f'upstream_tree_{i}','position':[x,y],'sort_y':y+112,'frames':['assets/terrain/eldenmere/foliage/tree/idle.png'],'frame_duration_ms':600,'phase_offset':0})
        c.rectangle((x+36,y+96,x+59,y+119),fill='white')
    for i,(x,y) in enumerate([(290,228),(330,204),(358,416),(596,414),(60,212),(260,370),(690,338),(226,180),(678,510)]):
        base.alpha_composite(shrub,(x,y));c.rectangle((x+3,y+13,x+20,y+23),fill='white')
    # Stones and a small direction sign at the southern entrance.
    d=ImageDraw.Draw(base)
    d.rectangle((216,490,219,513),fill=WOOD['shadow']);d.rectangle((202,489,234,498),fill=WOOD['base']);d.line((204,489,232,489),fill=WOOD['light'])
    d.line((207,493,223,493),fill=IRON['shadow']);d.line((207,493,212,490),fill=IRON['shadow']);d.line((207,493,212,496),fill=IRON['shadow'])
    c.rectangle((216,506,220,514),fill='white')
    frames=[]
    for phase in range(6):
        ground=base.copy()
        for x,y in sorted(streamcells):
            if not 0<=x<32:continue
            mask=mask_for(streamcells,x,y);idx=stream['lookup_256'][mask];rx,ry,_,_=stream['tiles'][idx]['rect']
            ground.alpha_composite(water[phase].crop((rx,ry,rx+24,ry+24)),(24*x,24*y))
            ground.alpha_composite(banks.crop((rx,ry,rx+24,ry+24)),(24*x,24*y))
        # Sparse marks advance east in the main stream; the side race flows south.
        gd=ImageDraw.Draw(ground)
        for x in range(phase*2-24,768,37):
            gd.line((x,126,x+3,126),fill=W['reflection'])
            gd.line((x+17,145,x+20,145),fill=W['flow'])
        # A dry earth race bed is visible beneath the controller's trickle/full overlay.
        gd=ImageDraw.Draw(ground);gd.rectangle((532,168,547,575),fill=D['shadow'])
        gd.line((531,168,531,575),fill=D['edge']);gd.line((548,168,548,575),fill=D['edge'])
        frames.append(save(ground.convert('RGB'),MAP/'ground'/f'frame_{phase+1:02}.png'))
    collisionpath=save(collision,MAP/'collision.png')
    overview=Image.open(ROOT/frames[0]).convert('RGB')
    for e in entities:overview.paste(tree,tuple(e['position']),tree)
    overviewpath=save(overview,MAP/'overview.png')
    destination='assets/maps/eldenmere/playable/map.json'
    record={'id':'upstream','name':'Upper Millrace','kind':'exterior','size_tiles':[32,24],'tile_size':24,'size_pixels':list(SIZE),'spawn':[168,516],
            'player_probe_size':[24,12],'player_draw_anchor':[12,30],'ground_frames':frames,'ground_frame_duration_ms':200,'collision':collisionpath,
            'entities':entities,'foreground':[],'npcs':[],'landmarks':[{'id':'intake','name':'Millrace intake','position':[480,288]}],
            'overview':overviewpath,'world_links':[{'id':'upstream_to_town','position':[168,516],'destination':destination,'spawn':[720,192],'arrival_facing':'front','label':'Return to Eldenmere','radius':22}]}
    write(MAP/'map.json',record)
    townpath=ROOT/'assets/maps/eldenmere/playable/map.json';town=json.loads(townpath.read_text())
    town.setdefault('exterior_scenes',{})['upstream']=rel(MAP/'map.json')
    links=town.setdefault('world_links',[]);links[:]=[l for l in links if l.get('id')!='town_to_upstream']
    links.append({'id':'town_to_upstream','position':[720,168],'destination':rel(MAP/'map.json'),'spawn':[168,492],'arrival_facing':'back','label':'Follow the millrace upstream','radius':22})
    write(townpath,town)


def build():
    build_scene()
    props=native_props()
    layout={'scene_id':'upstream','town_trail':[720,168],'mill_mechanism':[960,384],'mill_race':[1080,384],
            'entrance':[168,516],'intake':[456,240],'bypass':[456,288],'spell':[480,336],'lever':[456,384],
            'mira_intake':[492,240],'mira_bypass':[492,288],'mira_spell':[492,352],'mira_lever':[492,384],
            'mill_return':[984,408],'halden_resolution':[1032,408],
            'pool_rect':[494,316,54,36],'catch':[502,340],'bypass_handle':[498,278],'lever_grip':[498,374]}
    write(ART/'layout.json',layout)
    write(ART/'art.json',{'version':1,'palette_sources':['assets/terrain/eldenmere/irrigation/palette.json','assets/terrain/eldenmere/gate/palette.json'],
                          'props':props,'water_conservation':'Residual inspection water moves into the adjacent drain; the main stream continues to flow.'})
    print('Built upstream scene, reversible town link, and five stateful intake props.')

if __name__=='__main__':build()
