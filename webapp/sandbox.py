""" The order simulator: "they do this, I do this" on a throwaway copy of the game.

    A user who turned the simulator on (profile page) can guess the orders of the other powers in a movement phase
    and see how the engine would resolve them together with their own real orders. Nothing is saved: the guesses
    live in the request, the game and its meta are never touched, and the other powers' real (secret) orders are
    cleared from the copies before anything else happens. Units without an order hold, like in the real game.

    The adjudication is the engine's (`Game.process()` on a copy); this module only prepares the copy, classifies
    each order's outcome from the engine's result codes and draws it. Success has no result code; the codes of
    a failure are 'bounce', 'cut', 'void', 'no convoy', 'dislodged' (see `diplomacy.utils.order_results`).

    Marks drawn over the engine's own arrows (shape first, colour as reinforcement; fixed size on the map):
    a green check (move: near its head, support/convoy: on its midpoint) for an order that works, a red cross at
    the end of a move line cut short for a bounce, a red slash and a faded line for a cut support, a faded line
    for a disrupted convoy, a grey "?" and a faded line for a void order, a red ring around a dislodged unit, a
    faint dotted ring around a unit that holds because nobody ordered it and a dashed halo in the power's colour
    around a unit whose order is a guess (the user's own real orders have none).
"""
import copy
import functools
import logging
import time

from diplomacy import Game
from diplomacy.engine.renderer import Renderer, _attr
from webapp import gameplay, i18n
from webapp.i18n import gettext as _

LOGGER = logging.getLogger(__name__)

GREEN, RED, GREY, WHITE = '#1a7f37', '#c62828', '#666666', '#ffffff'
FADED = '0.35'
MARK_RADIUS = 11
RING_RADIUS, HALO_RADIUS = 26, 31
KNOWN_FAILURES = {'bounce', 'cut', 'void', 'no convoy', 'dislodged', 'disrupted'}


class SandboxError(Exception):
    """ The simulation can't run: `messages` are the (translated) reasons to show the user. """

    def __init__(self, messages):
        super().__init__('; '.join(str(message) for message in messages))
        self.messages = list(messages)


# ----------------------------------------------------------------------------------------------------------------
# Preparing and adjudicating the copy
# ----------------------------------------------------------------------------------------------------------------
def parse_order(order):
    """ Splits a normalized movement order: 'F NTH C A LON - BEL' -> ('convoy', 'NTH', 'LON', 'BEL').

        :return: (kind, loc of the unit, loc of the other unit involved or None, destination or None);
            kind is 'hold', 'move', 'support' or 'convoy'.
    """
    words = order.split()
    loc = words[1]
    if words[-1] == 'H' or len(words) < 3:
        return 'hold', loc, None, None
    if words[2] == '-':
        return 'move', loc, loc, words[3]
    other = words[4] if words[3] in ('A', 'F') else words[3]
    dest = words[-1] if '-' in words else other
    return ('support' if words[2] == 'S' else 'convoy'), loc, other, dest


def classify(kind, codes, convoyed_codes=()):
    """ Outcome of an order from the result codes of its unit (without 'dislodged'): 'success', 'bounce' (a move
        that does not arrive), 'cut' (a support), 'disrupted' (a convoy) or 'void'.

        :param convoyed_codes: for a convoy order, the result codes of the unit being convoyed.
    """
    codes = set(codes)
    if kind == 'move':
        if codes & {'bounce', 'no convoy'}:
            return 'bounce'
    elif kind == 'support':
        if 'cut' in codes:
            return 'cut'
        if codes & {'no convoy', 'disrupted'}:
            return 'void'
    elif kind == 'convoy':
        if codes & {'no convoy', 'disrupted'} or 'no convoy' in convoyed_codes:
            return 'disrupted'
    return 'void' if codes else 'success'


def _validated_orders(game, meta, my_powers, guesses):
    """ The orders to simulate per power: the user's real ones, plus the guesses (checked like real orders).

        :return: {power: [orders]}
        :raise SandboxError: if a guess is not valid.
    """
    phase = game.get_current_phase()
    possible = game.get_all_possible_orders()
    owner = {loc: power for power in game.powers for loc in game.get_orderable_locations(power)}
    neutral = set(meta.get('neutral', []))
    errors, by_power = [], {power: list(game.get_orders(power)) for power in my_powers}
    for loc, order in guesses.items():
        if not order:
            continue
        power = owner.get(loc)
        if power is None:
            errors.append(_('There is no unit at %(loc)s to guess an order for.', loc=loc))
        elif power in my_powers:
            errors.append(_('%(loc)s is your own unit: give its order in the orders form.', loc=loc))
        elif power in neutral:
            errors.append(_('%(power)s is neutral in this game: its units just hold.', power=i18n.power_name(power)))
        elif order == 'WAIVE' or order not in possible.get(loc, []):
            errors.append(_('"%(order)s" is not a valid guess for %(loc)s in %(phase)s.', order=order, loc=loc,
                            phase=phase))
        else:
            by_power.setdefault(power, []).append(order)
    if errors:
        raise SandboxError(errors)
    return by_power


