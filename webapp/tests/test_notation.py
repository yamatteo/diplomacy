""" Orders described in words (webapp/notation.py) and the profile switch that shows them. """
import logging
import random
import re

import pytest
from flask import g

from diplomacy import Game
from webapp import notation
from webapp.tests.test_app import Browser, app_fixture, start_game  # pylint: disable=unused-import

STANDARD = 'standard'

ENGLISH = {
    'A NWY H': 'Army Norway (NWY) holds',
    'A NWY - DEN': 'Army Norway (NWY) moves to Denmark (DEN)',
    'A NWY - DEN VIA': 'Army Norway (NWY) moves to Denmark (DEN) via convoy',
    'A BUD S A VIE': 'Army Budapest (BUD) supports Army Vienna (VIE) to hold',
    'A BUD S A VIE - GAL': 'Army Budapest (BUD) supports Army Vienna (VIE) to Galicia (GAL)',
    'F ADR C A VEN - APU': 'Fleet Adriatic Sea (ADR) convoys Army Venice (VEN) to Apulia (APU)',
    'A SEV R ARM': 'Army Sevastopol (SEV) retreats to Armenia (ARM)',
    'A SEV D': 'Army Sevastopol (SEV) disbands',
    'A BER B': 'Build Army at Berlin (BER)',
    'F BER B': 'Build Fleet at Berlin (BER)',
    'F BOT - BAL': 'Fleet Gulf of Bothnia (BOT) moves to Baltic Sea (BAL)',
    'F STP/SC - BOT': 'Fleet St Petersburg south coast (STP/SC) moves to Gulf of Bothnia (BOT)',
    'F GAS S F MAO - SPA/NC': 'Fleet Gascony (GAS) supports Fleet Mid-Atlantic Ocean (MAO) to Spain north coast (SPA/NC)',
    'F BUL/EC R RUM': 'Fleet Bulgaria east coast (BUL/EC) retreats to Rumania (RUM)',
    'F STP/NC B': 'Build Fleet at St Petersburg north coast (STP/NC)',
}
ITALIAN_NWY = 'Armata Norvegia (NWY) muove a Danimarca (DEN) via mare'
ITALIAN = {
    'A NWY - DEN': 'Armata Norvegia (NWY) muove a Danimarca (DEN)',
    'A NWY H': 'Armata Norvegia (NWY) resta ferma',
    'F ADR C A VEN - APU': 'Flotta Mare Adriatico (ADR) trasporta Armata Venezia (VEN) a Puglia (APU) via mare',
    'F STP/SC - BOT': 'Flotta S. Pietroburgo costa sud (STP/SC) muove a Golfo di Botnia (BOT)',
    'A BER B': 'Costruzione di Armata a Berlino (BER)',
}


def in_language(app, lang):
    """ A request context whose language is `lang`. """
    context = app.test_request_context()
    context.push()
    g.lang = lang
    return context


@pytest.fixture(name='english')
def english_fixture(app):
    context = in_language(app, 'en')
    yield
    context.pop()


@pytest.fixture(name='italian')
def italian_fixture(app):
    context = in_language(app, 'it')
    yield
    context.pop()


def test_orders_in_english(english):
    for order, text in ENGLISH.items():
        assert notation.describe_order(order, STANDARD) == text, order
    assert notation.describe_unit('F STP/SC', STANDARD) == 'Fleet St Petersburg south coast (STP/SC)'
    assert notation.describe_loc('NWY', STANDARD) == 'Norway (NWY)'
    assert notation.describe_short('A PAR - BUR', STANDARD) == 'moves to Burgundy (BUR)'
    assert (notation.describe_short('A PAR S A MAR - BUR', STANDARD)
            == 'supports Army Marseilles (MAR) to Burgundy (BUR)')
    assert notation.describe_short('A BER B', STANDARD) == 'Build Army at Berlin (BER)'


