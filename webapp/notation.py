""" Orders described in words, for players who find the traditional notation confusing (profile switch
    ``explicit_orders``, see webapp/users.py): ``A NWY - DEN VIA`` -> "Army Norway (NWY) moves to Denmark (DEN) via
    convoy". The abbreviations always stay in brackets, because the map's labels show only those.

    Only the display changes: stored orders, form values, logs and error messages keep the traditional notation.
    Anything that cannot be described (``WAIVE``, an unknown province or map) is returned as it is, with a
    warning in the log. Texts are translated like the rest of the interface (webapp/i18n_it.py); province names
    through `i18n.province_name`. No dependency but the engine.
"""
import functools
import logging

from diplomacy import Game
from webapp.i18n import gettext as _, province_name

LOGGER = logging.getLogger(__name__)

SMALL_WORDS = {' Of ': ' of '}


@functools.lru_cache(maxsize=None)
def _names(map_name):
    """ {abbreviation: English name} of a map's provinces and coasts ('STP/SC': 'ST PETERSBURG (SOUTH COAST)'). """
    return {abbr: name for name, abbr in Game(map_name=map_name).map.loc_name.items()}


def english_name(name):
    """ 'GULF OF BOTHNIA' -> 'Gulf of Bothnia'. """
    name = name.title()
    for word, small in SMALL_WORDS.items():
        name = name.replace(word, small)
    return name


def describe_loc(loc, map_name):
    """ 'NWY' -> 'Norway (NWY)'; 'STP/SC' -> 'St Petersburg south coast (STP/SC)'. Raises ValueError if unknown. """
    names = _names(map_name)
    loc = loc.upper()
    base, _slash, coast = loc.partition('/')
    if base not in names or (coast and loc not in names):
        raise ValueError('unknown location %r' % loc)
    name = province_name(base, english_name(names[base]))
    if coast:
        coasts = {'NC': _('north coast'), 'SC': _('south coast'), 'EC': _('east coast'), 'WC': _('west coast')}
        if coast not in coasts:
            raise ValueError('unknown coast %r' % loc)
        name = '%s %s' % (name, coasts[coast])
    return '%s (%s)' % (name, loc)


def _unit(unit, map_name):
    words = unit.lstrip('*').split()
    if len(words) != 2 or words[0] not in ('A', 'F'):
        raise ValueError('not a unit: %r' % unit)
    where = describe_loc(words[1], map_name)
    return _('Army %(loc)s', loc=where) if words[0] == 'A' else _('Fleet %(loc)s', loc=where)


def _split(order, map_name):
    """ :return: (the unit's description, the rest of the order in words), the unit is '' for a build. """
    words = order.split()
    if len(words) < 3:
        raise ValueError('too short')
    unit = ' '.join(words[:2])
    verb, rest = words[2], words[3:]
    if verb == 'B' and not rest:
        where = describe_loc(words[1], map_name)
        _unit(unit, map_name)       # validates the unit
        return '', (_('Build Army at %(loc)s', loc=where) if words[0] == 'A'
                    else _('Build Fleet at %(loc)s', loc=where))
    own = _unit(unit, map_name)
    if verb == 'H' and not rest:
        return own, _('holds')
    if verb == 'D' and not rest:
        return own, _('disbands')
    if verb == 'R' and len(rest) == 1:
        return own, _('retreats to %(dest)s', dest=describe_loc(rest[0], map_name))
    if verb == '-' and len(rest) == 1:
        return own, _('moves to %(dest)s', dest=describe_loc(rest[0], map_name))
    if verb == '-' and len(rest) == 2 and rest[1] == 'VIA':
        return own, _('moves to %(dest)s via convoy', dest=describe_loc(rest[0], map_name))
    if verb == 'S' and len(rest) == 2:
        return own, _('supports %(other)s to hold', other=_unit(' '.join(rest), map_name))
    if verb == 'S' and len(rest) == 4 and rest[2] == '-':
        return own, _('supports %(other)s to %(dest)s', other=_unit(' '.join(rest[:2]), map_name),
                      dest=describe_loc(rest[3], map_name))
    if verb == 'C' and len(rest) == 4 and rest[2] == '-':
        return own, _('convoys %(other)s to %(dest)s', other=_unit(' '.join(rest[:2]), map_name),
                      dest=describe_loc(rest[3], map_name))
    raise ValueError('unknown order shape')


def _safe(function, text, map_name):
    try:
        return function(text, map_name)
    except Exception as exc:            # pylint: disable=broad-except
        LOGGER.warning('Cannot describe %r on map %r (shown as it is): %s: %s', text, map_name,
                       type(exc).__name__, exc)
        return text


def describe_order(order, map_name):
    """ 'A NWY - DEN VIA' -> 'Army Norway (NWY) moves to Denmark (DEN) via convoy'. Unparsable: `order`. """
    def describe(text, name):
        unit, rest = _split(text, name)
        return '%s %s' % (unit, rest) if unit else rest
    return _safe(describe, order, map_name)


def describe_short(order, map_name):
    """ The order without its unit, for the order dialog (whose title names the unit): 'moves to Denmark (DEN)'.
        A build has no unit yet, so it is described whole. Unparsable: `order`. """
    return _safe(lambda text, name: _split(text, name)[1], order, map_name)


def describe_unit(unit, map_name):
    """ 'A NWY' -> 'Army Norway (NWY)'. Unparsable: `unit`. """
    return _safe(_unit, unit, map_name)