def _prepared_copy(game, meta, by_power):
    """ A copy of the game holding exactly the orders of `by_power` (everybody else's are cleared). """
    clone = Game.from_dict(game.to_dict())
    if meta.get('win'):
        clone.win = meta['win']
    for power in clone.powers:
        clone.clear_orders(power)
    for power, orders in by_power.items():
        clone.error = []
        clone.set_orders(power, orders)
        if clone.error:
            # Should not happen (orders come from get_all_possible_orders): drawn as given, logged.
            LOGGER.error('Engine rejected simulated orders of %s in %s: orders=%s errors=%s', power,
                         clone.get_current_phase(), orders, [str(error) for error in clone.error])
            clone.error = []
    return clone


class Simulation:
    """ What the renderer needs: the units' orders, outcomes and flags, all keyed by the unit's location. """

    def __init__(self, orders, codes, guessed):
        """ :param orders: {loc: (power, order string)}
            :param codes: {loc: [result codes]} from the processed copy
            :param guessed: set of locs whose order is a guess
        """
        unknown = {code for loc_codes in codes.values() for code in loc_codes} - KNOWN_FAILURES
        if unknown:
            LOGGER.warning('Unknown order result codes in a simulation (drawn as void): %s', sorted(unknown))
        self.orders, self.guessed = orders, set(guessed)
        self.dislodged = {loc for loc, loc_codes in codes.items() if 'dislodged' in loc_codes}
        self.outcome, self.kind = {}, {}
        for loc, (_power, order) in orders.items():
            kind, _loc, other, _dest = parse_order(order)
            own = [code for code in codes.get(loc, []) if code != 'dislodged']
            self.kind[loc] = kind
            self.outcome[loc] = classify(kind, own, codes.get(other, []) if kind == 'convoy' else ())

    def describe(self, units):
        """ One dict per unit: ``unit``, ``power``, ``order`` ('' if it holds because nobody ordered it),
            ``guess``, ``outcome`` ('success', 'bounce', 'cut', 'disrupted', 'void' or 'hold') and ``dislodged``. """
        result = []
        for power, unit in units:
            loc = unit.split()[1]
            order = self.orders.get(loc, (power, ''))[1]
            outcome = self.outcome.get(loc, 'hold')
            if outcome == 'success' and self.kind.get(loc) == 'hold':
                outcome = 'hold'
            result.append({'unit': unit, 'power': power, 'order': order, 'guess': loc in self.guessed,
                           'outcome': outcome, 'dislodged': loc in self.dislodged})
        return result


# ----------------------------------------------------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------------------------------------------------
def _node(xml_map, tag, **attributes):
    node = xml_map.createElement(tag)
    for name, value in attributes.items():
        node.setAttribute(name.rstrip('_').replace('_', '-'), str(value))
    return node


def _ring(xml_map, x, y, radius, color, width, dash=None, opacity=1):
    ring = _node(xml_map, 'circle', cx=x, cy=y, r=radius, fill='none', stroke=color, stroke_width=width,
                 opacity=opacity)
    if dash:
        ring.setAttribute('stroke-dasharray', dash)
    return ring


def _mark(xml_map, kind, x, y):
    """ A fixed-size mark centered on (x, y): 'success', 'bounce', 'cut' or 'void'. """
    group = _node(xml_map, 'g', transform='translate(%.1f,%.1f)' % (x, y))
    if kind == 'cut':       # a slash over the line: no disc, so it reads differently from the cross
        group.appendChild(_node(xml_map, 'line', x1=-13, y1=13, x2=13, y2=-13, stroke=WHITE, stroke_width=9,
                                stroke_linecap='round'))
        group.appendChild(_node(xml_map, 'line', x1=-13, y1=13, x2=13, y2=-13, stroke=RED, stroke_width=5,
                                stroke_linecap='round'))
        return group
    color = {'success': GREEN, 'bounce': RED, 'void': GREY}[kind]
    group.appendChild(_node(xml_map, 'circle', r=MARK_RADIUS, fill=WHITE, stroke=color, stroke_width=2.5))
    if kind == 'success':
        shape = _node(xml_map, 'path', d='M-5,0 L-1.5,4 L5.5,-4.5')
    elif kind == 'bounce':
        shape = _node(xml_map, 'path', d='M-4.5,-4.5 L4.5,4.5 M4.5,-4.5 L-4.5,4.5')
    else:
        shape = _node(xml_map, 'path', d='M-3.5,-3 C-3.5,-8 4,-8 4,-3 C4,0 0,0 0,3 M0,6.5 L0,7.5')
    for name, value in dict(fill='none', stroke=color, stroke_width=3, stroke_linecap='round',
                            stroke_linejoin='round').items():
        shape.setAttribute(name.replace('_', '-'), str(value))
    group.appendChild(shape)
    return group


