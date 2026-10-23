"""Draw the proposed town as a measured planning diagram, not finished game art."""
from collections import deque
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'docs/world/eldenmere/blockout'
TILE = 24
ORIGIN = (72, 168)
BOARD_SIZE = (2304, 1600)
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
COLORS = {'ink': '#283a35', 'muted': '#60716b', 'paper': '#f4f2e9',
          'ground': {1: '#c7d4af', 2: '#b2c598', 3: '#829b7d'},
          'water': '#5e9daf', 'channel': '#447e98', 'road': '#dfcfad',
          'road_edge': '#baa781', 'cliff': '#8b856a', 'orange': '#d16a27',
          'purple': '#8b468d', 'blue': '#315ba0'}


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_DIR/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size)


def cells(rect):
    x,y,w,h=rect
    return {(xx,yy) for yy in range(y,y+h) for xx in range(x,x+w)}


def centre(point):
    return (ORIGIN[0]+point[0]*TILE+TILE/2, ORIGIN[1]+point[1]*TILE+TILE/2)


def bounds(rect):
    x,y,w,h=rect
    return (ORIGIN[0]+x*TILE,ORIGIN[1]+y*TILE,ORIGIN[0]+(x+w)*TILE,ORIGIN[1]+(y+h)*TILE)


def line_cells(points,width=1):
    result=set()
    lo=-(width//2)
    for a,b in zip(points,points[1:]):
        x1,y1=a[:2];x2,y2=b[:2]
        if x1!=x2 and y1!=y2:
            raise ValueError('Planning polylines must follow the tile grid.')
        if x1==x2:
            result.update((x1+offset,y) for y in range(min(y1,y2),max(y1,y2)+1) for offset in range(lo,lo+width))
        else:
            result.update((x,y1+offset) for x in range(min(x1,x2),max(x1,x2)+1) for offset in range(lo,lo+width))
    return result


def interpolate(value,stops):
    for (a,va),(b,vb) in zip(stops,stops[1:]):
        if a<=value<=b:
            return va+(vb-va)*(value-a)/(b-a)
    raise ValueError(value)


def branch_nodes(branch):
    nodes=[]
    for a,b in zip(branch['points'],branch['points'][1:]):
        x,y,h=a;xx,yy,hh=b
        distance=abs(xx-x)+abs(yy-y)
        for step in range(distance+1):
            if nodes and step==0:
                continue
            nodes.append([x+(xx-x)*step//distance,y+(yy-y)*step//distance,h+(hh-h)*step/distance])
    return nodes


def geometry(recipe):
    width,height=recipe['size_tiles']
    levels=[[recipe['base_elevation'] for _ in range(width)] for _ in range(height)]
    for region in recipe['elevations']:
        for x,y in cells(region['rect']):
            levels[y][x]=region['level']
    stream=[]
    water=set()
    for start,end,x in recipe['stream_centres']:
        for y in range(start,end+1):
            stream.append([x,y,interpolate(y,recipe['stream_levels'])])
            water.update((xx,y) for xx in range(x-1,x+2))
    branches={r['id']:branch_nodes(r) for r in recipe['water_branches']}
    for nodes in branches.values():
        water.update((x,y) for x,y,_ in nodes)
    buildings=set().union(*(cells(r['rect']) for r in recipe['buildings']))
    decks=set().union(*(cells(r['rect']) for r in recipe['crossings']))
    stairs=set().union(*(cells(r['rect']) for r in recipe['stairs']))
    roads=set().union(*(line_cells(r['points'],r['width']) for r in recipe['roads']))
    walkable={(x,y) for y in range(height) for x in range(width)
              if (x,y) not in buildings and ((x,y) not in water or (x,y) in decks)}
    road_walk=roads&walkable
    for x,y in roads:
        if (x,y) not in walkable:
            raise ValueError(f'Road is blocked at {(x,y)}')
    nodes={r['id']:r['door'] for r in recipe['buildings']}
    nodes.update({r['id']:r.get('approach',r['position']) for r in recipe['landmarks']})
    return {'levels':levels,'water':water,'stream':stream,'branches':branches,'buildings':buildings,
            'decks':decks,'stairs':stairs,'roads':roads,'road_walk':road_walk,'walkable':walkable,'nodes':nodes}


def route(geo,start,end):
    start,end=tuple(start),tuple(end)
    previous={start:None}
    queue=deque([start])
    while queue:
        p=queue.popleft()
        if p==end:
            path=[]
            while p is not None:
                path.append(list(p));p=previous[p]
            return list(reversed(path))
        x,y=p
        for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if q in previous or q not in geo['road_walk']:
                continue
            xx,yy=q
            delta=abs(geo['levels'][y][x]-geo['levels'][yy][xx])
            if delta and not (delta==1 and p in geo['stairs'] and q in geo['stairs']):
                continue
            previous[q]=p;queue.append(q)
    raise ValueError(f'Unreachable road route: {start} to {end}')


def arrow(draw,a,b,color,width=3,head=8):
    draw.line((a,b),fill=color,width=width)
    angle=math.atan2(b[1]-a[1],b[0]-a[0])
    points=[b,(b[0]-head*math.cos(angle-.55),b[1]-head*math.sin(angle-.55)),
              (b[0]-head*math.cos(angle+.55),b[1]-head*math.sin(angle+.55))]
    draw.polygon(points,fill=color)


def badge(draw,point,text,color):
    x,y=point
    draw.ellipse((x-17,y-17,x+17,y+17),fill=color,outline='white',width=3)
    draw.text((x,y-1),text,font=font(16,True),fill='white',anchor='mm')


def plate(draw,point,text,size=16,color=None):
    f=font(size,True);x,y=point
    box=draw.textbbox((x,y),text,font=f,anchor='mm')
    draw.rounded_rectangle((box[0]-8,box[1]-5,box[2]+8,box[3]+5),radius=4,fill=COLORS['paper'])
    draw.text((x,y),text,font=f,fill=color or COLORS['ink'],anchor='mm')


def paragraph(draw,x,y,text,width=510,size=20,color=None):
    f=font(size)
    words=text.split();line=''
    for word in words:
        candidate=f'{line} {word}'.strip()
        if draw.textlength(candidate,font=f)>width and line:
            draw.text((x,y),line,font=f,fill=color or COLORS['muted']);y+=size+10;line=word
        else:
            line=candidate
    if line:
        draw.text((x,y),line,font=f,fill=color or COLORS['muted']);y+=size+10
    return y


def base_map(recipe,geo):
    board=Image.new('RGB',BOARD_SIZE,COLORS['paper'])
    draw=ImageDraw.Draw(board)
    draw.text((72,32),'ELDENMERE',font=font(43,True),fill=COLORS['ink'])
    draw.text((72,91),f"Overhead blockout 01  /  64 x 56 tiles  /  24px grid  /  {recipe['status'].upper()}",font=font(23),fill=COLORS['muted'])
    draw.text((1608,91),'NORTH ↑',font=font(23,True),fill=COLORS['ink'],anchor='ra')
    width,height=recipe['size_tiles']
    for y in range(height):
        for x in range(width):
            px,py=ORIGIN[0]+x*TILE,ORIGIN[1]+y*TILE
            draw.rectangle((px,py,px+TILE-1,py+TILE-1),fill=COLORS['ground'][geo['levels'][y][x]])
            draw.line((px,py,px+TILE-1,py),fill='#9dac8e' if x%4==0 and y%4==0 else COLORS['ground'][geo['levels'][y][x]])
    # A faint four-tile ruler keeps building sizes measurable without a busy cell grid.
    for x in range(0,width+1,4):
        px=ORIGIN[0]+x*TILE
        draw.line((px,ORIGIN[1],px,ORIGIN[1]+height*TILE),fill='#a9b99a',width=1)
        draw.text((px,ORIGIN[1]-22),str(x),font=font(13),fill=COLORS['muted'],anchor='mm')
    for y in range(0,height+1,4):
        py=ORIGIN[1]+y*TILE
        draw.line((ORIGIN[0],py,ORIGIN[0]+width*TILE,py),fill='#a9b99a',width=1)
        draw.text((ORIGIN[0]-20,py),str(y),font=font(13),fill=COLORS['muted'],anchor='mm')
    # Grade boundaries are walls/steep banks; stairs cut explicit openings.
    for y in range(height):
        for x in range(width):
            for dx,dy in ((1,0),(0,1)):
                xx,yy=x+dx,y+dy
                if xx>=width or yy>=height or geo['levels'][y][x]==geo['levels'][yy][xx]:
                    continue
                if ((x,y) in geo['stairs'] and (xx,yy) in geo['stairs']) or ((x,y) in geo['water'] and (xx,yy) in geo['water']):
                    continue
                px,py=ORIGIN[0]+xx*TILE,ORIGIN[1]+yy*TILE
                end=(px,py+TILE) if dx else (px+TILE,py)
                draw.line(((px,py),end),fill=COLORS['cliff'],width=5)
    for space in recipe['spaces']:
        x0,y0,x1,y1=bounds(space['rect'])
        fill={'commons':'#d4d2ac','yard':'#d0c7a3','plots':'#b1a67e','garden':'#a9bd8d'}[space['kind']]
        draw.rectangle((x0+2,y0+2,x1-2,y1-2),fill=fill,outline='#9a9b79',width=2)
        if space['kind'] in ('garden','plots'):
            for xx in range(x0+10,x1,12):
                draw.line((xx,y0+7,xx,y1-7),fill='#7b9471',width=3)
    for x,y in geo['roads']:
        draw.rectangle(bounds([x,y,1,1]),fill=COLORS['road'])
    for x,y in geo['roads']:
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            if (x+dx,y+dy) in geo['roads']:
                continue
            px,py=ORIGIN[0]+x*TILE,ORIGIN[1]+y*TILE
            edge=(px+(TILE if dx==1 else 0),py,px+(TILE if dx==1 else 0),py+TILE) if dx else (px,py+(TILE if dy==1 else 0),px+TILE,py+(TILE if dy==1 else 0))
            draw.line(edge,fill=COLORS['road_edge'],width=2)
    for x,y in geo['water']:
        draw.rectangle(bounds([x,y,1,1]),fill=COLORS['water'] if any(x==xx and y==yy for xx,yy,_ in geo['stream']) or any(abs(x-xx)<=1 and y==yy for xx,yy,_ in geo['stream']) else COLORS['channel'])
    for crossing in recipe['crossings']:
        x0,y0,x1,y1=bounds(crossing['rect'])
        draw.rectangle((x0,y0,x1,y1),fill='#b08d61',outline='#6e614d',width=3)
        for xx in range(x0+8,x1,12):
            draw.line((xx,y0+3,xx,y1-3),fill='#88704f',width=2)
        if crossing['kind']=='stream_bridge':
            draw.line((x0,y0,x1,y0),fill='#6e614d',width=5)
            draw.line((x0,y1,x1,y1),fill='#6e614d',width=5)
    for stair in recipe['stairs']:
        x0,y0,x1,y1=bounds(stair['rect'])
        draw.rectangle((x0,y0,x1,y1),fill='#ccc8ae',outline='#777b69',width=2)
        if stair['orientation']=='north-south':
            for yy in range(y0+7,y1,8):
                draw.line((x0+2,yy,x1-2,yy),fill='#8d907d',width=2)
        else:
            for xx in range(x0+7,x1,8):
                draw.line((xx,y0+2,xx,y1-2),fill='#8d907d',width=2)
    for building in recipe['buildings']:
        x0,y0,x1,y1=bounds(building['rect'])
        fill='#737f7c' if building['id']=='sanctuary' else '#758999' if building['id']=='mill' else '#b28a6e' if building['id']=='mira' else '#a58070'
        draw.rectangle((x0+4,y0+5,x1+4,y1+5),fill='#889574')
        draw.rectangle((x0,y0,x1,y1),fill=fill,outline='#5d6054',width=3)
        draw.line((x0+7,y0+6,x1-7,y0+6),fill='#d2c5ac',width=2)
        label_size=18 if x1-x0>=96 else 15
        draw.text(((x0+x1)/2,(y0+y1)/2-8),building['label'],font=font(label_size,True),fill='white',anchor='mm')
        detail=building['detail'] if building['id']!='sanctuary' else '8 x 5 footprint'
        draw.text(((x0+x1)/2,(y0+y1)/2+15),detail,font=font(11),fill='#f1ecdf',anchor='mm')
        dx,dy=centre(building['door'])
        draw.rectangle((dx-8,dy-11,dx+8,dy-3),fill='#554b3c',outline='#f1ecdf',width=1)
    # Wheel's reserved contact with the west-flowing race, not new sprite art.
    wx,wy=centre((44,15))
    draw.ellipse((wx-13,wy-13,wx+13,wy+13),fill='#ab936c',outline='#5e624e',width=3)
    for yy in (11,25,36,51):
        xx=next(x for x,y,_ in geo['stream'] if y==yy)
        x,y=centre((xx,yy));arrow(draw,(x,y-11),(x,y+12),'#edf7f6',3,7)
    for branch in recipe['water_branches']:
        for a,b in zip(branch['points'],branch['points'][1:]):
            if abs(a[0]-b[0])+abs(a[1]-b[1])<5:
                continue
            mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
            dx=0 if a[0]==b[0] else (1 if b[0]>a[0] else -1)
            dy=0 if a[1]==b[1] else (1 if b[1]>a[1] else -1)
            x,y=centre((mx,my));arrow(draw,(x-dx*10,y-dy*10),(x+dx*10,y+dy*10),'#e6f3f4',2,6)
    for drop in recipe['drops']:
        x,y=centre(drop['position'])
        draw.polygon(((x,y-12),(x+12,y),(x,y+12),(x-12,y)),fill='#f1e0a4',outline='#7d704d',width=2)
        draw.text((x,y),'↓',font=font(15,True),fill='#675f43',anchor='mm')
    gx,gy=centre((60,27))
    draw.rectangle((gx-12,gy-7,gx+12,gy+7),fill='#9a7958',outline='#574f3c',width=3)
    draw.line((gx-13,gy,gx+13,gy),fill='#eed9a5',width=3)
    plate(draw,centre((16,6.1)),'SANCTUARY TERRACE / L2',16)
    plate(draw,centre((14,17)),'Courtyard steps',15)
    plate(draw,centre((20,34)),'COMMONS / FESTIVAL',16)
    plate(draw,centre((20,36)),'12 x 8 gathering space',13)
    plate(draw,centre((20,39)),'Aldric arrival + village gathering',12)
    plate(draw,centre((42,21)),'Sack storage',13)
    plate(draw,centre((35,22)),'Upper crossing',14)
    plate(draw,centre((35,45)),'Main lantern bridge',15)
    plate(draw,centre((53,21)),'EASTERN TERRACE / L2',16)
    plate(draw,centre((54.5,23.8)),'Gate + channel inspection',14)
    draw.line((centre((58,24.5)),centre((60,26.5))),fill='#635e49',width=2)
    plate(draw,centre((46,36.7)),'Terrace steps',14)
    draw.line((centre((46,35)),centre((46,36.1))),fill='#635e49',width=2)
    plate(draw,centre((47.7,4.2)),'Mill supply ↓',14)
    plate(draw,centre((55,4.4)),'Upper supply ↓',14)
    plate(draw,centre((53,36.7)),'Field spillway →',13)
    draw.line((centre((56.5,36.7)),centre((59.3,36))),fill='#635e49',width=2)
    plate(draw,centre((23,52)),'SOUTH ROAD / ALDRIC ARRIVAL',16)
    plate(draw,centre((22,1.5)),'WOODLAND ROUTE ↑',16)
    draw.line((ORIGIN[0],ORIGIN[1]+56*TILE,ORIGIN[0]+64*TILE,ORIGIN[1]+56*TILE),fill='#71816d',width=2)
    draw.text((72,1544),'Building rectangles show ground footprints. Interiors use separate room maps. North is up.',font=font(20),fill=COLORS['muted'])
    return board


def sidebar(board,quest=False,status='review'):
    draw=ImageDraw.Draw(board);x=1660;y=170
    draw.text((x,y),'QUEST ROUTES' if quest else 'A VILLAGE BUILT FOR DAILY LIFE',font=font(24,True),fill=COLORS['ink']);y+=52
    if quest:
        items=[('01  START + RETURN','#d16a27','Sanctuary bedroom, breakfast and Serene. Return here after both remaining homes.'),
               ('02  HALDEN FIRST','#d16a27','Medicine and three grain sacks. Tomas helps here, then returns to the sanctuary.'),
               ('03 / 04  EITHER ORDER','#8b468d','Elira: lantern and stool inside her cottage. Venn: recovery supplies, gate pin and channel outside.'),
               ('NEXT  FIND MIRA','#315ba0','MQ02 visits the workshop and mill, then follows the upstream path to a separate woodland map.')]
        for title,color,body in items:
            draw.text((x,y),title,font=font(21,True),fill=color);y+=36
            y=paragraph(draw,x,y,body);y+=30
        y+=6
        draw.text((x,y),'HOW TO READ THE ROUTES',font=font(22,True),fill=COLORS['ink']);y+=40
        for color,text in [('#d16a27','Orange: sanctuary to Halden.'),('#8b468d','Purple: one example loop after Halden. Elira and Venn may be visited in either order.'),('#596477','Gray dashes: Tomas returns alone.'),('#315ba0','Blue dashes: the upstream MQ02 connection; exact woodland obstacle remains open.')]:
            draw.line((x,y+12,x+34,y+12),fill=color,width=5)
            y=paragraph(draw,x+50,y,text,width=470,size=19);y+=18
        y+=20
        y=paragraph(draw,x,y,'Open exploration remains available. Quest order is handled by dialogue and quest state; these paths are not locked gates.',size=19)
    else:
        y=paragraph(draw,x,y,'Two crossings form a compact loop. Homes cluster around everyday routes; the commons remains open for visitors and the festival.');y+=28
        draw.text((x,y),'GROUND + MOVEMENT',font=font(22,True),fill=COLORS['ink']);y+=44
        for color,text in [(COLORS['ground'][1],'L1  Village lanes and both stream crossings'),(COLORS['ground'][2],'L2  Sanctuary terrace and eastern plots'),(COLORS['ground'][3],'L3  Northern headwater upland')]:
            draw.rectangle((x,y+2,x+24,y+26),fill=color,outline='#7e8d73')
            y=paragraph(draw,x+42,y,text,width=480,size=19);y+=14
        y=paragraph(draw,x,y,'Stone boundaries mark elevation changes. Steps provide the intended walking connections. Main lanes are 2-3 tiles wide; stream decks are 2 tiles deep.',size=19);y+=30
        draw.text((x,y),'WATER ALWAYS DESCENDS',font=font(22,True),fill=COLORS['ink']);y+=42
        for text in ['Shared headwaters lie on the northern woodland map. Three independent feeds enter this plan.', 'The mill supply descends from the north, turns around the mill and flows west beneath the wheel.', 'The independent upper supply feeds the south-flowing Venn gate, then drops through the field spillway.', 'Both bridge ends meet at L1. Stream water runs below their level decks.']:
            y=paragraph(draw,x,y,'• '+text,size=19);y+=18
        y+=14
        draw.text((x,y),'ROOMS + FUTURE LANDMARKS',font=font(22,True),fill=COLORS['ink']);y+=40
        y=paragraph(draw,x,y,'Elira 10 x 10 / Halden 13 x 10 / Venn 16 x 10. Sanctuary and workshop shapes are planning placeholders requiring their own art.',size=19)
    draw.rounded_rectangle((1640,1430,2240,1512),radius=10,fill='#e4e3d6')
    heading='APPROVED PLAN / NOT A PLAYABLE MAP' if status=='approved' else 'DESIGN REVIEW / NOT A PLAYABLE MAP'
    caption='Approved geography; see terrain pass for native-art fitting.' if status=='approved' else 'Geography and precise footprints await review.'
    draw.text((1660,1445),heading,font=font(19,True),fill=COLORS['ink'])
    draw.text((1660,1478),caption,font=font(18),fill=COLORS['muted'])


def quest_map(base,recipe,geo,routes):
    board=base.copy();draw=ImageDraw.Draw(board)
    for name,color,width,dashed in [('elira_first','#8b468d',5,False),('first_visit','#d16a27',8,False),('tomas_return','#596477',3,True)]:
        for segment in routes[name]['segments']:
            points=[centre(p) for p in segment['path']]
            offset=-8 if name=='tomas_return' else 5 if name=='elira_first' else 0
            points=[(x+offset,y+offset) for x,y in points]
            for i,(a,b) in enumerate(zip(points,points[1:])):
                if not dashed or i%2==0:
                    draw.line((a,b),fill=color,width=width)
            if name=='first_visit':
                for i in range(4,len(points)-1,12):
                    arrow(draw,points[i],points[i+1],color,width,10)
    upstream=route(geo,geo['nodes']['mira'],geo['nodes']['woodland_exit'])
    for i,(a,b) in enumerate(zip(upstream,upstream[1:])):
        if i%2==0:
            ax,ay=centre(a);bx,by=centre(b)
            draw.line((ax+8,ay,bx+8,by),fill=COLORS['blue'],width=4)
    for label,node,color in [('1','sanctuary',COLORS['orange']),('2','halden',COLORS['orange']),('3','elira',COLORS['purple']),('4','venn',COLORS['purple'])]:
        x,y=centre(geo['nodes'][node]);badge(draw,(x+25,y+12),label,color)
    for node in ('mira','mill'):
        x,y=centre(geo['nodes'][node]);draw.ellipse((x-11,y-11,x+11,y+11),outline=COLORS['blue'],width=4)
    x,y=centre((60,27));badge(draw,(x+38,y),'G','#8b468d')
    return board


def build():
    recipe=json.loads((OUTPUT/'recipe.json').read_text())
    geo=geometry(recipe)
    routes={}
    for r in recipe['quest_routes']:
        segments=[]
        for a,b in zip(r['nodes'],r['nodes'][1:]):
            path=route(geo,geo['nodes'][a],geo['nodes'][b])
            segments.append({'from':a,'to':b,'steps':len(path)-1,'path':path})
        routes[r['id']]={**r,'segments':segments}
    # Every ordinary home, quest approach and map exit must join the planned lanes.
    for node,point in geo['nodes'].items():
        route(geo,geo['nodes']['sanctuary'],point)
    base=base_map(recipe,geo)
    geography=base.copy();sidebar(geography,status=recipe['status'])
    geography.save(OUTPUT/'overhead_blockout.png')
    quests=quest_map(base,recipe,geo,routes);sidebar(quests,True,status=recipe['status'])
    quests.save(OUTPUT/'quest_routes.png')
    combined=geography.resize((1152,800),Image.Resampling.LANCZOS)
    combined.save(OUTPUT/'overview_small.png')
    result={**recipe,'planning_only':True,'engine_map_implemented':False,
            'relative_elevation_units':True,'approved_asset_pixel_heights_reinterpreted':False,
            'narrative_reference':'docs/narrative/game_01/CH01_MQ01.md',
            'chapter_reference':'docs/narrative/game_01/CHAPTER_01.md',
            'ground_levels':geo['levels'],'stream_flow':geo['stream'],'branch_flows':geo['branches'],
            'road_cells':sorted(geo['roads']),'water_cells':sorted(geo['water']),
            'walkable_road_cells':sorted(geo['road_walk']),'stairs_cells':sorted(geo['stairs']),
            'quest_routes':list(routes.values()),'preview_size':list(BOARD_SIZE),
            'map_pixel_rect':[*ORIGIN,64*TILE,56*TILE]}
    (OUTPUT/'blockout.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f"Built 64x56 planning blockout; {len(geo['nodes'])} destinations connected; five quest route variants exported.")


if __name__=='__main__':
    build()
