""" The web app's map renderer: the engine's `Renderer` with order arrows that are easier to read.

    The engine aims every arrow at the *unit slot* of the target province (an offset coordinate next to the
    province's name) and draws it with a heavy black shadow; support and convoy lines differ only in the length of
    their dashes. `WebRenderer` keeps the engine's drawing of everything else and redraws the four arrow kinds
    (move, support, support to hold, convoy):

    - a move, a support of a move and a convoyed move end at the centre of the target province, taken from the
      position of its name in the SVG's ``BriefLabelLayer`` (text-anchor middle, placed by hand near the middle of
      the province); the arrow stops `Style.stop` short of it so the head does not sit on the name. A province
      without a name keeps the engine's unit position. Support to hold still points at the unit it supports.
    - lines have a thin light outline instead of the shadow, supports are dotted and convoys long dashed, and the
      arrow heads are bigger and coloured like the line (markers added to the output's ``<defs>``).

    Nothing of the engine or of the SVG files is changed: styles are inline attributes. `renderer_for(game)` and
    `render(game)` give a renderer per game from one cached per map (loading and parsing the SVG once).
"""
import copy
import functools
import logging
import re
from collections import namedtuple
from xml.dom import minidom

from diplomacy import Game
from diplomacy.engine.renderer import Renderer, ARMY, _attr
from diplomacy.utils.equilateral_triangle import EquilateralTriangle

LOGGER = logging.getLogger(__name__)

# `classic` draws with the engine's own classes and black arrow heads (the baseline for comparisons).
Style = namedtuple('Style', 'classic anchor stop start min_visible outline outline_extra width head dash_support '
                         'dash_convoy halo')
STYLE = Style(classic=False, anchor='label', stop=6, start=22, min_visible=30, outline='#ffffff', outline_extra=5, width=6, head=26,
              dash_support='2,9', dash_convoy='20,9', halo=True)
LABEL_RAISE = {'labeltext18': 5, 'labeltext24': 7}      # the label's baseline is below its visual middle
HALO = 'stroke="#ffffff" stroke-width="3.5" stroke-opacity="0.85" stroke-linejoin="round" paint-order="stroke"'


