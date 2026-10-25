"""Export Liam and his parents from a retained generated concept plate.

Uses the existing band-sampling/material-mapping process for 24x36 characters.
The generated plate supplies the new designs; the export registers their game
scale, hard-alpha palette, eyes and common foot baseline for review.
"""
import json
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont

from build_tomas_idle import sample_source

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/liam_family'
REVIEW=ROOT/'docs/reviews/liam_family'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BACKGROUND='#e8edf2'
STATUS='approved'
COMMON={
    'outline':['#1a0e16'],
    'skin':['#e8c49d','#eda052'],
    'linen':['#bcae91','#ded1ae','#fbeed0'],
    'leather':['#3d2118','#84512e','#9d6238'],
}
SPECS={
    'liam_mother':{
        'label':'Mother','age_range':'mid-30s','role':'mother','occupation':'teacher',
        'bounds':[156,125,488,958],'occupied':[5,1,14,34],'eyes':[[10,9],[13,9]],
        'iris':'#4e7950',
        'materials':{'hair':['#3d2118','#71452c','#a47545'],
                     'dress':['#294f50','#3e7778','#6aa0a0']},
        'bands':[
            ([125,385],[1,14],['outline','hair','skin']),
            ([385,521],[14,21],['outline','dress','linen','skin']),
            ([521,817],[21,29],['outline','dress','linen','skin']),
            ([817,898],[29,32],['outline','dress']),
            ([898,958],[32,35],['outline','leather']),
        ],
        'windows':[
            ([238,239,408,372],['skin']),
            ([221,353,289,583],['outline','hair']),
            ([165,605,211,673],['outline','skin']),
            ([436,605,484,673],['outline','skin']),
            ([215,536,422,819],['outline','linen']),
        ],
        'layers':{'head':[0,14],'bodice_and_arms':[14,21],
                  'skirt_and_hands':[21,32],'boots':[32,36]},
        'design':'Chestnut braid, green eyes, blue-green dress, cream apron and brown boots.',
    },
    'liam':{
        'label':'Liam','age_years':8,'role':'child',
        'bounds':[640,318,892,958],'occupied':[6,9,12,26],'eyes':[[10,17],[13,17]],
        'iris':'#4e7950',
        'materials':{'hair':['#3d2118','#71452c','#a47545'],
                     'tunic':['#8a601d','#b88a2c','#d6ae50'],
                     'collar':['#294f3c','#476a46','#7b925b'],
                     'trousers':['#51413b','#746050','#9d7953']},
        'bands':[
            ([318,555],[9,21],['outline','hair','skin']),
            ([555,751],[21,28],['outline','tunic','skin']),
            ([751,844],[28,31],['outline','trousers']),
            ([844,879],[31,32],['outline','skin']),
            ([879,958],[32,35],['outline','leather']),
        ],
        'windows':[
            ([689,441,841,549],['skin']),
            ([725,555,816,619],['outline','collar','skin']),
            ([645,712,694,766],['outline','skin']),
            ([840,712,889,766],['outline','skin']),
        ],
        'layers':{'head':[0,21],'upper_body':[21,25],
                  'tunic_and_hands':[25,28],'legs_and_boots':[28,36]},
        'design':'Tousled chestnut hair, green eyes, ochre tunic, green collar, brown breeches and small boots.',
    },
    'liam_father':{
        'label':'Father','age_range':'mid-30s','role':'father',
        'bounds':[1016,76,1414,958],'occupied':[4,1,16,34],'eyes':[[10,9],[13,9]],
        'iris':'#8b7344',
        'materials':{'hair':['#302019','#573622','#84512e'],
                     'tunic':['#803d31','#a6523b','#ca7c50'],
                     'trousers':['#352a29','#51413b','#746050'],
                     'buckle':['#b99b55']},
        'bands':[
            ([76,331],[1,14],['outline','hair','skin']),
            ([331,529],[14,22],['outline','tunic','linen','skin']),
            ([529,568],[22,23],['outline','leather','buckle']),
            ([568,681],[23,26],['outline','tunic','skin']),
            ([681,845],[26,31],['outline','trousers']),
            ([845,958],[31,35],['outline','leather']),
        ],
        'windows':[
            ([1142,182,1290,278],['skin']),
            ([1152,278,1284,330],['outline','hair','skin']),
            ([1139,324,1293,424],['outline','linen','skin']),
            ([1028,483,1107,580],['outline','linen']),
            ([1327,483,1408,580],['outline','linen']),
            ([1024,589,1092,681],['outline','skin']),
            ([1340,589,1411,681],['outline','skin']),
        ],
        'layers':{'head':[0,14],'upper_body':[14,23],
                  'tunic_and_hands':[23,26],'legs_and_boots':[26,36]},
        'design':'Dark brown hair and short beard, hazel eyes, clay-red tunic, ivory sleeves and dark trousers.',
    },
}


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n')


