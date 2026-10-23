"""Assemble Serene's walks from approved art and directional stride masks."""
import argparse

from PIL import Image

from build_character_walk import ROOT, blank, build_direction_board, isolated, on_background, read_json, rgba, shifted, write_json
from build_dress_walk import legs_pose


def skirt_layer(idle, pose, palette, under_hand_rects=()):
    """Retain apron, pocket and patch pixels while posing the hem beneath hands."""
    output = blank(idle.size)
    allowed = {rgba(c) for key in ('sage', 'linen', 'mantle', 'outline')
               for c in palette['materials'][key]}
    for y, (source_y, left, right, sway) in enumerate(pose['skirt_rows'], start=21):
        for x in range(left, right):
            color = idle.getpixel((x, source_y))
            if any(rx <= x < rx+rw and ry <= source_y < ry+rh for rx,ry,rw,rh in under_hand_rects):
                color = rgba(palette['materials']['sage'][1])
            if color not in allowed:
                color = rgba(palette['materials']['sage'][1])
            if x in (left, right-1):
                color = rgba(palette['materials']['outline'][0])
            output.putpixel((x+sway, y), color)
    return output


def arm_layer(mask, template, palette, dy, neck_exclusion=None):
    """Use shared arm silhouettes with sage sleeves and turned-back linen cuffs."""
    codes = {rgba(v): k for k,v in template['semantic_colors'].items()}
    output = blank(mask.size)
    m = palette['materials']
    for y in range(mask.height):
        for x in range(mask.width):
            pixel = mask.getpixel((x,y))
            if not pixel[3]:
                continue
            semantic = codes[pixel]
            if neck_exclusion and semantic.startswith('skin_'):
                nx,ny,nw,nh=neck_exclusion
                if nx <= x < nx+nw and ny <= y < ny+nh:
                    continue
            if semantic == 'outline':
                color = m['outline'][0]
            elif semantic.startswith('skin_'):
                color = m['skin'][0 if semantic == 'skin_base' else 1]
            else:
                material = 'linen' if y >= 18+dy else 'sage'
                index = {'fabric_shadow':0,'fabric_base':1,'fabric_light':2}[semantic]
                color = m[material][index]
            output.putpixel((x,y), rgba(color))
    return output