class WebRenderer(Renderer):
    """ See the module's docstring. `style` is a `Style`. """

    def __init__(self, game, svg_path=None, style=STYLE):
        super().__init__(game, svg_path)
        self.style = style
        self.label_centers = self._load_label_centers()

    # -- data
    def _load_label_centers(self):
        """ {'PAR': (x, y)}: the middle of each province's name in the SVG. """
        centers = {}
        if not self.xml_map:
            return centers
        for layer in minidom.parseString(self.xml_map).getElementsByTagName('g'):
            if layer.getAttribute('id') != 'BriefLabelLayer':
                continue
            for text in layer.getElementsByTagName('text'):
                kind = 'labeltext18' if 'labeltext18' in text.getAttribute('class') else 'labeltext24'
                centers[text.firstChild.data.strip().upper()] = (float(text.getAttribute('x')),
                                                                float(text.getAttribute('y')) - LABEL_RAISE[kind])
        return centers

    def _target_center(self, loc):
        """ Where arrows into `loc` (e.g. 'BUR', 'STP/SC') aim. """
        if self.style.anchor == 'label' and loc[:3] in self.label_centers:
            return self.label_centers[loc[:3]]
        return self._get_unit_center(loc, False)

    def _segment(self, src, target):
        """ The visible part of an arrow from the unit at `src` to `target`: (start, tip). With label anchoring it
            starts at the unit icon's edge (`style.start` from `src`) and ends `style.stop` short of `target`, but
            never shows less than `style.min_visible`: a very short move's tip passes the target's centre. """
        (x1, y1), (x2, y2) = src, target
        length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1.0)
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        if self.style.anchor != 'label':
            stop = min(float(self.metadata['symbol_size'][ARMY][1]) / 2 + 2 * self._colored_stroke_width(),
                       length / 2)
            return src, (round(x2 - ux * stop, 2), round(y2 - uy * stop, 2))
        start = min(self.style.start, length / 2)
        reach = max(length - self.style.stop, start + self.style.min_visible)
        return (round(x1 + ux * start, 2), round(y1 + uy * start, 2)), (round(x1 + ux * reach, 2),
                                                                       round(y1 + uy * reach, 2))

    def _start_of(self, src, toward):
        """ Where a line leaving the unit at `src` towards `toward` comes out of the unit's icon. """
        (x1, y1), (x2, y2) = src, toward
        length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1.0)
        start = min(self.style.start, length / 2) if self.style.anchor == 'label' else 0
        return round(x1 + (x2 - x1) / length * start, 2), round(y1 + (y2 - y1) / length * start, 2)

    # -- drawing helpers
    def _order_layer(self, xml_map, layer_id):
        for node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if node.nodeName == 'g' and _attr(node, 'id') == 'OrderLayer':
                for layer in node.childNodes:
                    if layer.nodeName == 'g' and _attr(layer, 'id') == layer_id:
                        return layer
        return None

    def _stroked(self, xml_map, tag, geometry, power_name, kind, arrow):
        """ The two nodes of one line or curve: (outline, coloured). `kind` is 'move', 'support' or 'convoy'. """
        outline, line = xml_map.createElement(tag), xml_map.createElement(tag)
        for node in (outline, line):
            for name, value in geometry.items():
                node.setAttribute(name, str(value))
        style = self.style
        if style.classic:
            outline.setAttribute('class', 'varwidthshadow' if kind == 'move' else 'shadowdash')
            if kind == 'move':
                outline.setAttribute('stroke-width', str(self._plain_stroke_width()))
            line.setAttribute('class', {'move': 'varwidthorder', 'support': 'supportorder',
                                        'convoy': 'convoyorder'}[kind])
            line.setAttribute('stroke', self.metadata['color'][power_name])
            if kind == 'move':
                line.setAttribute('stroke-width', str(self._colored_stroke_width()))
            if arrow:
                line.setAttribute('marker-end', 'url(#arrow)')
            return outline, line
        for node in (outline, line):
            node.setAttribute('fill', 'none')
            node.setAttribute('stroke-linecap', 'round' if kind == 'support' else 'butt')
        outline.setAttribute('stroke', style.outline)
        outline.setAttribute('stroke-opacity', '0.9')
        outline.setAttribute('stroke-width', str(style.width + style.outline_extra))
        line.setAttribute('stroke', self.metadata['color'][power_name])
        line.setAttribute('stroke-width', str(style.width))
        dash = {'support': style.dash_support, 'convoy': style.dash_convoy}.get(kind)
        if dash:
            line.setAttribute('stroke-dasharray', dash)
            outline.setAttribute('stroke-dasharray', dash)
            if kind == 'support':
                outline.setAttribute('stroke-dasharray', dash)
        if arrow:
            line.setAttribute('marker-end', 'url(#webarrow-%s)' % power_name.lower())
        return outline, line

    def _add(self, xml_map, layer_id, power_name, pairs, extra=()):
        """ Puts the outlines, then the coloured lines, then `extra` nodes in a group of the order layer. """
        group = xml_map.createElement('g')
        if extra:
            group.setAttribute('stroke', self.metadata['color'][power_name])
        for outline, _line in pairs:
            group.appendChild(outline)
        for _outline, line in pairs:
            group.appendChild(line)
        for node in extra:
            group.appendChild(node)
        layer = self._order_layer(xml_map, layer_id)
        if layer is not None:
            layer.appendChild(group)
        return xml_map

    # -- the four arrows
    def _issue_move_order(self, xml_map, src_loc, dest_loc, power_name):
        is_dislodged = self.game.get_current_phase()[-1] == 'R'
        start, end = self._segment(self._get_unit_center(src_loc, is_dislodged), self._target_center(dest_loc))
        pair = self._stroked(xml_map, 'line', {'x1': start[0], 'y1': start[1], 'x2': end[0], 'y2': end[1]},
                             power_name, 'move', arrow=True)
        return self._add(xml_map, 'Layer1', power_name, [pair])

    def _issue_support_move_order(self, xml_map, loc, src_loc, dest_loc, power_name):
        start, src = self._get_unit_center(loc, False), self._get_unit_center(src_loc, False)
        end = self._segment(src, self._target_center(dest_loc))[1]
        start = self._start_of(start, src)
        path = 'M {},{} C {},{} {},{} {},{}'.format(start[0], start[1], src[0], src[1], src[0], src[1], end[0], end[1])
        pair = self._stroked(xml_map, 'path', {'d': path}, power_name, 'support', arrow=True)
        return self._add(xml_map, 'Layer2', power_name, [pair])

    def _issue_support_hold_order(self, xml_map, loc, dest_loc, power_name):
        symbol = 'SupportHoldUnit'
        symbol_x, symbol_y = self._center_symbol_around_unit(dest_loc, False, symbol)
        symbol_node = xml_map.createElement('use')
        symbol_node.setAttribute('x', symbol_x)
        symbol_node.setAttribute('y', symbol_y)
        symbol_node.setAttribute('height', self.metadata['symbol_size'][symbol][0])
        symbol_node.setAttribute('width', self.metadata['symbol_size'][symbol][1])
        symbol_node.setAttribute('xlink:href', '#{}'.format(symbol))
        centre, dest = self._get_unit_center(loc, False), self._get_unit_center(dest_loc, False)
        start = self._start_of(centre, dest)
        length = max(((dest[0] - centre[0]) ** 2 + (dest[1] - centre[1]) ** 2) ** 0.5, 1.0)
        back = float(self.metadata['symbol_size'][symbol][1]) / 2
        end = (round(centre[0] + (length - back) / length * (dest[0] - centre[0]), 2),
               round(centre[1] + (length - back) / length * (dest[1] - centre[1]), 2))
        pair = self._stroked(xml_map, 'line', {'x1': start[0], 'y1': start[1], 'x2': end[0], 'y2': end[1]},
                             power_name, 'support', arrow=False)
        return self._add(xml_map, 'Layer2', power_name, [pair], extra=[symbol_node])

    def _issue_convoy_order(self, xml_map, loc, src_loc, dest_loc, power_name):
        symbol = 'ConvoyTriangle'
        symbol_x, symbol_y = self._center_symbol_around_unit(src_loc, False, symbol)
        height, width = (float(value) for value in self.metadata['symbol_size'][symbol])
        triangle = EquilateralTriangle(x_top=float(symbol_x) + width / 2, y_top=float(symbol_y),
                                       x_right=float(symbol_x) + width, y_right=float(symbol_y) + height,
                                       x_left=float(symbol_x), y_left=float(symbol_y) + height)
        symbol_node = xml_map.createElement('use')
        symbol_node.setAttribute('x', symbol_x)
        symbol_node.setAttribute('y', str(float(symbol_y) - height / 6))
        symbol_node.setAttribute('height', self.metadata['symbol_size'][symbol][0])
        symbol_node.setAttribute('width', self.metadata['symbol_size'][symbol][1])
        symbol_node.setAttribute('xlink:href', '#{}'.format(symbol))

        fleet, army = self._get_unit_center(loc, False), self._get_unit_center(src_loc, False)
        target = self._target_center(dest_loc)
        first_end = triangle.intersection(fleet[0], fleet[1])                    # fleet -> army, no head
        second_start = triangle.intersection(target[0], target[1])               # army -> destination
        end = self._segment(army, target)[1]
        first_start = self._start_of(fleet, first_end)
        first = self._stroked(xml_map, 'line', {'x1': first_start[0], 'y1': first_start[1], 'x2': first_end[0],
                                                'y2': first_end[1]}, power_name, 'convoy', arrow=False)
        second = self._stroked(xml_map, 'line', {'x1': second_start[0], 'y1': second_start[1], 'x2': end[0],
                                                 'y2': end[1]}, power_name, 'convoy', arrow=True)
        return self._add(xml_map, 'Layer2', power_name, [first, second], extra=[symbol_node])

    # -- the SVG text: arrow heads and name halos
    def _heads(self):
        """ One marker per power: a head of the power's colour with a light edge, sized in map units. """
        size = self.style.head
        markers = []
        for power, color in self.metadata['color'].items():
            markers.append(
                '<marker id="webarrow-%s" markerUnits="userSpaceOnUse" markerWidth="%s" markerHeight="%s" '
                'orient="auto" refX="9" refY="5" viewBox="0 0 10 10"><path d="M 0 0 L 10 5 L 0 10 z" fill="%s" '
                'stroke="%s" stroke-width="1.1" stroke-linejoin="round"/></marker>'
                % (power.lower(), size, size, color, self.style.outline))
        return ''.join(markers)

    def render(self, incl_orders=True, incl_abbrev=False, output_format='svg', output_path=None):
        svg = super().render(incl_orders=incl_orders, incl_abbrev=incl_abbrev, output_format=output_format,
                             output_path=output_path)
        if not svg:
            return svg
        if not self.style.classic and '</defs>' in svg:
            svg = svg.replace('</defs>', self._heads() + '</defs>', 1)
        if self.style.halo and incl_abbrev:
            svg = re.sub(r'(<g [^>]*id="BriefLabelLayer")', r'\1 ' + HALO, svg, count=1)
        return svg


# ----------------------------------------------------------------------------------------------------------------
# One renderer per map, a copy per game
# ----------------------------------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _base_renderer(renderer_class, map_name):
    """ A renderer of the map, loaded once. Renders only read the loaded SVG and metadata, so each game draws with
        a shallow copy of it. """
    return renderer_class(Game(map_name=map_name))


def renderer_for(game, renderer_class=WebRenderer):
    """ A renderer of `game` (a copy of the cached one of its map). """
    renderer = copy.copy(_base_renderer(renderer_class, game.map_name))
    renderer.game = game
    return renderer


def render(game, incl_orders=True, incl_abbrev=True):
    """ The SVG of `game` (as `game.render`), drawn by the web app's renderer; `game.renderer` is set to it. """
    game.renderer = renderer_for(game)
    return game.render(incl_orders=incl_orders, incl_abbrev=incl_abbrev)