def test_orders_in_italian(italian):
    assert notation.describe_order('A NWY - DEN VIA', STANDARD) == ITALIAN_NWY
    for order, text in ITALIAN.items():
        assert notation.describe_order(order, STANDARD) == text, order
    assert notation.describe_short('A PAR - BUR', STANDARD) == 'muove a Borgogna (BUR)'


@pytest.mark.parametrize('text', ['WAIVE', '', 'A', 'A NWY', 'A XXX H', 'A NWY - XXX', 'A NWY X DEN', 'G NWY H',
                                  'A NWY S A VIE - GAL - BUD', 'F NWY/XX H', 'A NWY - DEN VIA EXTRA'])
def test_unparsable_orders_come_back_unchanged_with_a_warning(english, caplog, text):
    with caplog.at_level(logging.WARNING, logger='webapp.notation'):
        assert notation.describe_order(text, STANDARD) == text
    records = [record for record in caplog.records if record.name == 'webapp.notation']
    assert [record.levelno for record in records] == [logging.WARNING]
    assert repr(text) in records[0].getMessage()


def test_unknown_map_comes_back_unchanged_with_a_warning(english, caplog):
    with caplog.at_level(logging.WARNING, logger='webapp.notation'):
        assert notation.describe_order('A PAR H', 'no_such_map') == 'A PAR H'
        assert notation.describe_unit('A PAR', 'no_such_map') == 'A PAR'
    records = [record for record in caplog.records if record.name == 'webapp.notation']
    assert len(records) == 2 and 'no_such_map' in records[0].getMessage()


def all_orders(seeds=(1, 2, 3), phases=45):
    """ Every possible order of some seeded random games' first phases (movement, retreats, adjustments). """
    found = set()
    for seed in seeds:
        random.seed(seed)
        game = Game()
        for _ in range(phases):
            if game.is_game_done:
                break
            possible = game.get_all_possible_orders()
            for orders in possible.values():
                found.update(orders)
            for power_name in sorted(game.powers):      # sorted: the same game whatever the hash seed
                game.set_orders(power_name, [random.choice(sorted(possible[loc]))
                                             for loc in sorted(game.get_orderable_locations(power_name))
                                             if possible[loc]])
            game.process()
    return sorted(found)


@pytest.mark.parametrize('lang', ['en', 'it'])
def test_every_possible_order_of_a_game_is_described(app, caplog, lang):
    orders = all_orders()
    assert len(orders) > 500 and any(order.endswith(' B') for order in orders) \
        and any(' R ' in order for order in orders) and any(order.endswith(' VIA') for order in orders)
    locs = set(Game().map.locs)
    context = in_language(app, lang)
    try:
        with caplog.at_level(logging.WARNING, logger='webapp.notation'):
            for order in orders:
                if order == 'WAIVE':
                    continue
                text = notation.describe_order(order, STANDARD)
                assert text != order, order
                for word in order.split():
                    if word in locs:
                        assert '(%s)' % word in text, (order, text)
                short = notation.describe_short(order, STANDARD)
                assert short and text.endswith(short), (order, text, short)
    finally:
        context.pop()
    assert not [record for record in caplog.records if record.name == 'webapp.notation']


def enable(app, name='anna'):
    browser = Browser(app, name)
    browser.post('/profile/orders-style', explicit_orders='yes')
    return browser


def test_switch_is_off_by_default_and_saved_from_the_profile(app):
    anna = Browser(app, 'anna')
    store = app.config['USER_STORE']
    assert 'name="explicit_orders"' in anna.text('/profile')
    assert 'checked' not in anna.text('/profile').split('name="explicit_orders"')[1][:60]
    assert not store.load()['anna@example.com'].explicit_orders
    assert anna.post('/profile/orders-style', explicit_orders='yes').status_code == 302
    assert store.load()['anna@example.com'].explicit_orders and not store.load()['bruno@example.com'].explicit_orders
    assert 'checked' in anna.text('/profile').split('name="explicit_orders"')[1][:60]
    anna.post('/profile/orders-style')                              # unchecked box: nothing is sent
    assert not store.load()['anna@example.com'].explicit_orders


