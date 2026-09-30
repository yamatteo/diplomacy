""" Game logic between the web views and the engine: order choices, submission, lazy phase processing.

    There is no background process: `process_if_due()` is called on every game request and processes the
    phase when every player is ready or the deadline has passed.

    The web app's own state lives in `meta` (saved next to the game):
    ``phase`` (the phase the clock/ready flags refer to), ``deadline`` (epoch seconds or None),
    ``phase_hours`` ({'M': 48, 'R': 24, 'A': 24}; 0 = no deadline), ``ready`` and ``submitted`` (per power),
    ``players`` (how many people the game was started for), ``neutral`` (powers nobody plays: their units
    hold, never support and are disbanded if they must retreat; see `VARIANTS`), ``win`` (supply centers needed
    to win, if not the map's default) and ``allies`` ({power: power whose player also controls it}: in the
    2 player game Italy joins the winner of a coin flip in 1902).
"""
import logging
import random
import re
import time

from diplomacy import Game

LOGGER = logging.getLogger(__name__)

PHASE_TYPE_NAMES = {'M': 'Movement', 'R': 'Retreats', 'A': 'Adjustments'}
DEFAULT_PHASE_HOURS = {'M': 48, 'R': 24, 'A': 24}
ORDER_GROUPS = ['Hold', 'Move', 'Move via convoy', 'Support', 'Convoy', 'Retreat', 'Build', 'Disband']
# Safety net: phases processed in a single request (e.g. several phases where no player has anything to order).
MAX_PHASES_PER_REQUEST = 12

ALL_POWERS = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
# "Alternate way to play" (rulebook p.19): how the seven powers are grouped for N players. Powers in no group are
# neutral. The 2 player game is played from the standard 1901 start (not 1914 as in the rulebook): Italy is neutral
# until Spring 1902, then joins one side chosen by a coin flip (`ITALY_JOINS_YEAR`), and 24 centers win.
VARIANTS = {
    7: [[power] for power in ALL_POWERS],
    6: [[power] for power in ALL_POWERS if power != 'ITALY'],
    5: [[power] for power in ALL_POWERS if power not in ('ITALY', 'GERMANY')],
    4: [['ENGLAND'], ['AUSTRIA', 'FRANCE'], ['GERMANY', 'TURKEY'], ['ITALY', 'RUSSIA']],
    3: [['ENGLAND', 'GERMANY', 'AUSTRIA'], ['RUSSIA', 'ITALY'], ['FRANCE', 'TURKEY']],
    2: [['ENGLAND', 'FRANCE', 'RUSSIA'], ['AUSTRIA', 'GERMANY', 'TURKEY']],
}
TWO_PLAYER_WIN = 24
ITALY_JOINS_YEAR = 1902
MIN_PLAYERS, MAX_PLAYERS = min(VARIANTS), max(VARIANTS)


def neutral_powers(players):
    """ Powers nobody plays in a game for `players` people. """
    grouped = {power for group in VARIANTS[players] for power in group}
    return [power for power in ALL_POWERS if power not in grouped]


def check_assignment(players, users):
    """ Compares the users file with the rulebook grouping for `players` people.

        :return: list of warnings (empty if every group has exactly one user and neutral powers have none).
    """
    warnings = []
    owner = {power: user.name for user in users.values() for power in user.powers}
    groups = [set(group) for group in VARIANTS[players]]
    for group in groups:
        names = {owner.get(power) for power in group}
        label = '/'.join(power.title() for power in sorted(group))
        if names == {None}:
            warnings.append('Nobody plays %s.' % label)
        elif len(names) > 1:
            warnings.append('%s should be played by a single user, but is split between %s.' % (
                label, ', '.join(sorted(name or 'nobody' for name in names))))
    for power in neutral_powers(players):
        if power in owner:
            warnings.append('%s is neutral with %d players, but %s is assigned to it.' % (
                power.title(), players, owner[power]))
    for user in users.values():
        if user.powers and set(user.powers) not in groups and set(user.powers) - set(neutral_powers(players)):
            warnings.append('%s controls %s, which is not a group of the %d player game.' % (
                user.name, ', '.join(power.title() for power in user.powers), players))
    return warnings


def plan_assignment(names, players, rng=random, random_select=True, random_powers=True):
    """ Chooses `players` of the users `names` and gives each a group of powers of the `players` player game.

        :param random_select: pick the players at random (else the first ones in `names`).
        :param random_powers: shuffle which player gets which group (else in order).
        :return: {username: [powers]}
    """
    if players not in VARIANTS:
        raise ValueError('Unsupported number of players: %r' % (players,))
    if len(names) < players:
        raise ValueError('%d users available, %d needed.' % (len(names), players))
    chosen = rng.sample(list(names), players) if random_select else list(names)[:players]
    groups = [list(group) for group in VARIANTS[players]]
    if random_powers:
        rng.shuffle(groups)
    return dict(zip(chosen, groups))


