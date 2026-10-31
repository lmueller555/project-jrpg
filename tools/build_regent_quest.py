"""Build the visitors and ordinary road-work props from approved pixel assets.

All characters retain the approved 24x36 body/foot registration. Walk cycles
reuse the approved adult motion and change only costume/material pixels.
"""
from pathlib import Path
import json,hashlib,math
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/story/regent'
DIRECTIONS=('front','left','right','back')
OUTLINE='#1a0e16';WOOD='#836347';WOOD_LIGHT='#b79a6c';WOOD_DARK='#573e2a'
SPECS={
 'aldric':{'name':'Regent Aldric','source':'male_03','position':[732,1032],
           'hair':['#3b302d','#70635a','#aaa196'],
           'shirt':['#263d4e','#3e5869','#637c89'],
           'trousers':['#343037','#514850','#75656a']},
 'road_foreman':{'name':'Road foreman','source':'male_02','position':[700,548],
           'hair':['#242027','#38343d','#55515b'],
           'shirt':['#60402d','#976b43','#c19a64'],
           'trousers':['#35343b','#4b4952','#68646e']},
 'regent_clerk':{'name':'Clerk','source':'male_01','position':[708,1054],
           'hair':['#30251f','#5b3f2b','#8b6343'],
           'shirt':['#354653','#607987','#8b9c9f'],
           'trousers':['#493e3b','#725d4c','#a38a6a']},
 'regent_driver':{'name':'Driver','source':'male_01','position':[744,1104],
           'hair':['#312924','#69513c','#9a7857'],
           'shirt':['#344c37','#547953','#80986b'],
           'trousers':['#5b4130','#896348','#b48c5c']},
}
SOURCE_SHADES={
 'male_01':{'hair':['#3d2118','#71452c','#9d6238'], 'shirt':['#455531','#6e7d43','#919b61'], 'trousers':['#8c704f','#b99a6d','#d1b486']},
 'male_02':{'hair':['#242027','#38343d','#55515b'], 'shirt':['#713d32','#a65b45','#cd8260'], 'trousers':['#35343b','#4b4952','#68646e']},
 'male_03':{'hair':['#666168','#979199','#c5bfc5'], 'shirt':['#394955','#596e7d','#8197a5'], 'trousers':['#594334','#7e6049','#a58565']},
}

def rgba(c):return (*bytes.fromhex(c[1:]),255)
def load(path):return Image.open(ROOT/path).convert('RGBA')
def save(path,image):
 p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);image.save(p);return p.relative_to(ROOT).as_posix()
def recolor(source,spec,direction,offset=0):
 im=source.copy();mapping={}
 for material in ('hair','shirt','trousers'):
  mapping.update({rgba(a):rgba(b) for a,b in zip(SOURCE_SHADES[spec['source']][material],spec[material])})
 # Material palettes already distinguish hair/shirt/trousers; leather remains.
 for y in range(im.height):
  for x in range(im.width):
   pixel=im.getpixel((x,y))
   if pixel in mapping:im.putpixel((x,y),mapping[pixel])
 d=ImageDraw.Draw(im)
 if spec['name']=='Regent Aldric':
  # A modest travelling coat: pale neckcloth and small old-gold clasp/buttons.
  if direction=='front':
   for p in [(11,14+offset),(12,14+offset)]:d.point(p,fill='#e8d9b4')
   for p in [(12,16+offset),(12,19+offset)]:d.point(p,fill='#b69a60')
  elif direction in ('left','right'):
   x=9 if direction=='left' else 14
   d.point((x,14+offset),fill='#e8d9b4');d.point((x,16+offset),fill='#b69a60')
  # Coat hem changes clothing only; articulated trouser/boot pixels stay native.
  for y in range(23+offset,25+offset):
   for x in range(8,16):
    p=im.getpixel((x,y))
    if p[:3] in [rgba(c)[:3] for c in spec['trousers']]:im.putpixel((x,y),rgba(spec['shirt'][0]))
 elif spec['name']=='Clerk' and direction!='back':
  # Folded folio held at the ordinary belt, without extending an arm.
  x=13 if direction in ('front','right') else 7
  d.rectangle((x,21+offset,x+2,23+offset),fill='#ded0aa');d.point((x+1,22+offset),fill='#9c8b6b')
 return im

