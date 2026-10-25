"""Export nine new family idles; approved fronts and palettes are read-only."""
import hashlib
import json

from PIL import Image,ImageDraw

from build_liam_family_idles import ROOT,SOURCE,BACKGROUND,board,font,write
from build_tomas_idle import sample_source

REVIEW=ROOT/'docs/reviews/liam_family_turnaround'
DIRECTIONS=('front','left','right','back')
SPECS={
    'liam_mother':{
        'label':'Mother','height':34,'head_end':14,
        'layers':{'head':[0,14],'bodice_and_arms':[14,21],
                  'skirt_and_hands':[21,32],'boots':[32,36]},
        'views':{
            'left':{'bounds':[116,40,287,543],'occupied':[6,1,12,34],'eyes':[[9,9]],
                    'windows':[([140,118,207,213],['skin'])]},
            'right':{'bounds':[422,40,594,543],'occupied':[6,1,12,34],'eyes':[[14,9]],
                     'windows':[([497,118,582,213],['skin']),
                                ([480,179,535,292],['outline','hair'])]},
            'back':{'bounds':[735,40,921,543],'occupied':[5,1,14,34],'eyes':[],
                    'windows':[([846,175,892,288],['outline','hair']),
                               ([771,207,865,228],['outline','linen','skin']),
                               ([749,280,902,301],['outline','linen'])]},
        },
    },
    'liam':{
        'label':'Liam','height':26,'head_end':21,
        'layers':{'head':[0,21],'upper_body':[21,25],
                  'tunic_and_hands':[25,28],'legs_and_boots':[28,36]},
        'views':{
            'left':{'bounds':[120,587,272,944],'occupied':[7,9,10,26],'eyes':[[10,17]],
                    'windows':[([169,721,220,753],['outline','collar','skin']),
                               ([146,663,218,728],['skin'])]},
            'right':{'bounds':[432,587,581,944],'occupied':[7,9,10,26],'eyes':[[13,17]],
                     'windows':[([482,721,538,753],['outline','collar','skin']),
                                ([488,663,563,728],['skin'])]},
            'back':{'bounds':[753,588,899,939],'occupied':[6,9,12,26],'eyes':[],
                    'windows':[([790,721,861,747],['outline','collar'])]},
        },
    },
    'liam_father':{
        'label':'Father','height':34,'head_end':14,
        'layers':{'head':[0,14],'upper_body':[14,23],
                  'tunic_and_hands':[23,26],'legs_and_boots':[26,36]},
        'views':{
            'left':{'bounds':[116,965,283,1511],'occupied':[5,1,14,34],'eyes':[[9,8]],
                    'windows':[([137,1034,210,1091],['skin']),
                               ([141,1133,199,1174],['outline','linen','skin']),
                               ([212,1213,277,1284],['outline','linen']),
                               ([227,1284,272,1337],['outline','skin'])]},
            'right':{'bounds':[423,966,594,1511],'occupied':[5,1,14,34],'eyes':[[14,8]],
                     'windows':[([490,1034,566,1091],['skin']),
                                ([505,1133,567,1174],['outline','linen','skin']),
                                ([426,1213,486,1284],['outline','linen']),
                                ([431,1284,481,1337],['outline','skin'])]},
            'back':{'bounds':[717,965,948,1507],'occupied':[4,1,16,34],'eyes':[],
                    'windows':[([775,1113,892,1138],['outline','linen','skin']),
                               ([719,1207,771,1284],['outline','linen']),
                               ([895,1207,946,1284],['outline','linen']),
                               ([727,1284,770,1338],['outline','skin']),
                               ([897,1284,941,1338],['outline','skin'])]},
        },
    },
}


