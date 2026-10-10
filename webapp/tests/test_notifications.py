""" Push notifications through the web app: subscribing, test notifications, removing devices, diagnostics. """
import json
import time

import http_ece

from webapp.tests.test_app import Browser, app_fixture  # pylint: disable=unused-import
from webapp.tests.test_webpush import FakePushService, browser_subscription


def subscribe(browser, subscription):
    return browser.post('/notifications/subscribe', subscription=json.dumps(subscription))


def test_service_worker_manifest_and_icons_are_public(app):
    client = app.test_client()
    worker = client.get('/sw.js')
    assert worker.status_code == 200 and 'javascript' in worker.content_type
    assert "addEventListener('push'" in worker.get_data(as_text=True)
    manifest = client.get('/manifest.webmanifest')
    assert manifest.content_type == 'application/manifest+json'
    assert manifest.get_json()['display'] == 'standalone'
    for icon in manifest.get_json()['icons']:
        assert client.get(icon['src']).status_code == 200
    assert client.get('/notifications').status_code == 302           # the page itself needs a login


def test_subscribe_send_test_and_remove_device(app):
    service = FakePushService()
    app.config['NOTIFIER'].opener = service
    bruno = Browser(app, 'bruno')
    page = bruno.text('/notifications')
    assert app.config['NOTIFIER'].public_key in page and 'None yet' in page

    subscription, private_key, auth = browser_subscription()
    reply = subscribe(bruno, subscription)
    assert reply.status_code == 200 and reply.get_json()['new']
    assert not subscribe(bruno, subscription).get_json()['new']     # refreshing does not duplicate it
    assert len(app.config['NOTIFIER'].store.all()) == 1
    page = bruno.text('/notifications')
    assert 'fcm.googleapis.com' in page and subscription['endpoint'] not in page

    bruno.post('/notifications/test')
    assert 'Test notification sent to 1 device' in bruno.text('/notifications')
    payload = json.loads(http_ece.decrypt(service.requests[0].data, private_key=private_key, auth_secret=auth,
                                          version='aes128gcm'))
    assert payload['title'] == 'Diplomacy' and payload['url'] == '/notifications'
    assert app.config['NOTIFIER'].store.all()[0]['last_ok']

    # Another user cannot remove bruno's device; bruno can.
    device = app.config['NOTIFIER'].store.summary()['bruno'][0]['id']
    anna = Browser(app, 'anna')
    anna.post('/notifications/remove', device=device)
    assert len(app.config['NOTIFIER'].store.all()) == 1
    bruno.post('/notifications/remove', device=device)
    assert app.config['NOTIFIER'].store.all() == []
    assert 'enabled notifications on any device' in (bruno.post('/notifications/test') and
                                                     bruno.text('/notifications'))


def test_expired_devices_are_forgotten_and_bad_subscriptions_rejected(app):
    app.config['NOTIFIER'].opener = FakePushService(410)
    bruno = Browser(app, 'bruno')
    subscription, _, _ = browser_subscription()
    subscribe(bruno, subscription)
    bruno.post('/notifications/test')
    assert '1 of 1 device(s) failed (410)' in bruno.text('/notifications')
    assert app.config['NOTIFIER'].store.all() == []

    evil, _, _ = browser_subscription('https://attacker.example.com/collect')
    reply = subscribe(bruno, evil)
    assert reply.status_code == 400 and 'unknown push service' in reply.get_json()['error']
    assert subscribe(bruno, 'not json').status_code == 400
    # The page's script removes the device of this browser by endpoint.
    subscribe(bruno, subscription)
    assert bruno.post('/notifications/remove', endpoint=subscription['endpoint']).get_json() == {
        'ok': True, 'removed': True}


def test_same_browser_moves_to_the_user_logged_in(app):
    subscription, _, _ = browser_subscription()
    subscribe(Browser(app, 'bruno'), subscription)
    subscribe(Browser(app, 'anna'), subscription)
    assert [entry['user'] for entry in app.config['NOTIFIER'].store.all()] == ['anna']


def test_debug_info_shows_devices_without_endpoints(app):
    subscription, _, _ = browser_subscription()
    subscribe(Browser(app, 'bruno'), subscription)
    info = app.test_client().get('/debug/info?token=debug-secret').get_json()
    assert info['push']['enabled'] and info['push']['devices']['bruno'][0]['service'].startswith('fcm.googleapis.com#')
    text = json.dumps(info)
    assert subscription['endpoint'] not in text and subscription['keys']['auth'] not in text
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert subscription['endpoint'] not in log


def payloads(service, keys):
    """ Decrypted notifications received by the fake push service, as (endpoint, data). """
    return [(request.full_url, json.loads(http_ece.decrypt(request.data, private_key=keys[request.full_url][0],
                                                           auth_secret=keys[request.full_url][1],
                                                           version='aes128gcm')))
            for request in service.requests]


def subscribe_all(app, *names):
    """ Subscribes one device for each user. :return: {endpoint: (private key, auth)} """
    keys = {}
    for name in names:
        subscription, private_key, auth = browser_subscription('https://fcm.googleapis.com/fcm/send/' + name)
        subscribe(Browser(app, name), subscription)
        keys[subscription['endpoint']] = (private_key, auth)
    return keys