def actor_sheet(identifier,spec):
 sheet=Image.new('RGBA',(120,144));idles={};walks={};sources={}
 for row,direction in enumerate(DIRECTIONS):
  source_path=f"assets/characters/npcs/{spec['source']}/idle_{direction}.png"
  native=load(source_path);im=recolor(native,spec,direction)
  sheet.alpha_composite(im,(0,row*36));idles[direction]=[0,row*36,24,36]
  sources[source_path]=hashlib.sha256((ROOT/source_path).read_bytes()).hexdigest()
  meta=json.loads((ROOT/f"assets/characters/npcs/{spec['source']}/walk_{direction}/animation.json").read_text())
  frames=[]
  for i,frame in enumerate(meta['frames']):
   path=f"assets/characters/npcs/{spec['source']}/walk_{direction}/"+frame['file']
   walk=load(path);dy=frame.get('upper_body_offset',[0,0])[1]
   im=recolor(walk,spec,direction,dy);rect=[(i+1)*24,row*36,24,36]
   sheet.alpha_composite(im,rect[:2]);frames.append({'rect':rect,'duration_ms':frame['duration_ms']})
  walks[direction]=frames
 png=save(Path('actors')/identifier/'poses.png',sheet)
 meta={'canvas':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34], 'sheet':png,'idles':idles,'walks':walks,'source_hashes':sources,'design':'practical travelling clothing; no crown or armour'}
 path=OUT/'actors'/identifier/'animation.json';path.write_text(json.dumps(meta,indent=2)+'\n')
 assert set(sheet.getchannel('A').tobytes())<={0,255}
 return {'id':identifier,'name':spec['name'],'position':spec['position'],'probe_size':[8,4],'draw_anchor':[12,30],'art':path.relative_to(ROOT).as_posix(),'facing':'front'}

def venn_recolor(im,direction,dy=0):
 im=im.copy();mapping={rgba(a):rgba(b) for a,b in {'#455531':'#694439','#6e7d43':'#97614b','#919b61':'#bc8563'}.items()}
 for y in range(36):
  for x in range(24):
   pixel=im.getpixel((x,y))
   if pixel in mapping:im.putpixel((x,y),mapping[pixel])
 d=ImageDraw.Draw(im)
 if direction=='front':d.rectangle((11,16+dy,12,22+dy),fill='#e6d9ba')
 for x in (6,7,16,17):
  for y in range(17+dy,22+dy):
   if im.getpixel((x,y))[:3] in ((105,68,57),(151,97,75),(188,133,99)):d.point((x,y),fill='#ded1ae')
 return im

def haul_arm(shoulder,wrist):
 dx,dy=wrist[0]-shoulder[0],wrist[1]-shoulder[1];distance=math.hypot(dx,dy)
 upper,forearm=4.,4.5
 assert abs(upper-forearm)<distance<=upper+forearm
 along=(upper*upper-forearm*forearm+distance*distance)/(2*distance)
 height=math.sqrt(max(0.,upper*upper-along*along))
 elbow=(shoulder[0]+dx*along/distance-dy*height/distance,
        shoulder[1]+dy*along/distance+dx*height/distance)
 im=Image.new('RGBA',(24,36));d=ImageDraw.Draw(im)
 points=[tuple(round(v) for v in point) for point in (shoulder,elbow,wrist)]
 d.line(points,fill=OUTLINE,width=3);d.line(points,fill='#ded1ae',width=1)
 x,y=points[-1];d.line((x,y,x+1,y),fill='#e8c49d')
 return im,[list(shoulder),list(elbow),list(wrist)]