class _MarkedRenderer(Renderer):
    """ The engine's renderer, plus the simulation's marks. `sim` is set on a copy for each render. """
    sim = None

    # -- helpers
    def _layer(self, xml_map, layer_id, parent_id=None):
        """ A layer of the SVG: a top-level group, or (with `parent_id`) a group inside another. """
        for node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if node.nodeName == 'g' and _attr(node, 'id') == (parent_id or layer_id):
                if not parent_id:
                    return node
                for sub in node.childNodes:
                    if sub.nodeName == 'g' and _attr(sub, 'id') == layer_id:
                        return sub
        return xml_map.getElementsByTagName('svg')[0]

    def _on_top(self, xml_map, node):
        """ Adds a mark above everything. It never takes clicks: the units below stay clickable. """
        node.setAttribute('pointer-events', 'none')
        self._layer(xml_map, 'HighestOrderLayer').appendChild(node)

    def _last_order(self, xml_map, layer_id):
        """ The group the engine's last `_issue_*` call added to the order layer `layer_id`. """
        return self._layer(xml_map, layer_id, 'OrderLayer').lastChild

    def _midpoint(self, loc, other):
        (x1, y1), (x2, y2) = self._get_unit_center(loc, False), self._get_unit_center(other, False)
        return (x1 + x2) / 2, (y1 + y2) / 2

    def _mark_outcome(self, xml_map, loc, mark_at, node):
        """ Fades `node` (the order's group) when it failed and puts the outcome's mark on `mark_at`. """
        outcome = self.sim.outcome.get(loc)
        if outcome in ('cut', 'disrupted', 'void'):
            node.setAttribute('opacity', FADED)
        mark = {'success': 'success', 'bounce': 'bounce', 'cut': 'cut', 'void': 'void'}.get(outcome)
        if mark:
            self._on_top(xml_map, _mark(xml_map, mark, *mark_at))
        return outcome

    # -- units: rings
    def _add_unit(self, xml_map, unit, power_name, is_dislodged):
        xml_map = super()._add_unit(xml_map, unit, power_name, is_dislodged)
        if self.sim is None or is_dislodged:
            return xml_map
        loc = unit.split()[1]
        x, y = self._get_unit_center(loc, False)
        if loc in self.sim.dislodged:
            self._on_top(xml_map, _ring(xml_map, x, y, RING_RADIUS, RED, 4))
        if loc not in self.sim.orders:
            self._on_top(xml_map, _ring(xml_map, x, y, RING_RADIUS, GREY, 3, dash='1,6', opacity=0.7))
        elif loc in self.sim.guessed:
            self._on_top(xml_map, _ring(xml_map, x, y, HALO_RADIUS, self.metadata['color'][power_name], 3,
                                        dash='9,5'))
        return xml_map

    # -- orders
    def _issue_move_order(self, xml_map, src_loc, dest_loc, power_name):
        xml_map = super()._issue_move_order(xml_map, src_loc, dest_loc, power_name)
        if self.sim is None or self.sim.kind.get(src_loc) != 'move':
            return xml_map
        node = self._last_order(xml_map, 'Layer1')
        lines = [line for line in node.childNodes if line.nodeName == 'line']
        x1, y1, x2, y2 = (float(lines[0].getAttribute(name)) for name in ('x1', 'y1', 'x2', 'y2'))
        if self.sim.outcome[src_loc] == 'bounce':       # cut short, without the arrowhead
            x2, y2 = (x1 + x2) / 2, (y1 + y2) / 2
            for line in lines:
                line.setAttribute('x2', '%.2f' % x2)
                line.setAttribute('y2', '%.2f' % y2)
                if line.hasAttribute('marker-end'):
                    line.removeAttribute('marker-end')
            at = (x2, y2)
        else:                                           # near the head
            length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1)
            back = min(MARK_RADIUS + 6, length / 2)
            at = (x2 - (x2 - x1) / length * back, y2 - (y2 - y1) / length * back)
        self._mark_outcome(xml_map, src_loc, at, node)
        return xml_map

    def _issue_support_hold_order(self, xml_map, loc, dest_loc, power_name):
        xml_map = super()._issue_support_hold_order(xml_map, loc, dest_loc, power_name)
        if self.sim is not None and self.sim.kind.get(loc) == 'support':
            self._mark_outcome(xml_map, loc, self._midpoint(loc, dest_loc), self._last_order(xml_map, 'Layer2'))
        return xml_map

    def _issue_support_move_order(self, xml_map, loc, src_loc, dest_loc, power_name):
        xml_map = super()._issue_support_move_order(xml_map, loc, src_loc, dest_loc, power_name)
        if self.sim is not None and self.sim.kind.get(loc) == 'support':
            # The engine draws a cubic curve loc -> (src, src) -> dest': its point at t=0.5.
            (x0, y0), (xs, ys) = self._get_unit_center(loc, False), self._get_unit_center(src_loc, False)
            end = [float(value) for value in
                   self._last_order(xml_map, 'Layer2').firstChild.getAttribute('d').split()[-1].split(',')]
            at = ((x0 + 6 * xs + end[0]) / 8, (y0 + 6 * ys + end[1]) / 8)
            self._mark_outcome(xml_map, loc, at, self._last_order(xml_map, 'Layer2'))
        return xml_map

    def _issue_convoy_order(self, xml_map, loc, src_loc, dest_loc, power_name):
        xml_map = super()._issue_convoy_order(xml_map, loc, src_loc, dest_loc, power_name)
        if self.sim is not None and self.sim.kind.get(loc) == 'convoy':
            self._mark_outcome(xml_map, loc, self._midpoint(loc, src_loc), self._last_order(xml_map, 'Layer2'))
        return xml_map