def new_game(created_by, now, players=MAX_PLAYERS):
    """ Creates a standard game for `players` people and its meta. """
    if players not in VARIANTS:
        raise ValueError('Unsupported number of players: %r' % (players,))
    game = Game(game_id='game_%s' % time.strftime('%Y%m%d_%H%M%S', time.gmtime(now)))
    meta = {'created_by': created_by, 'created_at': now, 'phase_hours': dict(DEFAULT_PHASE_HOURS),
            'last_processed': None, 'players': players, 'neutral': neutral_powers(players), 'allies': {}}
    if players == 2:
        meta['win'] = TWO_PLAYER_WIN
    start_phase_clock(game, meta, now)
    LOGGER.info('New game %s created by %s: players=%d neutral=%s map=%s rules=%s phase=%s deadline=%s',
                game.game_id, created_by, players, meta['neutral'], game.map_name, game.rules,
                game.get_current_phase(), meta['deadline'])
    return game, meta


def start_phase_clock(game, meta, now):
    """ Resets ready flags and the deadline for the (new) current phase. """
    phase = game.get_current_phase()
    hours = meta['phase_hours'].get(phase[-1], 0)
    meta['phase'] = phase
    meta['ready'] = {}
    meta['submitted'] = {}
    meta['deadline'] = now + hours * 3600 if hours and not game.is_game_done else None


def players_by_power(game, meta, users):
    """ Returns {power_name: username} for users assigned to a (non-neutral) power of this game. """
    players = {}
    neutral = meta.get('neutral', [])
    for user in users.values():
        for power in user.powers:
            if power in neutral:
                LOGGER.warning('User %r is assigned to %s, which is neutral in this game: ignored', user.name, power)
            elif game.has_power(power):
                players[power] = user.name
            else:
                LOGGER.warning('User %r is assigned to %s, which is not a power of map %s',
                               user.name, power, game.map_name)
    for power, ally in meta.get('allies', {}).items():
        if ally in players and power not in players:
            players[power] = players[ally]
    return players


def powers_of(game, meta, user):
    """ The powers `user` may give orders to in this game. """
    neutral = meta.get('neutral', [])
    powers = [power for power in user.powers if game.has_power(power) and power not in neutral]
    powers += [power for power, ally in meta.get('allies', {}).items() if ally in powers and power not in neutral]
    return powers


def italy_joins(game, meta, now):
    """ 2 player game: from Spring 1902 Italy is no longer neutral but played by the winner of a coin flip. """
    phase = game.get_current_phase()
    if 'ITALY' not in meta.get('neutral', []) or meta.get('players') != 2 or game.is_game_done:
        return
    if not phase[1:5].isdigit() or int(phase[1:5]) < ITALY_JOINS_YEAR:
        return
    side = random.choice([group[0] for group in VARIANTS[2]])
    meta['neutral'].remove('ITALY')
    meta.setdefault('allies', {})['ITALY'] = side
    LOGGER.info('Coin flip at %s: Italy joins the side of %s (%s). neutral=%s allies=%s', phase, side,
                '/'.join(next(group for group in VARIANTS[2] if group[0] == side)), meta['neutral'], meta['allies'])


def active_powers(game, meta, users):
    """ Powers that have a player and something to order in the current phase. """
    return [power for power in players_by_power(game, meta, users) if game.get_orderable_locations(power)]


def due_reason(game, meta, users, now):
    """ Returns why the current phase should be processed now, or None if it should not. """
    if game.is_game_done:
        return None
    players = players_by_power(game, meta, users)
    if not players:
        return None                                     # Nobody plays: never auto-process (it would never stop).
    active = active_powers(game, meta, users)
    if not active:
        return 'no player has orders to give in this phase'
    if all(meta['ready'].get(power) for power in active):
        return 'all players ready'
    if meta['deadline'] and now >= meta['deadline']:
        return 'deadline passed'
    return None


