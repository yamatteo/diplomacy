""" Web Push sender: VAPID keys (RFC 8292), payload encryption (RFC 8291, aes128gcm) and delivery (RFC 8030).

    Written against `cryptography` alone instead of using pywebpush, which drags in aiohttp and friends (disk
    quota on PythonAnywhere). Requests go through urllib, which honours the http(s)_proxy variables that
    PythonAnywhere's free tier sets: the push services of Chrome/Android, Firefox, Safari/iOS and Edge are all on
    its allowlist.

    A browser subscription is ``{"endpoint": url, "keys": {"p256dh": ..., "auth": ...}}`` (what
    ``PushSubscription.toJSON()`` returns). The endpoint is a secret capability URL: log `describe_endpoint()`
    instead of the endpoint itself.
"""
import base64
import hashlib
import json
import logging
import os
import struct
import time
import urllib.error
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

LOGGER = logging.getLogger(__name__)

# Push services we deliver to. Anything else is refused, so a player cannot make the server POST to arbitrary URLs.
PUSH_HOST_SUFFIXES = ('fcm.googleapis.com', 'push.services.mozilla.com', 'push.apple.com', 'notify.windows.com')
RECORD_SIZE = 4096
# Plaintext room in a single aes128gcm record: record size - 16 (GCM tag) - 1 (padding delimiter) - 86 (header).
MAX_PAYLOAD_BYTES = RECORD_SIZE - 16 - 1 - 86
DEFAULT_TTL = 24 * 3600         # how long the push service keeps a message for an offline device (seconds)
TIMEOUT = 10                    # seconds per request to a push service


def b64url(data):
    """ Unpadded base64url, as used throughout Web Push. """
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def b64url_decode(text):
    """ Decodes base64url with or without padding. """
    text = text.strip()
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def describe_endpoint(endpoint):
    """ Loggable stand-in for an endpoint: its host and a short hash ('fcm.googleapis.com#3fa2c1'). """
    host = urllib.parse.urlsplit(endpoint or '').hostname or '?'
    return '%s#%s' % (host, hashlib.sha256((endpoint or '').encode()).hexdigest()[:6])


def check_subscription(subscription):
    """ Validates a subscription from a browser. :return: error message, or None if it is usable. """
    if not isinstance(subscription, dict):
        return 'subscription is not an object'
    endpoint = subscription.get('endpoint')
    parts = urllib.parse.urlsplit(endpoint if isinstance(endpoint, str) else '')
    host = (parts.hostname or '').lower()
    if parts.scheme != 'https' or not host:
        return 'endpoint is not an https URL'
    if not any(host == suffix or host.endswith('.' + suffix) for suffix in PUSH_HOST_SUFFIXES):
        return 'unknown push service %s' % host
    keys = subscription.get('keys')
    if not isinstance(keys, dict):
        return 'missing keys'
    try:
        p256dh, auth = b64url_decode(keys.get('p256dh', '')), b64url_decode(keys.get('auth', ''))
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), p256dh)
    except (ValueError, TypeError, AttributeError):
        return 'invalid p256dh key'
    if len(auth) != 16:
        return 'invalid auth secret'
    return None


# ----------------------------------------------------------------------------------------------------------------
# VAPID: identifies this server to the push services
# ----------------------------------------------------------------------------------------------------------------
class VapidKey:
    """ The server's P-256 key pair. Browsers subscribe with its public key, so replacing it (deleting the file)
        silently invalidates every existing subscription: players then have to enable notifications again. """

    def __init__(self, private_key):
        self.private_key = private_key

    @classmethod
    def load_or_create(cls, path):
        """ Reads the PEM key at `path`, creating it on first run. """
        if not os.path.exists(path):
            key = ec.generate_private_key(ec.SECP256R1())
            pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption())
            temp = path + '.tmp'
            with open(temp, 'wb') as file:
                file.write(pem)
            os.chmod(temp, 0o600)
            os.replace(temp, path)
            LOGGER.warning('Created a new VAPID key %s: any existing push subscriptions stop working', path)
        with open(path, 'rb') as file:
            return cls(serialization.load_pem_private_key(file.read(), password=None))

    @property
    def public_key(self):
        """ The application server key that browsers subscribe with (base64url of the uncompressed point). """
        return b64url(self.private_key.public_key().public_bytes(serialization.Encoding.X962,
                                                                 serialization.PublicFormat.UncompressedPoint))

    def authorization(self, endpoint, subject, now):
        """ The ``Authorization`` header for a request to `endpoint`: a JWT signed with ES256. """
        parts = urllib.parse.urlsplit(endpoint)
        header = b64url(json.dumps({'typ': 'JWT', 'alg': 'ES256'}, separators=(',', ':')).encode())
        claims = b64url(json.dumps({'aud': '%s://%s' % (parts.scheme, parts.netloc), 'exp': int(now) + 12 * 3600,
                                    'sub': subject}, separators=(',', ':')).encode())
        signing_input = ('%s.%s' % (header, claims)).encode('ascii')
        r, s = decode_dss_signature(self.private_key.sign(signing_input, ec.ECDSA(hashes.SHA256())))
        signature = b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))
        return 'vapid t=%s.%s, k=%s' % (signing_input.decode('ascii'), signature, self.public_key)


