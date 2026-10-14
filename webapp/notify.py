""" Push notifications to players' devices: the subscription store and delivery to users.

    ``subscriptions.json`` in the data dir lists the browsers (phones, computers) where a user enabled
    notifications: ``{"subscriptions": [{"user", "endpoint", "keys", "created_at", "agent", "last_ok",
    "last_error"}]}``. It has its own lock, separate from the game's, so delivering notifications never holds up
    the game. Endpoints are secret capability URLs: logs and /debug/info only show `webpush.describe_endpoint()`.

    The VAPID key is ``vapid_private.pem`` in the data dir. Deleting it invalidates every subscription.
"""
import contextlib
import fcntl
import hashlib
import json
import logging
import os
import time

from webapp import webpush

LOGGER = logging.getLogger(__name__)

MAX_DEVICES_PER_USER = 10       # oldest subscriptions beyond this are dropped (stale browsers pile up otherwise)


def device_id(endpoint):
    """ Short stable id of a subscription, for forms and logs (the endpoint itself is secret). """
    return hashlib.sha256(endpoint.encode()).hexdigest()[:16]


class SubscriptionStore:
    """ Reads and writes subscriptions.json. Every method takes the lock and re-reads the file. """

    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, 'subscriptions.json')
        self.lock_path = os.path.join(data_dir, 'subscriptions.lock')

    @contextlib.contextmanager
    def _locked(self):
        with open(self.lock_path, 'w', encoding='utf-8') as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def _read(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, encoding='utf-8') as file:
                return json.load(file)['subscriptions']
        except (OSError, ValueError, KeyError):
            LOGGER.exception('Cannot read %s: treating it as empty (players must enable notifications again)',
                             self.path)
            return []

    def _write(self, subscriptions):
        temp = self.path + '.tmp'
        with open(temp, 'w', encoding='utf-8') as file:
            json.dump({'subscriptions': subscriptions}, file, indent=1)
        os.chmod(temp, 0o600)
        os.replace(temp, self.path)

    def all(self):
        """ Every subscription (dicts, see module doc). """
        with self._locked():
            return self._read()

    def for_users(self, names):
        """ Subscriptions of the given users. """
        names = set(names)
        return [entry for entry in self.all() if entry['user'] in names]

    def add(self, user, subscription, agent, now):
        """ Records a browser subscription for `user`. The same endpoint registered earlier (possibly by another
            user logged in on the same device) is replaced. :return: True if the endpoint is new. """
        endpoint = subscription['endpoint']
        with self._locked():
            entries = self._read()
            previous = [entry for entry in entries if entry['endpoint'] == endpoint]
            entries = [entry for entry in entries if entry['endpoint'] != endpoint]
            entries.append({'user': user, 'endpoint': endpoint, 'keys': subscription['keys'],
                            'created_at': previous[0]['created_at'] if previous else now, 'agent': agent[:200],
                            'last_ok': previous[0].get('last_ok') if previous else None, 'last_error': None})
            mine = [entry for entry in entries if entry['user'] == user]
            dropped = mine[:-MAX_DEVICES_PER_USER]
            entries = [entry for entry in entries if entry not in dropped]
            self._write(entries)
        if previous and previous[0]['user'] != user:
            LOGGER.info('Push subscription %s moved from user %r to %r', webpush.describe_endpoint(endpoint),
                        previous[0]['user'], user)
        for entry in dropped:
            LOGGER.info('Dropped oldest push subscription %s of %r (more than %d devices)',
                        webpush.describe_endpoint(entry['endpoint']), user, MAX_DEVICES_PER_USER)
        return not previous

    def remove(self, user, device):
        """ Forgets the subscription of `user` with this device id. :return: True if one was removed. """
        with self._locked():
            entries = self._read()
            kept = [entry for entry in entries if not (entry['user'] == user and device_id(entry['endpoint']) == device)]
            if len(kept) != len(entries):
                self._write(kept)
        return len(kept) != len(entries)

    def record(self, results, now):
        """ Stores delivery outcomes ({endpoint: SendResult}) and forgets subscriptions the push service says no
            longer exist. :return: endpoints removed. """
        with self._locked():
            entries = self._read()
            gone = [entry['endpoint'] for entry in entries
                    if entry['endpoint'] in results and results[entry['endpoint']].gone]
            for entry in entries:
                result = results.get(entry['endpoint'])
                if result and result.ok:
                    entry['last_ok'], entry['last_error'] = now, None
                elif result:
                    entry['last_error'] = {'at': now, 'status': result.status, 'detail': result.detail[:200]}
            self._write([entry for entry in entries if entry['endpoint'] not in gone])
        return gone

    def summary(self):
        """ Subscriptions without endpoints or keys, for /debug/info: {user: [device descriptions]}. """
        result = {}
        for entry in self.all():
            result.setdefault(entry['user'], []).append(describe_device(entry))
        return result


def describe_device(entry):
    """ What a user (or /debug/info) may see of a subscription. """
    return {'id': device_id(entry['endpoint']), 'service': webpush.describe_endpoint(entry['endpoint']),
            'agent': entry.get('agent', ''), 'created_at': entry.get('created_at'), 'last_ok': entry.get('last_ok'),
            'last_error': entry.get('last_error')}


class Notifier:
    """ Sends notifications to users on every device where they enabled them. """

    def __init__(self, data_dir, contact=None):
        self.store = SubscriptionStore(data_dir)
        self.vapid_key = webpush.VapidKey.load_or_create(os.path.join(data_dir, 'vapid_private.pem'))
        self.contact = contact          # VAPID subject (mailto:...); defaults to the site URL, see `send`
        self.opener = None              # tests replace urlopen with a fake push service

    @property
    def public_key(self):
        return self.vapid_key.public_key

    def send(self, users, data, site_url, topic=None, ttl=webpush.DEFAULT_TTL):
        """ Delivers `data` ({"title", "body", "url", "tag"}, read by the service worker) to every device of
            `users`. Never raises: failures are logged and recorded on the subscription.

            :param site_url: the site's root URL; the VAPID subject if no contact address is configured.
            :return: {email: [SendResult]}
        """
        started, now = time.perf_counter(), time.time()
        subject = self.contact or site_url
        entries = self.store.for_users(users)
        results, by_user = {}, {user: [] for user in users}
        for entry in entries:
            try:
                kwargs = {'opener': self.opener} if self.opener else {}
                result = webpush.send(entry, data, self.vapid_key, subject, ttl=ttl, topic=topic, **kwargs)
            except Exception as exc:    # pylint: disable=broad-except
                LOGGER.exception('Push to %s of %r failed', webpush.describe_endpoint(entry['endpoint']),
                                 entry['user'])
                result = webpush.SendResult(None, repr(exc))
            results[entry['endpoint']] = result
            by_user[entry['user']].append(result)
        gone = self.store.record(results, now) if results else []
        LOGGER.info('Notification %r (topic=%s) to %s: %d devices, %d delivered, %d gone (removed: %s), '
                    'users without devices: %s, in %.0f ms', data.get('title'), topic, sorted(users), len(entries),
                    sum(result.ok for result in results.values()), len(gone),
                    [webpush.describe_endpoint(endpoint) for endpoint in gone],
                    sorted(user for user, user_results in by_user.items() if not user_results),
                    (time.perf_counter() - started) * 1000)
        return by_user
