""" Players, read from a plain text file (`users.txt` in the data dir).

    One user per line: ``username:password:POWERS`` or ``username:password:POWERS:admin``.
    POWERS is the power the user plays (e.g. FRANCE), several separated by commas (FRANCE,AUSTRIA: one player
    controlling more countries, for games with fewer than 7 players), or ``-`` for none (spectator / admin only).
    Lines starting with # are comments. Passwords are plain text and cannot contain ':'.
    The file is re-read on every request, so edits apply immediately.
"""
import hmac
import logging
import os
import secrets
from collections import namedtuple

LOGGER = logging.getLogger(__name__)

User = namedtuple('User', 'name password powers is_admin')

HEADER = """# Diplomacy users. One per line:   username:password:POWERS[:admin]
# POWERS is one or more (comma separated) of AUSTRIA ENGLAND FRANCE GERMANY ITALY RUSSIA TURKEY, or - for none.
# In games with fewer than 7 players give several powers to one user, e.g. FRANCE,AUSTRIA.
# Add :admin to let a user start games, force processing and change deadlines.
# Passwords are plain text and cannot contain ':'. Changes apply immediately (no reload needed).
# Example:
#   anna:correct-horse:FRANCE
#   marco:tin-roof-sun:GERMANY,TURKEY
#   piero:battery-staple:-:admin
"""


def ensure_users_file(path):
    """ Creates the users file with a single admin (random password) if it does not exist. """
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        file.write(HEADER + 'admin:%s:-:admin\n' % secrets.token_urlsafe(9))
    os.chmod(path, 0o600)
    LOGGER.warning('No users file found: created %s with a single user "admin" and a random password. '
                   'Open that file to read the password and add players.', path)


def load_users(path):
    """ Parses the users file. Bad lines are skipped and logged (without their content: it holds a password).

        :return: dict of username -> User
    """
    users = {}
    powers = {}
    try:
        with open(path, encoding='utf-8') as file:
            lines = file.read().splitlines()
    except OSError as exc:
        LOGGER.error('Cannot read users file %s: %r', path, exc)
        return users
    for number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        fields = [field.strip() for field in line.split(':')]
        if len(fields) not in (3, 4) or not fields[0] or not fields[1]:
            LOGGER.warning('users file line %d ignored: expected username:password:POWERS[:admin], got %d fields',
                           number, len(fields))
            continue
        if len(fields) == 4 and fields[3].lower() != 'admin':
            LOGGER.warning('users file line %d ignored (user %r): 4th field must be "admin"', number, fields[0])
            continue
        name = fields[0]
        if name in users:
            LOGGER.warning('users file line %d ignored: duplicate username %r', number, name)
            continue
        user_powers = []
        for power in (item.strip().upper() for item in fields[2].split(',')):
            if power in ('-', '') or power in user_powers:
                continue
            if power in powers:
                LOGGER.warning('users file line %d: power %s already assigned to %r; %r does not get it',
                               number, power, powers[power], name)
                continue
            powers[power] = name
            user_powers.append(power)
        users[name] = User(name=name, password=fields[1], powers=tuple(user_powers), is_admin=len(fields) == 4)
    if not any(user.is_admin for user in users.values()):
        LOGGER.warning('users file %s has no admin: nobody can start a game', path)
    return users


def check_login(users, name, password):
    """ Returns the User if the credentials match, else None. """
    user = users.get(name)
    # Compare against a dummy value for unknown users so timing doesn't reveal which names exist.
    expected = user.password if user else secrets.token_urlsafe(9)
    if hmac.compare_digest(password.encode('utf-8'), expected.encode('utf-8')) and user:
        return user
    return None


def users_summary(users):
    """ Users without passwords, for logs and /debug/info. """
    return [{'name': user.name, 'powers': list(user.powers), 'admin': user.is_admin} for user in users.values()]
