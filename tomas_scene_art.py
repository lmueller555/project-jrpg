"""Identity-scoped Tomas density boundary. No schedule, cue or prop ownership."""
from rendering import load_art
BASE = 'assets/characters/named_hd/tomas'
ACTIONS = 'assets/characters/tomas/activity_hd'
BREAKFAST = 'assets/story/sanctuary_opening/poses/'
SACKS = 'assets/story/halden/tomas/'
PROPS = 'assets/characters/tomas/routines/props/'

def enabled(actor):
    return (getattr(actor,'data',{}).get('id')=='tomas'
            and getattr(actor,'sprite_root',None)==BASE
            and getattr(actor,'animation_path',None)==ACTIONS+'/routines/animations.json')

def replacement(actor,path,flipped=False):
    if not enabled(actor):return None
    if path.startswith(BREAKFAST+'tomas'):
        suffix=path[len(BREAKFAST):]
        if flipped:
            if suffix=='tomas_seated.png':suffix='tomas_seated_right.png'
            elif suffix.startswith('tomas_eat/'):suffix=suffix.replace('tomas_eat/','tomas_eat_right/',1)
            else:return None
        return ACTIONS+'/breakfast/'+suffix
    if path.startswith(SACKS):return ACTIONS+'/sack/'+path[len(SACKS):]
    if path.startswith(PROPS) and path[len(PROPS):] in ('bundle.png','stack.png','mechanism.png'):
        return ACTIONS+'/routines/props/'+path[len(PROPS):]
    if path=='assets/story/halden/sack.png':return ACTIONS+'/sack/sack.png'
    return None

def image(world,actor,path,legacy_loader,flipped=False):
    native=replacement(actor,path,flipped)
    return load_art(world,native,{'artwork_pixels_per_world_pixel':2}) if native else legacy_loader(path)
