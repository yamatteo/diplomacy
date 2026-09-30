""" Flask web app for a single Diplomacy game among friends, sized for the PythonAnywhere free tier.

    Configuration comes from environment variables (set them in the PythonAnywhere WSGI file):

    - DIPLOMACY_DATA_DIR: folder for logs and game data (default: <repo>/instance).
    - DIPLOMACY_DEBUG_TOKEN: enables the /debug/* endpoints; pass it as ?token=... or X-Debug-Token header.
    - DIPLOMACY_LOG_LEVEL: root log level (default: DEBUG).
    - DIPLOMACY_TIMEZONE: time zone used to display deadlines (default: Europe/Rome).

    Files in the data dir: users.txt (players, see webapp/users.py), game.json (+ backups/, archive/),
    secret_key (signs session cookies), logs/app.log.
"""
import hmac
import logging
import logging.handlers
import os
import secrets
import sys
import time
import traceback
import uuid
from collections import deque
from datetime import timedelta
from zoneinfo import ZoneInfo

from flask import Flask, abort, g, jsonify, request

from webapp.diagnostics import REPO_DIR, environment_info
from webapp.store import GameStore
from webapp.users import ensure_users_file, load_users, users_summary

LOGGER = logging.getLogger('webapp')
LOG_FORMAT = '%(asctime)s %(levelname)s [pid %(process)d] [%(request_id)s] %(name)s: %(message)s'


class RequestIdFilter(logging.Filter):
    """ Stamps every log record with the current request id ('-' outside requests),
        so all lines of one failing request can be grepped together. """
    def filter(self, record):
        try:
            record.request_id = g.get('request_id', '-')
        except RuntimeError:  # outside application context
            record.request_id = '-'
        return True


def setup_logging(log_file, level):
    """ Logs to a rotating file in the data dir (readable via /debug/logs) and to stderr
        (which PythonAnywhere writes to the web app's error log). """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5,
                                                        encoding='utf-8')
    stream_handler = logging.StreamHandler(sys.stderr)
    root = logging.getLogger()
    # create_app() may run more than once per process (tests, reloads): don't stack handlers.
    for handler in list(root.handlers):
        if getattr(handler, '_webapp', False):
            root.removeHandler(handler)
    for handler in (file_handler, stream_handler):
        handler._webapp = True  # pylint: disable=protected-access
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        root.addHandler(handler)
    root.setLevel(level)


def tail(path, lines):
    """ Returns the last `lines` lines of a text file. """
    with open(path, encoding='utf-8', errors='replace') as file:
        return ''.join(deque(file, maxlen=lines))


def load_secret_key(path):
    """ Returns the key signing session cookies, creating it on first run. Deleting the file logs everyone out. """
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as file:
            file.write(secrets.token_hex(32))
        os.chmod(path, 0o600)
        LOGGER.info('Created session secret key file %s', path)
    with open(path, encoding='utf-8') as file:
        return file.read().strip()


def game_diagnostics(app):
    """ Users and game state for /debug/info. Never raises: a broken game file is exactly when this is needed. """
    from webapp import gameplay     # pylint: disable=import-outside-toplevel
    result = {}
    try:
        users = load_users(app.config['USERS_FILE'])
        result['users'] = users_summary(users)
        store = app.config['GAME_STORE']
        result['game_file'] = {'path': store.path, 'exists': store.exists(),
                               'size_bytes': os.path.getsize(store.path) if store.exists() else 0,
                               'backups': sorted(os.listdir(store.backup_dir))[-10:]
                                          if os.path.isdir(store.backup_dir) else []}
        game, meta = store.load()
        result['game'] = gameplay.game_summary(game, meta, users) if game else None
    except Exception:   # pylint: disable=broad-except
        result['error'] = traceback.format_exc()
    return result