def haul_walk(direction,index,dy,normal):
 # Reassemble the approved walking body without its swinging arms. Its native
 # head/leg pixels remain identical; only both elbows now support fixed grips.
 part=ROOT/f'assets/source/characters/npcs/male_01/walk_{direction}/parts'
 im=Image.open(part/f'frame_{index+1:02}_legs.png').convert('RGBA')
 im.alpha_composite(Image.open(part/'waist.png').convert('RGBA'))
 shirt=Image.open(part/'shirt.png').convert('RGBA')
 lower=Image.new('RGBA',(24,36));lower.alpha_composite(shirt.crop((0,19,24,36)),(0,19))
 lower.alpha_composite(shirt.crop((0,0,24,19)),(0,dy))
 if dy==-1:lower.alpha_composite(shirt.crop((0,18,24,19)),(0,18))
 im.alpha_composite(lower);im.alpha_composite(Image.open(part/'pouch.png').convert('RGBA'))
 im=venn_recolor(im,direction,dy)
 far,far_joints=haul_arm((13,17+dy),(19,20))
 near,near_joints=haul_arm((10,17+dy),(16,22))
 im.alpha_composite(far);im.alpha_composite(near)
 head=Image.open(part/'head.png').convert('RGBA');im.alpha_composite(head,(0,dy))
 # Copy the exact approved walking head/legs, including directional shading.
 im.paste(normal.crop((0,0,24,14)),(0,0));im.paste(normal.crop((0,26,24,36)),(0,26))
 assert im.crop((0,0,24,14)).tobytes()==normal.crop((0,0,24,14)).tobytes(),(direction,index,'head')
 assert im.crop((0,26,24,36)).tobytes()==normal.crop((0,26,24,36)).tobytes(),(direction,index,'legs')
 return im,{'near':near_joints,'far':far_joints}

def venn_walks():
 # One atlas supports normal walking home and two-handed cart handling.
 sheet=Image.new('RGBA',(216,144));idles={};walks={};hauls={}
 for row,direction in enumerate(DIRECTIONS):
  sheet.alpha_composite(load(f'assets/story/venn/father/idle_{direction}.png'),(0,row*36));idles[direction]=[0,row*36,24,36]
  meta=json.loads((ROOT/f'assets/characters/npcs/male_01/walk_{direction}/animation.json').read_text());walks[direction]=[];hauls[direction]=[]
  for i,frame in enumerate(meta['frames']):
   dy=frame.get('upper_body_offset',[0,0])[1]
   normal=venn_recolor(load(f'assets/characters/npcs/male_01/walk_{direction}/'+frame['file']),direction,dy)
   rect=[(i+1)*24,row*36,24,36];sheet.alpha_composite(normal,rect[:2]);walks[direction].append({'rect':rect,'duration_ms':frame['duration_ms']})
   haul,joints=haul_walk(direction,i,dy,normal);rect=[(i+5)*24,row*36,24,36]
   sheet.alpha_composite(haul,rect[:2]);hauls[direction].append({'rect':rect,'duration_ms':frame['duration_ms'],'joints':joints,'world_grips':[[5,-8],[8,-10]]})
 png=save(Path('actors/venn_father/poses.png'),sheet)
 path=OUT/'actors/venn_father/animation.json';path.write_text(json.dumps({'canvas':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],'sheet':png,'idles':idles,'walks':walks,'haul_walks':hauls,'haul_arm_lengths':[4,4.5],'cart_actor_offset':[5,-30],'identity':'animation only for existing VennResident; never instantiate a duplicate'},indent=2)+'\n')
 return path.relative_to(ROOT).as_posix()

