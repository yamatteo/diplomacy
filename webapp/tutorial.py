""" Content of the help page that is computed from the engine instead of being written by hand:
    worked examples (drawn by the renderer, resolved by the adjudicator) and the province table.
    Both are static for a given map, so they are built once per process and cached, without any translated text:
    the examples' titles and explanations come from `example_texts()` in the language of each request, and the
    game words (powers, results, province kinds) are English keys translated by the template.
"""
import functools
import logging
import re

from diplomacy import Game

from webapp.gameplay import _clean_svg
from webapp.i18n import gettext as _

LOGGER = logging.getLogger(__name__)

# Each example: powers' units and orders on an otherwise empty board, and the provinces the picture shows.
EXAMPLES = [
    {'id': 'standoff',
     'orders': {'GERMANY': ['A BER - SIL'], 'RUSSIA': ['A WAR - SIL']},
     'focus': ['BER', 'SIL', 'WAR', 'PRU', 'BOH']},
    {'id': 'support',
     'orders': {'FRANCE': ['A MAR - BUR', 'A GAS S A MAR - BUR'], 'GERMANY': ['A BUR H']},
     'focus': ['MAR', 'BUR', 'GAS', 'PAR']},
    {'id': 'cut',
     'orders': {'GERMANY': ['A PRU - WAR', 'A SIL S A PRU - WAR'], 'RUSSIA': ['A WAR H', 'A BOH - SIL']},
     'focus': ['PRU', 'WAR', 'SIL', 'BOH']},
    {'id': 'support-hold',
     'orders': {'FRANCE': ['F LYO - TYS', 'F WES S F LYO - TYS'], 'ITALY': ['F TYS H', 'F ROM S F TYS']},
     'focus': ['LYO', 'WES', 'TYS', 'ROM']},
    {'id': 'convoy',
     'orders': {'ENGLAND': ['A LON - NWY VIA', 'F NTH C A LON - NWY']},
     'focus': ['LON', 'NTH', 'NWY']},
]

AREA_TYPES = {'LAND': 'Inland', 'COAST': 'Coastal', 'PORT': 'Coastal', 'WATER': 'Sea'}


def example_texts():
    """ Title and explanation of each worked example, in the language of the current request: {id: (title, text)}.
        Not cached, unlike the examples themselves. """
    return {
        'standoff': (_('A standoff (bounce)'),
                     _('Germany and Russia both order an army into Silesia. The forces are equal, one against one, '
                       'so nobody moves and Silesia stays empty.')),
        'support': (_('A supported attack'),
                    _('The French army in Marseilles attacks Burgundy with the support of the army in Gascony: '
                      'two against one. The German army is dislodged and will have to retreat.')),
        'cut': (_('Cutting a support'),
                _('Germany attacks Warsaw from Prussia with support from Silesia. But Russia attacks Silesia from '
                  'Bohemia: that attack fails, yet it is enough to cut the support. The attack on Warsaw is now '
                  'one against one and bounces.')),
        'support-hold': (_('Supporting a unit that stays'),
                         _('France attacks the Tyrrhenian Sea with support (two), but the Italian fleet there is '
                           'supported in place by the fleet in Rome (two). Equal forces: the attack bounces.')),
        'convoy': (_('A convoy'),
                   _('The English fleet in the North Sea carries the army from London to Norway in a single turn. '
                     'Both orders are needed: the army moves, the fleet convoys.')),
    }


def _success_word(order):
    """ What to call (English key, see `views.order_result_label`) an order the engine reports no failure for. A support or convoy that 'succeeds' was
        given as ordered, whatever then happened to the move it helped. """
    words = order.split()
    if 'S' in words[2:]:
        return 'support given'
    if 'C' in words[2:]:
        return 'convoy made'
    return 'holds' if words[-1] == 'H' else 'succeeds'


def _crop(svg, renderer, locs, margin=130):
    """ Restricts an SVG of the whole map to the area around the given provinces. """
    points = [renderer.metadata['coord'][loc]['unit'] for loc in locs]
    xs, ys = [float(x) for x, _ in points], [float(y) for _, y in points]
    left, top = min(xs) - margin, min(ys) - margin
    width, height = max(xs) - min(xs) + 2 * margin, max(ys) - min(ys) + 2 * margin
    view_box = 'viewBox="%.0f %.0f %.0f %.0f"' % (left, top, width, height)
    return re.sub(r'viewBox="[^"]*"', view_box, svg, count=1)


@functools.lru_cache(maxsize=None)
def examples():
    """ Builds the worked examples: a picture of the orders and the results the engine gives them.

        :return: list of dicts with id, svg and rows [(power, order, [result keys])]
    """
    built = []
    for example in EXAMPLES:
        game = Game()
        game.clear_units()
        game.clear_centers()
        for power, orders in example['orders'].items():
            game.set_units(power, [' '.join(order.split()[:2]) for order in orders])
        for power, orders in example['orders'].items():
            game.set_orders(power, orders)
        accepted = game.get_orders()
        svg = _crop(_clean_svg(game.render(incl_orders=True, incl_abbrev=True)), game.renderer, example['focus'])
        phase_data = game.process()
        rows = []
        for power, orders in example['orders'].items():
            if len(accepted[power]) != len(orders):
                LOGGER.error('Help example %s: engine accepted %s out of %s for %s', example['id'],
                             accepted[power], orders, power)
            for order in orders:
                unit = ' '.join(order.split()[:2])
                results = [str(result) for result in phase_data.results.get(unit, []) if str(result)]
                rows.append((power, order, results or [_success_word(order)]))
        built.append({'id': example['id'], 'svg': svg, 'rows': rows})
    LOGGER.info('Built %d help examples: %s', len(built),
                {example['id']: [row[2] for row in example['rows']] for example in built})
    return built


@functools.lru_cache(maxsize=None)
def provinces():
    """ Province table for the standard map: [(kind, [(abbreviation, name, is supply center, home power)])], with
        kind 'Inland', 'Coastal' or 'Sea' and the home power as a key ('FRANCE', or '' if none). """
    game_map = Game().map
    homes = {loc: power for power, locs in game_map.homes.items() for loc in locs if power != 'UNOWNED'}
    groups = {}
    for name, abbr in game_map.loc_name.items():
        kind = AREA_TYPES.get(game_map.area_type(abbr))
        if kind and '/' not in abbr:                    # 'STP/NC' etc. are coasts of a province, not provinces
            groups.setdefault(kind, []).append((abbr, name.title(), abbr in game_map.scs,
                                                homes.get(abbr, '')))
    return [(kind, sorted(groups[kind])) for kind in ('Inland', 'Coastal', 'Sea') if kind in groups]