# ----------------------------------------------------------------------------------------------------------------
# Encryption and delivery
# ----------------------------------------------------------------------------------------------------------------
def _hkdf(salt, info, length, secret):
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(secret)


def encrypt(subscription, payload):
    """ Encrypts `payload` (bytes) for one subscription: the aes128gcm body of a push request (RFC 8291). """
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError('push payload too large: %d bytes (max %d)' % (len(payload), MAX_PAYLOAD_BYTES))
    ua_public = b64url_decode(subscription['keys']['p256dh'])
    auth_secret = b64url_decode(subscription['keys']['auth'])
    ua_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public)
    local_key = ec.generate_private_key(ec.SECP256R1())     # fresh for every message
    as_public = local_key.public_key().public_bytes(serialization.Encoding.X962,
                                                    serialization.PublicFormat.UncompressedPoint)
    ikm = _hkdf(auth_secret, b'WebPush: info\x00' + ua_public + as_public, 32,
                local_key.exchange(ec.ECDH(), ua_key))
    salt = os.urandom(16)
    content_key = _hkdf(salt, b'Content-Encoding: aes128gcm\x00', 16, ikm)
    nonce = _hkdf(salt, b'Content-Encoding: nonce\x00', 12, ikm)
    ciphertext = AESGCM(content_key).encrypt(nonce, payload + b'\x02', None)    # \x02: last record, no padding
    return salt + struct.pack('!IB', RECORD_SIZE, len(as_public)) + as_public + ciphertext


class SendResult:
    """ Outcome of one delivery. `gone` means the subscription no longer exists and should be forgotten. """

    def __init__(self, status, detail=''):
        self.status = status            # HTTP status, or None if the push service could not be reached
        self.detail = detail

    @property
    def ok(self):
        return self.status is not None and 200 <= self.status < 300

    @property
    def gone(self):
        return self.status in (404, 410)

    def __repr__(self):
        return 'SendResult(%s%s)' % (self.status, ', %r' % self.detail if self.detail else '')


def send(subscription, data, vapid_key, subject, ttl=DEFAULT_TTL, topic=None, urgency='normal', now=None,
         opener=urllib.request.urlopen):
    """ Delivers `data` (a JSON-able dict, read by the service worker) to one subscription. Never raises for
        delivery problems: they are returned (and logged) as a SendResult.

        :param subject: VAPID contact, ``mailto:...`` or the site's https URL (push services may use it to warn
            about problems; Apple refuses ``localhost``).
        :param topic: optional label (url-safe, max 32 characters); a newer message with the same topic replaces
            an undelivered older one on the push service.
    """
    endpoint = subscription['endpoint']
    who = describe_endpoint(endpoint)
    body = encrypt(subscription, json.dumps(data, separators=(',', ':')).encode('utf-8'))
    headers = {'Authorization': vapid_key.authorization(endpoint, subject, time.time() if now is None else now),
               'Content-Encoding': 'aes128gcm', 'Content-Type': 'application/octet-stream',
               'TTL': str(int(ttl)), 'Urgency': urgency}
    if topic:
        headers['Topic'] = topic
    request = urllib.request.Request(endpoint, data=body, headers=headers, method='POST')
    started = time.perf_counter()
    try:
        with opener(request, timeout=TIMEOUT) as response:
            result = SendResult(response.status)
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read(300).decode('utf-8', 'replace')
        except Exception:   # pylint: disable=broad-except
            detail = ''
        result = SendResult(exc.code, detail.strip())
    except Exception as exc:    # pylint: disable=broad-except
        # Timeouts, DNS, proxy refusals (403 from PythonAnywhere's proxy shows up as URLError/OSError).
        result = SendResult(None, repr(exc))
    LOGGER.log(logging.INFO if result.ok else logging.WARNING, 'Push to %s (%d bytes, ttl=%s, topic=%s) -> %r in '
               '%.0f ms', who, len(body), ttl, topic, result, (time.perf_counter() - started) * 1000)
    return result