def test_off_the_page_shows_raw_orders(app):
    anna = start_game(app)
    page = anna.text('/')
    assert 'data-short' not in page and 'data-unit' not in page
    assert '<div class="orders-grid">' in page and 'minmax(0, 1fr)' not in page
    assert '<option value="A PAR - BUR" >A PAR - BUR</option>' in page
    assert '<strong>A PAR</strong>' in page


def test_navigation_wraps_on_narrow_screens(app):
    page = Browser(app, 'anna').text('/')
    assert re.search(r'header nav \{[^}]*flex-wrap: wrap', page)


def test_on_the_page_describes_orders_but_values_stay_traditional(app):
    start_game(app)
    anna = enable(app)
    page = anna.text('/')
    assert 'value="A PAR - BUR"' in page and 'Army Paris (PAR) moves to Burgundy (BUR)</option>' in page
    assert 'data-short="moves to Burgundy (BUR)"' in page and 'data-unit="Army Paris (PAR)"' in page
    assert '<div class="orders-grid" style="grid-template-columns: minmax(0, 1fr)">' in page      # one column
    assert '<strong>Army Paris (PAR)</strong>' in page
    assert '<strong>Fleet Brest (BRE)</strong>' in page
    assert 'moves to Mid-Atlantic Ocean (MAO)</option>' in page
    reply = anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', order_BRE='F BRE - MAO', ready='yes')
    assert reply.status_code == 302


def test_on_orders_can_still_be_submitted_and_history_describes_them(app):
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    enable(app)
    anna.post('/orders', phase='S1901M', order_BRE='F BRE - MAO', order_PAR='A PAR - BUR', ready='yes')
    assert re.search(r'<option value="A PAR - BUR" selected data-short="[^"]+">Army Paris', anna.text('/'))
    bruno.post('/orders', phase='S1901M', ready='yes')
    history = anna.text('/history/S1901M')
    assert 'Fleet Brest (BRE) moves to Mid-Atlantic Ocean (<span class="sea">MAO</span>)' in history
    assert 'A PAR - BUR' not in history
    assert 'F BRE - <span class="sea">MAO</span>' in bruno.text('/history/S1901M')      # bruno: traditional


def test_sandbox_outcomes_carry_a_text(app):
    anna = start_game(app)
    anna.post('/profile/sandbox', sandbox='yes')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR')
    outcomes = anna.post('/sandbox', phase='S1901M', guess_MUN='A MUN - BUR').get_json()['outcomes']
    texts = {item['unit']: item['text'] for item in outcomes}
    assert texts['A PAR'] == 'A PAR - BUR' and texts['A MUN'] == 'A MUN - BUR'
    anna.post('/profile/orders-style', explicit_orders='yes')
    outcomes = anna.post('/sandbox', phase='S1901M', guess_MUN='A MUN - BUR').get_json()['outcomes']
    texts = {item['unit']: item['text'] for item in outcomes}
    assert texts['A PAR'] == 'Army Paris (PAR) moves to Burgundy (BUR)'
    assert texts['A MUN'] == 'Army Munich (MUN) moves to Burgundy (BUR)'
    assert all(item['order'] in ('', 'A PAR - BUR', 'A MUN - BUR') for item in outcomes)     # raw values stay
    page = anna.text('/')
    assert 'item.text' in page and 'data-short' in page


def test_help_stays_traditional_and_the_province_table_is_translated(app):
    anna = enable(app)
    assert 'A PAR - BUR' in anna.text('/help') and 'Army Paris' not in anna.text('/help')
    anna.post('/profile/lang', lang='it')
    help_page = anna.text('/help')
    assert 'Norvegia' in help_page and 'Mar Tirreno' in help_page and 'A PAR - BUR' in help_page
