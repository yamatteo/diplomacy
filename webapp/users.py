""" Players' accounts, kept by the app in ``users.json`` in the data dir (managed from the admin page, not by hand).

    One account per email address: ``{"users": [{"email", "name", "powers", "admin", "password",
    "session_version", "link", "created_at"}]}``.

    - ``email`` is the account's id: stored lowercase, unique, never changed. Sessions, push subscriptions and
      logs refer to users by it.
    - ``name`` is the display name shown to the other players (unique ignoring case).
    - ``powers`` the powers the user plays (several for games with fewer than 7 players, none for a spectator).
    - ``password`` is a PBKDF2 hash (``pbkdf2_sha256$iterations$salt$hash``), or null until the user sets one.
    - ``session_version`` goes up on every password change: sessions made before it are logged out.
    - ``link`` is the pending set-password link, ``{"hash": sha256(token), "expires"}``, or null. The admin
      issues it (for new users and forgotten passwords) and sends it to the user; it works once, for
      `LINK_DAYS` days. Only its hash is stored, so the file never holds a usable token or password.

    The file is re-read on every request; changes run under an exclusive lock (``users.lock``) and are written
    atomically, readable by the owner only.
"""
import base64
import contextlib
import fcntl
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from collections import namedtuple

LOGGER = logging.getLogger(__name__)

User = namedtuple('User', 'email name powers is_admin password session_version link')

PBKDF2_ITERATIONS = 600_000         # about 0.2 s per login; the count is stored in each hash, so it can change
LINK_DAYS = 7
MAX_NAME_LENGTH = 30
MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH = 8, 200
EMAIL_RE = re.compile(r'^[^@\s:]+@[^@\s]+\.[^@\s]+$')


# ----------------------------------------------------------------------------------------------------------------
# Passwords and link tokens
# ----------------------------------------------------------------------------------------------------------------
def _b64(data):
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def _unb64(text):
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def hash_password(password, iterations=None):
    """ Returns the PBKDF2-SHA256 hash string of `password`, with a random salt. """
    iterations = iterations or PBKDF2_ITERATIONS
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return 'pbkdf2_sha256$%d$%s$%s' % (iterations, _b64(salt), _b64(digest))


def verify_password(password, stored):
    """ True if `password` matches the hash string `stored`. A malformed hash never matches. """
    try:
        scheme, iterations, salt, digest = stored.split('$')
        if scheme != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), _unb64(salt), int(iterations))
        return hmac.compare_digest(actual, _unb64(digest))
    except (AttributeError, ValueError):
        return False


def token_hash(token):
    """ What is stored of a set-password link token. """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def password_problem(password, confirm):
    """ Why a new password is not acceptable, or None. """
    if password != confirm:
        return 'The two passwords differ.'
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        return 'The password must be %d to %d characters long.' % (MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH)
    return None


def normalize_email(email):
    """ Emails are compared and stored lowercase, without surrounding spaces. """
    return (email or '').strip().lower()


def check_login(users, email, password):
    """ Returns the User if the credentials match, else None. Unknown emails and users without a password still
        compute a hash, so timing doesn't reveal which emails exist. """
    user = users.get(normalize_email(email))
    if user and user.password:
        return user if verify_password(password, user.password) else None
    hash_password(password)
    return None


def login_failure_reason(users, email):
    """ Why a login failed, for the log only (the user always gets the same message). """
    user = users.get(normalize_email(email))
    if not user:
        return 'unknown email'
    return 'wrong password' if user.password else 'no password set yet'


# ----------------------------------------------------------------------------------------------------------------
# The users file
# ----------------------------------------------------------------------------------------------------------------
def _to_user(record):
    link = record.get('link')
    return User(email=record['email'], name=record['name'], powers=tuple(record.get('powers') or ()),
                is_admin=bool(record.get('admin')), password=record.get('password'),
                session_version=int(record.get('session_version') or 0),
                link=dict(link) if link else None)


def link_state(user, now):
    """ 'none', 'pending' or 'expired'. """
    if not user.link:
        return 'none'
    return 'pending' if user.link['expires'] > now else 'expired'


