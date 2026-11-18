"""World-sized canvas with ordered, display-density character patches.

Patches capture the background at the actor's depth. Later blits are replayed
within disjoint patches, retaining foreground transparency and occlusion.
"""
import math
import pygame


class WorldCanvas(pygame.Surface):
    def __init__(self, size):
        super().__init__(size)
        self.patches = []
        self.snapshots = {}
        self.dense = pygame.Surface((size[0]*2, size[1]*2), pygame.SRCALPHA)

    def reset_detail(self):
        self.patches.clear()
        self.snapshots.clear()

    def sync_primitives(self):
        """Include direct pygame.draw/fill effects that bypass Surface.blit."""
        for rect in self.patches:
            key=tuple(rect)
            current=pygame.image.tobytes(self.subsurface(rect),'RGB')
            previous=self.snapshots[key]
            if current != previous:
                for index in range(rect.w*rect.h):
                    offset=index*3
                    color=current[offset:offset+3]
                    if color != previous[offset:offset+3]:
                        self.dense.fill(tuple(color), (2*(rect.x+index%rect.w),
                                                      2*(rect.y+index//rect.w),2,2))
                self.snapshots[key]=current

    @staticmethod
    def doubled(rect):
        return pygame.Rect(rect.x*2, rect.y*2, rect.w*2, rect.h*2)

    def blit(self, source, dest, area=None, special_flags=0):
        self.sync_primitives()
        result = super().blit(source, dest, area, special_flags)
        if self.patches and result:
            origin = pygame.Rect(dest).topleft if isinstance(dest, pygame.Rect) else dest[:2]
            sx, sy = (0, 0) if area is None else pygame.Rect(area).topleft
            for patch in self.patches:
                overlap = result.clip(patch)
                if not overlap:continue
                crop = pygame.Rect(overlap.x-int(origin[0])+sx,
                                   overlap.y-int(origin[1])+sy, overlap.w, overlap.h)
                image = pygame.transform.scale(source.subsurface(crop), (overlap.w*2, overlap.h*2))
                self.dense.blit(image, self.doubled(overlap), special_flags=special_flags)
                self.snapshots[tuple(patch)]=pygame.image.tobytes(self.subsurface(patch),'RGB')
        return result

    def blit_art(self, source, position):
        self.sync_primitives()
        x, y = position
        bounds = pygame.Rect(math.floor(x), math.floor(y),
                             math.ceil(x+source.get_width()/2)-math.floor(x),
                             math.ceil(y+source.get_height()/2)-math.floor(y))
        bounds = bounds.clip(self.get_clip())
        remaining = [bounds] if bounds else []
        for old in self.patches:
            pieces = []
            for rect in remaining:
                overlap = rect.clip(old)
                if not overlap:pieces.append(rect);continue
                pieces.extend(r for r in (
                    pygame.Rect(rect.x,rect.y,rect.w,overlap.top-rect.top),
                    pygame.Rect(rect.x,overlap.bottom,rect.w,rect.bottom-overlap.bottom),
                    pygame.Rect(rect.x,overlap.top,overlap.left-rect.left,overlap.h),
                    pygame.Rect(overlap.right,overlap.top,rect.right-overlap.right,overlap.h),
                ) if r.w and r.h)
            remaining = pieces
        for rect in remaining:
            self.dense.blit(pygame.transform.scale(self.subsurface(rect), (rect.w*2,rect.h*2)),
                            self.doubled(rect))
            self.snapshots[tuple(rect)]=pygame.image.tobytes(self.subsurface(rect),'RGB')
        self.patches.extend(remaining)
        self.dense.set_clip(self.doubled(bounds))
        self.dense.blit(source, (round(x*2),round(y*2)))
        self.dense.set_clip(None)

    def present_detail(self, target):
        self.sync_primitives()
        for rect in self.patches:
            # Use common rounded edges at non-integer window scales.
            x0=round(rect.left*target.get_width()/self.get_width())
            x1=round(rect.right*target.get_width()/self.get_width())
            y0=round(rect.top*target.get_height()/self.get_height())
            y1=round(rect.bottom*target.get_height()/self.get_height())
            if x1>x0 and y1>y0:
                target.blit(pygame.transform.scale(self.dense.subsurface(self.doubled(rect)),
                                                  (x1-x0,y1-y0)),(x0,y0))


def draw_actor(target, actor, surface, position, elapsed_ms):
    detail_provider = getattr(actor, 'detailed_sprite', None)
    if detail_provider is None:detail_provider = getattr(actor, 'detailed_idle', lambda _: None)
    detail = detail_provider(elapsed_ms)
    if detail is not None and isinstance(target, WorldCanvas):
        image, detail_anchor = detail
        # Recover the ground position from the caller's ordinary drawing anchor,
        # then apply the detailed artwork's anchor at its fixed 2x density.
        anchor = getattr(actor, 'story_draw_anchor', None) or actor.draw_anchor
        target.blit_art(image, (position[0]+anchor[0]-detail_anchor[0]/2,
                                position[1]+anchor[1]-detail_anchor[1]/2))
    else:
        target.blit(surface, position)