def create_app():
    """ Application factory (used by the WSGI file and by `flask --app webapp run`). """
    started = time.time()
    data_dir = os.path.abspath(os.environ.get('DIPLOMACY_DATA_DIR') or os.path.join(REPO_DIR, 'instance'))
    config = {
        'DATA_DIR': data_dir,
        'LOG_FILE': os.path.join(data_dir, 'logs', 'app.log'),
        'DEBUG_TOKEN': os.environ.get('DIPLOMACY_DEBUG_TOKEN', ''),
        'USERS_FILE': os.path.join(data_dir, 'users.txt'),
        'TIMEZONE': os.environ.get('DIPLOMACY_TIMEZONE', 'Europe/Rome'),
    }
    setup_logging(config['LOG_FILE'], os.environ.get('DIPLOMACY_LOG_LEVEL', 'DEBUG').upper())

    try:
        ZoneInfo(config['TIMEZONE'])
    except Exception:   # pylint: disable=broad-except
        LOGGER.error('Unknown DIPLOMACY_TIMEZONE %r: falling back to UTC', config['TIMEZONE'])
        config['TIMEZONE'] = 'UTC'

    app = Flask(__name__)
    app.config.update(config)
    app.config['GAME_STORE'] = GameStore(data_dir)
    app.secret_key = load_secret_key(os.path.join(data_dir, 'secret_key'))
    app.config.update(PERMANENT_SESSION_LIFETIME=timedelta(days=90), SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_HTTPONLY=True)
    ensure_users_file(config['USERS_FILE'])

    info = environment_info(config)
    LOGGER.info('=== App starting ===')
    for key, value in info.items():
        LOGGER.info('startup %s = %r', key, value)
    if not config['DEBUG_TOKEN']:
        LOGGER.warning('DIPLOMACY_DEBUG_TOKEN is not set: /debug/* endpoints are disabled')
    if not info['in_virtualenv']:
        LOGGER.warning('Not running inside a virtualenv: check the virtualenv path on the Web tab')
    for key, value in game_diagnostics(app).items():
        LOGGER.info('startup %s = %r', key, value)

    @app.before_request
    def start_request():
        g.request_id = uuid.uuid4().hex[:8]
        g.start_time = time.perf_counter()
        # PythonAnywhere's proxy puts the client address in X-Real-IP.
        g.client_ip = request.headers.get('X-Real-IP', request.remote_addr)

    @app.after_request
    def log_request(response):
        duration_ms = (time.perf_counter() - g.start_time) * 1000
        # Never log the debug token itself.
        args = {key: ('***' if key == 'token' else value) for key, value in request.args.items()}
        LOGGER.info('%s %s %s -> %s in %.1f ms (ip=%s, ua=%r)', request.method, request.path, args or '',
                    response.status_code, duration_ms, g.client_ip, request.headers.get('User-Agent', ''))
        response.headers['X-Request-ID'] = g.request_id
        return response

    @app.errorhandler(Exception)
    def handle_exception(exc):
        if hasattr(exc, 'code') and hasattr(exc, 'get_response'):  # HTTPException: 404, 403, ...
            return exc
        LOGGER.error('Unhandled exception on %s %s:\n%s', request.method, request.path, traceback.format_exc())
        request_id = g.get('request_id', '-')
        return ('Internal error. Report this request id to the admin: %s\n' % request_id, 500,
                {'Content-Type': 'text/plain; charset=utf-8', 'X-Request-ID': request_id})

    def require_debug_token():
        expected = app.config['DEBUG_TOKEN']
        given = request.args.get('token') or request.headers.get('X-Debug-Token', '')
        if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
            LOGGER.warning('Rejected debug access to %s from %s', request.path, g.client_ip)
            abort(404)

    @app.route('/healthz')
    def healthz():
        return jsonify(status='ok', commit=info['git']['commit'], uptime_s=round(time.time() - started))

    @app.route('/debug/info')
    def debug_info():
        require_debug_token()
        return jsonify(dict(environment_info(app.config), uptime_s=round(time.time() - started),
                            **game_diagnostics(app)))

    @app.route('/debug/logs')
    def debug_logs():
        require_debug_token()
        lines = min(request.args.get('lines', 200, type=int), 5000)
        return tail(app.config['LOG_FILE'], lines), 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route('/debug/error')
    def debug_error():
        """ Deliberately fails, to check that tracebacks reach the logs. """
        require_debug_token()
        raise RuntimeError('Deliberate test error from /debug/error')

    from webapp import views    # pylint: disable=import-outside-toplevel
    app.register_blueprint(views.bp)

    LOGGER.info('=== App ready in %.2f s ===', time.time() - started)
    return app
