""" End-to-end tests of the web app through Flask's test client, against a temporary data dir. """
import json
import os
import re
import time

import pytest

from webapp import create_app

USERS = """# test users
anna:pw-anna:FRANCE:admin
bruno:pw-bruno:GERMANY
carla:pw-carla:-
"""


@pytest.fixture(name='app')
def app_fixture(tmp_path, monkeypatch):
    """ App with its data dir in a temp folder and three users (France+admin, Germany, spectator). """
    monkeypatch.setenv('DIPLOMACY_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('DIPLOMACY_DEBUG_TOKEN', 'debug-secret')
    (tmp_path / 'users.txt').write_text(USERS)
    app = create_app()
    app.config['TESTING'] = True
    return app


class Browser:
    """ A logged-in test client that handles the CSRF token like a browser would. """

    def __init__(self, app, username=None, password=None):
        self.client = app.test_client()
        if username:
            response = self.post('/login', username=username, password=password or 'pw-' + username)
            assert response.status_code == 302, response.get_data(as_text=True)

    def csrf(self):
        page = self.client.get('/login').get_data(as_text=True)
        return re.search(r'name="csrf" value="([^"]+)"', page).group(1)

    def get(self, path):
        return self.client.get(path)

    def text(self, path):
        response = self.client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        return response.get_data(as_text=True)

    def post(self, path, **form):
        return self.client.post(path, data=dict(form, csrf=self.csrf()))


def map_of(page):
    """ The SVG map embedded in a page. """
    return page[page.index('<div class="card map">'):page.index('</svg>')]


def read_game_file(app):
    with open(os.path.join(app.config['DATA_DIR'], 'game.json'), encoding='utf-8') as file:
        return json.load(file)


def start_game(app):
    anna = Browser(app, 'anna')
    assert anna.post('/admin/new-game', confirm='yes').status_code == 302
    return anna


def test_users_file_is_created_with_random_admin(tmp_path, monkeypatch):
    monkeypatch.setenv('DIPLOMACY_DATA_DIR', str(tmp_path))
    app = create_app()
    lines = [line for line in (tmp_path / 'users.txt').read_text().splitlines() if not line.startswith('#')]
    assert len(lines) == 1 and lines[0].startswith('admin:') and lines[0].endswith(':-:admin')
    password = lines[0].split(':')[1]
    assert len(password) >= 10
    browser = Browser(app, 'admin', password)
    assert 'No game yet' in browser.text('/')


def test_login_required_and_wrong_password(app):
    anonymous = Browser(app)
    assert anonymous.get('/').status_code == 302
    assert anonymous.get('/history').status_code == 302
    assert anonymous.get('/admin').status_code == 302
    response = anonymous.post('/login', username='anna', password='wrong')
    assert response.status_code == 200 and 'Wrong username or password' in response.get_data(as_text=True)
    assert anonymous.get('/').status_code == 302
    # Passwords never reach the log.
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert 'pw-anna' not in log and 'wrong' not in log.split('Failed login')[-1].split('\n')[0]


def test_post_without_csrf_token_is_rejected(app):
    client = app.test_client()
    client.get('/login')
    assert client.post('/login', data={'username': 'anna', 'password': 'pw-anna'}).status_code == 400


def test_only_admin_can_use_admin_pages(app):
    bruno = Browser(app, 'bruno')
    assert bruno.get('/admin').status_code == 403
    assert bruno.post('/admin/new-game', confirm='yes').status_code == 403
    assert not os.path.exists(os.path.join(app.config['DATA_DIR'], 'game.json'))


def test_new_game_needs_confirmation(app):
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game')
    assert 'No game yet' in anna.text('/')
    anna.post('/admin/new-game', confirm='yes')
    assert 'Spring 1901, Movement' in anna.text('/')


def test_orders_form_lists_only_own_units(app):
    anna = start_game(app)
    page = anna.text('/')
    assert 'Your orders (France)' in page
    assert 'name="order_PAR"' in page and 'name="order_BRE"' in page and 'name="order_MAR"' in page
    assert 'name="order_BER"' not in page                       # a German unit
    assert '<option value="A PAR - BUR"' in page
    carla = Browser(app, 'carla')
    assert 'Your orders' not in carla.text('/')                 # spectator


def test_orders_are_saved_secret_and_editable(app):
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    anna_map_before, bruno_map_before = map_of(anna.text('/')), map_of(bruno.text('/'))
    response = anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', order_BRE='', order_MAR='A MAR H')
    assert response.status_code == 302
    page = anna.text('/')
    assert 'Orders saved for S1901M' in page
    assert '<option value="A PAR - BUR" selected>' in page
    assert 'orders submitted, not ready' in page
    assert sorted(read_game_file(app)['game']['powers']['FRANCE']['orders']) == ['A MAR', 'A PAR']
    # Germany sees that France submitted, but not what.
    bruno_page = bruno.text('/')
    assert 'orders submitted, not ready' in bruno_page
    assert ' selected>' not in bruno_page                       # no order of his own, and none of hers shown
    assert map_of(bruno_page) == bruno_map_before               # her orders are not drawn on his map...
    assert map_of(page) != anna_map_before                      # ...but they are on hers
    # Still S1901M: France is not ready and Germany has not submitted.
    assert read_game_file(app)['game']['phase'] == 'SPRING 1901 MOVEMENT'
    # France can change its mind.
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - PIC')
    orders = read_game_file(app)['game']['powers']['FRANCE']['orders']
    assert orders == {'A PAR': '- PIC'}


def test_invalid_orders_are_rejected(app):
    anna = start_game(app)
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - MOS')
    assert 'is not a valid order' in anna.text('/')
    anna.post('/orders', phase='S1901M', order_BER='A BER - KIE')     # not France's unit
    assert 'You cannot give orders for BER' in anna.text('/')
    assert read_game_file(app)['game']['powers']['FRANCE']['orders'] == {}
    assert read_game_file(app)['game']['powers']['GERMANY']['orders'] == {}
    # The spectator cannot order at all.
    assert Browser(app, 'carla').post('/orders', phase='S1901M', order_PAR='A PAR - BUR').status_code == 403


def test_phase_is_processed_when_all_players_are_ready(app):
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    assert read_game_file(app)['game']['phase'] == 'SPRING 1901 MOVEMENT'
    bruno.post('/orders', phase='S1901M', order_MUN='A MUN - BUR', ready='yes')
    data = read_game_file(app)
    assert data['game']['phase'] == 'FALL 1901 MOVEMENT'
    assert data['meta']['ready'] == {} and data['meta']['last_processed']['reason'] == 'all players ready'
    assert os.path.exists(os.path.join(app.config['DATA_DIR'], 'backups', 'game_before_S1901M.json'))
    page = anna.text('/')
    assert 'Fall 1901, Movement' in page
    assert 'A PAR - BUR' in page and 'bounce' in page              # previous phase, now public
    history = bruno.text('/history/S1901M')
    assert 'A MUN - BUR' in history and 'bounce' in history
    assert bruno.get('/history/S1950M').status_code == 404
    # Orders sent with the form of the old phase are refused, not applied to the new phase.
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - PIC', ready='yes')
    assert 'NOT recorded' in anna.text('/')
    assert read_game_file(app)['game']['powers']['FRANCE']['orders'] == {}


def test_phase_is_processed_when_deadline_passes(app):
    anna = start_game(app)
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR')      # saved, not ready
    data = read_game_file(app)
    assert data['meta']['deadline'] > time.time() + 47 * 3600
    data['meta']['deadline'] = time.time() - 1
    with open(os.path.join(app.config['DATA_DIR'], 'game.json'), 'w', encoding='utf-8') as file:
        json.dump(data, file)
    page = Browser(app, 'carla').text('/')                             # any page view triggers processing
    assert 'Processed: S1901M' in page and 'Fall 1901, Movement' in page
    data = read_game_file(app)
    assert data['meta']['last_processed']['reason'] == 'deadline passed'
    assert 'A BUR' in data['game']['powers']['FRANCE']['units']
    assert data['meta']['deadline'] > time.time() + 47 * 3600


def test_admin_actions(app):
    anna = start_game(app)
    anna.post('/admin/deadline', hours='')
    assert read_game_file(app)['meta']['deadline'] is None
    anna.post('/admin/deadline', hours='12')
    assert 11.9 * 3600 < read_game_file(app)['meta']['deadline'] - time.time() < 12.1 * 3600
    anna.post('/admin/settings', hours_M='72', hours_R='0', hours_A='12')
    assert read_game_file(app)['meta']['phase_hours'] == {'M': 72.0, 'R': 0.0, 'A': 12.0}
    anna.post('/admin/process')
    data = read_game_file(app)
    assert data['game']['phase'] == 'FALL 1901 MOVEMENT'
    assert 71.9 * 3600 < data['meta']['deadline'] - time.time() < 72.1 * 3600
    anna.post('/admin/draw', confirm='yes')
    assert 'The game is over' in anna.text('/')
    # A new game archives the old one.
    anna.post('/admin/new-game', confirm='yes')
    assert read_game_file(app)['game']['phase'] == 'SPRING 1901 MOVEMENT'
    assert len(os.listdir(os.path.join(app.config['DATA_DIR'], 'archive'))) == 1


def test_builds_are_limited_and_retreat_phase_is_skipped(app):
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    anna.post('/orders', phase='S1901M', order_MAR='A MAR - SPA', order_BRE='F BRE - MAO', order_PAR='A PAR - PIC',
              ready='yes')
    bruno.post('/orders', phase='S1901M', ready='yes')
    anna.post('/orders', phase='F1901M', order_MAO='F MAO - POR', ready='yes')
    bruno.post('/orders', phase='F1901M', ready='yes')
    # Germany has nothing to build, so only France is awaited in W1901A.
    page = anna.text('/')
    assert 'Winter 1901, Adjustments' in page and 'You may build up to 2 unit(s)' in page
    assert 'nothing to order' in page
    anna.post('/orders', phase='W1901A', order_BRE='F BRE B', order_MAR='A MAR B', order_PAR='A PAR B')
    assert 'Too many orders' in anna.text('/')
    anna.post('/orders', phase='W1901A', order_BRE='F BRE B', order_MAR='A MAR B', ready='yes')
    data = read_game_file(app)
    assert data['game']['phase'] == 'SPRING 1902 MOVEMENT'
    assert {'F BRE', 'A MAR'} <= set(data['game']['powers']['FRANCE']['units'])


def test_no_players_means_no_automatic_processing(tmp_path, monkeypatch):
    monkeypatch.setenv('DIPLOMACY_DATA_DIR', str(tmp_path))
    (tmp_path / 'users.txt').write_text('boss:pw-boss:-:admin\n')
    app = create_app()
    boss = Browser(app, 'boss')
    boss.post('/admin/new-game', confirm='yes')
    data = read_game_file(app)
    data['meta']['deadline'] = time.time() - 1
    with open(tmp_path / 'game.json', 'w', encoding='utf-8') as file:
        json.dump(data, file)
    boss.text('/')
    assert read_game_file(app)['game']['phase'] == 'SPRING 1901 MOVEMENT'


def test_debug_info_reports_game_without_secrets(app):
    anna = start_game(app)
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR')
    response = app.test_client().get('/debug/info?token=debug-secret')
    info = response.get_json()
    assert info['game']['phase'] == 'S1901M'
    assert {'name': 'bruno', 'powers': ['GERMANY'], 'admin': False} in info['users']
    text = response.get_data(as_text=True)
    assert 'pw-anna' not in text and 'A PAR - BUR' not in text


def test_help_page_examples_and_rulebook(app):
    anonymous = Browser(app)
    page = anonymous.text('/help')                                  # public
    assert 'Cheat sheet' in page and 'Mid-Atlantic Ocean' in page and '<code>MAO</code>' in page
    assert 'BUL/EC</code> Bulgaria' not in page                     # coasts are not listed as provinces
    # The examples are resolved by the engine: check they say what the rulebook says.
    from webapp import tutorial
    results = {example['id']: [row[2] for row in example['rows']] for example in tutorial.examples()}
    assert results == {
        'standoff': ['bounce', 'bounce'],
        'support': ['succeeds', 'support given', 'dislodged'],
        'cut': ['bounce', 'cut', 'holds', 'bounce'],
        'support-hold': ['bounce', 'support given', 'holds', 'support given'],
        'convoy': ['succeeds', 'convoy made'],
    }
    diagram = anonymous.get('/help/diagram/convoy.svg')
    assert diagram.status_code == 200 and diagram.mimetype == 'image/svg+xml' and diagram.data.startswith(b'<svg')
    assert anonymous.get('/help/diagram/unknown.svg').status_code == 404
    # The rulebook is for logged-in players only.
    assert anonymous.get('/rules.pdf').status_code == 302
    rulebook = Browser(app, 'carla').get('/rules.pdf')
    assert rulebook.status_code == 200 and rulebook.mimetype == 'application/pdf' and rulebook.data[:4] == b'%PDF'
    assert 'private' in rulebook.headers['Cache-Control']


def make_app(tmp_path, monkeypatch, users):
    monkeypatch.setenv('DIPLOMACY_DATA_DIR', str(tmp_path))
    (tmp_path / 'users.txt').write_text(users)
    app = create_app()
    app.config['TESTING'] = True
    return app


def test_user_with_several_powers_orders_them_in_one_form(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, 'anna:pw-anna:FRANCE,AUSTRIA:admin\nbruno:pw-bruno:ENGLAND\n')
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes', players='6')
    page = anna.text('/')
    assert 'name="order_PAR"' in page and 'name="order_VIE"' in page and 'name="order_LON"' not in page
    assert anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', order_VIE='A VIE - GAL').status_code == 302
    powers = read_game_file(app)['game']['powers']
    assert sorted(powers['FRANCE']['orders']) == ['A PAR'] and sorted(powers['AUSTRIA']['orders']) == ['A VIE']
    anna.post('/orders', phase='S1901M', order_LON='F LON - NTH')      # England's unit
    assert 'You cannot give orders for LON' in anna.text('/')
    assert read_game_file(app)['game']['powers']['ENGLAND']['orders'] == {}


def test_neutral_powers_do_not_block_and_cannot_be_ordered(tmp_path, monkeypatch):
    users = 'anna:pw-anna:FRANCE:admin\nbruno:pw-bruno:GERMANY\n'
    app = make_app(tmp_path, monkeypatch, users)
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes', players='5')
    assert read_game_file(app)['meta']['neutral'] == ['GERMANY', 'ITALY']
    assert 'neutral (units hold)' in anna.text('/')
    # Germany is neutral: bruno has no power to order with, and only anna's readiness counts.
    assert Browser(app, 'bruno').post('/orders', phase='S1901M', order_MUN='A MUN H').status_code == 403
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    assert read_game_file(app)['game']['phase'] == 'FALL 1901 MOVEMENT'


def test_new_game_rejects_bad_player_count(app):
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes', players='9')
    assert not os.path.exists(os.path.join(app.config['DATA_DIR'], 'game.json'))
    anna.post('/admin/new-game', confirm='yes')                        # default: 7 players
    assert read_game_file(app)['meta']['players'] == 7


def test_two_player_game_italy_joins_in_1902(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, 'anna:pw-anna:ENGLAND,FRANCE,RUSSIA:admin\nbruno:pw-bruno:AUSTRIA,GERMANY,TURKEY\n')
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes', players='2')
    meta = read_game_file(app)['meta']
    assert meta['neutral'] == ['ITALY'] and meta['win'] == 24
    # Everybody holds and is ready, until 1902 starts.
    for _ in range(8):
        game, _meta = app.config['GAME_STORE'].load()
        if game.get_current_phase() == 'S1902M':
            break
        for name in ('anna', 'bruno'):
            Browser(app, name).post('/orders', phase=game.get_current_phase(), ready='yes')
    data = read_game_file(app)
    assert data['game']['phase'] == 'SPRING 1902 MOVEMENT'
    assert data['meta']['neutral'] == [] and data['meta']['allies']['ITALY'] in ('ENGLAND', 'AUSTRIA')
    winner = 'anna' if data['meta']['allies']['ITALY'] == 'ENGLAND' else 'bruno'
    assert 'name="order_ROM"' in Browser(app, winner).text('/')


def test_neutral_power_keeps_units_it_has_no_centers_for(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, 'anna:pw-anna:FRANCE:admin\nbruno:pw-bruno:GERMANY\n')
    anna, bruno = Browser(app, 'anna'), Browser(app, 'bruno')
    anna.post('/admin/new-game', confirm='yes', players='6')
    store = app.config['GAME_STORE']
    anna.post('/orders', phase='S1901M', order_MAR='A MAR - SPA', ready='yes')     # France takes Spain: a build
    bruno.post('/orders', phase='S1901M', ready='yes')
    for browser in (anna, bruno):                       # Fall 1901: hold; France waits to build
        browser.post('/orders', phase='F1901M', ready='yes')
    game, meta = store.load()
    assert game.get_current_phase() == 'W1901A' and 'ITALY' in meta['neutral']
    italian_units = sorted(game.get_power('ITALY').units)
    assert len(italian_units) == 3
    # Italy loses all its centers: the engine would disband its units (more units than centers).
    game.set_centers('ITALY', [], reset=True)
    store.save(game, meta)
    Browser(app, 'anna').post('/admin/process')
    data = read_game_file(app)
    assert data['game']['phase'] == 'SPRING 1902 MOVEMENT'
    assert sorted(data['game']['powers']['ITALY']['units']) == italian_units
