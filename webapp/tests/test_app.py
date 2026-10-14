""" End-to-end tests of the web app through Flask's test client, against a temporary data dir. """
import json
import os
import re
import time

import pytest

from webapp import create_app
from webapp.users import UserStore

USERS = """# test users
anna:pw-anna:FRANCE:admin
bruno:pw-bruno:GERMANY
carla:pw-carla:-
"""


def email_of(name):
    return name if '@' in name else name + '@example.com'


def write_users(data_dir, text):
    """ Creates the users of `text` (lines ``name:password:POWERS[:admin]``) in the data dir's users.json, with
        email name@example.com and display name Name. """
    store = UserStore(os.path.join(str(data_dir), 'users.json'))
    for line in text.splitlines():
        if line.strip() and not line.startswith('#'):
            fields = line.split(':')
            powers = [power for power in fields[2].split(',') if power not in ('', '-')]
            store.create(email_of(fields[0]), fields[0].title(), is_admin=len(fields) == 4, powers=powers,
                         password=fields[1])
    return store


@pytest.fixture(name='app')
def app_fixture(tmp_path, monkeypatch):
    """ App with its data dir in a temp folder and three users (France+admin, Germany, spectator). """
    monkeypatch.setenv('DIPLOMACY_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('DIPLOMACY_DEBUG_TOKEN', 'debug-secret')
    write_users(tmp_path, USERS)
    app = create_app()
    app.config['TESTING'] = True
    return app


class Browser:
    """ A logged-in test client that handles the CSRF token like a browser would. """

    def __init__(self, app, username=None, password=None):
        self.client = app.test_client()
        if username:
            response = self.post('/login', email=email_of(username), password=password or 'pw-' + username)
            assert response.status_code == 302, response.get_data(as_text=True)

    def csrf(self):
        page = self.client.get('/login').get_data(as_text=True)
        return re.search(r'name="csrf" value="([^"]+)"', page).group(1)

    def get(self, path):
        return self.finish(self.client.get(path))

    def text(self, path):
        response = self.get(path)
        assert response.status_code == 200, (path, response.status_code)
        return response.get_data(as_text=True)

    def post(self, path, **form):
        return self.finish(self.client.post(path, data=dict(form, csrf=self.csrf())))

    @staticmethod
    def finish(response):
        """ Closes the response like a WSGI server does once it is sent, which runs `call_on_close` callbacks
            (push notifications are delivered there). The test client leaves that to the caller. """
        response.get_data()
        response.close()
        return response


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


def link_token(text):
    """ The token of the set-password link in a page or reply. """
    return re.search(r'/set-password\?token=([A-Za-z0-9_-]+)', text).group(1)


def set_password_with_link(browser, token, password):
    """ Opens a set-password link and chooses `password`. """
    page = browser.text('/set-password?token=' + token)
    assert 'Set your password' in page and 'name="password"' in page, page
    return browser.post('/set-password', token=token, password=password, confirm=password)


def test_first_admin_is_created_with_the_debug_link(tmp_path, monkeypatch):
    monkeypatch.setenv('DIPLOMACY_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('DIPLOMACY_DEBUG_TOKEN', 'debug-secret')
    app = create_app()
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert 'There are no users yet: open /debug/admin-link' in log
    assert app.test_client().get('/debug/admin-link?email=boss@example.com').status_code == 404
    assert app.test_client().get('/debug/admin-link?token=wrong&email=boss@example.com').status_code == 404
    assert not os.path.exists(tmp_path / 'users.json')
    reply = app.test_client().get('/debug/admin-link?token=debug-secret&email=Boss@Example.com')
    assert reply.status_code == 200 and reply.headers['Referrer-Policy'] == 'no-referrer'
    text = reply.get_data(as_text=True)
    assert text.startswith('Set-password link for boss@example.com (admin)') and 'https://localhost/set-password' in text
    token = link_token(text)
    users = app.config['USER_STORE'].load()
    assert list(users) == ['boss@example.com'] and users['boss@example.com'].is_admin
    assert users['boss@example.com'].name == 'boss' and users['boss@example.com'].password is None
    browser = Browser(app)
    assert set_password_with_link(browser, token, 'boss-password').status_code == 302
    assert 'No game yet' in browser.text('/')
    assert Browser(app, 'boss', 'boss-password').text('/admin')
    # Recovery: an existing user gets a new link and becomes admin.
    app.config['USER_STORE'].set_admin('boss@example.com', False)
    reply = app.test_client().get('/debug/admin-link?token=debug-secret&email=boss@example.com')
    assert reply.status_code == 200 and app.config['USER_STORE'].load()['boss@example.com'].is_admin
    assert app.test_client().get('/debug/admin-link?token=debug-secret&email=not-an-email').status_code == 400
    for path in ('users.json', 'logs/app.log'):
        content = (tmp_path / path).read_text()
        assert token not in content and 'boss-password' not in content, path


def test_without_users_and_debug_token_the_log_says_nobody_can_log_in(tmp_path, monkeypatch):
    monkeypatch.setenv('DIPLOMACY_DATA_DIR', str(tmp_path))
    (tmp_path / 'users.txt').write_text('anna:pw-anna:FRANCE:admin\n')
    app = create_app()
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert 'users.txt is no longer used' in log and 'nobody can log in' in log
    assert app.config['USER_STORE'].load() == {}
    assert Browser(app).post('/login', email='anna', password='pw-anna').status_code == 200   # not logged in


def invite(admin, email, name, **extra):
    """ The admin adds a user; returns the token of the link shown on the admin page. """
    assert admin.post('/admin/users/add', email=email, name=name, **extra).status_code == 302
    page = admin.text('/admin')
    assert 'shown only now' in page and 'href="mailto:%s?subject=' % email.lower() in page
    return link_token(page)


def test_invited_user_sets_a_password_with_a_link_that_works_once(app):
    anna = Browser(app, 'anna')
    token = invite(anna, 'Dario@Example.com', 'Dario')
    page = anna.text('/admin')
    assert 'shown only now' not in page                                # the link is shown once
    assert 'dario@example.com' in page and 'link pending until' in page
    assert 'mailto:dario@example.com?subject=' not in page and token not in page
    # A user without a password cannot log in, whatever they type.
    assert Browser(app).post('/login', email='dario@example.com', password='').status_code == 200
    dario = Browser(app)
    page = dario.text('/set-password?token=' + token)
    assert 'dario@example.com' in page and 'Dario' in page
    assert dario.get('/set-password?token=' + token).headers['Referrer-Policy'] == 'no-referrer'
    reply = dario.post('/set-password', token=token, password='short', confirm='short')
    assert 'must be 8 to 200 characters' in reply.get_data(as_text=True)
    reply = dario.post('/set-password', token=token, password='dario-password', confirm='other-password')
    assert 'The two passwords differ' in reply.get_data(as_text=True)
    assert dario.post('/set-password', token=token, password='dario-password',
                      confirm='dario-password').status_code == 302
    assert 'Password saved' in dario.text('/')                          # logged in
    # Login with the email in any case.
    assert Browser(app, ' DARIO@example.COM ', 'dario-password').text('/')
    # The link was used: it does not work again.
    again = Browser(app)
    assert 'This link does not work' in again.text('/set-password?token=' + token)
    reply = again.post('/set-password', token=token, password='evil-password', confirm='evil-password')
    assert 'This link does not work' in reply.get_data(as_text=True)
    assert Browser(app).post('/login', email='dario@example.com', password='evil-password').status_code == 200
    assert 'Wrong email or password' in Browser(app).post('/login', email='dario@example.com',
                                                          password='evil-password').get_data(as_text=True)
    # Neither the password nor the token is stored or logged.
    for path in (app.config['USERS_FILE'], app.config['LOG_FILE']):
        content = open(path, encoding='utf-8').read()
        assert token not in content and 'dario-password' not in content, path
    assert 'pw-anna' not in open(app.config['USERS_FILE'], encoding='utf-8').read()
    assert 'Password set with a link: user=\'dario@example.com\'' in open(app.config['LOG_FILE'],
                                                                         encoding='utf-8').read()


def test_expired_link_is_refused(app):
    anna = Browser(app, 'anna')
    token = invite(anna, 'dario@example.com', 'Dario')
    path = app.config['USERS_FILE']
    with open(path, encoding='utf-8') as file:
        data = json.load(file)
    [record] = [record for record in data['users'] if record['email'] == 'dario@example.com']
    record['link']['expires'] = time.time() - 1
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file)
    dario = Browser(app)
    assert 'This link has expired' in dario.text('/set-password?token=' + token)
    reply = dario.post('/set-password', token=token, password='dario-password', confirm='dario-password')
    assert 'This link has expired' in reply.get_data(as_text=True)
    assert app.config['USER_STORE'].load()['dario@example.com'].password is None
    assert 'link expired' in anna.text('/admin')


def test_new_password_logs_out_other_sessions(app):
    bruno_phone = Browser(app, 'bruno')
    assert bruno_phone.get('/').status_code == 200
    anna = Browser(app, 'anna')
    assert anna.post('/admin/users/link', email='bruno@example.com').status_code == 302
    token = link_token(anna.text('/admin'))
    assert bruno_phone.get('/').status_code == 200          # a new link alone changes nothing
    assert Browser(app, 'bruno').get('/').status_code == 200   # the old password still works until the link is used
    bruno_laptop = Browser(app)
    assert set_password_with_link(bruno_laptop, token, 'new-bruno-password').status_code == 302
    assert bruno_laptop.get('/').status_code == 200
    assert bruno_phone.get('/').status_code == 302            # logged out
    assert 'from before a password change' in open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert Browser(app).post('/login', email='bruno@example.com', password='pw-bruno').status_code == 200
    assert Browser(app, 'bruno', 'new-bruno-password').get('/').status_code == 200


def test_admin_manages_users(app):
    anna = Browser(app, 'anna')
    invite(anna, 'dario@example.com', 'Dario')
    # Email and name must be valid and unique (ignoring case).
    for email, name, error in [('DARIO@example.com', 'Someone', 'already a user'),
                               ('elena@example.com', 'dario', 'already taken'),
                               ('not-an-email', 'Elena', 'not a valid email'),
                               ('elena@example.com', '', 'must be 1 to 30'),
                               ('elena@example.com', 'x' * 31, 'must be 1 to 30')]:
        anna.post('/admin/users/add', email=email, name=name)
        assert error in anna.text('/admin'), (email, name)
    assert sorted(app.config['USER_STORE'].load()) == ['anna@example.com', 'bruno@example.com',
                                                       'carla@example.com', 'dario@example.com']
    # Admin rights.
    anna.post('/admin/users/admin', email='dario@example.com', admin='yes')
    assert app.config['USER_STORE'].load()['dario@example.com'].is_admin
    anna.post('/admin/users/admin', email='dario@example.com', admin='')
    assert not app.config['USER_STORE'].load()['dario@example.com'].is_admin
    anna.post('/admin/users/admin', email='anna@example.com', admin='')
    assert 'cannot change your own admin rights' in anna.text('/admin')
    assert app.config['USER_STORE'].load()['anna@example.com'].is_admin
    # Deleting needs confirmation, and is not possible for yourself.
    anna.post('/admin/users/delete', email='anna@example.com', confirm='yes')
    assert 'cannot delete yourself' in anna.text('/admin')
    anna.post('/admin/users/delete', email='bruno@example.com')
    assert 'bruno@example.com' in app.config['USER_STORE'].load()
    bruno = Browser(app, 'bruno')
    anna.post('/admin/users/delete', email='bruno@example.com', confirm='yes')
    assert 'bruno@example.com' not in app.config['USER_STORE'].load()
    assert bruno.get('/').status_code == 302                  # deleted users are logged out
    assert 'anna@example.com' in app.config['USER_STORE'].load()


def test_only_admins_can_manage_users(app):
    bruno = Browser(app, 'bruno')
    for path, form in [('/admin/users/add', {'email': 'evil@example.com', 'name': 'Evil'}),
                       ('/admin/users/link', {'email': 'anna@example.com'}),
                       ('/admin/users/admin', {'email': 'bruno@example.com', 'admin': 'yes'}),
                       ('/admin/users/delete', {'email': 'anna@example.com', 'confirm': 'yes'})]:
        assert bruno.post(path, **form).status_code == 403, path
    users = app.config['USER_STORE'].load()
    assert sorted(users) == ['anna@example.com', 'bruno@example.com', 'carla@example.com']
    assert not users['bruno@example.com'].is_admin and users['anna@example.com'].link is None


def test_game_page_shows_names_not_emails(app):
    anna = start_game(app)
    page = Browser(app, 'bruno').text('/')
    assert '<td>France</td><td>Anna</td>' in page and '<td>Germany</td><td>Bruno</td>' in page
    assert 'anna@example.com' not in page and 'carla@example.com' not in page
    assert 'anna@example.com' not in Browser(app, 'bruno').text('/history')
    assert 'anna@example.com' in anna.text('/admin')


def test_login_required_and_wrong_password(app):
    anonymous = Browser(app)
    assert anonymous.get('/').status_code == 302
    assert anonymous.get('/history').status_code == 302
    assert anonymous.get('/admin').status_code == 302
    response = anonymous.post('/login', email='anna@example.com', password='bad-guess-123')
    assert response.status_code == 200 and 'Wrong email or password' in response.get_data(as_text=True)
    assert anonymous.get('/').status_code == 302
    # Passwords never reach the log.
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert 'pw-anna' not in log and 'bad-guess-123' not in log and 'reason=wrong password' in log


def test_post_without_csrf_token_is_rejected(app):
    client = app.test_client()
    client.get('/login')
    assert client.post('/login', data={'email': 'anna@example.com', 'password': 'pw-anna'}).status_code == 400


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
    assert 'id="order-dialog"' in page and 'name="order_PAR" data-power="france"' in page   # click-a-unit dialog
    carla = Browser(app, 'carla')
    carla_page = carla.text('/')
    assert 'Your orders' not in carla_page and 'id="order-dialog"' not in carla_page   # spectator


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


def test_autosave_never_marks_ready_and_changes_take_ready_back(app):
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    map_before = map_of(anna.text('/'))

    def autosave(browser, **orders):
        response = browser.post('/orders', phase='S1901M', autosave='yes', ready='yes', **orders)
        assert response.status_code == 200
        return response.get_json()

    # Choosing the default for every unit changes nothing: France is not even "submitted".
    reply = autosave(anna, order_PAR='', order_BRE='', order_MAR='')
    assert reply['ok'] and not reply['ready'] and not reply['unready']
    assert 'FRANCE' not in read_game_file(app)['meta']['submitted']
    # A real choice is saved and drawn on her map at once, but not marked ready even if the form says so.
    reply = autosave(anna, order_PAR='A PAR - BUR')
    assert reply['ok'] and not reply['ready']
    assert reply['svg'] != map_before[len('<div class="card map">'):] and '<svg' in reply['svg']
    assert 'orders submitted, not ready' in reply['status'] and 'not marked ready' in reply['summary']
    data = read_game_file(app)
    assert data['game']['powers']['FRANCE']['orders'] == {'A PAR': '- BUR'}
    assert data['meta']['ready'] == {'FRANCE': False}
    # "I'm done" is a normal submit; autosaving the same orders again keeps it...
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    reply = autosave(anna, order_PAR='A PAR - BUR')
    assert reply['ready'] and not reply['unready'] and 'You are marked ready' in reply['summary']
    # ...changing an order takes it back.
    reply = autosave(anna, order_PAR='A PAR - PIC')
    assert not reply['ready'] and reply['unready']
    assert read_game_file(app)['meta']['ready'] == {'FRANCE': False}
    # The last player's autosaves never get the phase processed, even when everybody else is ready.
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - PIC', ready='yes')
    autosave(bruno, order_MUN='A MUN - BUR')
    data = read_game_file(app)
    assert data['game']['phase'] == 'SPRING 1901 MOVEMENT' and data['meta']['ready'] == {'FRANCE': True,
                                                                                         'GERMANY': False}
    bruno.post('/orders', phase='S1901M', order_MUN='A MUN - BUR', ready='yes')
    assert read_game_file(app)['game']['phase'] == 'FALL 1901 MOVEMENT'
    # An autosave from the old phase's page is refused and the page told to reload, where the error is shown.
    assert autosave(anna, order_PAR='A PAR - PIC') == {'ok': False, 'reload': True}
    assert 'NOT recorded' in anna.text('/')


def test_autosave_errors_are_reported_in_the_reply(app):
    anna = start_game(app)
    reply = anna.post('/orders', phase='S1901M', autosave='yes', order_PAR='A PAR - MOS').get_json()
    assert reply['ok'] is False and 'is not a valid order' in reply['errors'][0]
    reply = anna.post('/orders', phase='S1901M', autosave='yes', order_BER='A BER - KIE').get_json()
    assert reply == {'ok': False, 'errors': ['You cannot give orders for BER.']}
    assert read_game_file(app)['game']['powers']['FRANCE']['orders'] == {}
    page = anna.text('/')
    assert 'is not a valid order' not in page and 'You cannot give' not in page      # not flashed again later
    assert 'id="done-button"' in page and 'name="ready"' in page        # JS button, and the no-JS checkbox


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


def test_sea_provinces_are_in_italics(app):
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    assert '<strong>F BRE</strong>' in anna.text('/')
    anna.post('/orders', phase='S1901M', order_BRE='F BRE - MAO', ready='yes')
    bruno.post('/orders', phase='S1901M', ready='yes')
    page = anna.text('/')
    assert '<strong>F <span class="sea">MAO</span></strong>' in page             # orders form
    assert 'F BRE - <span class="sea">MAO</span>' in page                        # last phase's orders
    assert 'F BRE - <span class="sea">MAO</span>' in bruno.text('/history/S1901M')
    assert re.search(r'<text class="sealabel"[^>]*>MAO<', map_of(page))           # map label
    assert re.search(r'<text class="labeltext18"[^>]*>BRE<', map_of(page))


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
    write_users(tmp_path, 'boss:pw-boss:-:admin\n')
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
    assert {'email': 'bruno@example.com', 'name': 'Bruno', 'powers': ['GERMANY'], 'admin': False,
            'has_password': True, 'link': 'none', 'link_expires': None} in info['users']
    text = response.get_data(as_text=True)
    assert 'pw-anna' not in text and 'A PAR - BUR' not in text and 'pbkdf2' not in text


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
    write_users(tmp_path, users)
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


def test_admin_assigns_powers_to_random_users(tmp_path, monkeypatch):
    users = 'boss:pw-boss:-:admin\n' + ''.join('p%d:pw-p%d:-\n' % (i, i) for i in range(1, 5))
    app = make_app(tmp_path, monkeypatch, users)
    store = app.config['USER_STORE']
    candidates = ['p%d@example.com' % i for i in range(1, 5)]
    boss = Browser(app, 'boss')
    boss.post('/admin/assign', players='3', candidates=candidates, random_select='yes', random_powers='yes')
    loaded = store.load()
    groups = sorted(sorted(user.powers) for user in loaded.values() if user.powers)
    assert groups == [['AUSTRIA', 'ENGLAND', 'GERMANY'], ['FRANCE', 'TURKEY'], ['ITALY', 'RUSSIA']]
    assert loaded['boss@example.com'].is_admin and loaded['boss@example.com'].powers == ()
    assert all(user.password for user in loaded.values())                  # passwords and admin flags kept
    # Not enough candidates, and a game in progress needs confirmation.
    assert 'users available' in (boss.post('/admin/assign', players='4', candidates=candidates[:1]) and
                                 boss.text('/admin'))
    boss.post('/admin/new-game', confirm='yes', players='3')
    before = (tmp_path / 'users.json').read_text()
    boss.post('/admin/assign', players='2', candidates=candidates[:2])
    assert (tmp_path / 'users.json').read_text() == before
    boss.post('/admin/assign', players='2', candidates=candidates[:2], confirm='yes', random_powers='yes')
    assert sum(1 for user in store.load().values() if user.powers) == 2


def test_plan_assignment_without_randomness():
    from webapp import gameplay
    assert gameplay.plan_assignment(['a', 'b', 'c', 'd'], 3, random_select=False, random_powers=False) == {
        'a': ['ENGLAND', 'GERMANY', 'AUSTRIA'], 'b': ['RUSSIA', 'ITALY'], 'c': ['FRANCE', 'TURKEY']}


def test_profile_needs_login(app):
    anonymous = Browser(app)
    for response in (anonymous.get('/profile'), anonymous.post('/profile/name', name='Evil'),
                     anonymous.post('/profile/password', current='x', password='new-password', confirm='new-password')):
        assert response.status_code == 302 and response.headers['Location'].endswith('/login')


def test_user_changes_their_name(app):
    start_game(app)
    bruno = Browser(app, 'bruno')
    page = bruno.text('/profile')
    assert 'bruno@example.com' in page and 'value="Bruno"' in page
    assert 'href="/profile"' in bruno.text('/')
    bruno.post('/profile/name', name='  Il Kaiser  ')
    assert 'Name changed to Il Kaiser' in bruno.text('/profile')
    assert app.config['USER_STORE'].load()['bruno@example.com'].name == 'Il Kaiser'
    assert '<td>Germany</td><td>Il Kaiser</td>' in Browser(app, 'anna').text('/')
    # Taken (in any capitalization), empty or too long names are refused.
    for name, error in [('ANNA', 'already taken'), ('', 'must be 1 to 30'), ('x' * 31, 'must be 1 to 30')]:
        bruno.post('/profile/name', name=name)
        assert error in bruno.text('/profile'), name
    assert app.config['USER_STORE'].load()['bruno@example.com'].name == 'Il Kaiser'
    # Changing only the capitalization of your own name is fine.
    bruno.post('/profile/name', name='IL KAISER')
    assert app.config['USER_STORE'].load()['bruno@example.com'].name == 'IL KAISER'
    assert "User 'bruno@example.com' changed their name: 'Il Kaiser' -> 'IL KAISER'" in open(
        app.config['LOG_FILE'], encoding='utf-8').read()


def test_user_changes_their_password(app):
    store = app.config['USER_STORE']
    bruno, bruno_phone = Browser(app, 'bruno'), Browser(app, 'bruno')
    before = store.load()['bruno@example.com'].password
    # Wrong current password, too short or mismatched new one: refused, nothing changes.
    bruno.post('/profile/password', current='bad-guess-123', password='brand-new-pass', confirm='brand-new-pass')
    assert 'the current password is wrong' in bruno.text('/profile')
    bruno.post('/profile/password', current='pw-bruno', password='short', confirm='short')
    assert 'must be 8 to 200 characters' in bruno.text('/profile')
    bruno.post('/profile/password', current='pw-bruno', password='brand-new-pass', confirm='other-new-pass')
    assert 'The two passwords differ' in bruno.text('/profile')
    assert store.load()['bruno@example.com'].password == before
    assert bruno_phone.get('/').status_code == 200
    # Success: this session stays, the other one is logged out, only the new password works.
    bruno.post('/profile/password', current='pw-bruno', password='brand-new-pass', confirm='brand-new-pass')
    assert 'Password changed' in bruno.text('/profile')
    assert bruno.get('/').status_code == 200
    assert bruno_phone.get('/').status_code == 302
    assert 'Wrong email or password' in Browser(app).post('/login', email='bruno@example.com',
                                                          password='pw-bruno').get_data(as_text=True)
    assert Browser(app, 'bruno', 'brand-new-pass').get('/').status_code == 200
    for path in (app.config['USERS_FILE'], app.config['LOG_FILE']):
        content = open(path, encoding='utf-8').read()
        assert 'brand-new-pass' not in content and 'bad-guess-123' not in content, path