def process_phase(game, meta, store, now, reason):
    """ Saves, backs up, processes the current phase and starts the clock of the next one. """
    phase = game.get_current_phase()
    store.save(game, meta)
    store.backup('before_%s' % phase)
    LOGGER.info('Processing %s (%s). ready=%s submitted=%s orders=%s', phase, reason, meta['ready'],
                sorted(meta['submitted']), game.get_orders())
    neutral_units = {power: list(game.get_power(power).units) for power in meta.get('neutral', [])
                     if game.has_power(power)} if phase[-1] == 'A' else {}
    if meta.get('win'):
        game.win = meta['win']          # the engine resets it from the map every time the game is loaded
    phase_data = game.process()
    for power, units in neutral_units.items():
        # The engine disbands units in excess of supply centers; neutral units must stay where they are.
        if sorted(game.get_power(power).units) != sorted(units):
            LOGGER.info('Restoring units of neutral %s after %s: %s -> %s', power, phase,
                        game.get_power(power).units, units)
            game.set_units(power, units, reset=True)
    results = {unit: [str(result) for result in unit_results if str(result)]
               for unit, unit_results in phase_data.results.items()}
    LOGGER.info('Processed %s -> %s. results=%s', phase, game.get_current_phase(), results)
    LOGGER.info('After %s: centers=%s units=%s', phase, game.get_centers(), game.get_units())
    if game.is_game_done:
        LOGGER.info('Game is over: outcome=%s', game.outcome)
    meta['last_processed'] = {'phase': phase, 'at': now, 'reason': reason}
    italy_joins(game, meta, now)
    start_phase_clock(game, meta, now)
    LOGGER.info('Now in %s, deadline=%s', game.get_current_phase(), meta['deadline'])
    store.save(game, meta)


def process_if_due(game, meta, users, store, now):
    """ Processes the current phase (and following ones) while they are due.

        :return: list of processed phase names
    """
    processed = []
    while len(processed) < MAX_PHASES_PER_REQUEST:
        reason = due_reason(game, meta, users, now)
        if not reason:
            break
        processed.append(game.get_current_phase())
        process_phase(game, meta, store, now, reason)
    else:
        LOGGER.warning('Stopped after processing %d phases in one request: %s', len(processed), processed)
    return processed


# ----------------------------------------------------------------------------------------------------------------
# Orders
# ----------------------------------------------------------------------------------------------------------------
def order_group(order):
    """ Classifies an order string (e.g. 'A PAR S A MAR - BUR' -> 'Support'). """
    words = order.split()
    if words[-1] == 'H':
        return 'Hold'
    if words[-1] == 'B':
        return 'Build'
    if words[-1] == 'D':
        return 'Disband'
    if 'R' in words[2:]:
        return 'Retreat'
    if 'S' in words[2:]:
        return 'Support'
    if 'C' in words[2:]:
        return 'Convoy'
    if words[-1] == 'VIA':
        return 'Move via convoy'
    return 'Move'


def order_loc(order):
    """ Location (without coast) of the unit an order is for: 'F STP/SC - BOT' -> 'STP'. """
    return order.split()[1][:3]


def order_choices(game, power_name):
    """ Describes what a power can order in the current phase, for the orders form.

        :return: dict with ``phase_type``, ``note`` (what is expected), ``default`` (what an empty choice means),
            ``limit`` (max number of orders, or None) and ``items``: one per orderable location, each with
            ``loc``, ``label``, ``current`` (submitted order or '') and ``groups`` [(group name, [orders])].
    """
    power = game.get_power(power_name)
    phase_type = game.get_current_phase()[-1]
    possible = game.get_all_possible_orders()
    current = {order_loc(order): order for order in game.get_orders(power_name)}
    units = {unit.lstrip('*')[2:5]: unit for unit in list(power.units) + list(power.retreats)}
    build_count = len(power.centers) - len(power.units)
    note, default, limit = '', 'Hold', None
    if phase_type == 'R':
        note, default = 'Your dislodged units must retreat or be disbanded.', 'Disband'
    elif phase_type == 'A' and build_count > 0:
        note = 'You may build up to %d unit(s).' % build_count
        default, limit = 'No build', build_count
    elif phase_type == 'A' and build_count < 0:
        note = ('You must disband %d unit(s). If you choose fewer, the engine picks the rest for you.'
                % -build_count)
        default, limit = 'Keep', -build_count

    items = []
    for loc in game.get_orderable_locations(power_name):
        groups = {}
        for order in possible.get(loc, []):
            if order == 'WAIVE':
                continue
            groups.setdefault(order_group(order), []).append(order)
        items.append({'loc': loc,
                      'label': units.get(loc, 'Build at %s' % loc),
                      'current': current.get(loc, ''),
                      'groups': [(name, sorted(groups[name])) for name in ORDER_GROUPS if name in groups]})
    return {'phase_type': phase_type, 'note': note, 'default': default, 'limit': limit, 'items': items}