def test_players_are_notified_when_a_new_phase_starts(app):
    service = FakePushService()
    app.config['NOTIFIER'].opener = service
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes')
    keys = subscribe_all(app, 'anna', 'bruno', 'carla')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    assert service.requests == []
    Browser(app, 'bruno').post('/orders', phase='S1901M', order_MUN='A MUN - BUR', ready='yes')   # processes
    received = dict(payloads(service, keys))
    assert sorted(received) == ['https://fcm.googleapis.com/fcm/send/anna', 'https://fcm.googleapis.com/fcm/send/bruno']
    anna_note = received['https://fcm.googleapis.com/fcm/send/anna']
    assert anna_note['title'] == 'Diplomacy: Fall 1901, Movement' and anna_note['tag'] == 'phase'
    assert anna_note['body'].startswith('Orders needed for France. Deadline: ')
    assert received['https://fcm.googleapis.com/fcm/send/bruno']['body'].startswith('Orders needed for Germany.')
    assert all(request.get_header('Topic') == 'phase' for request in service.requests)
    assert 47 * 3600 < int(service.requests[0].get_header('Ttl')) <= 48 * 3600
    assert 'A PAR' not in json.dumps(list(received.values()))       # never any orders


def test_game_over_is_notified_to_all_players(app):
    service = FakePushService()
    app.config['NOTIFIER'].opener = service
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes')
    keys = subscribe_all(app, 'anna', 'bruno')
    anna.post('/admin/draw', confirm='yes')
    notes = [data for _, data in payloads(service, keys)]
    assert len(notes) == 2 and all(note['title'] == 'Diplomacy: the game is over' for note in notes)
    assert notes[0]['body'].startswith('Draw between')


def test_failing_push_service_does_not_break_processing(app):
    app.config['NOTIFIER'].opener = FakePushService(OSError('proxy says no'))
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes')
    subscribe_all(app, 'anna')
    response = anna.post('/admin/process')
    assert response.status_code == 302
    assert 'Fall 1901' in anna.text('/')
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert 'proxy says no' in log and 'Queued new phase notifications for F1901M' in log


def set_deadline(app, seconds_from_now, started_hours_ago=1):
    """ Moves the current phase's deadline (and start) in game.json. """
    path = app.config['DATA_DIR'] + '/game.json'
    with open(path, encoding='utf-8') as file:
        data = json.load(file)
    data['meta']['deadline'] = time.time() + seconds_from_now
    data['meta']['phase_started'] = time.time() - started_hours_ago * 3600
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file)
    return data


def test_due_reminders_once_per_threshold_and_not_for_ready_powers():
    from webapp import gameplay
    from webapp.users import User
    users = {'anna': User('anna', 'x', ('FRANCE',), False), 'bruno': User('bruno', 'x', ('GERMANY',), False),
             'carla': User('carla', 'x', ('ENGLAND',), False)}
    game, meta = gameplay.new_game('anna', 0)
    meta['ready']['ENGLAND'] = True
    meta['submitted']['GERMANY'] = 1
    deadline = meta['deadline']                         # 48 h after the start
    assert gameplay.due_reminders(game, meta, users, deadline - 13 * 3600, (12, 2)) == {}
    first = gameplay.due_reminders(game, meta, users, deadline - 11 * 3600, (12, 2))
    assert first == {'anna': {'hours': 12, 'powers': [('FRANCE', False)]},
                     'bruno': {'hours': 12, 'powers': [('GERMANY', True)]}}
    assert gameplay.due_reminders(game, meta, users, deadline - 10 * 3600, (12, 2)) == {}
    meta['ready']['GERMANY'] = True
    assert gameplay.due_reminders(game, meta, users, deadline - 3600, (12, 2)) == {
        'anna': {'hours': 2, 'powers': [('FRANCE', False)]}}
    assert gameplay.due_reminders(game, meta, users, deadline + 1, (12, 2)) == {}         # processed, not reminded
    # A threshold as long as the phase is skipped: no reminder right after a short phase starts.
    gameplay.start_phase_clock(game, meta, 0)
    meta['deadline'] = 10 * 3600
    assert gameplay.due_reminders(game, meta, users, 60, (12, 2)) == {}
    assert set(gameplay.due_reminders(game, meta, users, 9 * 3600, (12, 2))) == {'anna', 'bruno', 'carla'}


def test_cron_tick_needs_the_token(app):
    assert app.test_client().get('/cron/tick?token=x').status_code == 404           # no token configured
    app.config['CRON_TOKEN'] = 'cron-secret'
    assert app.test_client().get('/cron/tick?token=wrong').status_code == 404
    assert app.test_client().get('/cron/tick?token=cron-secret').get_json() == {'game': None}
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert 'cron-secret' not in log


def test_cron_tick_sends_reminders_and_processes_passed_deadlines(app):
    app.config['CRON_TOKEN'] = 'cron-secret'
    service = FakePushService()
    app.config['NOTIFIER'].opener = service
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes')
    keys = subscribe_all(app, 'anna', 'bruno')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    tick = Browser(app)                                 # the external scheduler: no login
    set_deadline(app, 3600 + 90)
    reply = tick.get('/cron/tick?token=cron-secret').get_json()
    assert reply['phase'] == 'S1901M' and reply['queued_notifications'] == 1
    [(endpoint, note)] = payloads(service, keys)
    assert endpoint.endswith('/bruno')                  # anna is done
    assert note['title'] == 'Diplomacy: 1 h 1 min left for Spring 1901, Movement'
    assert note['body'].startswith('Not done yet: Germany (no orders yet). Deadline: ')
    tick.get('/cron/tick?token=cron-secret')
    assert len(service.requests) == 1                   # not twice
    set_deadline(app, -1)
    assert tick.get('/cron/tick?token=cron-secret').get_json()['phase'] == 'F1901M'
    assert [note['title'] for _, note in payloads(service, keys)[1:]] == ['Diplomacy: Fall 1901, Movement'] * 2
