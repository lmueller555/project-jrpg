"""Full-width Aether Lattice exploration and explicit purchases."""
import math
import pygame

from attribute_icons import draw_attribute_icon
from ui_style import FOREST_DARK, IVORY, GOLD, BRASS, MUTED, DISABLED


class LatticeUI:
    MIN_ZOOM = .05
    MAX_ZOOM = 2.0
    CAMERA_DURATION = .18
    ZOOM_DURATION = .18
    CURSOR_SPEED = 180.0
    PULSE_PERIOD = 1.2
    DIRECTIONS = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
                  pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}

    @staticmethod
    def _steps_label(amount):return str(amount)+' Step'+('' if amount == 1 else 's')

    def __init__(self, game):
        self.game = game
        self.character_id = getattr(game.attributes, 'character_id', 'caelan')
        self.close_rect = pygame.Rect(438, 14, 24, 24)
        self.help_rect = pygame.Rect(410, 14, 22, 24)
        self.map_rect = pygame.Rect(16, 78, 448, 226)
        self.help_panel = pygame.Rect(32, 40, 416, 248)
        self.help_view = pygame.Rect(46, 80, 386, 188)
        self.help_close_rect = pygame.Rect(410, 47, 24, 24)
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
        self.target_zoom = self.zoom
        self._zoom_start = self.zoom
        self._zoom_elapsed = self.ZOOM_DURATION
        self._zoom_anchor = None
        self.pan = pygame.Vector2(0, 0)
        self.cursor_position = pygame.Vector2(0, 0)
        self._keys = set()
        self._camera_start = self.pan.copy()
        self._camera_target = self.pan.copy()
        self._camera_elapsed = self.CAMERA_DURATION
        self._pulse_elapsed = 0.0
        self._drag_moved = False
        self._drag_start = None
        self._drag_pan = None
        self._click_node = None
        self.context_rect = self.action_rect = None
        self._displayed_offer = None
        self._displayed_context_rect = self._displayed_action_rect = None
        self.message = ''
        self._held = False
        self.dragging = False
        self.help_open = False
        self.help_scroll = 0
        self.help_max_scroll = 0

    def open(self):
        self.is_open = True
        self.message = ''
        self.hovered = None
        self.pointer = None
        self.help_open = False
        self._held = self.dragging = False
        self._keys.clear()
        self._pulse_elapsed = 0.0
        self._hide_context()
        self._select(self.lattice.state(self.character_id)['position'], center=True)
        self.center_on(self.selected, immediate=True)
        self.game.ui.sound('confirm')

    def close(self):
        self.is_open = False
        self.hovered = None
        self.pointer = None
        self.help_open = False
        self._held = self.dragging = False
        self._keys.clear()
        self._cancel_zoom()
        self._hide_context()
        self.game.ui.sound('back')

    def _select(self, identifier, center=False):
        if identifier not in self.board.nodes:return
        self._zoom_anchor = None
        self.cursor_position.update(self.board.nodes[identifier]['position'])
        self._pulse_elapsed = 0.0
        self._hide_context()
        if identifier != self.selected:
            self.selected = identifier
            self.message = ''
            self.game.ui.sound('move')
        if center:self.center_on(identifier)

    @property
    def navigating(self):return bool(self._keys) or self.dragging

    @property
    def pulse_strength(self):
        if getattr(self.game.audio, 'reduced_motion', False):return 1.0
        return .5+.5*math.cos(self._pulse_elapsed*math.tau/self.PULSE_PERIOD)

    def _camera_to(self, position, immediate=False):
        self._zoom_anchor = None
        target = pygame.Vector2(position)
        if immediate or getattr(self.game.audio, 'reduced_motion', False):
            self.pan.update(target)
            self._camera_elapsed = self.CAMERA_DURATION
        else:
            self._camera_start = self.pan.copy()
            self._camera_elapsed = 0.0
        self._camera_target = target

    def center_on(self, identifier, immediate=False):
        if identifier in self.board.nodes:
            self._camera_to(self.board.nodes[identifier]['position'], immediate)

    def _nearest_node(self, position):
        point = pygame.Vector2(position)
        return min(self.board.nodes, key=lambda identifier:
                   (point.distance_squared_to(self.board.nodes[identifier]['position']), identifier))

    def _clamp_cursor(self):
        points = [node['position'] for node in self.board.nodes.values()]
        padding = 48
        self.cursor_position.x = max(min(p[0] for p in points)-padding,
                                     min(max(p[0] for p in points)+padding, self.cursor_position.x))
        self.cursor_position.y = max(min(p[1] for p in points)-padding,
                                     min(max(p[1] for p in points)+padding, self.cursor_position.y))

    def _settle_cursor(self):
        self._select(self._nearest_node(self.cursor_position), center=True)

    def _stop_navigation(self, settle=True):
        was_navigating = self.navigating
        self._keys.clear()
        self.dragging = False
        self._drag_pan = self._drag_start = self._click_node = None
        self._drag_moved = False
        if settle and was_navigating:self._settle_cursor()

    def _drag_to(self, point):
        """Keep the grabbed map point under the pointer, without camera lag."""
        if not self.dragging or point is None:return
        delta = pygame.Vector2(point)-self._drag_start
        if not self._drag_moved and delta.length_squared() < 9:return
        self._drag_moved = True
        self.pan.update(self._drag_pan-delta/self.zoom)
        self.cursor_position.update(self.pan)
        self._camera_target = self.pan.copy()
        self._camera_elapsed = self.CAMERA_DURATION

    def update(self, dt):
        """Advance exploration and selection feedback while the world is paused."""
        if not self.is_open:return
        dt = max(0.0, min(float(dt), .25))
        if self.help_open:
            self._stop_navigation()
        if self._zoom_elapsed < self.ZOOM_DURATION:
            self._zoom_elapsed = min(self.ZOOM_DURATION, self._zoom_elapsed+dt)
            t = self._zoom_elapsed/self.ZOOM_DURATION
            eased = 1-(1-t)**3
            self.zoom = (self.target_zoom if self._zoom_elapsed >= self.ZOOM_DURATION
                         or getattr(self.game.audio, 'reduced_motion', False)
                         else self._zoom_start+(self.target_zoom-self._zoom_start)*eased)
        if self._keys and not self.dragging:
            direction = sum((pygame.Vector2(self.DIRECTIONS[key]) for key in self._keys), pygame.Vector2())
            if direction.length_squared():
                direction.normalize_ip()
                self.cursor_position += direction*self.CURSOR_SPEED*dt/self.zoom
                self._clamp_cursor()
        if self.navigating:
            self._zoom_anchor = None
            # Drag events position the camera directly; keyboard exploration follows.
            if not self.dragging:
                if getattr(self.game.audio, 'reduced_motion', False):self.pan.update(self.cursor_position)
                else:self.pan += (self.cursor_position-self.pan)*(1-math.exp(-24*dt))
            self._camera_target = self.pan.copy()
            self._camera_elapsed = self.CAMERA_DURATION
        elif self._zoom_anchor is not None:
            world, offset = self._zoom_anchor
            self.pan.update(world-offset/self.zoom)
            if self._zoom_elapsed >= self.ZOOM_DURATION:self._zoom_anchor = None
        elif self._camera_elapsed < self.CAMERA_DURATION:
            if getattr(self.game.audio, 'reduced_motion', False):
                self._camera_to(self._camera_target, immediate=True)
            self._camera_elapsed = min(self.CAMERA_DURATION, self._camera_elapsed+dt)
            t = self._camera_elapsed/self.CAMERA_DURATION
            eased = 1-(1-t)**3
            self.pan.update(self._camera_start.lerp(self._camera_target, eased))
        if not self.navigating:self._pulse_elapsed = (self._pulse_elapsed+dt) % self.PULSE_PERIOD

    def node_position(self, identifier):
        return self._map_position(self.board.nodes[identifier]['position'])

    def _map_position(self, position):
        return pygame.Vector2(self.map_rect.center)+(pygame.Vector2(position)-self.pan)*self.zoom

    def edge_points(self, edge):
        """Sample an authored curve; an ordinary connection stays one straight line."""
        start, end = (pygame.Vector2(self.board.nodes[edge[key]]['position'])
                      for key in ('from', 'to'))
        if 'curve' not in edge:return [self._map_position(start), self._map_position(end)]
        control = pygame.Vector2(edge['curve'])
        length = (start.distance_to(control)+control.distance_to(end))*self.zoom
        segments = max(3, min(64, math.ceil(length/7)))
        return [self._map_position(start*(1-t)**2+control*(2*(1-t)*t)+end*t*t)
                for t in (index/segments for index in range(segments+1))]

    def _edge_midpoint(self, edge):
        start, end = (pygame.Vector2(self.board.nodes[edge[key]]['position'])
                      for key in ('from', 'to'))
        point = ((start+end)/2 if 'curve' not in edge else
                 start*.25+pygame.Vector2(edge['curve'])*.5+end*.25)
        return self._map_position(point)

    @staticmethod
    def _draw_path(painter, color, points, width=1, dashed=False):
        if not dashed:
            pygame.draw.lines(painter.canvas, color, False,
                              [painter.point(point) for point in points],
                              max(1, round(width*painter.scale)))
            return
        # Keep dash lengths continuous across the sampled curve's segments.
        drawing, remaining = True, 5.0
        for start, end in zip(points, points[1:]):
            delta = end-start
            length = delta.length()
            if not length:continue
            direction = delta/length
            cursor = start.copy()
            while length > 1e-7:
                step = min(length, remaining)
                target = cursor+direction*step
                if drawing:painter.line(color, cursor, target, width)
                cursor = target
                length -= step
                remaining -= step
                if remaining <= 1e-7:
                    drawing = not drawing
                    remaining = 5.0 if drawing else 4.0

    def fit_board(self):
        """Position an isolated preview fixture; no player control binds this helper."""
        points = [pygame.Vector2(node['position']) for node in self.board.nodes.values()]
        points.extend(pygame.Vector2(edge['curve']) for edge in self.board.edges if 'curve' in edge)
        left, right = min(p.x for p in points), max(p.x for p in points)
        top, bottom = min(p.y for p in points), max(p.y for p in points)
        self._stop_navigation(settle=False)
        target = min((self.map_rect.width-44)/max(1, right-left),
                     (self.map_rect.height-74)/max(1, bottom-top))
        self._zoom_to(target, focus=((left+right)/2, (top+bottom)/2))

    def reset_zoom(self):
        """Set up a preview close-up; player zoom uses the mouse wheel only."""
        self._stop_navigation()
        self._zoom_to(1.0, focus=self.board.nodes[self.selected]['position'])

    def _cancel_zoom(self):
        self.target_zoom = self._zoom_start = self.zoom
        self._zoom_elapsed = self.ZOOM_DURATION
        self._zoom_anchor = None

    def _zoom_to(self, amount, focus=None, anchor=None):
        """Retarget from the rendered view, preserving a wheel's world anchor."""
        self.target_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, amount))
        self._zoom_start = self.zoom
        self._zoom_elapsed = 0.0
        if anchor is not None and not self.navigating:
            offset = pygame.Vector2(anchor)-pygame.Vector2(self.map_rect.center)
            self._zoom_anchor = (self.pan+offset/self.zoom, offset)
            self._camera_elapsed = self.CAMERA_DURATION
        else:
            self._zoom_anchor = None
            if focus is not None:self._camera_to(focus)
        if getattr(self.game.audio, 'reduced_motion', False):
            self.zoom = self.target_zoom
            self._zoom_elapsed = self.ZOOM_DURATION
            if self._zoom_anchor is not None:
                world, offset = self._zoom_anchor
                self.pan.update(world-offset/self.zoom)
                self._zoom_anchor = None

    def _zoom(self, factor, anchor=None):
        if self.dragging:return
        target = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.target_zoom*factor))
        if math.isclose(target, self.target_zoom):return
        focus = self.cursor_position if self.navigating else self.board.nodes[self.selected]['position']
        self._zoom_to(target, focus=focus, anchor=anchor)

    def _node_at(self, point):
        if point is None or not self.map_rect.collidepoint(point):return None
        nodes = [(self.node_position(identifier).distance_squared_to(point), identifier)
                 for identifier in self.board.nodes]
        distance, identifier = min(nodes)
        radius = max(5, self._node_radius(identifier, self.board.nodes[identifier])+3)
        return identifier if distance <= radius*radius else None

    def _move_reason(self):
        return self.game.lattice_move_reason(self.selected)

    def _activation_reason(self):
        return self.game.lattice_activation_reason(self.selected)

    def _hide_context(self):
        self.context_rect = self.action_rect = None
        self._displayed_offer = None
        self._displayed_context_rect = self._displayed_action_rect = None

    def action_preview(self):
        """Describe an affordable command without changing progression or selection."""
        if not self.is_open or self.help_open or self.navigating:return None
        if self.selected not in self.board.nodes:return None
        identifier = self.selected
        node = self.board.nodes[identifier]
        if not self._move_reason():
            route = self.lattice.route(identifier, self.character_id)
            return {'action': 'move', 'node': identifier, 'button': 'Move',
                    'lines': [node.get('name', identifier),
                              'Travel: '+self._steps_label(len(route)-1),
                              self._steps_label(self.lattice.steps(self.character_id))+' available']}
        if self._activation_reason():return None
        lines = []
        if node['kind'] == 'stat':
            label = self.game.attributes.definitions[node['stat']]['label']
            value = self.game.attributes.value(node['stat'])
            lines.append(label+': '+str(value)+' → '+str(value+node['amount']))
            if node['stat'] in ('hp', 'mp'):
                current = (self.game.attributes.current_hp if node['stat'] == 'hp'
                           else self.game.attributes.current_mp)
                lines.append('Current '+label+' stays '+str(current)+'.')
        elif node['kind'] == 'ability':
            lines.append('Learn '+self.board.abilities[node['ability_id']]['name']+'.')
        for crystal, amount in node['cost'].items():
            lines.append(self.board.crystals[crystal]['name']+' ×'+str(amount))
        return {'action': 'activate', 'node': identifier, 'button': 'Activate', 'lines': lines}

    def _execute_offer(self, offer):
        # Both the visible offer and the model must still allow this exact command.
        if offer != self.action_preview():return False
        identifier = offer['node']
        success = (self.game.move_lattice(identifier) if offer['action'] == 'move'
                   else self.game.activate_lattice(identifier))
        self._hide_context()
        if success:
            self.message = 'Travel complete.' if offer['action'] == 'move' else 'Node activated.'
            if offer['action'] == 'move':self.center_on(identifier)
            self.game.ui.sound('confirm')
        else:self.game.ui.sound('back')
        return success

    def _context_layout(self, painter):
        """Place a compact offer beside the selected node, inside the map."""
        self.context_rect = self.action_rect = None
        offer = self.action_preview()
        if offer is None:return [], 0
        center = self.node_position(offer['node'])
        bounds = self.map_rect.inflate(-16, -16)
        if not bounds.collidepoint(center):return [], 0
        radius = self._node_radius(offer['node'], self.board.nodes[offer['node']])
        gap = math.ceil(radius+12)
        right_space = bounds.right-center.x-gap
        left_space = center.x-gap-bounds.left
        side = 1 if right_space >= left_space else -1
        available = max(right_space, left_space)
        width = min(208, int(available))
        if width < 112:return [], 0
        lines = []
        for line in offer['lines']:lines.extend(painter.wrap(line, width-18, role='small'))
        line_height = painter.font('small').get_linesize()+2
        button_height = painter.font(bold=True).get_linesize()+8
        height = len(lines)*line_height+button_height+26
        if height > bounds.height:
            # A wide card can fit more demanding text without clipping its cost.
            width = min(bounds.width, max(width, 280))
            lines = []
            for line in offer['lines']:lines.extend(painter.wrap(line, width-18, role='small'))
            height = len(lines)*line_height+button_height+26
            # Prefer above/below when the wider card would cross the selected node.
            candidates = [pygame.Rect(center.x-width/2, center.y-gap-height, width, height),
                          pygame.Rect(center.x-width/2, center.y+gap, width, height)]
        else:
            x = center.x+gap if side > 0 else center.x-gap-width
            candidates = [pygame.Rect(x, center.y-height/2, width, height)]
        node_bounds = pygame.Rect(0, 0, gap*2, gap*2)
        node_bounds.center = center
        candidates = [rect.clamp(bounds) for rect in candidates]
        self.context_rect = min(candidates, key=lambda rect:
                                rect.clip(node_bounds).width*rect.clip(node_bounds).height)
        self.action_rect = pygame.Rect(self.context_rect.left+9,
                                       self.context_rect.bottom-button_height-9,
                                       self.context_rect.width-18, button_height)
        return lines, line_height

    def detail_text(self):
        if self.selected not in self.board.nodes:return []
        state = self.lattice.state(self.character_id)
        node = (self.lattice.reward_node(self.selected, self.character_id)
                if self.selected in state['activated'] else self.board.nodes[self.selected])
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
        if self.message:lines.insert(0, self.message)
        lines.append('Aether Crystals')
        for identifier, crystal in self.board.crystals.items():
            lines.append(crystal['name']+': '+str(self.game.inventory.quantity(identifier)))
        learned = self.lattice.learned_abilities(self.character_id)
        if learned:
            lines.append('Known abilities')
            lines.extend(self.board.abilities[identifier]['name'] for identifier in learned)
        return [line for line in lines if line]

    def _layout(self, painter):
        heading_height = painter.font('heading', bold=True).get_linesize()
        small_height = painter.font('small').get_linesize()
        top = 16+heading_height+5+small_height*2+10
        self.map_rect = pygame.Rect(16, top, 448, 304-top)
        return heading_height, small_height

    def _help_lines(self, painter):
        text = ('Click a node to select and center it. Hold the left mouse button and drag to pan. '
                'Release a drag to center the node nearest the gold cursor. '
                'Hold the arrow keys to browse with the gold cursor; release to select its nearest node.\n'
                'Use the mouse wheel over the map to zoom around the pointer. '
                'Exploring never spends Steps or crystals.\n'
                'A reachable node shows its travel cost and a Move button when you have enough Steps. '
                'Click Move to travel. Each connection costs one Step, including return travel and blank nodes.\n'
                'At your current node, an Activate button shows its bonus and crystal cost when you can afford it. '
                'Click Activate to spend those crystals and gain the bonus once. Rank is never spent.\n'
                'Escape or × returns to Pause. F1 or ? opens this help. '
                'Use the mouse wheel or Page Up / Page Down to read the help; Escape or × closes it.')
        lines = painter.wrap(text, self.help_view.width, role='small')
        height = painter.font('small').get_linesize()+2
        self.help_max_scroll = max(0, len(lines)*height-self.help_view.height)
        self.help_scroll = max(0, min(self.help_scroll, self.help_max_scroll))
        return lines, height

    def handle_event(self, event):
        if not self.is_open:return False
        painter = self._painter()
        self._layout(painter)
        self._context_layout(painter)
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.pointer = point
        # Release/focus events must clear input even when help owns the keyboard.
        if event.type == pygame.KEYUP and event.key in self.DIRECTIONS:
            held = event.key in self._keys
            self._keys.discard(event.key)
            if held and not self.navigating:self._settle_cursor()
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag_to(point)
            was_dragging, moved, clicked = self.dragging, self._drag_moved, self._click_node
            self._held = self.dragging = False
            self._drag_pan = self._drag_start = self._click_node = None
            self._drag_moved = False
            if was_dragging and not self._keys:
                if moved:self._settle_cursor()
                elif clicked is not None and self._node_at(point) == clicked:
                    self._select(clicked, center=True)
            return True
        if event.type in (pygame.WINDOWLEAVE, pygame.WINDOWFOCUSLOST):
            self.hovered = None
            self.pointer = None
            self._held = False
            self._stop_navigation()
            self._cancel_zoom()
            self._hide_context()
            return True
        if self.help_open:
            self._help_lines(painter)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:self.help_open = False
                elif event.key in (pygame.K_PAGEDOWN, pygame.K_DOWN):self.help_scroll = min(self.help_max_scroll, self.help_scroll+64)
                elif event.key in (pygame.K_PAGEUP, pygame.K_UP):self.help_scroll = max(0, self.help_scroll-64)
                elif event.key == pygame.K_HOME:self.help_scroll = 0
                elif event.key == pygame.K_END:self.help_scroll = self.help_max_scroll
            elif event.type == pygame.MOUSEWHEEL:self.help_scroll = max(0, min(self.help_max_scroll, self.help_scroll-event.y*24))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._held:return True
                self._held = True
                if point is not None and self.help_close_rect.collidepoint(point):self.help_open = False
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and not getattr(event, 'repeat', False):self.close()
            elif event.key in self.DIRECTIONS:
                if self.dragging:return True
                self._zoom_anchor = None
                self._keys.add(event.key)
                self.hovered = None
                self._hide_context()
            elif event.key in (pygame.K_F1, pygame.K_QUESTION):
                self._stop_navigation()
                self.help_open = True
                self._hide_context()
        elif event.type == pygame.MOUSEWHEEL:
            pointer = self.pointer
            if pointer is None:pointer = self.game.to_canvas(pygame.mouse.get_pos())
            if pointer is not None and self.map_rect.collidepoint(pointer):
                self._zoom(1.2**max(-10, min(10, event.y)), anchor=pointer)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            if point is None:return True
            if self.close_rect.collidepoint(point):self.close()
            elif self.help_rect.collidepoint(point):
                self._stop_navigation()
                self.help_open = True
                self._hide_context()
            elif self._displayed_action_rect is not None and self._displayed_action_rect.collidepoint(point):
                if self._displayed_offer == self.action_preview():
                    self._execute_offer(self._displayed_offer)
                else:self._hide_context()
            elif self._displayed_context_rect is not None and self._displayed_context_rect.collidepoint(point):
                # A preview is a readable card, never a click through to the map.
                pass
            elif self.map_rect.collidepoint(point):
                self._cancel_zoom()
                self._keys.clear()
                self._click_node = self._node_at(point)
                self.dragging = True
                self._drag_start = pygame.Vector2(point)
                self._drag_pan = self.pan.copy()
                self._camera_target = self.pan.copy()
                self._camera_elapsed = self.CAMERA_DURATION
                self._drag_moved = False
                self.cursor_position.update(self.pan)
                self._hide_context()
        elif event.type == pygame.MOUSEMOTION:
            self.hovered = self._node_at(point)
            if self.dragging and point is not None:
                self._drag_to(point)
                self.hovered = None
            elif self.dragging and point is None:self._stop_navigation()
        return True

    def _circle(self, painter, color, center, radius, width=0):
        pygame.draw.circle(painter.canvas, color, painter.point(center), max(1, round(radius*painter.scale)),
                           max(1, round(width*painter.scale)) if width else 0)

    def _node_radius(self, identifier, node):
        radius = max(1.5, 10*self.zoom)
        formation_id = getattr(self.board, 'node_formations', {}).get(identifier)
        formation = getattr(self.board, 'formations', {}).get(formation_id)
        if formation and formation['center_node'] == identifier:
            baseline = {'hp': 100, 'mp': 5}.get(node.get('stat'), 1)
            if node['kind'] == 'ability' or (node['kind'] == 'stat' and node['amount'] > baseline):
                radius *= 1.25
        return radius

    def _draw_map(self, painter):
        painter.panel(self.map_rect)
        painter.clip(self.map_rect.inflate(-3, -3))
        state = self.lattice.state(self.character_id)
        rank = self.lattice.rank(self.character_id)
        offer = self.action_preview()
        route = (self.lattice.route(self.selected, self.character_id) or []
                 if offer is not None and offer['action'] == 'move' else [])
        pairs = {frozenset((a, b)) for a, b in zip(route, route[1:])}
        for edge in self.board.edges:
            points = self.edge_points(edge)
            required = edge.get('min_rank', 1)
            color = GOLD if frozenset((edge['from'], edge['to'])) in pairs else BRASS
            if rank < required:
                color = DISABLED
                self._draw_path(painter, color, points, dashed=True)
                middle = self._edge_midpoint(edge)
                if self.zoom >= .35 and self.map_rect.inflate(-30, -30).collidepoint(middle):
                    painter.text('Rank '+str(required), middle+(0, -13), role='small', color=MUTED, anchor='midbottom')
            else:self._draw_path(painter, color, points, 2 if color == GOLD else 1)
        for identifier, node in self.board.nodes.items():
            if identifier in state['activated']:
                node = self.lattice.reward_node(identifier, self.character_id)
            center = self.node_position(identifier)
            radius = self._node_radius(identifier, node)
            if not self.map_rect.inflate(radius*2, radius*2).collidepoint(center):continue
            crystal = next(iter(node['cost']), None)
            color = self.board.crystals[crystal]['color'] if crystal else BRASS
            active = identifier in state['activated']
            selected = identifier == self.selected and not self.navigating
            fill = pygame.Color(color if active else FOREST_DARK)
            if selected:
                strength = self.pulse_strength
                glow = pygame.Color(FOREST_DARK).lerp(pygame.Color(GOLD), .35+.5*strength)
                halo = max(1.25, 5*self.zoom)+strength*max(.5, 2*self.zoom)
                self._circle(painter, glow, center, radius+halo, max(.7, 2*self.zoom))
                fill = fill.lerp(pygame.Color(GOLD), .12+.18*strength)
            self._circle(painter, fill, center, radius)
            self._circle(painter, IVORY if identifier in state['visited'] else color, center, radius, 1)
            if self.zoom >= .65 and node['kind'] == 'stat':
                icon = pygame.Rect(0, 0, max(9, radius*1.3), max(9, radius*1.3));icon.center = center
                draw_attribute_icon(painter, node['stat'], icon, FOREST_DARK if active else color)
            elif self.zoom >= .4 and node['kind'] == 'ability':
                painter.lantern(center, color=FOREST_DARK if active else color, size=radius*.8)
            if identifier == state['position']:
                gap = max(1.0, 4*self.zoom)
                self._circle(painter, GOLD, center, radius+gap, max(.7, 2*self.zoom))
                painter.line(GOLD, center+(0, -radius-gap-max(1, 5*self.zoom)),
                             center+(0, -radius-gap-max(.5, self.zoom)), max(.7, 2*self.zoom))
            if not selected and identifier == self.hovered:
                self._circle(painter, IVORY, center, radius+max(1.0, 3*self.zoom), 1)
        if self.navigating:
            center = pygame.Vector2(self.map_rect.center)+(self.cursor_position-self.pan)*self.zoom
            radius = max(1.5, 10*self.zoom)
            self._circle(painter, FOREST_DARK, center, radius+max(1, 2*self.zoom))
            self._circle(painter, GOLD, center, radius)
        painter.clip()

    def _draw_context(self, painter):
        lines, line_height = self._context_layout(painter)
        offer = self.action_preview()
        self._displayed_offer = None
        self._displayed_context_rect = self._displayed_action_rect = None
        if self.context_rect is None or offer is None:return
        painter.panel(self.context_rect)
        for index, line in enumerate(lines):
            painter.text(line, (self.context_rect.left+9,
                                self.context_rect.top+8+index*line_height),
                         role='small', color=GOLD if index == 0 else IVORY)
        painter.button(self.action_rect, offer['button'])
        self._displayed_offer = offer
        self._displayed_context_rect = self.context_rect.copy()
        self._displayed_action_rect = self.action_rect.copy()

    def draw(self, canvas):
        if not self.is_open:return
        painter = self._painter(canvas)
        heading_height, small_height = self._layout(painter)
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
        self._draw_context(painter)
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
