"""Assemble Tomas's shorter walks from approved directional art and shared poses."""
import argparse

from PIL import Image, ImageDraw

from build_character_walk import ROOT, blank, build_direction_board, isolated, materialize, on_background, read_json, rgba, shifted, write_json
from build_dress_walk import legs_pose
from build_serene_idle import font


def registered_arm(mask, template, palette, registration, neck_exclusion=None):
    # Register the adult arm region to Tomas's narrower, shorter proportions.
    if neck_exclusion:
        mask=mask.copy()
        nx,ny,nw,nh=neck_exclusion
        skin_codes={rgba(template['semantic_colors'][key]) for key in ('skin_base','skin_shadow')}
        for y in range(ny,ny+nh):
            for x in range(nx,nx+nw):
                if mask.getpixel((x,y)) in skin_codes:mask.putpixel((x,y),(0,0,0,0))
    colored=materialize(mask,template,palette)
    x,y,width,height=registration['source_rect']
    scaled=colored.crop((x,y,x+width,y+height)).resize(tuple(registration['target_size']),Image.Resampling.NEAREST)
    output=blank((24,36))
    output.paste(scaled,tuple(registration['offset']))
    return output


def build(direction='front'):
    output=ROOT/f'assets/characters/tomas/walk_{direction}'
    recipe=read_json(output/'recipe.json')
    template_path=(output/recipe['template']).resolve()
    template=read_json(template_path)
    palette=read_json(output/recipe['materials'])
    idle=Image.open(output/recipe['idle']).convert('RGBA')
    parts=(output/recipe['parts_directory']).resolve()
    parts.mkdir(parents=True,exist_ok=True)
    m=palette['materials']
    # The shared calf/boot adapter receives trouser colors for the upper leg.
    leg_materials={
        'outline':{'base':m['outline'][0]},
        'skin':{'base':m['trousers'][1],'shadow':m['trousers'][0]},
        'leather':dict(zip(('shadow','base','light'),m['leather'],strict=True))
    }
    head=isolated(idle,recipe['head_rect'])
    upper=isolated(idle,recipe['upper_body_rect'])
    if 'neckline_rect' in recipe:
        upper.alpha_composite(isolated(idle,recipe['neckline_rect']))
    waist=isolated(idle,recipe['waist_rect'])
    hem=isolated(idle,recipe['hem_rect'])
    for name,image in [('head',head),('upper_body',upper),('waist',waist),('tunic_hem',hem)]:
        image.save(parts/f'{name}.png')
    frames,records,comparisons=[],[],[]
    for phase,pose in zip(template['frames'],recipe['costume_poses'],strict=True):
        assert phase['id']==pose['id']
        dy=phase['upper_body_offset'][1]
        directory=template_path.parent/f"frame_{phase['id']}"
        legs=legs_pose(Image.open(directory/'legs.png').convert('RGBA'),pose,leg_materials)
        patch=blank(idle.size)
        for x,y in pose['patch_pixels']:
            assert legs.getpixel((x,y)) in {rgba(c) for c in m['trousers']}, 'Patch must lie within trouser cloth'
            patch.putpixel((x,y),rgba(m['patch'][0]))
        torso=shifted(upper,dy)
        if dy==-1:
            x,y,w,h=recipe['upper_body_rect']
            torso.alpha_composite(isolated(upper,[x,y+h-1,w,1]))
        layers={'legs':legs,'left_knee_patch':patch,'waist':waist,'tunic_hem':hem}
        for side in ('left','right'):
            mask=Image.open(directory/f'{side}_arm_mask.png').convert('RGBA')
            layers[f'{side}_arm']=registered_arm(mask,template,recipe['arm_palette'],recipe['arm_registration'],recipe.get('arm_neck_exclusion'))
        # The original chest and collar cover any overlap from registered arms.
        layers['upper_body']=torso
        layers['head']=shifted(head,dy)
        image=blank(idle.size)
        layer_files=[]
        for name,layer in layers.items():
            path=parts/f"frame_{phase['id']}_{name}.png"
            layer.save(path)
            image.alpha_composite(layer)
            layer_files.append(str(path.relative_to(ROOT)))
        assert image.size==(24,36) and image.getbbox()[1::2]==(3+dy,35)
        assert set(image.getchannel('A').tobytes())=={0,255}
        for x,y in recipe['idle_eye_pixels']:
            assert image.getpixel((x,y+dy))==rgba(palette['eyes']['pupil'])
            assert image.getpixel((x,y+dy+1))==rgba(palette['eyes']['iris'])
        image.save(output/f"frame_{phase['id']}.png")
        frames.append(image)
        compare=blank((48,36))
        reference=Image.open(template_path.parent/phase['reference']).convert('RGBA')
        assert reference.getbbox()[1]==image.getbbox()[1]-2
        compare.paste(reference,(0,0));compare.paste(image,(24,0))
        board=Image.new('RGB',(768,624),'#e8edf2')
        board.paste(on_background(compare,16),(0,0))
        draw=ImageDraw.Draw(board)
        draw.text((80,590),'Caelan (approved)',font=font(20),fill='#26343e')
        draw.text((470,590),'Tomas (review)',font=font(20),fill='#26343e')
        comparisons.append(board)
        records.append({
            'file':f"frame_{phase['id']}.png",'rect':[(len(frames)-1)*24,0,24,36],
            'phase':phase['phase'],'duration_ms':phase['duration_ms'],
            'upper_body_offset':phase['upper_body_offset'],
            'shoulder_offset':phase['upper_body_offset'],
            'visible_height_px':32-dy,'eyes':[[x,y+dy] for x,y in recipe['idle_eye_pixels']],
            'boot_top_rows':pose['boot_top_rows'],'patch_pixels':pose['patch_pixels'],
            'layers_from_repo_root':layer_files
        })
        if 'leg_split_x' in pose:records[-1]['leg_split_x']=pose['leg_split_x']
    sheet=blank((96,36))
    for i,image in enumerate(frames):sheet.paste(image,(i*24,0))
    sheet.save(output/'spritesheet.png')
    on_background(sheet,12).save(output/'frames_review.png')
    durations=[phase['duration_ms'] for phase in template['frames']]
    previews=[on_background(image,20) for image in frames]
    for name,images in [(f'walk_{direction}_preview.gif',previews),('shared_motion_comparison.gif',comparisons)]:
        images[0].save(output/name,save_all=True,append_images=images[1:],duration=durations,
                       loop=0,disposal=2,optimize=False)
    write_json(output/'animation.json',{
        'character':'tomas','animation':f'walk.{direction}','status':recipe['approval_status'],
        'image':'spritesheet.png','frame_size':[24,36],'foot_anchor':[12,34],
        'rest_visible_height_px':32,'height_difference_from_caelan_px':-2,
        'loop':True,'duration_ms':sum(durations),'frames':records,
        'template':recipe['template'],'recipe':'recipe.json','offsets_baked_into_pixels':True,
        'arm_registration':recipe['arm_registration'],
        'knee_patch':({'anatomical_side':'left','front_screen_side':'right'} if direction=='front' else
                      {'anatomical_side':'left','visible':direction=='left','visibility_reason':
                       {'left':'near left leg','right':'occluded from right profile','back':'front of knee faces away'}[direction]}),
        'review':{'gif':f'walk_{direction}_preview.gif','scale':20,'background':'#e8edf2'},
        'comparison':{'gif':'shared_motion_comparison.gif','scale':16,'columns':['caelan','tomas']}
    })
    print(f'Built Tomas {direction} walk: four phases, shorter appearance and directional costume poses.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--direction',choices=['front','left','right','back','remaining','all'],default='front')
    args=parser.parse_args()
    directions=('left','right','back') if args.direction=='remaining' else ('front','left','right','back') if args.direction=='all' else (args.direction,)
    for direction in directions:build(direction)
    if args.direction in ('remaining','all'):build_direction_board('tomas')