def submit_orders(game, meta, power_name, chosen, ready, now):
    """ Replaces the orders of a power for the current phase.

        :param chosen: dict of location -> order string ('' for the default).
        :param ready: True if the player is done and the phase may be processed early.
        :return: list of error messages; empty if the orders were accepted.
    """
    phase = game.get_current_phase()
    if power_name in meta.get('neutral', []):
        LOGGER.warning('Orders for neutral %s rejected: chosen=%s', power_name, chosen)
        return ['%s is neutral in this game and cannot be given orders.' % power_name.title()]
    possible = game.get_all_possible_orders()
    orderable = game.get_orderable_locations(power_name)
    orders, errors = [], []
    for loc, order in chosen.items():
        if not order:
            continue
        if loc not in orderable or order == 'WAIVE' or order not in possible.get(loc, []):
            errors.append('"%s" is not a valid order for %s in %s.' % (order, loc, phase))
        else:
            orders.append(order)
    limit = order_choices(game, power_name)['limit']
    if limit is not None and len(orders) > limit:
        errors.append('Too many orders: at most %d in this phase, you gave %d.' % (limit, len(orders)))
    if errors:
        LOGGER.warning('Rejected orders from %s in %s: chosen=%s errors=%s', power_name, phase, chosen, errors)
        return errors

    previous = game.get_orders(power_name)
    game.error = []
    game.clear_orders(power_name)
    game.set_orders(power_name, orders)
    if game.error:
        # Should not happen (orders come from get_all_possible_orders): restore and report.
        errors = [str(error) for error in game.error]
        LOGGER.error('Engine rejected orders from %s in %s: orders=%s errors=%s', power_name, phase, orders, errors)
        game.error = []
        game.clear_orders(power_name)
        game.set_orders(power_name, previous)
        game.error = []
        return errors
    meta['submitted'][power_name] = now
    meta['ready'][power_name] = bool(ready)
    LOGGER.info('Orders set by %s in %s: %s (was %s) ready=%s', power_name, phase,
                game.get_orders(power_name), previous, bool(ready))
    return []


# ----------------------------------------------------------------------------------------------------------------
# Views of the game
# ----------------------------------------------------------------------------------------------------------------
def _clean_svg(svg):
    """ Makes the engine's SVG embeddable in an HTML page and scalable with CSS. """
    svg = svg[svg.index('<svg'):]
    tag_end = svg.index('>')
    tag = re.sub(r'\s(width|height)="[^"]*"', '', svg[:tag_end])
    return tag + svg[tag_end:]


def render_current(game, orders_of=()):
    """ SVG of the current position. Only the orders of the powers in `orders_of` are drawn, if given:
        other powers' orders are secret until the phase is processed. """
    if not orders_of:
        return _clean_svg(game.render(incl_orders=False, incl_abbrev=True))
    copy = Game.from_dict(game.to_dict())
    for power_name in copy.powers:
        if power_name not in orders_of:
            copy.clear_orders(power_name)
    return _clean_svg(copy.render(incl_orders=True, incl_abbrev=True))


def render_phase(game, phase_data):
    """ SVG of a past phase with everybody's orders. """
    past = Game(map_name=game.map_name)
    past.set_phase_data(phase_data)
    return _clean_svg(past.render(incl_orders=True, incl_abbrev=True))


def phase_orders(game, phase_data):
    """ Orders and results of a past phase: [(power_name, [(order, result text)])]. """
    table = []
    for power_name in game.powers:
        rows = []
        for order in phase_data.orders.get(power_name) or []:
            unit = ' '.join(order.split()[:2])
            results = [str(result) for result in phase_data.results.get(unit, []) if str(result)]
            rows.append((order, ', '.join(results)))
        table.append((power_name, rows))
    return table


def power_status(game, meta, users):
    """ One row per power for the status table. """
    players = players_by_power(game, meta, users)
    neutral = meta.get('neutral', [])
    rows = []
    for power_name, power in game.powers.items():
        has_orders = bool(game.get_orderable_locations(power_name)) and not game.is_game_done
        if power.is_eliminated():
            state = 'eliminated'
        elif game.is_game_done:
            state = ''
        elif power_name in neutral:
            state = 'neutral (units hold)'
        elif power_name not in players:
            state = 'no player (units hold)'
        elif not has_orders:
            state = 'nothing to order'
        elif meta['ready'].get(power_name):
            state = 'ready'
        elif power_name in meta['submitted']:
            state = 'orders submitted, not ready'
        else:
            state = 'waiting for orders'
        rows.append({'power': power_name, 'player': players.get(power_name, ''), 'centers': len(power.centers),
                     'units': len(power.units), 'state': state})
    return rows


def game_summary(game, meta, users):
    """ Compact description of the game for /debug/info and logs. Contains no orders. """
    return {'game_id': game.game_id, 'map': game.map_name, 'phase': game.get_current_phase(),
            'done': game.is_game_done, 'outcome': game.outcome, 'phases_played': len(game.state_history),
            'meta': meta, 'status': power_status(game, meta, users)}