def prop_cart():
 im=Image.new('RGBA',(64,35));d=ImageDraw.Draw(im)
 # Shaft ends meet the two cart-hauling palms at world offsets(+5,-8)/(+8,-10).
 d.line((3,20,21,16),fill=WOOD_DARK,width=3);d.line((3,20,21,16),fill=WOOD_LIGHT)
 d.line((0,22,17,18),fill=WOOD_DARK,width=3);d.line((0,22,17,18),fill=WOOD_LIGHT)
 d.rectangle((15,9,60,22),fill=WOOD_DARK);d.rectangle((17,10,58,18),fill=WOOD)
 for x in range(20,59,6):d.line((x,10,x,18),fill=WOOD_LIGHT)
 d.line((16,8,60,8),fill=WOOD_LIGHT,width=2)
 for x in (25,53):
  d.ellipse((x-7,20,x+7,34),fill=OUTLINE);d.ellipse((x-5,22,x+5,32),fill=WOOD)
  d.line((x-4,23,x+4,31),fill=WOOD_LIGHT);d.line((x-4,31,x+4,23),fill=WOOD_LIGHT)
  d.ellipse((x-1,26,x+1,28),fill='#737e7a')
 return im

def prop_wagon():
 im=Image.new('RGBA',(80,48));d=ImageDraw.Draw(im)
 d.rectangle((6,13,72,32),fill=WOOD_DARK);d.rectangle((9,14,69,28),fill='#5b6a6d')
 for x in range(10,70,8):d.line((x,15,x,28),fill='#8a9290')
 d.polygon([(14,13),(21,1),(61,1),(69,13)],fill='#c7b894',outline=WOOD_DARK)
 d.line((17,11,65,11),fill='#e2d5b2')
 for x in (21,60):
  d.ellipse((x-7,29,x+7,43),fill=OUTLINE);d.ellipse((x-5,31,x+5,41),fill=WOOD)
  d.line((x-4,32,x+4,40),fill=WOOD_LIGHT);d.line((x-4,40,x+4,32),fill=WOOD_LIGHT)
 return im

def props():
 records=[]
 def add(identifier,position,image,sort_y,states=('waiting','released','settled')):
  path=save(Path('props')/(identifier+'.png'),image)
  records.append({'id':identifier,'scene':'eldenmere.playable','position':position,'sort_y':sort_y,'states':{s:path for s in states}})
 add('venn_cart',[625,522],prop_cart(),558)
 add('regent_wagon',[652,1060],prop_wagon(),1104)
 records[-1]['blocker']=[658,1090,68,15]
 im=Image.new('RGBA',(54,20));d=ImageDraw.Draw(im)
 for r,c in [((1,10,16,18),'#737e7a'),((13,5,29,17),'#8e9388'),((29,10,46,19),'#69736d'),((21,1,40,10),'#a4aaa0')]:d.rectangle(r,fill=c);d.line((r[0],r[1],r[2],r[1]),fill='#c0c0ab')
 add('road_stone',[650,588],im,608)
 # Hospitality belongs to the dining room. Four ordinary spare chairs join
 # its three family chairs without changing the opening breakfast furniture.
 for suffix,x,y,direction in [('north_a',276,132,'down'),('north_b',324,132,'down'),
                              ('south_a',276,210,'up'),('south_b',324,210,'up')]:
  filename=f'assets/terrain/eldenmere/cottage_furniture/sprites/chair_{direction}.png'
  records.append(dict(id='dining_guest_chair_'+suffix,scene='sanctuary_dining',
                      position=[x,y],sort_y=y+34,sort_priority=0,blocker=[x+2,y+30,20,5],
                      states={s:filename for s in ('waiting','released','settled')}))
 records.append(dict(id='dining_refreshments',scene='sanctuary_dining',position=[272,76],
                     sort_y=104,states={s:'assets/terrain/eldenmere/sanctuary_interior/props/breadboard.png'
                                       for s in ('waiting','released','settled')}))
 return records