def bands_for(identity,direction,view):
    top=view['bounds'][1];bottom=view['bounds'][3]
    if identity=='liam_mother':
        return [
            ([top,213],[1,14],['outline','hair','skin']),
            ([213,293],[14,21],['outline','dress','linen','skin']),
            ([293,455],[21,29],['outline','dress'] if direction=='back' else ['outline','dress','linen','skin']),
            ([455,500],[29,32],['outline','dress']),
            ([500,bottom],[32,35],['outline','leather']),
        ]
    if identity=='liam':
        head=729 if direction=='back' else 728
        return [
            ([top,head],[9,21],['outline','hair','skin']),
            ([head,831],[21,28],['outline','tunic','skin']),
            ([831,881],[28,31],['outline','trousers']),
            ([881,899],[31,32],['outline','skin']),
            ([899,bottom],[32,35],['outline','leather']),
        ]
    return [
        ([top,1121 if direction=='back' else 1141],[1,14],['outline','hair','skin']),
        ([1121 if direction=='back' else 1141,1237],[14,22],['outline','tunic','linen','skin']),
        ([1237,1264],[22,23],['outline','leather'] if direction=='back' else ['outline','leather','buckle']),
        ([1264,1330],[23,26],['outline','tunic','skin']),
        ([1330,1429],[26,31],['outline','trousers']),
        ([1429,bottom],[31,35],['outline','leather']),
    ]


