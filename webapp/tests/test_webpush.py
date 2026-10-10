""" Web Push sender, checked against an independent implementation (http_ece) and a fake push service. """
import io
import json
import urllib.error

import http_ece
import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from webapp import webpush


def browser_subscription(endpoint='https://fcm.googleapis.com/fcm/send/abc123'):
    """ What a browser would create: its own key pair and auth secret. Returns (subscription, private key, auth). """
    private_key = ec.generate_private_key(ec.SECP256R1())
    public = private_key.public_key().public_bytes(serialization.Encoding.X962,
                                                   serialization.PublicFormat.UncompressedPoint)
    auth = b'0123456789abcdef'
    subscription = {'endpoint': endpoint, 'keys': {'p256dh': webpush.b64url(public), 'auth': webpush.b64url(auth)}}
    return subscription, private_key, auth


def test_encrypted_payload_decrypts_with_http_ece():
    subscription, private_key, auth = browser_subscription()
    body = webpush.encrypt(subscription, b'{"title": "Spring 1901"}')
    assert http_ece.decrypt(body, private_key=private_key, auth_secret=auth,
                            version='aes128gcm') == b'{"title": "Spring 1901"}'
    with pytest.raises(ValueError):
        webpush.encrypt(subscription, b'x' * (webpush.MAX_PAYLOAD_BYTES + 1))


def test_vapid_key_is_created_once_and_signs_valid_jwts(tmp_path):
    path = str(tmp_path / 'vapid.pem')
    key = webpush.VapidKey.load_or_create(path)
    assert webpush.VapidKey.load_or_create(path).public_key == key.public_key
    assert len(webpush.b64url_decode(key.public_key)) == 65
    header = key.authorization('https://fcm.googleapis.com/fcm/send/abc', 'mailto:admin@example.com', 1000)
    token, public = header[len('vapid t='):].split(', k=')
    assert public == key.public_key
    head, claims, signature = token.split('.')
    assert json.loads(webpush.b64url_decode(head)) == {'typ': 'JWT', 'alg': 'ES256'}
    assert json.loads(webpush.b64url_decode(claims)) == {'aud': 'https://fcm.googleapis.com',
                                                         'exp': 1000 + 12 * 3600, 'sub': 'mailto:admin@example.com'}
    raw = webpush.b64url_decode(signature)
    der = encode_dss_signature(int.from_bytes(raw[:32], 'big'), int.from_bytes(raw[32:], 'big'))
    verifier = key.private_key.public_key()
    verifier.verify(der, ('%s.%s' % (head, claims)).encode(), ec.ECDSA(hashes.SHA256()))
    with pytest.raises(InvalidSignature):
        verifier.verify(der, ('%s.%sx' % (head, claims)).encode(), ec.ECDSA(hashes.SHA256()))


def test_check_subscription():
    subscription, _, _ = browser_subscription()
    assert webpush.check_subscription(subscription) is None
    for endpoint in ('https://web.push.apple.com/QGx', 'https://updates.push.services.mozilla.com/wpush/v2/x',
                     'https://wns2-par02p.notify.windows.com/w/?token=x'):
        assert webpush.check_subscription(dict(subscription, endpoint=endpoint)) is None
    assert 'unknown push service' in webpush.check_subscription(dict(subscription, endpoint='https://evil.com/x'))
    assert 'unknown push service' in webpush.check_subscription(
        dict(subscription, endpoint='https://fcm.googleapis.com.evil.com/x'))
    assert 'https' in webpush.check_subscription(dict(subscription, endpoint='http://fcm.googleapis.com/x'))
    assert 'p256dh' in webpush.check_subscription(dict(subscription, keys={'p256dh': 'AAAA', 'auth': 'x'}))
    assert webpush.check_subscription('nope') == 'subscription is not an object'


class FakePushService:
    """ Stands in for urlopen: records requests, answers with `status`. """

    def __init__(self, status=201):
        self.status = status
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        if isinstance(self.status, Exception):
            raise self.status
        if self.status >= 400:
            raise urllib.error.HTTPError(request.full_url, self.status, 'Gone', {}, io.BytesIO(b'expired'))
        response = io.BytesIO(b'')
        response.status = self.status
        return response


def test_send_delivers_encrypted_json_and_reports_gone_subscriptions(tmp_path, caplog):
    key = webpush.VapidKey.load_or_create(str(tmp_path / 'vapid.pem'))
    subscription, private_key, auth = browser_subscription()
    service = FakePushService()
    result = webpush.send(subscription, {'title': 'Hi'}, key, 'https://example.com/', topic='phase', opener=service)
    assert result.ok and not result.gone
    request = service.requests[0]
    assert request.full_url == subscription['endpoint'] and request.get_method() == 'POST'
    assert request.get_header('Content-encoding') == 'aes128gcm' and request.get_header('Topic') == 'phase'
    assert request.get_header('Authorization').startswith('vapid t=')
    assert json.loads(http_ece.decrypt(request.data, private_key=private_key, auth_secret=auth,
                                       version='aes128gcm')) == {'title': 'Hi'}
    assert subscription['endpoint'] not in caplog.text          # capability URL: never logged
    assert webpush.describe_endpoint(subscription['endpoint']) in caplog.text

    gone = webpush.send(subscription, {}, key, 'https://example.com/', opener=FakePushService(410))
    assert gone.gone and not gone.ok and gone.detail == 'expired'
    unreachable = webpush.send(subscription, {}, key, 'https://example.com/',
                               opener=FakePushService(urllib.error.URLError('Tunnel connection failed: 403')))
    assert unreachable.status is None and not unreachable.gone and '403' in unreachable.detail
