""" The web app's map renderer: arrows aim at the province names, nothing else of the map changes. """
import math
import re
import time
from xml.dom import minidom

from diplomacy import Game
from webapp import rendering
from webapp.rendering import STYLE, WebRenderer


def game_with_orders():
    game = Game()
    game.set_orders('FRANCE', ['A PAR - BUR', 'A MAR S A PAR - BUR', 'F BRE - MAO'])
    game.set_orders('GERMANY', ['A MUN - BUR', 'A BER S A MUN - BUR', 'F KIE H'])
    return game


def test_label_centers_cover_the_map():
    renderer = rendering.renderer_for(Game())
    provinces = {loc[:3].upper() for loc in renderer.game.map.locs}
    missing = provinces - set(renderer.label_centers)
    assert missing <= {'SWI'}, missing              # the impassable province has no name
    x, y = renderer.label_centers['BUR']
    ux, uy = (float(v) for v in renderer.metadata['coord']['BUR']['unit'])
    assert abs(x - ux) + abs(y - uy) < 80           # the name is near the province's unit position


MOUSE_ID = {'LYO': 'GOL', 'MAO': 'MID', 'NAO': 'NAT', 'NWG': 'NRG', 'TYS': 'TYN'}     # seas the MouseLayer names differently


def test_label_centers_lie_inside_their_provinces():
    renderer = rendering.renderer_for(Game())
    layer = next(g for g in minidom.parseString(renderer.xml_map).getElementsByTagName('g')
                 if g.getAttribute('id') == 'MouseLayer')
    dx, dy = (float(v) for v in re.findall(r'-?[\d.]+', layer.getAttribute('transform')))
    boxes = {}              # province -> its paths' control points, in map coordinates (a path or a group of paths)
    for node in layer.childNodes:
        if node.nodeType != node.ELEMENT_NODE or not node.getAttribute('id'):
            continue
        paths = [node] if node.tagName == 'path' else node.getElementsByTagName('path')
        numbers = [float(n) for path in paths for n in re.findall(r'-?\d+\.?\d*', path.getAttribute('d'))]
        boxes[node.getAttribute('id').upper()] = ([n + dx for n in numbers[0::2]], [n + dy for n in numbers[1::2]])
    pad = 5
    for loc, (x, y) in renderer.label_centers.items():
        assert MOUSE_ID.get(loc, loc) in boxes, 'no MouseLayer shape for %s' % loc
        xs, ys = boxes[MOUSE_ID.get(loc, loc)]
        assert min(xs) - pad <= x <= max(xs) + pad, (loc, x, (min(xs), max(xs)))
        assert min(ys) - pad <= y <= max(ys) + pad, (loc, y, (min(ys), max(ys)))


def test_rotated_labels_are_centred_through_their_transform():
    centers = rendering.renderer_for(Game()).label_centers
    expected = {'SKA': (754.5 + 7 * math.sin(math.radians(75)), 571.2 - 7 * math.cos(math.radians(75))),
                'POR': (175.1 + 7 * math.sin(math.radians(-60)), 1102.1 - 7 * math.cos(math.radians(-60))),
                'ROM': (744 + 5 * math.sin(math.radians(50)), 1093 - 5 * math.cos(math.radians(50)))}
    for loc, (x, y) in expected.items():
        assert abs(centers[loc][0] - x) < 1 and abs(centers[loc][1] - y) < 1, (loc, centers[loc], (x, y))


def test_move_arrow_points_into_the_target_province():
    game = game_with_orders()
    renderer = rendering.renderer_for(game)
    svg = rendering.render(game)
    ends = [(float(a), float(b)) for a, b in re.findall(r'<line [^>]*x2="([\d.]+)" y2="([\d.]+)"', svg)]
    target = renderer.label_centers['MAO']
    assert any(abs(x - target[0]) < STYLE.stop + 1 and abs(y - target[1]) < STYLE.stop + 1 for x, y in ends)
    assert 'marker-end="url(#webarrow-france)"' in svg
    assert '<marker id="webarrow-france"' in svg


def test_support_is_dotted_and_the_rest_of_the_map_is_the_engines():
    game = game_with_orders()
    svg = rendering.render(game)
    assert 'stroke-dasharray="%s"' % STYLE.dash_support in svg
    assert 'stroke="#ffffff" stroke-width="3.5"' in svg         # names have a halo
    plain = Game()
    assert rendering.render(plain, incl_orders=False).count('<use') == Game().render(incl_orders=False).count('<use')


def test_classic_style_keeps_the_engine_classes():
    game = game_with_orders()
    game.renderer = WebRenderer(game, style=STYLE._replace(classic=True, halo=False))
    svg = game.render(incl_orders=True, incl_abbrev=True)
    assert 'class="varwidthorder"' in svg and 'class="supportorder"' in svg
    assert 'webarrow' not in svg


def test_province_without_a_name_falls_back_to_the_unit_position():
    renderer = rendering.renderer_for(Game())
    assert renderer._target_center('SWI') == renderer._get_unit_center('SWI', False)   # pylint: disable=protected-access


def test_renderer_is_cached_per_map_and_fast():
    first = rendering.renderer_for(Game())
    second = rendering.renderer_for(Game())
    assert first is not second and first.xml_map is second.xml_map
    game = game_with_orders()
    rendering.render(game)
    started = time.perf_counter()
    for _ in range(5):
        rendering.render(game)
    average = (time.perf_counter() - started) / 5
    print('\nrender: %.0f ms' % (average * 1000))
    assert average < 0.5


def test_every_adjacent_move_has_a_visible_arrow():
    """ Short moves between neighbours used to vanish under the unit icon and the head. """
    renderer = rendering.renderer_for(Game())
    shortest = None
    for loc, neighbours in renderer.game.map.loc_abut.items():
        for other in neighbours:
            if loc.upper() == other.upper():
                continue
            src, target = renderer._get_unit_center(loc.upper(), False), renderer._target_center(other.upper())   # pylint: disable=protected-access
            start, tip = renderer._segment(src, target)                                                          # pylint: disable=protected-access
            visible = ((tip[0] - start[0]) ** 2 + (tip[1] - start[1]) ** 2) ** 0.5
            reach = ((tip[0] - src[0]) ** 2 + (tip[1] - src[1]) ** 2) ** 0.5
            distance = ((target[0] - src[0]) ** 2 + (target[1] - src[1]) ** 2) ** 0.5
            assert visible >= min(STYLE.min_visible, distance / 2) - 0.1, (loc, other, visible)
            assert reach >= distance - STYLE.stop - 0.1, (loc, other, reach, distance)    # never short of the centre
            shortest = min(shortest or visible, visible)
    print('\nshortest visible arrow: %.0f px' % shortest)


def test_short_move_is_drawn_from_the_icon_edge_to_the_province_centre():
    game = Game()
    game.set_orders('FRANCE', ['A PAR - BUR'])
    renderer = rendering.renderer_for(game)
    svg = rendering.render(game)
    svg = svg[svg.index('id="OrderLayer"'):]
    x1, y1, x2, y2 = (float(v) for v in re.search(
        r'<line [^>]*x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"', svg).groups())
    src = renderer._get_unit_center('PAR', False)                                      # pylint: disable=protected-access
    assert abs(((x1 - src[0]) ** 2 + (y1 - src[1]) ** 2) ** 0.5 - STYLE.start) < 0.1
    assert ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 >= STYLE.min_visible - 0.1