@functools.lru_cache(maxsize=None)
def _base_renderer(map_name):
    """ A renderer of the map, loaded once; each simulation draws with a shallow copy of it (the loaded SVG and
        metadata are only read while rendering). """
    return _MarkedRenderer(Game(map_name=map_name))


# ----------------------------------------------------------------------------------------------------------------
# The simulation
# ----------------------------------------------------------------------------------------------------------------
def simulate(game, meta, my_powers, guesses):
    """ Resolves, on copies, the user's real orders together with the guesses for the other powers.

        :param game: the loaded game (not changed).
        :param meta: the web app's meta of the game (not changed).
        :param my_powers: the powers the user plays; their real orders are used as they are.
        :param guesses: {loc: order string} for units of other powers; '' is ignored.
        :return: dict ``svg`` (the map at the start of the phase with the orders and their outcomes) and
            ``outcomes`` (one per unit, see `Simulation.describe`).
        :raise SandboxError: if the phase is not a movement phase or a guess is not valid.
    """
    started = time.perf_counter()
    phase = game.get_current_phase()
    if game.is_game_done or phase[-1] != 'M':
        raise SandboxError([_('The order simulator only works in movement phases.')])
    by_power = _validated_orders(game, meta, set(my_powers), guesses)

    processed = _prepared_copy(game, meta, by_power)
    codes = {unit.split()[1]: [str(code) for code in unit_codes if str(code)]
             for unit, unit_codes in processed.process().results.items()}
    shown = _prepared_copy(game, meta, by_power)
    orders = {parse_order(order)[1]: (power, order) for power, power_orders in by_power.items()
              for order in shown.get_orders(power)}
    guessed = {loc for loc, order in guesses.items() if order and loc in orders}
    simulation = Simulation(orders, codes, guessed)

    renderer = copy.copy(_base_renderer(game.map_name))
    renderer.game, renderer.sim = shown, simulation
    svg = gameplay._clean_svg(renderer.render(incl_orders=True, incl_abbrev=True))     # pylint: disable=protected-access
    units = [(power.name, unit) for power in game.powers.values() for unit in power.units]
    outcomes = simulation.describe(units)
    LOGGER.info('Simulated %s: %d guesses, %d orders, outcomes=%s, %.0f ms', phase,
                len([order for order in guesses.values() if order]), len(orders),
                {outcome: sum(1 for item in outcomes if item['outcome'] == outcome)
                 for outcome in sorted({item['outcome'] for item in outcomes})},
                (time.perf_counter() - started) * 1000)
    return {'svg': svg, 'outcomes': outcomes}
