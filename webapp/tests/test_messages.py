""" Messages between powers: privacy, unread counts, limits, push notifications and logging. """
import json

from webapp.tests.test_app import (Browser, app_fixture, read_game_file,  # pylint: disable=unused-import
                                     start_game, write_users)
from webapp.tests.test_notifications import payloads, subscribe_all
from webapp.tests.test_webpush import FakePushService

SECRET = 'Secret plan: Marseilles attacks at dawn'


def setup_game(app, extra='dora:pw-dora:ENGLAND\nenzo:pw-enzo:ITALY,RUSSIA'):
    """ Starts a game; anna=FRANCE, bruno=GERMANY, dora=ENGLAND, enzo=ITALY+RUSSIA, carla plays nothing. """
    write_users(app.config['DATA_DIR'], extra)
    return start_game(app)


def send(browser, to, text, as_power=None, **extra):
    form = dict(text=text, **extra)
    if as_power:
        form['as'] = as_power
    return browser.post('/messages/' + to, **form)


def test_private_message_is_seen_only_by_its_two_sides(app):
    setup_game(app)
    anna, bruno, dora = (Browser(app, name) for name in ('anna', 'bruno', 'dora'))
    reply = send(anna, 'GERMANY', SECRET)
    assert reply.status_code == 302 and reply.headers['Location'].endswith('/messages/GERMANY?as=FRANCE')
    assert SECRET in anna.text('/messages/GERMANY')
    assert SECRET in bruno.text('/messages/FRANCE')
    for path in ('/', '/messages', '/messages/FRANCE', '/messages/GERMANY', '/messages/GLOBAL', '/history'):
        assert SECRET not in dora.text(path), path
    assert dora.get('/messages/FRANCE').status_code == 200
    assert SECRET not in dora.text('/messages/FRANCE')
    for path in ('/', '/messages', '/history'):
        assert SECRET not in anna.text(path) and SECRET not in bruno.text(path)
    info = app.test_client().get('/debug/info?token=debug-secret').get_data(as_text=True)
    assert SECRET not in info and '"messages"' in info
    assert json.loads(info)['game']['messages'] == {'current': 1, 'total': 1}
    assert SECRET not in open(app.config['LOG_FILE'], encoding='utf-8').read()


def test_global_message_is_visible_to_all_players(app):
    setup_game(app)
    Browser(app, 'anna').post('/messages/GLOBAL', text='Hello world')
    for name in ('anna', 'bruno', 'dora', 'enzo'):
        assert 'Hello world' in Browser(app, name).text('/messages/GLOBAL'), name
    assert 'Hello world' not in Browser(app, 'bruno').text('/messages/FRANCE')       # not in the private thread
    assert 'You do not play a power' in Browser(app, 'carla').text('/messages')
    assert Browser(app, 'carla').get('/messages/GLOBAL').status_code == 404


def test_messages_survive_phase_processing_and_game_over(app):
    anna = setup_game(app)
    send(anna, 'GERMANY', SECRET)
    anna.post('/admin/process')
    assert 'Fall 1901' in anna.text('/')
    assert SECRET in Browser(app, 'bruno').text('/messages/FRANCE')
    assert SECRET not in anna.text('/history') and SECRET not in anna.text('/history/S1901M')
    send(Browser(app, 'bruno'), 'FRANCE', 'second')
    assert 'second' in anna.text('/messages/GERMANY')
    stored = read_game_file(app)['game']
    assert len(stored['message_history']['S1901M']) == 1 and len(stored['messages']) == 1
    anna.post('/admin/draw', confirm='yes')
    assert send(anna, 'GERMANY', 'after the end').status_code == 302
    assert 'after the end' in Browser(app, 'bruno').text('/messages/FRANCE')
    info = app.test_client().get('/debug/info?token=debug-secret').get_json()
    assert info['game']['messages']['total'] == 3


def test_unread_counts(app):
    anna = setup_game(app)
    bruno = Browser(app, 'bruno')
    send(anna, 'GERMANY', 'one')
    send(anna, 'GERMANY', 'two')
    send(anna, 'GLOBAL', 'all')
    assert 'Messages (3)' not in anna.text('/')                  # own messages are not unread
    page = bruno.text('/messages')
    assert 'Messages (3)' in page and '<strong>2</strong>' in page and '<strong>1</strong>' in page
    assert 'Messages (3)' in bruno.text('/')
    page = bruno.text('/messages/FRANCE')                          # opening clears that conversation
    assert 'Messages (1)' in page
    assert 'Messages (1)' in bruno.text('/') and 'Messages (3)' not in bruno.text('/')
    bruno.text('/messages/GLOBAL')
    assert 'Messages (' not in bruno.text('/')
    send(anna, 'GERMANY', 'three')
    assert 'Messages (1)' in bruno.text('/')
    assert read_game_file(app)['meta']['read']['bruno@example.com']['GERMANY:FRANCE']
    # Not loading the game, a page shows the plain link.
    assert 'Messages (' not in bruno.text('/notifications') and '>Messages<' in bruno.text('/notifications')


