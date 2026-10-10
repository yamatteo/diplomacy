""" Push notifications through the web app: subscribing, test notifications, removing devices, diagnostics. """
import json

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
