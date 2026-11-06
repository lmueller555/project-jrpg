"""Maintain the visitors and sanctuary meal from approved pixel assets.

All characters retain the approved 24x36 body/foot registration. Existing
visitor exports and modern room layout are preserved; Lucan's approved
directional idle and walk files are referenced without new drawings.
"""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/story/regent'
DIRECTIONS=('front','left','right','back')
OUTLINE='#1a0e16';WOOD='#836347';WOOD_LIGHT='#b79a6c';WOOD_DARK='#573e2a'
SPECS={
 'aldric':{'name':'Regent Aldric','source':'male_03','position':[732,1032],
           'hair':['#3b302d','#70635a','#aaa196'],
           'shirt':['#263d4e','#3e5869','#637c89'],
           'trousers':['#343037','#514850','#75656a']},
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
 add('regent_wagon',[652,1060],prop_wagon(),1104)
 records[-1]['blocker']=[658,1090,68,15]
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

def lucan_actor():
 """Reference the approved complete directional set without redrawing it."""
 folder=OUT/'actors/lucan';folder.mkdir(parents=True,exist_ok=True)
 idles={direction:f'assets/characters/lucan/idle_{direction}.png' for direction in DIRECTIONS}
 walks={}
 for direction in DIRECTIONS:
  base=ROOT/f'assets/characters/lucan/walk_{direction}'
  meta=json.loads((base/'animation.json').read_text())
  walks[direction]=[(base/frame['file']).relative_to(ROOT).as_posix() for frame in meta['frames']]
 animation={'canvas':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],
            'idles':idles,'walks':walks,'source':'approved Lucan directional idle and walking sets',
            'design':'Aldric personal guard; approved armor, sword and shield'}
 path=folder/'animation.json';path.write_text(json.dumps(animation,indent=2)+'\n')
 return {'id':'lucan','name':'Lucan Rooke','position':[672,1132],'probe_size':[8,4],
         'draw_anchor':[12,30],'art':path.relative_to(ROOT).as_posix(),'facing':'front'}


DEFAULT_LAYOUT={
 'arrival':[744,1032], 'courtyard':[228,252], 'serene':[288,116],
 'tomas':[108,200], 'aldric_courtyard':[228,200], 'aldric_aside':[378,144],
 'clerk_courtyard':[288,132], 'driver_courtyard':[288,252], 'lucan_courtyard':[336,252],
 'preparations':[264,128], 'welcome':[228,252], 'discussion':[228,252], 'aftermath':[168,228],
 'scene_id':'eldenmere.playable', 'aldric_arrival':[732,1032], 'clerk_arrival':[708,1054],
 'driver_arrival':[744,1104], 'lucan_arrival':[672,1132],
 'dining_scene_id':'sanctuary_dining', 'serene_meal':[144,228],
 'outside_courtyard':[386,318],
 'dining_stations':['preparations','serene','serene_meal','tomas','courtyard','welcome',
                    'discussion','aftermath','aldric_courtyard','clerk_courtyard',
                    'driver_courtyard','lucan_courtyard','aldric_aside']}

DEFAULT_LAYOUT.update(serene_meal=[168,116], lucan_courtyard=[336,132], driver_courtyard=[336,252])
DEFAULT_LAYOUT['meal_seats']={'tomas': {'position': [138, 200], 'approach': [108, 200], 'anchor': [12, 30], 'facing': 'right', 'image': 'assets/story/sanctuary_opening/poses/tomas_seated.png', 'sort_y': 206, 'flip_x': True}, 'aldric': {'position': [198, 200], 'approach': [228, 200], 'anchor': [12, 30], 'facing': 'left', 'image': 'assets/story/regent/poses/aldric_seated.png', 'sort_y': 206}, 'mother_serene': {'position': [168, 158], 'approach': [168, 116], 'anchor': [12, 30], 'facing': 'front', 'image': 'assets/story/regent/poses/serene_seated.png', 'sort_y': 206}, 'regent_clerk': {'position': [288, 158], 'approach': [288, 132], 'anchor': [12, 30], 'facing': 'front', 'image': 'assets/story/regent/poses/clerk_seated.png', 'sort_y': 206}, 'lucan': {'position': [336, 158], 'approach': [336, 132], 'anchor': [12, 30], 'facing': 'front', 'image': 'assets/story/regent/poses/lucan_seated.png', 'sort_y': 206}, 'regent_driver': {'position': [336, 234], 'approach': [336, 252], 'anchor': [12, 30], 'facing': 'back', 'image': 'assets/story/regent/poses/driver_seated.png', 'sort_y': 246}}

def build():
 """Maintain the revised visit without overwriting approved art or room edits.

 The three existing visitors keep their registered art. Lucan references his
 approved directional drawings directly. Existing modern room positions and
 props are retained, with obsolete cart/dispute stations explicitly retired.
 """
 OUT.mkdir(parents=True,exist_ok=True)
 old_art=json.loads((OUT/'art.json').read_text()) if (OUT/'art.json').exists() else {}
 previous={actor['id']:actor for actor in old_art.get('actors',[])}
 actors=[previous[identifier] if identifier in previous else actor_sheet(identifier,spec)
         for identifier,spec in SPECS.items()]
 actors.append(lucan_actor())
 props_records=old_art.get('props') or props()
 props_records=[prop for prop in props_records if prop['id'] not in ('venn_cart','road_stone')]
 (OUT/'art.json').write_text(json.dumps({'actors':actors,'props':props_records},indent=2)+'\n')
 layout=dict(DEFAULT_LAYOUT)
 old_layout=json.loads((OUT/'layout.json').read_text()) if (OUT/'layout.json').exists() else {}
 layout.update(old_layout)
 retired={'road','cart_start','cart_end','cart_actor_offset','venn_start','venn_end',
          'venn_cart_path','aldric_route','aldric_road','clerk_road','driver_road',
          'attendant_road','foreman','crew_resume','attendant_arrival','attendant_courtyard',
          'venn_road','foreman_road','venn_delivery','cart_route'}
 for key in retired:layout.pop(key,None)
 # Preserve explicit future Lucan positions; otherwise use the equivalent
 # visitor station in an older room layout without restoring that old actor.
 for phase in ('arrival','courtyard'):
  if 'lucan_'+phase not in old_layout and 'attendant_'+phase in old_layout:
   layout['lucan_'+phase]=old_layout['attendant_'+phase]
 layout['dining_stations']=[key for key in layout['dining_stations'] if key in layout]
 if 'lucan_courtyard' not in layout['dining_stations']:layout['dining_stations'].append('lucan_courtyard')
 (OUT/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
 print('Regent visit maintained with approved Lucan art; no cart-dispute assets generated.')


if __name__=='__main__':build()