def test_global_unread_counts_once_for_a_user_with_two_powers(app):
    setup_game(app)
    anna, enzo = Browser(app, 'anna'), Browser(app, 'enzo')
    send(anna, 'GLOBAL', 'all')
    assert 'Messages (1)' in enzo.text('/') and 'Messages (2)' not in enzo.text('/')
    enzo.text('/messages/GLOBAL?as=RUSSIA')
    assert 'Messages (' not in enzo.text('/')
    for power in ('ITALY', 'RUSSIA'):
        assert '<strong>1</strong>' not in enzo.text('/messages?as=' + power)
    assert read_game_file(app)['meta']['read']['enzo@example.com']['GLOBAL']
    send(anna, 'ITALY', 'to italy')
    send(anna, 'RUSSIA', 'to russia')
    assert 'Messages (2)' in enzo.text('/')
    enzo.text('/messages/FRANCE?as=ITALY')
    assert 'Messages (1)' in enzo.text('/')


def test_refused_messages(app):
    anna = setup_game(app)
    base = len(read_game_file(app)['game']['messages'])
    assert send(anna, 'GERMANY', '   ').status_code == 400
    assert send(anna, 'GERMANY', 'x' * 2001).status_code == 400
    assert send(anna, 'FRANCE', 'to myself').status_code == 302       # own power: refused with a flash
    assert send(anna, 'AUSTRIA', 'nobody there').status_code == 302   # no player
    assert send(anna, 'NARNIA', 'nowhere').status_code == 302
    assert send(anna, 'GERMANY', 'as another', as_power='GERMANY').status_code == 302
    assert send(Browser(app, 'carla'), 'GERMANY', 'no power').status_code == 302
    client = Browser(app, 'anna')
    assert client.client.post('/messages/GERMANY', data={'text': 'no csrf'}).status_code == 400
    assert len(read_game_file(app)['game']['messages']) == base
    assert send(anna, 'GERMANY', 'x' * 2000).status_code == 302
    assert 'x' * 100 in anna.text('/messages/GERMANY')
    assert anna.get('/messages/FRANCE').status_code == 404
    assert anna.get('/messages?as=GERMANY').status_code == 404
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert 'Refused message from FRANCE' in log and 'empty message' in log and 'nobody there' not in log


def test_push_notifications(app):
    service = FakePushService()
    app.config['NOTIFIER'].opener = service
    anna = setup_game(app)
    keys = subscribe_all(app, 'anna', 'bruno', 'dora')
    # dora's device wants turns only; a second device of bruno wants messages only.
    dora_device = app.config['NOTIFIER'].store.summary()['dora@example.com'][0]['id']
    Browser(app, 'dora').post('/notifications/channels', device=dora_device, channels='turns')
    service.requests.clear()
    send(anna, 'GERMANY', SECRET)
    received = payloads(service, keys)
    assert [url for url, _ in received] == ['https://fcm.googleapis.com/fcm/send/bruno']
    note = received[0][1]
    assert note['title'] == 'Message from France' and note['body'] == 'To Germany.'
    assert note['url'] == '/messages/FRANCE?as=GERMANY' and note['tag'] == 'msg-FRANCE-GERMANY'
    assert SECRET not in json.dumps(note) and service.requests[0].get_header('Topic') == 'msg-FRANCE-GERMANY'
    service.requests.clear()
    send(anna, 'GLOBAL', 'everyone listen')
    received = payloads(service, keys)
    assert [url[-5:] for url, _ in received] == ['bruno']             # dora: turns only; anna: the sender
    assert received[0][1]['body'] == 'To everyone.' and received[0][1]['url'] == '/messages/GLOBAL?as=GERMANY'


def test_push_in_the_recipients_language(app):
    service = FakePushService()
    app.config['NOTIFIER'].opener = service
    anna = setup_game(app)
    keys = subscribe_all(app, 'bruno')
    bruno = Browser(app, 'bruno')
    bruno.post('/profile/lang', lang='it')
    service.requests.clear()
    send(anna, 'GERMANY', SECRET)
    note = payloads(service, keys)[0][1]
    assert note['title'] == 'Messaggio da Francia' and note['body'] == 'A Germania.'
    assert 'Messaggi' in bruno.text('/')


def test_user_with_two_powers_writes_as_either(app):
    anna = setup_game(app)
    enzo = Browser(app, 'enzo')
    page = enzo.text('/messages')
    assert 'Messages of:' in page and 'Russia' in page
    assert send(enzo, 'FRANCE', 'from italy').status_code == 302            # default: the first power
    assert send(enzo, 'FRANCE', 'from russia', as_power='RUSSIA').status_code == 302
    assert send(enzo, 'ITALY', 'to myself', as_power='RUSSIA').status_code == 302   # own power: refused
    thread = anna.text('/messages/ITALY') + anna.text('/messages/RUSSIA')
    assert 'from italy' in anna.text('/messages/ITALY') and 'from russia' in anna.text('/messages/RUSSIA')
    assert 'to myself' not in thread
    assert 'from russia' in enzo.text('/messages/FRANCE?as=RUSSIA')
    assert 'from russia' not in enzo.text('/messages/FRANCE?as=ITALY')


def test_message_log_line_has_no_text(app):
    anna = setup_game(app)
    send(anna, 'GERMANY', SECRET)
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert "Message sent: from=FRANCE by='anna@example.com' to=GERMANY phase=S1901M length=%d" % len(SECRET) in log
    assert SECRET not in log and 'Secret' not in log
