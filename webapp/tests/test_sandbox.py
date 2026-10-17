""" The order simulator: outcomes of guessed scenarios, the marks drawn, and the endpoint's rules. """
import os
import random
import re
import statistics
import time

import pytest

from diplomacy import Game
from webapp import sandbox, views
from webapp.sandbox import SandboxError, simulate
from webapp.tests.test_app import Browser, app_fixture, email_of, make_app, start_game  # pylint: disable=unused-import

POWERS = ('AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY')


def position(**units):
    """ A Spring 1901 movement game with exactly the given units, e.g. ``position(FRANCE=['A PAR'])``. """
    game = Game()
    for power in POWERS:
        game.set_units(power, units.get(power, []), reset=True)
    return game


def outcomes(result):
    """ {unit: (outcome, dislodged)} of a simulation's result. """
    return {item['unit']: (item['outcome'], item['dislodged']) for item in result['outcomes']}


def run(game, my_powers=('FRANCE',), meta=None, **guesses):
    """ Simulates with `guesses` given as ``MUN='A MUN - BUR'``. """
    return simulate(game, meta or {}, set(my_powers), guesses)


def test_bounce_cuts_the_move_short_and_draws_a_cross():
    game = position(FRANCE=['A PAR'], GERMANY=['A MUN'])
    game.set_orders('FRANCE', ['A PAR - BUR'])
    result = run(game, MUN='A MUN - BUR')
    assert outcomes(result) == {'A PAR': ('bounce', False), 'A MUN': ('bounce', False)}
    assert result['svg'].count(sandbox.RED) >= 2                    # a cross for each of the two moves
    assert 'marker-end' not in result['svg'].split('id="OrderLayer"')[1].split('id="UnitLayer"')[0]


def test_marks_never_take_clicks_from_the_units():
    game = position(FRANCE=['A PAR'], GERMANY=['A MUN'])
    game.set_orders('FRANCE', ['A PAR - BUR'])
    svg = run(game, MUN='A MUN - BUR')['svg']
    assert svg.count('pointer-events="none"') >= 3                  # two crosses and a halo
    assert not re.search(r'<use[^>]*pointer-events', svg)


def test_supported_move_succeeds_and_cut_support_fails():
    game = position(FRANCE=['A PAR', 'A MAR'], ITALY=['A PIE'])
    game.set_orders('FRANCE', ['A PAR - BUR', 'A MAR S A PAR - BUR'])
    result = run(game)
    assert outcomes(result) == {'A PAR': ('success', False), 'A MAR': ('success', False),
                                'A PIE': ('hold', False)}
    assert sandbox.GREEN in result['svg'] and 'opacity="0.35"' not in result['svg']

    result = run(game, PIE='A PIE - MAR')
    assert outcomes(result) == {'A PAR': ('success', False), 'A MAR': ('cut', False),
                                'A PIE': ('bounce', False)}
    assert result['svg'].count('opacity="0.35"') == 1               # the cut support's line is faded
    assert [item['guess'] for item in result['outcomes']] == [False, False, True]


def test_dislodged_unit_is_ringed_and_unordered_units_hold():
    game = position(FRANCE=['A PAR', 'A MAR'], GERMANY=['A BUR'])
    game.set_orders('FRANCE', ['A PAR - BUR', 'A MAR S A PAR - BUR'])
    result = run(game)
    assert outcomes(result) == {'A PAR': ('success', False), 'A MAR': ('success', False),
                                'A BUR': ('hold', True)}
    assert [item['order'] for item in result['outcomes']] == ['A PAR - BUR', 'A MAR S A PAR - BUR', '']
    assert 'stroke-dasharray="1,6"' not in result['svg'].split('id="OrderLayer"')[0]
    assert 'r="%d"' % sandbox.RING_RADIUS in result['svg']


def test_unordered_unit_gets_the_assumed_hold_ring():
    game = position(FRANCE=['A PAR'], GERMANY=['A MUN'])
    result = run(game)
    assert outcomes(result) == {'A PAR': ('hold', False), 'A MUN': ('hold', False)}
    assert result['svg'].count('stroke-dasharray="1,6"') == 2