def build(direction='front'):
    output = ROOT/f'assets/characters/serene/walk_{direction}'
    recipe_path = output/'recipe.json'
    recipe = read_json(recipe_path)
    template_path = (output/recipe['template']).resolve()
    template = read_json(template_path)
    palette = read_json(output/recipe['palette'])
    idle = Image.open(output/recipe['idle']).convert('RGBA')
    parts = (output/recipe['parts_directory']).resolve()
    parts.mkdir(parents=True,exist_ok=True)
    m = palette['materials']
    leg_materials = {
        'outline':{'base':m['outline'][0]},
        'skin':{'base':m['skin'][0],'shadow':m['skin'][1]},
        'leather':dict(zip(('shadow','base','light'),m['leather'],strict=True))
    }
    head = isolated(idle,[0,0,24,14])
    mantle = isolated(idle,recipe.get('mantle_rect',[0,14,24,5]))
    bodice_rect=recipe.get('bodice_rect',[7,19,10,2])
    bodice = isolated(idle,bodice_rect)
    head.save(parts/'head.png')
    mantle.save(parts/'shoulder_mantle.png')
    bodice.save(parts/'bodice.png')
    frames, records, comparisons = [], [], []
    for phase,pose in zip(template['frames'],recipe['costume_poses'],strict=True):
        assert phase['id'] == pose['id']
        directory = template_path.parent/f"frame_{phase['id']}"
        dy = phase['upper_body_offset'][1]
        torso = bodice.copy()
        if dy == -1:
            bx,by,bw,_=bodice_rect
            torso.alpha_composite(shifted(isolated(idle,[bx,by,bw,1]),-1))
        layers = {
            'legs':legs_pose(Image.open(directory/'legs.png').convert('RGBA'),pose,leg_materials),
            'skirt_and_apron':skirt_layer(idle,pose,palette,recipe.get('skirt_under_hand_rects',())),
            'bodice':torso,
        }
        for side in ('left','right'):
            mask=Image.open(directory/f'{side}_arm_mask.png').convert('RGBA')
            layers[f'{side}_arm']=arm_layer(mask,template,palette,dy,recipe.get('arm_neck_exclusion'))
        layers['shoulder_mantle']=shifted(mantle,dy)
        layers['head']=shifted(head,dy)
        image=blank((24,36))
        layer_files=[]
        for name,layer in layers.items():
            path=parts/f"frame_{phase['id']}_{name}.png"
            layer.save(path)
            image.alpha_composite(layer)
            layer_files.append(str(path.relative_to(ROOT)))
        assert set(image.getchannel('A').tobytes()) == {0,255}
        assert image.getbbox()[3] == 35
        assert not image.getchannel('A').crop((0,35,24,36)).getbbox()
        for ex,ey in recipe['idle_eye_pixels']:
            assert image.getpixel((ex,ey+dy)) == rgba(palette['eyes']['pupil'])
            assert image.getpixel((ex,ey+dy+1)) == rgba(palette['eyes']['iris'])
        image.save(output/f"frame_{phase['id']}.png")
        frames.append(image)
        compare=blank((48,36))
        compare.paste(Image.open(template_path.parent/phase['reference']).convert('RGBA'),(0,0))
        compare.paste(image,(24,0))
        comparisons.append(on_background(compare,16))
        records.append({
            'file':f"frame_{phase['id']}.png",'rect':[(len(frames)-1)*24,0,24,36],
            'phase':phase['phase'],'duration_ms':phase['duration_ms'],
            'upper_body_offset':phase['upper_body_offset'],
            'shoulder_mantle_offset':phase['upper_body_offset'],
            'eyes':[[x,y+dy] for x,y in recipe['idle_eye_pixels']],
            'hem_row':20+len(pose['skirt_rows']),
            'boot_top_rows':pose['boot_top_rows'],'layers_from_repo_root':layer_files
        })
        if 'leg_split_x' in pose:
            records[-1]['leg_split_x']=pose['leg_split_x']
    sheet=blank((96,36))
    for i,image in enumerate(frames):
        sheet.paste(image,(i*24,0))
    sheet.save(output/'spritesheet.png')
    on_background(sheet,12).save(output/'frames_review.png')
    durations=[f['duration_ms'] for f in template['frames']]
    previews=[on_background(image,20) for image in frames]
    for name,images in [(f'walk_{direction}_preview.gif',previews),('shared_motion_comparison.gif',comparisons)]:
        images[0].save(output/name,save_all=True,append_images=images[1:],duration=durations,
                       loop=0,disposal=2,optimize=False)
    write_json(output/'animation.json',{
        'character':'serene','animation':f'walk.{direction}','status':recipe['approval_status'],
        'image':'spritesheet.png','frame_size':[24,36],'foot_anchor':template['foot_anchor'],
        'loop':True,'duration_ms':sum(durations),'frames':records,'template':recipe['template'],
        'recipe':'recipe.json','offsets_baked_into_pixels':True,
        'review':{'gif':f'walk_{direction}_preview.gif','scale':20,'background':'#e8edf2'},
        'comparison':{'gif':'shared_motion_comparison.gif','scale':16,'columns':['caelan','serene']}
    })
    print(f'Built Serene {direction} walk: four shared-stride frames, coordinated head/mantle bob and skirt sway.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--direction',choices=['front','left','right','back','remaining','all'],default='front')
    args=parser.parse_args()
    directions=('left','right','back') if args.direction=='remaining' else ('front','left','right','back') if args.direction=='all' else (args.direction,)
    for direction in directions:
        build(direction)
    if args.direction in ('remaining','all'):
        build_direction_board('serene')
