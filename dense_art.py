"""Actor integration for the shared full-scene density renderer."""
from rendering import WorldCanvas, artwork


def draw_actor(target, actor, surface, position, elapsed_ms):
    provider=getattr(actor,'detailed_sprite',None)
    if provider is None:provider=getattr(actor,'detailed_idle',lambda _:None)
    detail=provider(elapsed_ms)
    if detail is not None and isinstance(target,WorldCanvas):
        image,anchor=detail
        logical_anchor=getattr(actor,'story_draw_anchor',None) or actor.draw_anchor
        target.blit(artwork(image,2),(position[0]+logical_anchor[0]-anchor[0]/2,
                                     position[1]+logical_anchor[1]-anchor[1]/2))
    else:target.blit(surface,position)