def test_disrupted_convoy():
    game = position(ENGLAND=['A LON', 'F NTH'], GERMANY=['F SKA', 'F HEL'])
    game.set_orders('ENGLAND', ['A LON - BEL VIA', 'F NTH C A LON - BEL'])
    result = run(game, my_powers=('ENGLAND',), SKA='F SKA - NTH', HEL='F HEL S F SKA - NTH')
    assert outcomes(result) == {'A LON': ('bounce', False), 'F NTH': ('disrupted', True),
                                'F SKA': ('success', False), 'F HEL': ('success', False)}
    assert result['svg'].count('opacity="0.35"') == 1               # the convoy order's line


def test_convoy_that_works():
    game = position(ENGLAND=['A LON', 'F NTH'])
    game.set_orders('ENGLAND', ['A LON - BEL VIA', 'F NTH C A LON - BEL'])
    result = run(game, my_powers=('ENGLAND',))
    assert outcomes(result) == {'A LON': ('success', False), 'F NTH': ('success', False)}


def test_support_for_a_move_that_does_not_happen_is_void():
    game = position(FRANCE=['A PAR', 'A MAR'])
    game.set_orders('FRANCE', ['A MAR S A PAR - BUR'])
    result = run(game)
    assert outcomes(result) == {'A PAR': ('hold', False), 'A MAR': ('void', False)}
    assert result['svg'].count('opacity="0.35"') == 1


def test_guesses_are_marked_and_real_orders_are_not():
    game = position(FRANCE=['A PAR'], GERMANY=['A MUN'])
    game.set_orders('FRANCE', ['A PAR - BUR'])
    result = run(game, MUN='A MUN - RUH')
    assert [(item['unit'], item['guess']) for item in result['outcomes']] == [('A PAR', False), ('A MUN', True)]
    assert result['svg'].count('stroke-dasharray="9,5"') == 1       # the guess's halo only


def test_invalid_guesses_are_refused():
    game = position(FRANCE=['A PAR'], GERMANY=['A MUN'])
    meta = {'neutral': ['ITALY']}
    game.set_units('ITALY', ['A ROM'], reset=True)
    for guesses, text in [({'MUN': 'A MUN - PAR'}, 'not a valid guess'),
                          ({'MUN': 'WAIVE'}, 'not a valid guess'),
                          ({'MUN': 'F MUN - BUR'}, 'not a valid guess'),
                          ({'PAR': 'A PAR - BUR'}, 'your own unit'),
                          ({'BER': 'A BER H'}, 'no unit at BER'),
                          ({'ROM': 'A ROM - VEN'}, 'neutral')]:
        with pytest.raises(SandboxError) as error:
            simulate(game, meta, {'FRANCE'}, guesses)
        assert text in str(error.value), (guesses, str(error.value))


def test_only_movement_phases():
    game = position(FRANCE=['A PAR'])
    game.set_orders('FRANCE', ['A PAR - BUR'])
    game.process()
    assert game.get_current_phase() == 'F1901M'
    game.set_orders('FRANCE', ['A BUR - MUN'])
    game.set_orders('GERMANY', [])
    game.process()
    assert game.get_current_phase() == 'W1901A'
    with pytest.raises(SandboxError, match='only works in movement phases'):
        run(game)


def test_other_powers_real_orders_never_leak_into_the_simulation():
    game = position(FRANCE=['A PAR'], GERMANY=['A MUN'])
    game.set_orders('FRANCE', ['A PAR - BUR'])
    game.set_orders('GERMANY', ['A MUN - BUR'])                     # secret: not a guess
    before = game.to_dict()
    result = run(game)
    assert outcomes(result) == {'A PAR': ('success', False), 'A MUN': ('hold', False)}
    assert game.to_dict() == before                                 # the game itself is untouched
    assert game.get_orders('GERMANY') == ['A MUN - BUR']


# ----------------------------------------------------------------------------------------------------------------
# The endpoint
# ----------------------------------------------------------------------------------------------------------------
def simulator_on(browser):
    assert browser.post('/profile/sandbox', sandbox='yes').status_code == 302


def test_flag_is_set_on_the_profile_page(app):
    anna = Browser(app, 'anna')
    assert 'name="sandbox"' in anna.text('/profile')
    assert 'checked' not in anna.text('/profile').split('name="sandbox"')[1][:60]
    assert not app.config['USER_STORE'].load()['anna@example.com'].sandbox
    simulator_on(anna)
    assert app.config['USER_STORE'].load()['anna@example.com'].sandbox
    assert 'checked' in anna.text('/profile').split('name="sandbox"')[1][:60]
    anna.post('/profile/sandbox')                                   # unchecked box: nothing is sent
    assert not app.config['USER_STORE'].load()['anna@example.com'].sandbox
    assert not app.config['USER_STORE'].load()['bruno@example.com'].sandbox


