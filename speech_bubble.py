"""Readable display-resolution portrait bubbles in the running game world.

All layout and hit testing use world-view coordinates. Lettering is rendered
straight onto the display-resolution UI surface, separately from pixel art.
"""
from dataclasses import dataclass
import math

import pygame
from ui_style import UIStyle, FOREST, BRASS, IVORY, GOLD, MUTED

TEXT_WIDTH = 224
MAX_LINES = 3
PORTRAIT_SIZE = 48
PADDING = 8
TEXT_OFFSET = PADDING + PORTRAIT_SIZE + 10
PANEL_WIDTH = TEXT_OFFSET + TEXT_WIDTH + PADDING

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
    name_lines: tuple = ()
    line_height: int = 14

class SpeechBubble:
    def __init__(self, social):
        self.social = social
        self._fallback_surface = None

    def _painter(self, canvas=None):
        if hasattr(self.social, 'painter'):return self.social.painter(canvas)
        game = self.social.game
        if not hasattr(game, 'ui'):game.ui = UIStyle(game)
        if canvas is None:
            if self._fallback_surface is None:
                self._fallback_surface = pygame.Surface((480, 320), pygame.SRCALPHA)
            canvas = self._fallback_surface
        return game.ui.painter(canvas)

    def _camera(self, camera):
        if camera is not None:return camera
        director = getattr(self.social.game, 'camera', None)
        return director.position() if director is not None else (0, 0)

    def _anchor(self, camera):
        point = self.social.anchor_position()
        return (round(point[0]-camera[0]), round(point[1]-camera[1]))

    def _cutscene_phase(self):
        """Only the staged mill encounter uses deliberate off-speaker framing."""
        quest = getattr(self.social.game, 'mill_quest', None)
        if (getattr(quest, 'encounter_cutscene_active', False)
                and getattr(self.social, 'script_identifier', None) == 'mill_encounter_intro'):
            return getattr(quest, 'encounter_cutscene_phase', 'conversation')
        return None

    def _choice_content(self, choices, painter):
        half_width = (TEXT_WIDTH-6)//2
        columns = (2 if len(choices) == 2 and all(
            painter.font().size(option['text'])[0] <= half_width-26 for option in choices) else 1)
        button_width = half_width if columns == 2 else TEXT_WIDTH
        prompt = getattr(self.social, 'choice_prompt', None) or 'Will you help?'
        prompt_lines = tuple(painter.wrap(prompt, TEXT_WIDTH))
        option_lines = tuple(tuple(painter.wrap(option['text'], button_width-26)) for option in choices)
        line_height = painter.font().get_linesize()+2
        heights = tuple(max(24, len(lines)*line_height+10) for lines in option_lines)
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

    def layout(self, canvas_size=(480, 320), camera=None, painter=None):
        social = self.social
        if not social.active and not social.pending:return None
        painter = painter or self._painter()
        camera = self._camera(camera)
        anchor = self._anchor(camera)
        actor = social.resolve_speaker()
        opening = getattr(social.game, 'opening', None)
        visible_sleeping_player = (actor is social.game.player and getattr(opening, '_sleeping', False))
        offscreen = (actor is None or not (getattr(actor, 'story_visible', True) or visible_sleeping_player) or
                     not pygame.Rect((0, 0), (480, 320)).collidepoint(anchor))
        pending = social.pending
        cutscene_phase = self._cutscene_phase() if not pending else None
        choices = list(social.choice_options) if social.choosing else []
        prompt_lines, option_lines, name_lines = (), (), ()
        line_height = painter.font().get_linesize()+2
        hint_height = painter.font('small').get_height()
        if pending:
            name = getattr(social.actor, 'data', {}).get('name', 'Your companion')
            label = f'{name} is setting their work down…'
            prompt_lines = tuple(painter.wrap(label, PANEL_WIDTH-20, role='small'))
            width = min(PANEL_WIDTH, max(painter.font('small').size(line)[0] for line in prompt_lines)+20)
            height = max(28, len(prompt_lines)*(hint_height+2)+16)
            text_top = 8
        else:
            speaker = social.data['speakers'][social.page['speaker']]
            name = speaker['name']+(' · nearby' if offscreen and not cutscene_phase else '')
            name_lines = tuple(painter.wrap(name, TEXT_WIDTH, role='name', bold=True))
            text_top = 10+len(name_lines)*(painter.font('name', bold=True).get_linesize()+1)+4
            width = PANEL_WIDTH
            height = max(72, text_top+len(social.page['lines'])*line_height+hint_height+14)
            if choices:
                columns, button_width, prompt_lines, option_lines, heights = self._choice_content(choices, painter)
                button_top = text_top+len(prompt_lines)*line_height+5
                rows_height = max(heights) if columns == 2 else sum(heights)+4*(len(heights)-1)
                height = max(76, button_top+rows_height+hint_height+14)
        # Reserve only a small safe margin; speech no longer competes with a
        # permanent keyboard-help strip at the bottom of the game world.
        bounds = pygame.Rect(6, 6, 468, 304)
        if cutscene_phase:
            # Keep the creature in the upper part of the shot while its
            # off-screen observers speak. On the return shot the party stands
            # near the southern map bound, so the panel moves to the top instead.
            top = bounds.top if cutscene_phase == 'pan_back' else bounds.bottom-math.ceil(height)
            panel = pygame.Rect(bounds.centerx-width//2, top, width, math.ceil(height))
        else:
            panel = self._place(anchor, (width, math.ceil(height)), bounds,
                                self._protected_heads(anchor, camera))
        portrait = None if pending else pygame.Rect(panel.x+PADDING, panel.y+12,
                                                     PORTRAIT_SIZE, PORTRAIT_SIZE)
        choice_rects = []
        if choices:
            top = panel.y+button_top
            for index in range(len(choices)):
                choice_rects.append(pygame.Rect(panel.x+TEXT_OFFSET+(index%columns)*(button_width+6),
                                                top, button_width, heights[index]))
                if columns == 1:top += heights[index]+4
        speaker = social.data['speakers'][social.page['speaker']] if not pending else None
        return BubbleLayout(panel, portrait, (panel.x+TEXT_OFFSET, panel.y+text_top),
                            tuple(choice_rects), anchor,
                            None if cutscene_phase else self._tail_side(panel, anchor, offscreen), offscreen, pending,
                            speaker['portrait'] if speaker is not None else None,
                            prompt_lines, option_lines, name_lines, line_height)

    @staticmethod
    def _tail(painter, layout):
        panel, anchor, side = layout.panel, layout.anchor, layout.tail_side
        if side is None:return
        if side in ('bottom', 'top'):
            x = max(panel.left+12, min(panel.right-12, anchor[0]))
            y = panel.bottom-1 if side == 'bottom' else panel.top
            tip_y = min(y+9, anchor[1]) if side == 'bottom' else max(y-9, anchor[1])
            points = [(x-5, y), (x+5, y), (x, tip_y)]
        else:
            y = max(panel.top+12, min(panel.bottom-12, anchor[1]))
            x = panel.right-1 if side == 'right' else panel.left
            tip_x = min(x+9, anchor[0]) if side == 'right' else max(x-9, anchor[0])
            points = [(x, y-5), (x, y+5), (tip_x, y)]
        pygame.draw.polygon(painter.canvas, BRASS, [painter.point(point) for point in points])
        inner = [(round((x+points[2][0])/2), round((y+points[2][1])/2)) for x, y in points]
        pygame.draw.polygon(painter.canvas, FOREST, [painter.point(point) for point in inner])

    def draw(self, canvas, camera=None, elapsed_ms=0):
        painter = self._painter(canvas)
        layout = self.layout(camera=camera, painter=painter)
        if layout is None:return None
        social, panel = self.social, layout.panel
        self._tail(painter, layout)
        painter.panel(panel)
        if layout.pending:
            top = panel.y+8
            for line in layout.prompt_lines:
                painter.text(line, (panel.centerx, top), role='small', anchor='midtop')
                top += painter.font('small').get_height()+2
            return layout
        painter.image(social.portraits[layout.portrait_key], layout.portrait)
        painter.rect(BRASS, layout.portrait.inflate(2, 2), 1)
        name_x = panel.x+TEXT_OFFSET
        name_height = painter.font('name', bold=True).get_linesize()+1
        for index, line in enumerate(layout.name_lines):
            painter.text(line, (name_x, panel.y+10+index*name_height),
                         role='name', color=GOLD, bold=True)
        text_x, text_y = layout.text_origin
        if social.choosing:
            for index, line in enumerate(layout.prompt_lines):
                painter.text(line, (text_x, text_y+index*layout.line_height))
            point = getattr(social, 'pointer_position', None)
            pressed = bool(getattr(social, 'pointer_pressed', False))
            for lines, rect in zip(layout.option_lines, layout.choice_rects):
                selected = point is not None and rect.collidepoint(point)
                painter.button(rect, '', selected=selected, pressed=selected and pressed)
                first_y = rect.centery-((len(lines)-1)*layout.line_height)/2
                for index, line in enumerate(lines):
                    painter.text(line, (rect.centerx+(5 if selected else 0), first_y+index*layout.line_height),
                                 color=GOLD if selected else IVORY, anchor='center')
            hint = 'Choose a response'
        else:
            for index, line in enumerate(social.page['lines']):
                painter.text(line, (text_x, text_y+index*layout.line_height))
            hint = 'Click to continue'
        painter.text(hint, (text_x, panel.bottom-painter.font('small').get_height()-7),
                     role='small', color=MUTED)
        reduced_motion = getattr(getattr(social.game, 'audio', None), 'reduced_motion', False)
        if not social.choosing and (reduced_motion or int(elapsed_ms//650) % 2 == 0):
            painter.lantern((panel.right-12, panel.bottom-13), size=6)
        return layout
