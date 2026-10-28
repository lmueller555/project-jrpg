"""Aether Lattice navigation, explicit purchases and accessible node details."""
import pygame

from attribute_icons import draw_attribute_icon
from ui_style import (FOREST, FOREST_DARK, FOREST_LIGHT, IVORY, GOLD, BRASS,
                      MUTED, DISABLED, ERROR)


class LatticeUI:
    MIN_ZOOM = .18
    MAX_ZOOM = 2.0

    @staticmethod
    def _steps_label(amount):return str(amount)+' Step'+('' if amount == 1 else 's')

    def __init__(self, game):
        self.game = game
        self.character_id = getattr(game.attributes, 'character_id', 'caelan')
        self.close_rect = pygame.Rect(438, 14, 24, 24)
        self.help_rect = pygame.Rect(410, 14, 22, 24)
        self.move_rect = pygame.Rect(300, 252, 164, 24)
        self.activate_rect = pygame.Rect(300, 280, 164, 24)
        self.map_rect = pygame.Rect(16, 78, 274, 226)
        self.detail_view = pygame.Rect(307, 85, 147, 157)
        self.detail_track = pygame.Rect(458, 85, 4, 157)
        self.zoom_out_rect = pygame.Rect(24, 275, 24, 22)
        self.zoom_in_rect = pygame.Rect(52, 275, 24, 22)
        self.fit_rect = pygame.Rect(80, 275, 32, 22)
        self.help_panel = pygame.Rect(32, 40, 416, 248)
        self.help_view = pygame.Rect(46, 80, 386, 188)
        self.help_close_rect = pygame.Rect(410, 47, 24, 24)
        self.confirm_panel = pygame.Rect(28, 56, 424, 188)
        self.confirm_view = pygame.Rect(42, 94, 396, 114)
        self.confirm_rect = pygame.Rect(250, 216, 84, 20)
        self.cancel_rect = pygame.Rect(344, 216, 84, 20)
        self.reset()

    @property
    def lattice(self):return self.game.lattice

    @property
    def board(self):return self.lattice.board

    def _painter(self, canvas=None):
        return self.game.ui.painter(canvas if canvas is not None else self.game.ui_surface)

    def reset(self):
        self.is_open = False
        self.selected = None
        self.hovered = None
        self.pointer = None
        self.zoom = .8
        self.pan = pygame.Vector2(0, 0)
        self.pending = None
        self.message = ''
        self.detail_scroll = 0
        self.detail_max_scroll = 0
        self.detail_thumb = None
        self._held = False
        self.dragging = False
        self.drag_detail = False
        self.drag_origin = None
        self.help_open = False
        self.help_scroll = 0
        self.help_max_scroll = 0
        self.confirm_scroll = 0
        self.confirm_max_scroll = 0

    def open(self):
        self.is_open = True
        self.pending = None
        self.message = ''
        self.hovered = None
        self.pointer = None
        self.help_open = False
        self._held = self.dragging = self.drag_detail = False
        self._select(self.lattice.state(self.character_id)['position'], center=True)
        self.game.ui.sound('confirm')

    def close(self):
        self.is_open = False
        self.pending = None
        self.hovered = None
        self.pointer = None
        self.help_open = False
        self._held = self.dragging = self.drag_detail = False
        self.game.ui.sound('back')

    def _select(self, identifier, center=False):
        if identifier not in self.board.nodes:return
        if identifier != self.selected:
            self.selected = identifier
            self.detail_scroll = 0
            self.pending = None
            self.message = ''
            self.game.ui.sound('move')
        if center:self.center_on(identifier)

    def center_on(self, identifier):
        if identifier in self.board.nodes:self.pan.update(self.board.nodes[identifier]['position'])

    def node_position(self, identifier):
        point = pygame.Vector2(self.board.nodes[identifier]['position'])
        return pygame.Vector2(self.map_rect.center)+(point-self.pan)*self.zoom

    def fit_board(self):
        points = [pygame.Vector2(node['position']) for node in self.board.nodes.values()]
        left, right = min(p.x for p in points), max(p.x for p in points)
        top, bottom = min(p.y for p in points), max(p.y for p in points)
        self.pan.update((left+right)/2, (top+bottom)/2)
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM,
                        (self.map_rect.width-44)/max(1, right-left),
                        (self.map_rect.height-74)/max(1, bottom-top)))

    def _zoom(self, factor):
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom*factor))

    def _node_at(self, point):
        if point is None or not self.map_rect.collidepoint(point):return None
        radius = max(8, 11*self.zoom)
        nodes = [(self.node_position(identifier).distance_squared_to(point), identifier)
                 for identifier in self.board.nodes]
        distance, identifier = min(nodes)
        return identifier if distance <= radius*radius else None

    def _direction(self, direction):
        if self.selected not in self.board.nodes:return
        origin = pygame.Vector2(self.board.nodes[self.selected]['position'])
        forward = pygame.Vector2(direction)
        neighbors = set()
        for edge in self.board.edges:
            if edge['from'] == self.selected:neighbors.add(edge['to'])
            if edge['to'] == self.selected:neighbors.add(edge['from'])
        candidates = []
        for identifier, node in self.board.nodes.items():
            delta = pygame.Vector2(node['position'])-origin
            dot = delta.dot(forward)
            if dot <= 0:continue
            perpendicular = abs(delta.cross(forward))
            candidates.append((identifier not in neighbors, perpendicular/max(1, dot),
                               delta.length_squared(), identifier))
        if candidates:self._select(min(candidates)[-1], center=True)

    def _move_reason(self):
        return self.game.lattice_move_reason(self.selected)

    def _activation_reason(self):
        return self.game.lattice_activation_reason(self.selected)

    def _prepare(self, action):
        reason = self._move_reason() if action == 'move' else self._activation_reason()
        if reason:
            self.message = reason
            self.pending = None
            self.detail_scroll = 0
            return False
        self.pending = (action, self.selected)
        self.confirm_scroll = 0
        self.message = 'Confirm travel below.' if action == 'move' else 'Confirm crystal use below.'
        self.detail_scroll = 0
        self.game.ui.sound('confirm')
        return True

    def _commit(self):
        if self.pending is None:return False
        action, identifier = self.pending
        self.pending = None
        if identifier != self.selected:return False
        success = (self.game.move_lattice(identifier) if action == 'move'
                   else self.game.activate_lattice(identifier))
        if success:
            self.message = 'Travel complete.' if action == 'move' else 'Node activated.'
            if action == 'move':self.center_on(identifier)
            self.game.ui.sound('confirm')
        else:self.message = self._move_reason() if action == 'move' else self._activation_reason()
        self.detail_scroll = 0
        return success

    def _action(self, action):
        if self.pending == (action, self.selected):return self._commit()
        return self._prepare(action)

    def detail_text(self):
        if self.selected not in self.board.nodes:return []
        node = self.board.nodes[self.selected]
        state = self.lattice.state(self.character_id)
        lines = [node.get('name', self.selected)]
        if self.selected == state['position']:lines.append('Current position')
        if self.selected in state['activated']:lines.append('Activated')
        elif self.selected in state['visited']:lines.append('Visited')
        if node['kind'] == 'stat':
            label = self.game.attributes.definitions[node['stat']]['label']
            value = self.game.attributes.value(node['stat'])
            lines.append(label+' +'+str(node['amount']))
            if self.selected not in state['activated']:
                lines.append('After activation: '+str(value)+' → '+str(value+node['amount']))
            if node['stat'] in ('hp', 'mp'):lines.append('Current '+label+' stays unchanged.')
        elif node['kind'] == 'ability':
            ability = self.board.abilities[node['ability_id']]
            lines.extend((ability['name'], ability['description']))
        else:lines.append('Blank node: travel only.')
        route = self.lattice.route(self.selected, self.character_id)
        if route is not None:
            distance = max(0, len(route)-1)
            lines.append('Travel: '+self._steps_label(distance))
            if distance:lines.append('Return along this route: '+self._steps_label(distance))
        else:lines.append('No open route at this Attunement.')
        reason = self._move_reason()
        if reason:lines.append(reason)
        if node['cost']:
            lines.append('Activation cost')
            for crystal, amount in node['cost'].items():
                name = self.board.crystals[crystal]['name']
                lines.append(name+' ×'+str(amount)+' ('+str(self.game.inventory.quantity(crystal))+' owned)')
            reason = self._activation_reason()
            if reason:lines.append(reason)
        lines.append(node.get('description', ''))
        if self.pending is not None:lines.append('Enter confirms. Esc cancels.')
        if self.message:lines.insert(0, self.message)
        lines.append('Aether Crystals')
        for identifier, crystal in self.board.crystals.items():
            lines.append(crystal['name']+': '+str(self.game.inventory.quantity(identifier)))
        learned = self.lattice.learned_abilities(self.character_id)
        if learned:
            lines.append('Known abilities')
            lines.extend(self.board.abilities[identifier]['name'] for identifier in learned)
        return [line for line in lines if line]

    def confirmation_text(self):
        if self.pending is None:return []
        action, identifier = self.pending
        node = self.board.nodes[identifier]
        if action == 'move':
            route = self.lattice.route(identifier, self.character_id) or []
            cost = max(0, len(route)-1)
            return ['Move to '+node.get('name', identifier),
                    'Spend '+self._steps_label(cost)+' ('+str(self.lattice.steps(self.character_id))+' available).',
                    'Return along this path also costs '+self._steps_label(cost)+'.',
                    'No crystals are spent.',
                    'Attunement remains '+str(self.lattice.rank(self.character_id))+'.']
        lines = []
        if node['kind'] == 'stat':
            label = self.game.attributes.definitions[node['stat']]['label']
            value = self.game.attributes.value(node['stat'])
            lines.append(label+': '+str(value)+' → '+str(value+node['amount']))
            if node['stat'] in ('hp', 'mp'):
                current = self.game.attributes.current_hp if node['stat'] == 'hp' else self.game.attributes.current_mp
                lines.append('Current '+label+' remains '+str(current)+'.')
        elif node['kind'] == 'ability':lines.append('Learn '+self.board.abilities[node['ability_id']]['name']+'.')
        for crystal, amount in node['cost'].items():
            lines.append(self.board.crystals[crystal]['name']+' ×'+str(amount)+
                         ' ('+str(self.game.inventory.quantity(crystal))+' owned).')
        lines.append('This node can activate once for '+self.game.attributes.name+'.')
        return lines

    def _confirmation_layout(self, painter):
        lines = []
        for text in self.confirmation_text():lines.extend(painter.wrap(text, self.confirm_view.width, role='small'))
        height = painter.font('small').get_linesize()+3
        self.confirm_max_scroll = max(0, len(lines)*height-self.confirm_view.height)
        self.confirm_scroll = max(0, min(self.confirm_scroll, self.confirm_max_scroll))
        return lines, height

    def _layout(self, painter):
        heading_height = painter.font('heading', bold=True).get_linesize()
        small_height = painter.font('small').get_linesize()
        top = 16+heading_height+5+small_height*2+10
        self.map_rect = pygame.Rect(16, top, 274, 304-top)
        self.detail_view = pygame.Rect(307, top+8, 147, max(35, 242-top))
        self.detail_track = pygame.Rect(458, self.detail_view.top, 4, self.detail_view.height)
        self.zoom_out_rect = pygame.Rect(24, self.map_rect.bottom-29, 24, 22)
        self.zoom_in_rect = pygame.Rect(52, self.map_rect.bottom-29, 24, 22)
        self.fit_rect = pygame.Rect(80, self.map_rect.bottom-29, 32, 22)
        wrapped = []
        for text in self.detail_text():
            wrapped.extend(painter.wrap(text, self.detail_view.width, role='small'))
            wrapped.append('')
        line_height = painter.font('small').get_linesize()+2
        self.detail_max_scroll = max(0, len(wrapped)*line_height-self.detail_view.height)
        self.detail_scroll = max(0, min(self.detail_scroll, self.detail_max_scroll))
        self.detail_thumb = None
        if self.detail_max_scroll:
            height = max(14, round(self.detail_track.height*self.detail_view.height/
                                   (self.detail_max_scroll+self.detail_view.height)))
            offset = round((self.detail_track.height-height)*self.detail_scroll/self.detail_max_scroll)
            self.detail_thumb = pygame.Rect(self.detail_track.left, self.detail_track.top+offset,
                                           self.detail_track.width, height)
        return wrapped, line_height, heading_height, small_height

    def _scroll(self, amount):
        self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll+amount))

    def _help_lines(self, painter):
        text = ('Select a node with the arrow keys, Tab or a click. Selection never spends Steps or crystals.\n'
                'M prepares travel. A prepares activation. Press Enter or click the same action again to confirm. '
                'Esc cancels a prepared action, then returns to Pause.\n'
                'Drag the map to pan. Use the wheel, + or - to zoom. F fits the entire lattice.\n'
                'Page Up / Page Down scroll node details. Home / End reach their beginning or end. '
                'The detail scrollbar can also be dragged.\n'
                'Each connection costs one Step, including return travel and blank nodes. '
                'Activation uses the crystals listed for your current node. Rank is never spent.')
        lines = painter.wrap(text, self.help_view.width, role='small')
        height = painter.font('small').get_linesize()+2
        self.help_max_scroll = max(0, len(lines)*height-self.help_view.height)
        self.help_scroll = max(0, min(self.help_scroll, self.help_max_scroll))
        return lines, height

    def handle_event(self, event):
        if not self.is_open:return False
        painter = self._painter()
        self._layout(painter)
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.pointer = point
        if self.help_open:
            self._help_lines(painter)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):self.help_open = False
                elif event.key in (pygame.K_PAGEDOWN, pygame.K_DOWN):self.help_scroll = min(self.help_max_scroll, self.help_scroll+64)
                elif event.key in (pygame.K_PAGEUP, pygame.K_UP):self.help_scroll = max(0, self.help_scroll-64)
            elif event.type == pygame.MOUSEWHEEL:self.help_scroll = max(0, min(self.help_max_scroll, self.help_scroll-event.y*24))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and point is not None and self.help_close_rect.collidepoint(point):self.help_open = False
            return True
        if self.pending is not None:
            self._confirmation_layout(painter)
            if event.type == pygame.MOUSEMOTION:
                self.hovered = None
                return True
            if event.type == pygame.MOUSEWHEEL:
                self.confirm_scroll = max(0, min(self.confirm_max_scroll, self.confirm_scroll-event.y*24))
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and point is not None:
                if self.confirm_rect.collidepoint(point):self._commit();return True
                if self.cancel_rect.collidepoint(point):self.pending = None;self.message = '';return True
                if self.confirm_panel.collidepoint(point):return True
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END):
                if event.key == pygame.K_PAGEUP:self.confirm_scroll = max(0, self.confirm_scroll-self.confirm_view.height)
                elif event.key == pygame.K_PAGEDOWN:self.confirm_scroll = min(self.confirm_max_scroll, self.confirm_scroll+self.confirm_view.height)
                elif event.key == pygame.K_HOME:self.confirm_scroll = 0
                else:self.confirm_scroll = self.confirm_max_scroll
                return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and not getattr(event, 'repeat', False):
                if self.pending is not None:self.pending = None;self.message = ''
                else:self.close()
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                self._direction({pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}[event.key])
            elif event.key == pygame.K_TAB:
                ids = tuple(self.board.nodes)
                backwards = bool(getattr(event, 'mod', 0)&pygame.KMOD_SHIFT)
                self._select(ids[(ids.index(self.selected)+(-1 if backwards else 1)) % len(ids)], center=True)
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):self._zoom(1.2)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):self._zoom(1/1.2)
            elif event.key == pygame.K_f:self.fit_board()
            elif event.key == pygame.K_m and not getattr(event, 'repeat', False):self._action('move')
            elif event.key == pygame.K_a and not getattr(event, 'repeat', False):self._action('activate')
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and not getattr(event, 'repeat', False):self._commit()
            elif event.key == pygame.K_PAGEUP:self._scroll(-self.detail_view.height)
            elif event.key == pygame.K_PAGEDOWN:self._scroll(self.detail_view.height)
            elif event.key == pygame.K_HOME:self.detail_scroll = 0
            elif event.key == pygame.K_END:self.detail_scroll = self.detail_max_scroll
            elif event.key in (pygame.K_F1, pygame.K_QUESTION):self.help_open = True
        elif event.type == pygame.MOUSEWHEEL:
            pointer = self.pointer
            if pointer is None:pointer = self.game.to_canvas(pygame.mouse.get_pos())
            if pointer is not None and self.map_rect.collidepoint(pointer):self._zoom(1.2**event.y)
            else:self._scroll(-event.y*24)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            if point is None:return True
            if self.close_rect.collidepoint(point):self.close()
            elif self.help_rect.collidepoint(point):self.help_open = True
            elif self.move_rect.collidepoint(point):self._action('move')
            elif self.activate_rect.collidepoint(point):self._action('activate')
            elif self.zoom_out_rect.collidepoint(point):self._zoom(1/1.2)
            elif self.zoom_in_rect.collidepoint(point):self._zoom(1.2)
            elif self.fit_rect.collidepoint(point):self.fit_board()
            elif self.detail_thumb is not None and self.detail_track.inflate(10, 0).collidepoint(point):
                self.drag_detail = True
            elif self.map_rect.collidepoint(point):
                node = self._node_at(point)
                if node is not None:self._select(node)
                self.dragging = True
                self.drag_origin = pygame.Vector2(point)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = self.dragging = self.drag_detail = False
        elif event.type == pygame.MOUSEMOTION:
            self.hovered = self._node_at(point)
            if self.dragging and point is not None and self.drag_origin is not None:
                delta = pygame.Vector2(point)-self.drag_origin
                self.pan -= delta/self.zoom
                self.drag_origin = pygame.Vector2(point)
            elif self.drag_detail and point is not None and self.detail_thumb is not None:
                travel = self.detail_track.height-self.detail_thumb.height
                fraction = (point[1]-self.detail_track.top-self.detail_thumb.height/2)/max(1, travel)
                self.detail_scroll = round(max(0, min(1, fraction))*self.detail_max_scroll)
        elif event.type in (pygame.WINDOWLEAVE, pygame.WINDOWFOCUSLOST):
            self.hovered = None
            self.pointer = None
            self._held = self.dragging = self.drag_detail = False
        return True

    def _circle(self, painter, color, center, radius, width=0):
        pygame.draw.circle(painter.canvas, color, painter.point(center), max(1, round(radius*painter.scale)),
                           max(1, round(width*painter.scale)) if width else 0)

    def _draw_map(self, painter):
        painter.panel(self.map_rect)
        painter.clip(self.map_rect.inflate(-3, -3))
        state = self.lattice.state(self.character_id)
        rank = self.lattice.rank(self.character_id)
        route = self.lattice.route(self.selected, self.character_id) or []
        pairs = {frozenset((a, b)) for a, b in zip(route, route[1:])}
        for edge in self.board.edges:
            a, b = self.node_position(edge['from']), self.node_position(edge['to'])
            required = edge.get('min_rank', 1)
            color = GOLD if frozenset((edge['from'], edge['to'])) in pairs else BRASS
            if rank < required:
                color = DISABLED
                delta = b-a
                pieces = max(2, int(delta.length()/8))
                for index in range(0, pieces, 2):
                    painter.line(color, a+delta*index/pieces, a+delta*min(pieces, index+1)/pieces)
                middle = (a+b)/2
                if self.map_rect.inflate(-30, -30).collidepoint(middle):
                    painter.text('Rank '+str(required), middle+(0, -13), role='small', color=MUTED, anchor='midbottom')
            else:painter.line(color, a, b, 2 if color == GOLD else 1)
        for identifier, node in self.board.nodes.items():
            center = self.node_position(identifier)
            radius = max(4, round(10*self.zoom))
            if not self.map_rect.inflate(radius*2, radius*2).collidepoint(center):continue
            crystal = next(iter(node['cost']), None)
            color = self.board.crystals[crystal]['color'] if crystal else BRASS
            active = identifier in state['activated']
            self._circle(painter, color if active else FOREST_DARK, center, radius)
            self._circle(painter, IVORY if identifier in state['visited'] else color, center, radius, 1)
            if self.zoom >= .65 and node['kind'] == 'stat':
                icon = pygame.Rect(0, 0, max(9, radius*1.3), max(9, radius*1.3));icon.center = center
                draw_attribute_icon(painter, node['stat'], icon, FOREST_DARK if active else color)
            elif node['kind'] == 'ability':
                painter.lantern(center, color=FOREST_DARK if active else color, size=max(5, radius))
            if identifier == state['position']:
                self._circle(painter, GOLD, center, radius+4, 2)
                painter.line(GOLD, center+(0, -radius-9), center+(0, -radius-5), 2)
            if identifier == self.selected:
                box = pygame.Rect(0, 0, radius*2+14, radius*2+14);box.center = center
                painter.rect(IVORY, box, 1)
            elif identifier == self.hovered:self._circle(painter, IVORY, center, radius+3, 1)
        painter.clip()
        for rect, label in ((self.zoom_out_rect, '−'), (self.zoom_in_rect, '+'), (self.fit_rect, 'F')):
            painter.button(rect, label)
        painter.text('Drag: pan', (self.fit_rect.right+8, self.fit_rect.centery), role='small', color=MUTED, anchor='midleft')
        if self.hovered:
            text = self.board.nodes[self.hovered].get('name', self.hovered)
            lines = painter.wrap(text, self.map_rect.width-16, role='small')
            height = len(lines)*painter.font('small').get_linesize()+10
            painter.panel((self.map_rect.left+5, self.map_rect.top+5, self.map_rect.width-10, height))
            for index, line in enumerate(lines):
                painter.text(line, (self.map_rect.left+10, self.map_rect.top+10+index*painter.font('small').get_linesize()), role='small', color=GOLD)

    def draw(self, canvas):
        if not self.is_open:return
        painter = self._painter(canvas)
        lines, line_height, heading_height, small_height = self._layout(painter)
        painter.veil(215)
        painter.panel((8, 8, 464, 304))
        painter.text('Aether Lattice', (20, 16), role='heading', color=GOLD, bold=True)
        rank = self.lattice.rank(self.character_id)
        progress, needed = self.lattice.rp_progress(self.character_id)
        y = 16+heading_height+5
        painter.text(self.game.attributes.name+' · Attunement '+str(rank), (20, y), role='small')
        painter.text('RP '+str(progress)+' / '+str(needed)+' · '+self._steps_label(self.lattice.steps(self.character_id)),
                     (20, y+small_height), role='small', color=GOLD)
        painter.button(self.help_rect, '?')
        painter.button(self.close_rect, '×')
        self._draw_map(painter)
        painter.panel((300, self.map_rect.top, 164, 246-self.map_rect.top))
        painter.clip(self.detail_view)
        for index, line in enumerate(lines):
            painter.text(line, (self.detail_view.left, self.detail_view.top+index*line_height-self.detail_scroll),
                         role='small', color=IVORY)
        painter.clip()
        if self.detail_thumb is not None:
            painter.rect(FOREST_DARK, self.detail_track)
            painter.rect(BRASS, self.detail_thumb)
        move_pending = self.pending == ('move', self.selected)
        activation_pending = self.pending == ('activate', self.selected)
        painter.button(self.move_rect, 'Confirm Move' if move_pending else 'M: Move', disabled=bool(self._move_reason()))
        painter.button(self.activate_rect, 'Confirm Activate' if activation_pending else 'A: Activate', disabled=bool(self._activation_reason()))
        if self.pending is not None:
            painter.veil(80)
            painter.panel(self.confirm_panel)
            painter.text('Confirm travel' if move_pending else 'Confirm activation',
                         (42, 67), color=GOLD, bold=True)
            confirm_lines, height = self._confirmation_layout(painter)
            painter.clip(self.confirm_view)
            for index, line in enumerate(confirm_lines):
                painter.text(line, (self.confirm_view.left, self.confirm_view.top+index*height-self.confirm_scroll), role='small')
            painter.clip()
            if self.confirm_max_scroll:
                painter.text('PgUp / PgDn: read', (42, 226), role='small', color=MUTED, anchor='midleft')
            else:painter.text('Enter confirms', (42, 226), role='small', color=MUTED, anchor='midleft')
            painter.button(self.confirm_rect, 'Confirm')
            painter.button(self.cancel_rect, 'Cancel')
        if self.help_open:
            painter.veil(100)
            painter.panel(self.help_panel)
            painter.text('Lattice controls', (46, 50), color=GOLD, bold=True)
            painter.button(self.help_close_rect, '×')
            help_lines, height = self._help_lines(painter)
            painter.clip(self.help_view)
            for index, line in enumerate(help_lines):
                painter.text(line, (self.help_view.left, self.help_view.top+index*height-self.help_scroll), role='small')
            painter.clip()