def test_sandbox_endpoint_needs_the_flag_login_and_a_game(app):
    assert Browser(app).client.post('/sandbox', data={}).status_code in (302, 400)
    anna = start_game(app)
    reply = anna.post('/sandbox', phase='S1901M')
    assert reply.status_code == 403 and 'off' in reply.get_json()['errors'][0]
    simulator_on(anna)
    assert anna.post('/sandbox', phase='S1901M').get_json()['ok']


def test_sandbox_endpoint_rules(app):
    anna = start_game(app)
    simulator_on(anna)
    reply = anna.post('/sandbox', phase='W1900A')
    assert reply.status_code == 409 and reply.get_json()['reload']
    reply = anna.post('/sandbox', phase='S1901M', guess_PAR='A PAR - BUR')          # own unit
    assert reply.status_code == 400 and 'your own unit' in reply.get_json()['errors'][0]
    reply = anna.post('/sandbox', phase='S1901M', guess_MUN='A MUN - PAR')
    assert reply.status_code == 400 and 'not a valid guess' in reply.get_json()['errors'][0]
    reply = anna.post('/sandbox', phase='S1901M', guess_MUN='A MUN - BUR')
    data = reply.get_json()
    assert reply.status_code == 200 and data['ok'] and data['svg'].startswith('<svg')
    assert {item['unit']: item['guess'] for item in data['outcomes']}['A MUN'] is True


def test_sandbox_endpoint_changes_nothing_and_shows_no_secret_orders(app):
    anna, bruno = start_game(app), Browser(app, 'bruno')
    simulator_on(anna)
    bruno.post('/orders', phase='S1901M', order_MUN='A MUN - RUH', order_BER='A BER - KIE')   # secret
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR')
    game_file = os.path.join(app.config['DATA_DIR'], 'game.json')
    with open(game_file, 'rb') as file:
        before = file.read()
    for _ in range(3):
        data = anna.post('/sandbox', phase='S1901M', guess_MUN='A MUN - BUR').get_json()
    assert data['ok']
    by_unit = {item['unit']: item for item in data['outcomes']}
    assert by_unit['A MUN']['order'] == 'A MUN - BUR'               # the guess, not Bruno's real order
    assert by_unit['A BER']['order'] == '' and by_unit['A PAR']['order'] == 'A PAR - BUR'
    assert {item['order'] for item in data['outcomes']} == {'', 'A MUN - BUR', 'A PAR - BUR'}
    with open(game_file, 'rb') as file:
        assert file.read() == before                                # byte for byte
    # Bruno's real orders are still his own.
    assert Browser(app, 'bruno').text('/').count('A MUN - RUH') >= 1


def test_sandbox_endpoint_one_at_a_time_per_user(app):
    anna = start_game(app)
    simulator_on(anna)
    lock = views.SIMULATING.setdefault('anna@example.com', views.threading.Lock())
    assert lock.acquire(blocking=False)
    try:
        reply = anna.post('/sandbox', phase='S1901M')
        assert reply.status_code == 429 and 'still running' in reply.get_json()['errors'][0]
    finally:
        lock.release()
    assert anna.post('/sandbox', phase='S1901M').status_code == 200


# ----------------------------------------------------------------------------------------------------------------
# Cost
# ----------------------------------------------------------------------------------------------------------------
def crowded_game(seed=1, until='S1906M'):
    """ A mid-game position reached with random valid orders: many units and arrows. """
    rng = random.Random(seed)
    game = Game()
    while game.get_current_phase() != until and not game.is_game_done:
        possible = game.get_all_possible_orders()
        for power in game.powers:
            game.set_orders(power, [rng.choice(possible[loc]) for loc in game.get_orderable_locations(power)
                                    if possible[loc]])
        game.process()
    return game, rng