class UserStore:
    """ Loads and changes ``users.json``. Every change raises ValueError (with a message for the admin) if it is
        not allowed, and is logged by the caller. """

    def __init__(self, path):
        self.path = path
        self.lock_path = os.path.splitext(path)[0] + '.lock'

    def exists(self):
        return os.path.exists(self.path)

    def _read(self):
        """ The raw records (empty if there is no file yet). """
        if not self.exists():
            return []
        with open(self.path, encoding='utf-8') as file:
            data = json.load(file)
        return list(data.get('users', []))

    def _write(self, records):
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        temp = self.path + '.tmp'
        with open(temp, 'w', encoding='utf-8') as file:
            json.dump({'users': records}, file, indent=1)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, self.path)

    @contextlib.contextmanager
    def _editing(self):
        """ Yields the raw records under the lock and writes them back if the block succeeds. """
        os.makedirs(os.path.dirname(self.lock_path) or '.', exist_ok=True)
        with open(self.lock_path, 'w', encoding='utf-8') as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                records = self._read()
                yield records
                self._write(records)
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    @staticmethod
    def _find(records, email):
        email = normalize_email(email)
        for record in records:
            if record.get('email') == email:
                return record
        raise ValueError('There is no user %s.' % email)

    def load(self):
        """ Parses the users file. Bad records are skipped and logged (without passwords or link hashes).

            :return: dict of email -> User, in file order.
        """
        try:
            records = self._read()
        except (OSError, ValueError) as exc:
            LOGGER.error('Cannot read users file %s: %r', self.path, exc)
            return {}
        users, powers = {}, {}
        for number, record in enumerate(records, start=1):
            try:
                user = _to_user(record)
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                LOGGER.warning('users file record %d ignored: %r', number, exc)
                continue
            if user.email in users:
                LOGGER.warning('users file record %d ignored: duplicate email %r', number, user.email)
                continue
            user_powers = []
            for power in user.powers:
                if power in powers:
                    LOGGER.warning('users file record %d: power %s already assigned to %r; %r does not get it',
                                   number, power, powers[power], user.email)
                    continue
                powers[power] = user.email
                user_powers.append(power)
            users[user.email] = user._replace(powers=tuple(user_powers))
        if records and not any(user.is_admin for user in users.values()):
            LOGGER.warning('users file %s has no admin: nobody can start a game', self.path)
        return users

    def create(self, email, name, is_admin=False, powers=(), password=None, now=None):
        """ Adds a user (without a password unless given: send them a link). :return: the new User. """
        email, name = normalize_email(email), (name or '').strip()
        if not EMAIL_RE.match(email):
            raise ValueError('%r is not a valid email address.' % email)
        name_problem = self.name_problem(name)
        if name_problem:
            raise ValueError(name_problem)
        with self._editing() as records:
            if any(record.get('email') == email for record in records):
                raise ValueError('There is already a user %s.' % email)
            if any(record.get('name', '').lower() == name.lower() for record in records):
                raise ValueError('The name %r is already taken.' % name)
            record = {'email': email, 'name': name, 'powers': list(powers), 'admin': bool(is_admin),
                      'password': hash_password(password) if password else None, 'session_version': 0,
                      'link': None, 'created_at': now or time.time()}
            records.append(record)
        return _to_user(record)

    @staticmethod
    def name_problem(name):
        """ Why `name` cannot be a display name (uniqueness aside), or None. """
        if not 1 <= len(name) <= MAX_NAME_LENGTH:
            return 'The name must be 1 to %d characters long.' % MAX_NAME_LENGTH
        if any(ord(char) < 32 or ord(char) == 127 for char in name):
            return 'The name cannot contain control characters.'
        return None

    def delete(self, email):
        """ Removes a user. :return: the removed User. """
        with self._editing() as records:
            record = self._find(records, email)
            records.remove(record)
        return _to_user(record)

    def set_name(self, email, name):
        """ Changes a user's display name (same rules as at creation; changing only its capitalization is fine).
            :return: the updated User. """
        name = (name or '').strip()
        name_problem = self.name_problem(name)
        if name_problem:
            raise ValueError(name_problem)
        with self._editing() as records:
            record = self._find(records, email)
            if any(other is not record and other.get('name', '').lower() == name.lower() for other in records):
                raise ValueError('The name %r is already taken.' % name)
            record['name'] = name
        return _to_user(record)

    def set_admin(self, email, is_admin):
        """ Grants or revokes admin rights. :return: the User. """
        with self._editing() as records:
            record = self._find(records, email)
            record['admin'] = bool(is_admin)
        return _to_user(record)

    def issue_link(self, email, now):
        """ Makes a new set-password link for the user, replacing any previous one; the current password keeps
            working until the link is used. :return: (token, expires); only the token's hash is stored. """
        token = secrets.token_urlsafe(32)
        expires = now + LINK_DAYS * 86400
        with self._editing() as records:
            record = self._find(records, email)
            record['link'] = {'hash': token_hash(token), 'expires': expires}
        return token, expires

    def find_link(self, token, now):
        """ The user a set-password link token belongs to. :return: (User, None) or (None/User, problem) where
            problem is 'unknown' or 'expired'. """
        wanted = token_hash(token or '')
        for user in self.load().values():
            if user.link and hmac.compare_digest(user.link['hash'], wanted):
                return (user, None) if user.link['expires'] > now else (user, 'expired')
        return None, 'unknown'

    def redeem_link(self, token, password, now):
        """ Sets the password of the link's user, consumes the link and invalidates the user's sessions.
            :return: the updated User, or None if the link is unknown or expired. """
        wanted = token_hash(token or '')
        with self._editing() as records:
            for record in records:
                link = record.get('link')
                if link and hmac.compare_digest(link['hash'], wanted) and link['expires'] > now:
                    record['password'] = hash_password(password)
                    record['link'] = None
                    record['session_version'] = int(record.get('session_version') or 0) + 1
                    return _to_user(record)
        return None

    def set_password(self, email, password):
        """ Sets a user's password directly and invalidates their sessions. :return: the User. """
        with self._editing() as records:
            record = self._find(records, email)
            record['password'] = hash_password(password)
            record['session_version'] = int(record.get('session_version') or 0) + 1
        return _to_user(record)

    def assign_powers(self, assignment):
        """ Users in `assignment` ({email: [powers]}) get those powers, all other users none.
            :return: number of users whose powers changed. """
        changed = 0
        with self._editing() as records:
            for record in records:
                new = list(assignment.get(record.get('email'), []))
                if new != list(record.get('powers') or []):
                    changed += 1
                record['powers'] = new
        return changed


def users_summary(users, now=None):
    """ Users without password or link hashes, for logs and /debug/info. """
    now = now or time.time()
    return [{'email': user.email, 'name': user.name, 'powers': list(user.powers), 'admin': user.is_admin,
             'has_password': bool(user.password), 'link': link_state(user, now),
             'link_expires': user.link['expires'] if user.link else None} for user in users.values()]