def build():
 OUT.mkdir(parents=True,exist_ok=True)
 actors=[actor_sheet(identifier,spec) for identifier,spec in SPECS.items()]
 # The fourth visitor has approved art references, with no extra dialogue role.
 idle={d:f'assets/characters/npcs/male_01/idle_{d}.png' for d in DIRECTIONS}
 walk={d:[f'assets/characters/npcs/male_01/walk_{d}/frame_{i:02}.png' for i in range(1,5)] for d in DIRECTIONS}
 path=OUT/'actors/regent_attendant/animation.json';path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps({'idles':idle,'walks':walk,'canvas':[24,36],'draw_anchor':[12,30]},indent=2)+'\n')
 actors.append({'id':'regent_attendant','name':'Traveling attendant','position':[672,1132],'probe_size':[8,4],'draw_anchor':[12,30],'art':path.relative_to(ROOT).as_posix(),'facing':'front'})
 art={'actors':actors,'existing_actors':{'venn_father':{'art':venn_walks()}},'props':props()}
 (OUT/'art.json').write_text(json.dumps(art,indent=2)+'\n')
 layout={'arrival':[744,1032],'road':[610,520],'cart_start':[625,522],'cart_end':[955,390],
  'cart_actor_offset':[5,-30],'venn_start':[620,552],'venn_end':[950,420],
  'courtyard':[386,318],'serene':[364,326],'tomas':[420,348],
  'aldric_courtyard':[400,326],'aldric_aside':[442,304],
  'clerk_courtyard':[444,350],'driver_courtyard':[444,328],'attendant_courtyard':[324,340],
  'aldric_road':[610,512],'clerk_road':[582,524],'driver_road':[724,520],'attendant_road':[566,548],
  'foreman':[700,548],'crew_resume':[660,576],
  'preparations':[386,326], 'welcome':[386,318], 'discussion':[386,318], 'aftermath':[386,326],
  'venn_cart_path':[[620,552],[720,552],[744,480],[936,480],[972,408],[950,420]],
  'aldric_route':[[732,1032],[720,1032],[516,1032],[516,552],[610,512],[480,480],[384,384],[400,326]],
  'scene_id':'eldenmere.playable'}
 layout.update({'aldric_arrival':[732,1032],'clerk_arrival':[708,1054],'driver_arrival':[744,1104],'attendant_arrival':[672,1132], 'venn_road':layout['venn_start'],'foreman_road':layout['foreman'],'venn_delivery':layout['venn_end'],'cart_route':layout['venn_cart_path']})
 layout.update(outside_courtyard=[386,318],dining_scene_id='sanctuary_dining',preparations=[264,128],serene=[288,116],
               serene_meal=[144,228],tomas=[108,200],courtyard=[228,252],welcome=[228,252],
               discussion=[228,252],aftermath=[168,228],aldric_courtyard=[228,200],
               clerk_courtyard=[288,132],driver_courtyard=[288,252],
               attendant_courtyard=[336,252],aldric_aside=[378,144],
               dining_stations=['preparations','serene','serene_meal','tomas','courtyard',
                                'welcome','discussion','aftermath','aldric_courtyard',
                                'clerk_courtyard','driver_courtyard','attendant_courtyard','aldric_aside'])
 (OUT/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
 # Review of actual native-pixel art, not an alternative redesign.
 board=Image.new('RGB',(720,440),'#e8edf2');d=ImageDraw.Draw(board)
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
 for i,(identifier,spec) in enumerate(SPECS.items()):
  sheet=load(f'assets/story/regent/actors/{identifier}/poses.png');im=sheet.crop((0,0,24,36))
  large=im.resize((144,216),Image.Resampling.NEAREST);board.paste(large,(i*180+18,48),large)
  d.text((i*180+12,12),spec['name'],font=font,fill='#243529')
 cart=prop_cart().resize((256,136),Image.Resampling.NEAREST);board.paste(cart,(220,282),cart)
 work=ROOT/'work/regent_art';work.mkdir(parents=True,exist_ok=True);board.save(work/'actors_props.png')
 aldric=load('assets/story/regent/actors/aldric/poses.png').crop((0,0,24,36))
 bg=Image.new('RGBA',(24,36),'#788472');bg.alpha_composite(aldric)
 bg.resize((480,720),Image.Resampling.NEAREST).convert('RGB').save(work/'aldric_reference.png')
 print('Regent actors/props built; preserved approved body motion and 24x36 registration.')

if __name__=='__main__':build()