def font(size):return ImageFont.truetype(FONT,size)


def opaque(sprite,scale):
    canvas=Image.new('RGB',sprite.size,BACKGROUND);canvas.paste(sprite,(0,0),sprite)
    return canvas.resize((sprite.width*scale,sprite.height*scale),Image.Resampling.NEAREST)


def board(path,items,scale,title,subtitle):
    stride=24*scale+40;width=stride*len(items)+24;height=36*scale+176
    image=Image.new('RGB',(width,height),BACKGROUND);d=ImageDraw.Draw(image);d.fontmode='1'
    d.text((24,16),title,font=font(28),fill='#26343e')
    d.text((24,58),subtitle,font=font(20),fill='#52616c')
    baseline=112+35*scale
    d.line((20,baseline,width-20,baseline),fill='#b5c1c4',width=1)
    for i,(label,sprite) in enumerate(items):
        x=24+i*stride
        big=sprite.resize((24*scale,36*scale),Image.Resampling.NEAREST)
        image.paste(big,(x,112),big)
        d.text((x,36*scale+132),label,font=font(21),fill='#26343e')
    image.save(path)


def build():
    source=Image.open(SOURCE/'front_idle_concepts.png').convert('RGBA')
    REVIEW.mkdir(parents=True,exist_ok=True)
    recipes={};sprites={};records=[]
    for identity,spec in SPECS.items():
        output=ROOT/f'assets/characters/{identity}';output.mkdir(parents=True,exist_ok=True)
        age={k:spec[k] for k in ('age_years','age_range') if k in spec}
        palette={'status':STATUS,'materials':{**COMMON,**spec['materials']},
                 'eyes':{'pupil':'#1a0e16','iris':spec['iris']}}
        write(output/'palette.json',palette)
        recipe={'source':'front_idle_concepts.png','alpha_threshold':128,
                'source_bounds':spec['bounds'],'frame_size':[24,36],
                'occupied_rect':spec['occupied'],'foot_anchor':[12,34],
                'bands':[{'source_y':sy,'native_y':ny,'materials':m} for sy,ny,m in spec['bands']],
                'material_windows':[{'rect':rect,'materials':m} for rect,m in spec['windows']],
                'eyes':{'top_pixels':spec['eyes'],'height':2,'iris_offset_y':1},'layers':spec['layers']}
        native=sample_source(source,recipe,palette)
        x,y,w,h=spec['occupied'];bounds=native.getbbox()
        assert bounds==(x,y,x+w,y+h),(identity,bounds)
        assert bounds[3]==35 and native.size==(24,36)
        assert set(native.getchannel('A').tobytes())=={0,255}
        allowed={tuple(bytes.fromhex(c[1:]))+(255,) for colors in palette['materials'].values() for c in colors}
        allowed.update(tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['eyes'].values())
        pixels=getattr(native,'get_flattened_data',native.getdata)()
        assert all(pixel[3]==0 or pixel in allowed for pixel in pixels)
        for ex,ey in spec['eyes']:
            assert native.getpixel((ex,ey))==tuple(bytes.fromhex(palette['eyes']['pupil'][1:]))+(255,)
            assert native.getpixel((ex,ey+1))==tuple(bytes.fromhex(palette['eyes']['iris'][1:]))+(255,)
        native.save(output/'idle_front.png');sprites[identity]=native
        combined=Image.new('RGBA',(24,36));layers=[]
        for name,(first,last) in spec['layers'].items():
            layer=Image.new('RGBA',(24,36));layer.paste(native.crop((0,first,24,last)),(0,first))
            path=SOURCE/identity/'layers'/f'{name}.png';path.parent.mkdir(parents=True,exist_ok=True);layer.save(path)
            combined.alpha_composite(layer);layers.append(path.relative_to(ROOT).as_posix())
        assert combined.tobytes()==native.tobytes()
        review=Image.new('RGB',(720,1040),BACKGROUND);d=ImageDraw.Draw(review);d.fontmode='1'
        age_label=str(spec.get('age_years',spec.get('age_range')))
        d.text((28,20),f'{spec["label"]} / front idle / {age_label}',font=font(27),fill='#26343e')
        d.text((28,62),f'24x36 frame | {h} px visible | 24x review',font=font(20),fill='#52616c')
        review.paste(opaque(native,24),(72,108))
        d.text((28,990),'Design for review',font=font(22),fill='#52616c')
        review.save(REVIEW/f'{identity}.png')
        metadata={'character':identity,'display_label':spec['label'],'family':'liam_family',
                  'role':spec['role'],**age,'status':STATUS,'animation':'idle.front',
                  'image':'idle_front.png','frame_size':[24,36],'rect':[0,0,24,36],
                  'occupied_rect':spec['occupied'],'visible_height_px':h,'foot_anchor':[12,34],
                  'palette':'palette.json','source':'assets/source/characters/liam_family/front_idle_concepts.png',
                  'export_recipe':'assets/source/characters/liam_family/export.json',
                  'eyes':recipe['eyes'],'layers_from_repo_root':layers,'design':spec['design']}
        write(output/'idle_front.json',metadata);recipes[identity]=recipe;records.append(metadata)
    write(SOURCE/'export.json',{'source':'front_idle_concepts.png','characters':recipes})
    folder=ROOT/'assets/characters/liam_family';folder.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGBA',(72,36))
    for i,identity in enumerate(SPECS):sheet.alpha_composite(sprites[identity],(i*24,0))
    sheet.save(folder/'front_idles.png')
    members=[{**record,'sprite_root':f"assets/characters/{record['character']}",
              'sheet_rect':[i*24,0,24,36]} for i,record in enumerate(records)]
    for member in members:
        occupation=SPECS[member['character']].get('occupation')
        if occupation:member['occupation']=occupation
    family={'status':STATUS,'members':members,'sheet':'front_idles.png',
          'column_order':list(SPECS),'frame_size':[24,36],'parents_names':'unassigned',
          'quest_association':'unassigned'}
    # Appearance rebuilds retain the household's assigned game-world home.
    if (folder/'family.json').exists():
        home=json.loads((folder/'family.json').read_text()).get('home')
        if home:family['home']=home
    write(folder/'family.json',family)
    board(REVIEW/'family_front_idles.png',[
        ('Mother / mid-30s',sprites['liam_mother']),('Liam / 8',sprites['liam']),
        ('Father / mid-30s',sprites['liam_father'])],16,
        'Liam and his parents / front idle designs','Shared 16x scale | 24x36 frames | common foot baseline')
    comparison=[]
    for label,identity in [('Caelan / 18','caelan'),('Tomas / 14','tomas'),('Liam / 8','liam'),
                           ('Mother / mid-30s','liam_mother'),('Father / mid-30s','liam_father')]:
        sprite=sprites.get(identity)
        if sprite is None:sprite=Image.open(ROOT/f'assets/characters/{identity}/idle_front.png').convert('RGBA')
        comparison.append((label,sprite))
    board(REVIEW/'height_comparison.png',comparison,12,
          'Family and existing cast / height comparison','Shared 12x scale | approved Caelan and Tomas remain unchanged')
    print('Exported three 24x36 front idles: Liam 26 px tall; both parents 34 px tall.')


if __name__=='__main__':build()
