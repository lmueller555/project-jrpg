"""Portrait speech bubbles attached to speakers in the running game world.

Layout is shared by drawing and input, so moving the camera cannot leave a
quest answer's clickable area behind. All coordinates use the native canvas.
"""
from dataclasses import dataclass

import pygame


TEXT_WIDTH = 224
MAX_LINES = 3
PORTRAIT_SIZE = 48
PADDING = 8
TEXT_OFFSET = PADDING + PORTRAIT_SIZE + 10
PANEL_WIDTH = TEXT_OFFSET + TEXT_WIDTH + PADDING
LINE_HEIGHT = 17


@dataclass(frozen=True)
class BubbleLayout:
    panel: pygame.Rect
    portrait: pygame.Rect | None
    text_origin: tuple
    choice_rects: tuple
    anchor: tuple
    tail_side: str | None
    offscreen: bool
    pending: bool
    portrait_key: str | None
    prompt_lines: tuple = ()
    option_lines: tuple = ()


class SpeechBubble:
    def __init__(self, social):
        self.social = social
        self._portrait_cache = {}

    def _camera(self, camera):
        if camera is not None:return camera
        director = getattr(self.social.game, 'camera', None)
        return director.position() if director is not None else (0, 0)

    def _anchor(self, camera):
        point = self.social.anchor_position()
        return (round(point[0]-camera[0]), round(point[1]-camera[1]))

    def _wrap_label(self, text, width):
        lines, current = [], ''
        for word in text.split():
            proposed = (current+' '+word).strip()
            if current and self.social.font.size(proposed)[0] > width:
                lines.append(current)
                current = word
            else:current = proposed
        if current:lines.append(current)
        return tuple(lines or [''])

    def _choice_content(self, choices):
        half_width = (TEXT_WIDTH-6)//2
        columns = (2 if len(choices) == 2 and all(
            self.social.font.size(option['text'])[0] <= half_width-12 for option in choices) else 1)
        button_width = half_width if columns == 2 else TEXT_WIDTH
        prompt = getattr(self.social, 'choice_prompt', None) or 'Will you help?'
        prompt_lines = self._wrap_label(prompt, TEXT_WIDTH)
        option_lines = tuple(self._wrap_label(option['text'], button_width-12) for option in choices)
        heights = tuple(max(23, len(lines)*LINE_HEIGHT+8) for lines in option_lines)
        return columns, button_width, prompt_lines, option_lines, heights

    def _protected_heads(self, anchor, camera):
        """Keep listeners visible too when a reply switches the bubble's owner."""
        protected = [pygame.Rect(anchor[0]-14, anchor[1]-2, 28, 38)]
        game, world = self.social.game, self.social.game.world
        actors = [game.player, self.social.actor]
        # Authored exchanges have no initiating actor. Resolve their other
        # speakers in this room so breakfast replies preserve every face.
        speaker_ids = {self.social.data['speakers'].get(page['speaker'], {}).get('actor_id', page['speaker'])
                       for page in getattr(self.social, 'pages', [])}
        actors.extend(actor for actor in getattr(world, 'npcs', [])
                      if actor.data.get('id') in speaker_ids)
        seen = {id(self.social.resolve_speaker())}
        for actor in actors:
            if actor is None or id(actor) in seen:continue
            seen.add(id(actor))
            point = getattr(actor, 'story_position', None) or actor.position
            draw_anchor = (getattr(actor, 'story_draw_anchor', None) or
                           (getattr(world, 'data', {}).get('player_draw_anchor', (12, 30))
                            if actor is game.player else getattr(actor, 'draw_anchor', (12, 30))))
            image = getattr(actor, 'story_sprite', None)
            if image is None and hasattr(actor, 'sprite'):
                image = (actor.sprite() if actor is game.player else actor.sprite(getattr(game, 'elapsed_ms', 0)))
            top = image.get_bounding_rect().top if isinstance(image, pygame.Surface) else 0
            opening = getattr(game, 'opening', None)
            if actor is game.player and getattr(opening, '_sleeping', False):
                origin = opening.data['sleep_head_origin']
                head = (origin[0]+12, origin[1])
            else:head = (point[0], point[1]-draw_anchor[1]+top)
            protected.append(pygame.Rect(round(head[0]-camera[0])-14,
                                         round(head[1]-camera[1])-2, 28, 38))
        return protected

    @staticmethod
    def _place(anchor, size, bounds, protected):
        width, height = size
        x, y = anchor
        candidates = [
            pygame.Rect(x-width//2, y-height-10, width, height),
            pygame.Rect(x-width//2, min(head.top for head in protected)-height-8, width, height),
            pygame.Rect(x-width//2, max(y+42, max(head.bottom for head in protected)+6), width, height),
            pygame.Rect(x+24, y-height//2, width, height),
            pygame.Rect(x-width-24, y-height//2, width, height),
        ]
        best = None
        for preference, original in enumerate(candidates):
            panel = original.clamp(bounds)
            # Visible heads matter more than the preferred above-speaker slot.
            covered = sum(panel.clip(head).width*panel.clip(head).height for head in protected)
            displacement = abs(panel.x-original.x)+abs(panel.y-original.y)
            score = covered*100 + displacement + preference*5
            if best is None or score < best[0]:best = score, panel
        return best[1]

    @staticmethod
    def _tail_side(panel, anchor, offscreen):
        if offscreen:return None
        x, y = anchor
        if y >= panel.bottom:return 'bottom'
        if y <= panel.top:return 'top'
        if x >= panel.right:return 'right'
        if x <= panel.left:return 'left'
        return None

    def layout(self, canvas_size=(480, 320), camera=None):
        social = self.social
        if not social.active and not social.pending:return None
        camera = self._camera(camera)
        anchor = self._anchor(camera)
        actor = social.resolve_speaker()
        opening = getattr(social.game, 'opening', None)
        visible_sleeping_player = (actor is social.game.player and
                                   getattr(opening, '_sleeping', False))
        offscreen = (actor is None or not (getattr(actor, 'story_visible', True) or visible_sleeping_player) or
                     not pygame.Rect((0, 0), canvas_size).collidepoint(anchor))
        pending = social.pending
        choices = list(social.choice_options) if social.choosing else []
        prompt_lines, option_lines = (), ()
        if pending:
            name = getattr(social.actor, 'data', {}).get('name', 'Your companion')
            label = f'{name} is setting their work down...'
            width = min(PANEL_WIDTH, social.hint_font.size(label)[0]+PADDING*2)
            height = 32
        else:
            width = PANEL_WIDTH
            height = 102
            if choices:
                columns, button_width, prompt_lines, option_lines, heights = self._choice_content(choices)
                button_top = 30+len(prompt_lines)*LINE_HEIGHT+3
                rows_height = max(heights) if columns == 2 else sum(heights)+3*(len(heights)-1)
                height = max(height, button_top+rows_height+23)
        bounds = pygame.Rect(6, 6, canvas_size[0]-12, canvas_size[1]-30)
        panel = self._place(anchor, (width, height), bounds,
                            self._protected_heads(anchor, camera))
        portrait = None if pending else pygame.Rect(panel.x+PADDING, panel.y+28,
                                                     PORTRAIT_SIZE, PORTRAIT_SIZE)
        choice_rects = []
        if choices:
            top = panel.y+button_top
            for index in range(len(choices)):
                choice_rects.append(pygame.Rect(panel.x+TEXT_OFFSET+(index%columns)*(button_width+6),
                                                top, button_width, heights[index]))
                if columns == 1:top += heights[index]+3
        speaker = social.data['speakers'][social.page['speaker']] if not pending else None
        return BubbleLayout(panel, portrait, (panel.x+TEXT_OFFSET, panel.y+30),
                            tuple(choice_rects), anchor,
                            self._tail_side(panel, anchor, offscreen), offscreen, pending,
                            speaker['portrait'] if speaker is not None else None,
                            prompt_lines, option_lines)

    @staticmethod
    def _tail(canvas, layout):
        panel, anchor, side = layout.panel, layout.anchor, layout.tail_side
        if side is None:return
        # The short pointer identifies the speaker without drawing a long line
        # across the room when the panel has been clamped near a screen edge.
        if side in ('bottom', 'top'):
            x = max(panel.left+12, min(panel.right-12, anchor[0]))
            y = panel.bottom-1 if side == 'bottom' else panel.top
            tip_y = min(y+9, anchor[1]) if side == 'bottom' else max(y-9, anchor[1])
            points = [(x-6, y), (x+6, y), (x, tip_y)]
        else:
            y = max(panel.top+12, min(panel.bottom-12, anchor[1]))
            x = panel.right-1 if side == 'right' else panel.left
            tip_x = min(x+9, anchor[0]) if side == 'right' else max(x-9, anchor[0])
            points = [(x, y-6), (x, y+6), (tip_x, y)]
        pygame.draw.polygon(canvas, '#b7a47b', points)
        pygame.draw.polygon(canvas, '#263c35', [(round((x+points[2][0])/2), round((y+points[2][1])/2))
                                              for x, y in points])

    def _portrait(self, key):
        source = self.social.portraits[key]
        cache = self._portrait_cache.get(key)
        if cache is None or cache[0] is not source:
            cache = source, pygame.transform.scale(source, (PORTRAIT_SIZE, PORTRAIT_SIZE))
            self._portrait_cache[key] = cache
        return cache[1]

    def draw(self, canvas, camera=None, elapsed_ms=0):
        layout = self.layout(canvas.get_size(), camera)
        if layout is None:return None
        social, panel = self.social, layout.panel
        pygame.draw.rect(canvas, '#101b19', panel.move(2, 3), border_radius=4)
        self._tail(canvas, layout)
        pygame.draw.rect(canvas, '#263c35', panel, border_radius=4)
        pygame.draw.rect(canvas, '#b7a47b', panel, width=1, border_radius=4)
        pygame.draw.rect(canvas, '#526761', panel.inflate(-4, -4), width=1, border_radius=3)
        if layout.pending:
            name = getattr(social.actor, 'data', {}).get('name', 'Your companion')
            image = social.hint_font.render(f'{name} is setting their work down...', False, '#f7eed5')
            canvas.blit(image, image.get_rect(center=panel.center))
            return layout
        speaker = social.data['speakers'][social.page['speaker']]
        name = speaker['name']+(' (nearby)' if layout.offscreen else '')
        canvas.blit(social.name_font.render(name, False, '#ffdc71'), (panel.x+PADDING, panel.y+9))
        canvas.blit(self._portrait(layout.portrait_key), layout.portrait)
        pygame.draw.rect(canvas, '#b7a47b', layout.portrait.inflate(2, 2), 1)
        text_x, text_y = layout.text_origin
        if social.choosing:
            for index, line in enumerate(layout.prompt_lines):
                canvas.blit(social.font.render(line, False, '#f7eed5'),
                            (text_x, text_y+index*LINE_HEIGHT))
            for lines, rect in zip(layout.option_lines, layout.choice_rects):
                pygame.draw.rect(canvas, '#344e3e', rect, border_radius=2)
                pygame.draw.rect(canvas, '#b7a47b', rect, 1, border_radius=2)
                first_y = rect.centery-((len(lines)-1)*LINE_HEIGHT)//2
                for index, line in enumerate(lines):
                    label = social.font.render(line, False, '#ffdc71')
                    canvas.blit(label, label.get_rect(center=(rect.centerx, first_y+index*LINE_HEIGHT)))
            hint = 'Click a choice to answer'
        else:
            for index, line in enumerate(social.page['lines']):
                canvas.blit(social.font.render(line, False, '#f7eed5'),
                            (text_x, text_y+index*LINE_HEIGHT))
            hint = 'Click anywhere / Space'
        canvas.blit(social.hint_font.render(hint, False, '#c9c9b5'),
                    (text_x, panel.bottom-15))
        if not social.choosing and int(elapsed_ms//450) % 2 == 0:
            x, y = panel.right-17, panel.bottom-12
            pygame.draw.polygon(canvas, '#ffdc71', [(x-3, y-2), (x+3, y-2), (x, y+2)])
        return layout