def build():
    REVIEW.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/f'assets/characters/{identity}/{name}'
               for identity in SPECS for name in ('idle_front.png','idle_front.json','palette.json')]
    original={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    source=Image.open(SOURCE/'turnaround_concepts.png').convert('RGBA')
    recipes={};family_sprites={};family_records=[]
    for identity,spec in SPECS.items():
        output=ROOT/f'assets/characters/{identity}'
        palette=json.loads((output/'palette.json').read_text())
        allowed={tuple(bytes.fromhex(c[1:]))+(255,) for colors in palette['materials'].values() for c in colors}
        allowed.update(tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['eyes'].values())
        iris=tuple(bytes.fromhex(palette['eyes']['iris'][1:]))+(255,)
        pupil=tuple(bytes.fromhex(palette['eyes']['pupil'][1:]))+(255,)
        recipes[identity]={};records=[];sprites={}
        for direction,view in spec['views'].items():
            recipe={'source_bounds':view['bounds'],'occupied_rect':view['occupied'],
                    'frame_size':[24,36],'foot_anchor':[12,34],'alpha_threshold':128,
                    'bands':[{'source_y':sy,'native_y':ny,'materials':m} for sy,ny,m in bands_for(identity,direction,view)],
                    'material_windows':[{'rect':rect,'materials':materials} for rect,materials in view['windows']],
                    'eyes':{'top_pixels':view['eyes'],'height':2,'iris_offset_y':1},'layers':spec['layers']}
            native=sample_source(source,recipe,palette)
            box=native.getbbox()
            assert native.size==(24,36) and box[1::2]==(35-spec['height'],35),(identity,direction,box)
            assert set(native.getchannel('A').tobytes())=={0,255}
            pixels=list(getattr(native,'get_flattened_data',native.getdata)())
            assert all(not p[3] or p in allowed for p in pixels)
            assert pixels.count(iris)==(0 if direction=='back' else 1),(identity,direction,'iris count')
            for ex,ey in view['eyes']:
                assert native.getpixel((ex,ey))==pupil and native.getpixel((ex,ey+1))==iris
            if identity!='liam_father' and direction!='back':
                chin_x=10 if direction=='left' else 14
                chin_y=20 if identity=='liam' else 13
                skin={tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['materials']['skin']}
                assert native.getpixel((chin_x,chin_y)) in skin,(identity,direction,'closed chin')
            native.save(output/f'idle_{direction}.png');sprites[direction]=native
            combined=Image.new('RGBA',(24,36));layers=[]
            for name,(first,last) in spec['layers'].items():
                layer=Image.new('RGBA',(24,36));layer.paste(native.crop((0,first,24,last)),(0,first))
                path=SOURCE/identity/f'idle_{direction}_layers/{name}.png'
                path.parent.mkdir(parents=True,exist_ok=True);layer.save(path)
                combined.alpha_composite(layer);layers.append(path.relative_to(ROOT).as_posix())
            assert combined.tobytes()==native.tobytes()
            metadata_path=output/f'idle_{direction}.json'
            status=json.loads(metadata_path.read_text()).get('status','review') if metadata_path.exists() else 'review'
            metadata={'character':identity,'family':'liam_family','animation':f'idle.{direction}',
                      'status':status,'approved_front_reference':'idle_front.json',
                      'image':f'idle_{direction}.png','rect':[0,0,24,36],'frame_size':[24,36],
                      'occupied_rect':[box[0],box[1],box[2]-box[0],box[3]-box[1]],
                      'visible_height_px':spec['height'],'foot_anchor':[12,34],
                      'palette':'palette.json','eyes':recipe['eyes'],
                      'source':'assets/source/characters/liam_family/turnaround_concepts.png',
                      'export_recipe':'assets/source/characters/liam_family/turnaround_export.json',
                      'layers_from_repo_root':layers}
            if identity=='liam_mother':
                metadata['braid']={'anatomical_side':'right','visibility':{
                    'left':'far side, largely obscured','right':'near shoulder',
                    'back':'toward right shoulder'}[direction]}
            write(metadata_path,metadata);recipes[identity][direction]=recipe
        sprites['front']=Image.open(output/'idle_front.png').convert('RGBA')
        sheet=Image.new('RGBA',(96,36))
        for i,direction in enumerate(DIRECTIONS):
            sheet.alpha_composite(sprites[direction],(i*24,0))
            record=json.loads((output/f'idle_{direction}.json').read_text())
            records.append({'direction':direction,'rect':[i*24,0,24,36],
                            'status':record['status'],'metadata':f'idle_{direction}.json'})
        sheet.save(output/'idle_all.png')
        write(output/'idle_all.json',{'character':identity,'image':'idle_all.png','frame_size':[24,36],
              'foot_anchor':[12,34],'visible_height_px':spec['height'],'frames':records})
        board(REVIEW/f'{identity}_turnaround.png',[
              (f"{d.title()} / {records[i]['status']}",sprites[d]) for i,d in enumerate(DIRECTIONS)],12,
              f"{spec['label']} / directional idle sprites",'Approved front with new left, right and back | 24x36 frames | shared 12x scale')
        board(REVIEW/f'{identity}_new_views.png',[(d.title(),sprites[d]) for d in ('left','right','back')],20,
              f"{spec['label']} / left, right and back",'New directional designs for review | 20x native pixels')
        family_sprites[identity]=sprites;family_records.append({'character':identity,'label':spec['label'],
            'sprite_root':f'assets/characters/{identity}','visible_height_px':spec['height'],'frames':records})
    write(SOURCE/'turnaround_export.json',{'source':'turnaround_concepts.png','characters':recipes})
    sheet=Image.new('RGBA',(96,108))
    for row,identity in enumerate(SPECS):
        for column,direction in enumerate(DIRECTIONS):
            sheet.alpha_composite(family_sprites[identity][direction],(column*24,row*36))
    sheet.save(ROOT/'assets/characters/liam_family/idle_directions.png')
    status='approved' if all(frame['status']=='approved' for member in family_records for frame in member['frames']) else 'review'
    write(ROOT/'assets/characters/liam_family/idle_directions.json',{
        'status':status,'image':'idle_directions.png','frame_size':[24,36],'foot_anchor':[12,34],
        'row_order':list(SPECS),'column_order':list(DIRECTIONS),'members':family_records})
    image=Image.new('RGB',(1024,1140),BACKGROUND);draw=ImageDraw.Draw(image);draw.fontmode='1'
    draw.text((24,16),'Liam and his parents / idle turnarounds',font=font(28),fill='#26343e')
    draw.text((24,55),'Shared 8x scale | front approved; new directions for review',font=font(19),fill='#52616c')
    for column,direction in enumerate(DIRECTIONS):
        draw.text((144+column*216,92),direction.title(),font=font(20),fill='#26343e')
    for row,(identity,spec) in enumerate(SPECS.items()):
        y=128+row*336
        draw.text((18,y+124),spec['label'],font=font(20),fill='#26343e')
        draw.line((136,y+280,1008,y+280),fill='#b5c1c4')
        for column,direction in enumerate(DIRECTIONS):
            sprite=family_sprites[identity][direction].resize((192,288),Image.Resampling.NEAREST)
            image.paste(sprite,(144+column*216,y),sprite)
    image.save(REVIEW/'family_turnaround.png')
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in original.items())
    print('Exported nine new family idles; approved fronts/palettes unchanged; Liam 26px, parents 34px.')


if __name__=='__main__':build()