def test_simulation_cost_on_a_crowded_position(capsys):
    game, rng = crowded_game()
    assert game.get_current_phase() == 'S1906M'
    units = sum(len(power.units) for power in game.powers.values())
    mine = {'FRANCE'}
    possible = game.get_all_possible_orders()
    guesses = {loc: rng.choice(possible[loc]) for power in game.powers if power not in mine
               for loc in game.get_orderable_locations(power) if possible[loc]}
    game.set_orders('FRANCE', [rng.choice(possible[loc]) for loc in game.get_orderable_locations('FRANCE')
                               if possible[loc]])
    simulate(game, {}, mine, guesses)                               # warms the renderer cache
    times = []
    for _ in range(10):
        started = time.perf_counter()
        simulate(game, {}, mine, guesses)
        times.append((time.perf_counter() - started) * 1000)
    with capsys.disabled():
        print('\nsimulate(): %d units, %d guesses, median %.0f ms, max %.0f ms' % (
            units, len(guesses), statistics.median(times), max(times)))
    assert statistics.median(times) < 1000


# ----------------------------------------------------------------------------------------------------------------
# The game page
# ----------------------------------------------------------------------------------------------------------------
def guess_block(page):
    """ The hidden guess selects of the page. """
    return page[page.index('id="guess-selects"'):page.index('<dialog')]


def test_page_offers_guesses_for_foreign_units_outside_the_orders_form(app):
    anna = start_game(app)
    simulator_on(anna)
    Browser(app, 'bruno').post('/orders', phase='S1901M', order_MUN='A MUN - RUH', order_BER='A BER - KIE')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR')
    page = anna.text('/')
    assert 'id="sim-bar"' in page and 'id="sim-toggle"' in page and 'What the marks mean' in page
    assert 'id="guess_MUN"' in page and 'id="guess_ROM"' in page    # Germany's and Italy's units
    assert 'id="guess_PAR"' not in page and 'id="order_PAR"' in page
    start = page.index('id="orders-form"')
    form = page[start:page.index('</form>', start)]
    assert 'guess_' not in form and 'id="order_PAR"' in form
    assert 'name="guess_' not in page
    assert '<option value="A MUN - RUH">A MUN - RUH</option>' in guess_block(page)      # offered, not chosen
    assert 'selected' not in guess_block(page)                                          # no saved order leaks
    assert '<option value="A PAR - BUR" selected>' in form                              # her own, for contrast


def test_page_without_the_simulator_has_none_of_it(app):
    anna = start_game(app)
    page = anna.text('/')
    for text in ('sim-bar', 'sim-toggle', 'sim-map', 'sim-info', 'guess_', 'What the marks mean', '/sandbox',
                 'Order simulator'):
        assert text not in page, text
    assert '<div class="card map">' in page and 'id="order_PAR"' in page


def test_page_has_no_simulator_for_spectators_retreats_or_neutral_units(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, 'anna:pw-anna:FRANCE:admin\nbruno:pw-bruno:GERMANY\ncarla:pw-carla:-\n')
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes', players='6')               # Italy is neutral
    for name in ('anna', 'bruno', 'carla'):
        app.config['USER_STORE'].set_sandbox(email_of(name), True)
    page = anna.text('/')
    assert 'id="sim-bar"' in page and 'id="guess_MUN"' in page
    assert 'id="guess_ROM"' not in page and 'id="guess_VEN"' not in page   # neutral Italy just holds
    assert 'id="sim-bar"' not in Browser(app, 'carla').text('/')           # nothing to order
    # A retreat phase: Germany must retreat from Burgundy.
    store = app.config['GAME_STORE']
    game, meta = store.load()
    game.set_units('GERMANY', ['A BUR'], reset=True)
    game.set_orders('FRANCE', ['A PAR - BUR', 'A MAR S A PAR - BUR'])
    game.process()
    assert game.get_current_phase() == 'S1901R'
    store.save(game, meta)
    page = Browser(app, 'bruno').text('/')
    assert 'name="order_BUR"' in page and 'sim-bar' not in page and 'guess_' not in page


def test_page_size_with_the_simulator_on_a_crowded_position(tmp_path, monkeypatch, capsys):
    game, _rng = crowded_game()
    powers = [name for name, power in game.powers.items() if power.units]
    app = make_app(tmp_path, monkeypatch, 'anna:pw-anna:%s:admin\nbruno:pw-bruno:-\n' % powers[0])
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes')
    store = app.config['GAME_STORE']
    _game, meta = store.load()
    store.save(game, meta)
    plain = anna.text('/')
    simulator_on(anna)
    page = anna.text('/')
    assert 'id="sim-bar"' in page and page.count('<select id="guess_') >= 10
    with capsys.disabled():
        print('\npage: %d bytes without the simulator, %d with it (%d guess selects)' % (
            len(plain.encode()), len(page.encode()), page.count('<select id="guess_')))
    assert len(page.encode()) < 300_000
