""" Pages: login, the game (map, status, orders form), history and admin actions.

    Every request that touches the game runs inside `open_game()`: it takes the file lock, loads the game and
    processes the phase if it is due (lazy deadlines), so any page view keeps the game moving.
"""
import contextlib
import functools
import hmac
import json
import logging
import os
import re
import secrets
import time
import urllib.parse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import (Blueprint, Response, abort, current_app, flash, g, jsonify, redirect, render_template, request,
                   send_from_directory, session, url_for)
from markupsafe import Markup

from webapp import gameplay, tutorial
from webapp.users import (LINK_DAYS, check_login, link_state, login_failure_reason, normalize_email,
                          password_problem, verify_password)

LOGGER = logging.getLogger(__name__)
bp = Blueprint('game', __name__)


# ----------------------------------------------------------------------------------------------------------------
# Request plumbing: users, CSRF, game access
# ----------------------------------------------------------------------------------------------------------------
@bp.before_request
def load_user():
    """ Resolves the logged-in user from the users file (so removing a user, or changing their password, logs them
        out) and checks CSRF. """
    g.users = current_app.config['USER_STORE'].load()
    g.user = g.users.get(session.get('user', ''))
    if session.get('user') and not g.user:
        LOGGER.warning('Session for unknown user %r (deleted?): logging out', session.get('user'))
        session.pop('user', None)
        session.pop('session_version', None)
    elif g.user and session.get('session_version') != g.user.session_version:
        LOGGER.warning('Session of %r is from before a password change (session version %r, now %r): logging out',
                       g.user.email, session.get('session_version'), g.user.session_version)
        g.user = None
        session.pop('user', None)
        session.pop('session_version', None)
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(16)
    if request.method == 'POST':
        given = request.form.get('csrf', '')
        if not hmac.compare_digest(given.encode(), session['csrf'].encode()):
            LOGGER.warning('CSRF token mismatch on %s (user=%r, ip=%s)', request.path, session.get('user'),
                           g.get('client_ip'))
            abort(400, 'Form expired or invalid. Go back, reload the page and try again.')


def login_required(view):
    """ Redirects anonymous users to the login page. """
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for('game.login'))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    """ Only lets admins through. """
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for('game.login'))
        if not g.user.is_admin:
            LOGGER.warning('Non-admin %r tried to access %s', g.user.email, request.path)
            abort(403)
        return view(*args, **kwargs)
    return wrapper


@contextlib.contextmanager
def open_game():
    """ Locks and loads the game, processing it first if due. Yields (game, meta, store); game is None if
        there is no game. The caller saves with `store.save(game, meta)` if it changes anything. """
    store = current_app.config['GAME_STORE']
    with store.locked():
        game, meta = store.load()
        if game:
            g.map_name = game.map_name
            announce_processed(game, meta, gameplay.process_if_due(game, meta, g.users, store, time.time()))
            send_due_reminders(game, meta, store, time.time())
        yield game, meta, store


def announce_processed(game, meta, processed):
    """ Tells the user that phases were just processed, and the players by push notification. """
    if processed:
        flash('Processed: %s.' % ', '.join(processed), 'info')
        notify_new_phase(game, meta, processed)


# ----------------------------------------------------------------------------------------------------------------
# Push notifications about the game. They are queued during the request and sent once the response is out (see
# `deliver_notifications`), so they never hold the game lock nor slow down the page.
# ----------------------------------------------------------------------------------------------------------------
MAX_PUSH_TTL = 28 * 86400           # push services keep messages at most about 4 weeks


def queue_notification(users, data, topic=None, ttl=None):
    """ Schedules a push notification to `users` (emails) for after the response. """
    if current_app.config['NOTIFIER'] and users:
        g.setdefault('pending_push', []).append((sorted(users), data, topic, ttl or 7 * 86400))


def notify_new_phase(game, meta, processed):
    """ Tells each player whose powers have orders to give that the current phase started (or everybody that
        the game is over). Called after `processed` phases were processed. """
    now = time.time()
    phase = game.get_current_phase()
    players = gameplay.players_by_power(game, meta, g.users)
    url = url_for('game.index')
    if game.is_game_done:
        outcome = game.outcome[1:] if game.outcome and len(game.outcome) > 1 else []
        body = ('%s: %s.' % ('Winner' if len(outcome) == 1 else 'Draw between', ', '.join(power.title()
                                                                                       for power in outcome))
                if outcome else 'See the final position.')
        queue_notification(set(players.values()), {'title': 'Diplomacy: the game is over', 'body': body,
                                                   'url': url, 'tag': 'phase'}, topic='phase')
        LOGGER.info('Queued game over notification after %s to %s', processed, sorted(set(players.values())))
        return
    by_user = {}
    for power in gameplay.active_powers(game, meta, g.users):
        by_user.setdefault(players[power], []).append(power.title())
    deadline = (' Deadline: %s.' % format_time(meta['deadline'])) if meta['deadline'] else ''
    ttl = min(MAX_PUSH_TTL, max(60, int(meta['deadline'] - now))) if meta['deadline'] else None
    for user, powers in sorted(by_user.items()):
        queue_notification([user], {'title': 'Diplomacy: %s' % phase_title(phase),
                                    'body': 'Orders needed for %s.%s' % (', '.join(powers), deadline),
                                    'url': url, 'tag': 'phase'}, topic='phase', ttl=ttl)
    LOGGER.info('Queued new phase notifications for %s (after %s) to %s', phase, processed, by_user)


def send_due_reminders(game, meta, store, now):
    """ Queues deadline reminders for players who are not done yet (see `gameplay.due_reminders`). """
    if not current_app.config['NOTIFIER'] or game.is_game_done:
        return
    reminders = gameplay.due_reminders(game, meta, g.users, now, current_app.config['REMINDER_HOURS'])
    if not reminders:
        return
    store.save(game, meta)                          # records who was reminded, so it is not sent twice
    left = format_delta(meta['deadline'] - now)
    for user, reminder in sorted(reminders.items()):
        states = ['%s (%s)' % (power.title(), 'orders saved, but not marked done' if submitted else 'no orders yet')
                  for power, submitted in reminder['powers']]
        queue_notification([user], {'title': 'Diplomacy: %s left for %s' % (left, phase_title(meta['phase'])),
                                    'body': 'Not done yet: %s. Deadline: %s.' % ('; '.join(states),
                                                                                format_time(meta['deadline'])),
                                    'url': url_for('game.index'), 'tag': 'phase'},
                           topic='phase', ttl=max(60, int(meta['deadline'] - now)))


@bp.after_app_request
def deliver_notifications(response):
    """ Sends the queued push notifications once the response has been sent to the browser. """
    pending = g.pop('pending_push', None)
    if pending:
        app = current_app._get_current_object()     # pylint: disable=protected-access
        request_id, site_url = g.get('request_id', '-'), push_site_url()

        def deliver():
            with app.app_context():
                g.request_id = request_id           # so these log lines can be matched to the request
                for users, data, topic, ttl in pending:
                    try:
                        app.config['NOTIFIER'].send(users, data, site_url, topic=topic, ttl=ttl)
                    except Exception:   # pylint: disable=broad-except
                        LOGGER.exception('Delivering notification %r to %s failed', data.get('title'), users)
        response.call_on_close(deliver)
    return response


# ----------------------------------------------------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------------------------------------------------
def format_time(timestamp):
    """ Epoch seconds -> 'Thu 01 Oct 2026, 18:00' in the configured time zone. """
    zone = ZoneInfo(current_app.config['TIMEZONE'])
    return datetime.fromtimestamp(timestamp, timezone.utc).astimezone(zone).strftime('%a %d %b %Y, %H:%M')


def format_delta(seconds):
    """ Seconds -> '1 d 3 h', '45 min'. """
    seconds = max(0, int(seconds))
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    if days:
        return '%d d %d h' % (days, hours)
    if hours:
        return '%d h %d min' % (hours, rest // 60)
    return '%d min' % (rest // 60)


@bp.app_template_filter('seas')
def mark_seas(text):
    """ Order text -> HTML with sea provinces in italics ('F <i>NTH</i> - NWY'), as on the map. """
    seas = gameplay.sea_locations(g.get('map_name') or 'standard')
    return Markup(' ').join(Markup('<span class="sea">%s</span>') % word if word in seas else word
                            for word in str(text).split(' '))


def deadline_text(meta, now):
    """ Human description of the current deadline. """
    if not meta['deadline']:
        return 'No deadline: the phase is processed when all players are ready.'
    return '%s (%s), in %s. Processed earlier if all players are ready.' % (
        format_time(meta['deadline']), current_app.config['TIMEZONE'], format_delta(meta['deadline'] - now))


def phase_title(phase):
    """ 'S1901M' -> 'Spring 1901, Movement'. """
    seasons = {'S': 'Spring', 'F': 'Fall', 'W': 'Winter'}
    if len(phase) == 6 and phase[0] in seasons and phase[-1] in gameplay.PHASE_TYPE_NAMES:
        return '%s %s, %s' % (seasons[phase[0]], phase[1:5], gameplay.PHASE_TYPE_NAMES[phase[-1]])
    return phase.title()


# ----------------------------------------------------------------------------------------------------------------
# Login
# ----------------------------------------------------------------------------------------------------------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """ Login form. """
    if request.method == 'POST':
        email = normalize_email(request.form.get('email', ''))
        user = check_login(g.users, email, request.form.get('password', ''))
        if user:
            log_in(user)
            LOGGER.info('Login: user=%r name=%r powers=%s admin=%s ip=%s', user.email, user.name, list(user.powers),
                        user.is_admin, g.client_ip)
            return redirect(url_for('game.index'))
        LOGGER.warning('Failed login: email=%r reason=%s ip=%s', email, login_failure_reason(g.users, email),
                       g.client_ip)
        flash('Wrong email or password.', 'error')
    return render_template('login.html')


def log_in(user):
    """ Starts a fresh session for `user`. """
    session.clear()
    session['user'] = user.email
    session['session_version'] = user.session_version
    session['csrf'] = secrets.token_urlsafe(16)
    session.permanent = True
    g.user = user


@bp.route('/set-password', methods=['GET', 'POST'])
def set_password():
    """ The page a set-password link opens (for new users and forgotten passwords): the user chooses a password
        and is logged in. The link works once, until it expires. The token travels in the query string on GET and
        in a hidden field on POST; it is never logged. """
    now = time.time()
    store = current_app.config['USER_STORE']
    token = request.form.get('token', '') if request.method == 'POST' else request.args.get('token', '')
    user, problem = store.find_link(token, now)
    if problem:
        LOGGER.warning('Set-password link %s (%s, user=%r, ip=%s)', 'expired' if problem == 'expired' else 'invalid',
                       request.method, user.email if user else None, g.client_ip)
        response = Response(render_template('set_password.html', invalid=True, expired=problem == 'expired'))
    elif request.method == 'POST':
        password = request.form.get('password', '')
        error = password_problem(password, request.form.get('confirm', ''))
        if error:
            LOGGER.info('Set-password for %r refused: %s', user.email, error)
            flash(error, 'error')
            response = Response(render_template('set_password.html', user=user, token=token))
        else:
            user = store.redeem_link(token, password, now)
            if not user:                    # expired or used between the check above and now
                LOGGER.warning('Set-password link stopped working while being used (ip=%s)', g.client_ip)
                response = Response(render_template('set_password.html', invalid=True))
            else:
                LOGGER.info('Password set with a link: user=%r session_version=%d (older sessions logged out), '
                            'ip=%s', user.email, user.session_version, g.client_ip)
                log_in(user)
                flash('Password saved. You are logged in.', 'ok')
                response = redirect(url_for('game.index'))
    else:
        response = Response(render_template('set_password.html', user=user, token=token))
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response


@bp.route('/profile')
@login_required
def profile():
    """ The user's own account: change the display name or the password. """
    return render_template('profile.html')


@bp.route('/profile/name', methods=['POST'])
@login_required
def profile_name():
    """ Changes the user's display name. """
    old, new = g.user.name, request.form.get('name', '').strip()
    try:
        current_app.config['USER_STORE'].set_name(g.user.email, new)
    except ValueError as exc:
        LOGGER.info('Name change of %r to %r refused: %s', g.user.email, new, exc)
        flash('Name not changed: %s' % exc, 'error')
        return redirect(url_for('game.profile'))
    LOGGER.info('User %r changed their name: %r -> %r', g.user.email, old, new)
    flash('Name changed to %s.' % new, 'ok')
    return redirect(url_for('game.profile'))


@bp.route('/profile/password', methods=['POST'])
@login_required
def profile_password():
    """ Changes the user's password (the current one is required). Other sessions of the user are logged out;
        this one stays logged in. """
    if not verify_password(request.form.get('current', ''), g.user.password):
        LOGGER.warning('Password change of %r refused: wrong current password (ip=%s)', g.user.email, g.client_ip)
        flash('Password not changed: the current password is wrong.', 'error')
        return redirect(url_for('game.profile'))
    password = request.form.get('password', '')
    error = password_problem(password, request.form.get('confirm', ''))
    if error:
        LOGGER.info('Password change of %r refused: %s', g.user.email, error)
        flash('Password not changed: %s' % error, 'error')
        return redirect(url_for('game.profile'))
    user = current_app.config['USER_STORE'].set_password(g.user.email, password)
    session['session_version'] = user.session_version       # keeps this session; older ones are logged out
    LOGGER.info('User %r changed their password: session_version=%d (other sessions logged out), ip=%s',
                user.email, user.session_version, g.client_ip)
    flash('Password changed. Your other devices have to log in again.', 'ok')
    return redirect(url_for('game.profile'))


@bp.route('/logout', methods=['POST'])
def logout():
    """ Logs out. """
    LOGGER.info('Logout: user=%r', session.get('user'))
    session.clear()
    return redirect(url_for('game.login'))


# ----------------------------------------------------------------------------------------------------------------
# Game
# ----------------------------------------------------------------------------------------------------------------
@bp.route('/')
@login_required
def index():
    """ The game page: map, status of every power, and the orders form for the user's power(s). """
    now = time.time()
    with open_game() as (game, meta, _):
        if not game:
            return render_template('nogame.html')
        my_powers = gameplay.powers_of(game, meta, g.user)
        active = [power for power in my_powers if game.get_orderable_locations(power)] if not game.is_game_done else []
        choices = [{'power': power, 'choices': gameplay.order_choices(game, power)} for power in active]
        history = game.get_phase_history()
        context = dict(
            my_orders_state(game, meta, my_powers),
            phase=game.get_current_phase(),
            phase_title=phase_title(game.get_current_phase()),
            done=game.is_game_done,
            outcome=game.outcome,
            deadline=deadline_text(meta, now),
            my_powers=my_powers,
            choices=choices,
            seas=sorted(gameplay.sea_locations(game.map_name)),
            last_phase=history[-1].name if history else None,
            last_orders=gameplay.phase_orders(game, history[-1]) if history else None,
        )
    return render_template('game.html', **context)


def my_orders_state(game, meta, my_powers):
    """ The parts of the game page that change when the user saves orders: the map with their arrows, the status
        table and whether they are ready / have submitted. """
    active = [power for power in my_powers if game.get_orderable_locations(power)] if not game.is_game_done else []
    return {'svg': Markup(gameplay.render_current(game, orders_of=my_powers)),
            'status': gameplay.power_status(game, meta, g.users),
            'my_ready': bool(active) and all(meta['ready'].get(power) for power in active),
            'my_submitted': any(power in meta['submitted'] for power in active)}


@bp.route('/orders', methods=['POST'])
@login_required
def orders():
    """ Receives the orders form: either submitted (Save orders / I'm done) or autosaved by the game page's script
        each time an order is chosen (`autosave=yes`, answered with JSON). An autosave never marks the user ready,
        so it can never trigger processing, and it takes back "I'm done" if it changes an order. """
    now = time.time()
    autosave = request.form.get('autosave') == 'yes'

    def fail(messages, reload=False):
        """ Reports errors: flashed on the next page, or in the JSON reply for an autosave (reload=True: the page
            is out of date, the script reloads it and the flashed messages are shown there). """
        if autosave and not reload:
            return jsonify(ok=False, errors=messages)
        for message in messages:
            flash(message, 'error')
        return jsonify(ok=False, reload=True) if autosave else redirect(url_for('game.index'))

    with open_game() as (game, meta, store):
        if not game or game.is_game_done:
            return fail(['There is no game in progress.'], reload=True)
        powers = gameplay.powers_of(game, meta, g.user)
        if not powers:
            LOGGER.warning('User %r without a playable power tried to submit orders', g.user.email)
            abort(403)
        phase = game.get_current_phase()
        if request.form.get('phase') != phase:
            # The phase was processed between showing the form and submitting it.
            LOGGER.warning('Stale orders from %s: form phase=%r current phase=%s', powers,
                           request.form.get('phase'), phase)
            return fail(['The game moved on to %s before your orders arrived: they were NOT recorded. '
                         'Please enter orders for the new phase.' % phase], reload=True)
        chosen = {key[len('order_'):]: value.strip() for key, value in request.form.items()
                  if key.startswith('order_')}
        # One form can carry the orders of all the user's powers: split them by the power owning each location.
        by_power = {power: {} for power in powers if game.get_orderable_locations(power)}
        owner = {loc: power for power in by_power for loc in game.get_orderable_locations(power)}
        foreign = [loc for loc, order in chosen.items() if order and loc not in owner]
        if foreign:
            LOGGER.warning('User %r (powers %s) sent orders for locations that are not theirs: %s',
                           g.user.email, powers, foreign)
            return fail(['You cannot give orders for %s.' % ', '.join(sorted(foreign))])
        for loc, order in chosen.items():
            if loc in owner:
                by_power[owner[loc]][loc] = order
        ready = None if autosave else request.form.get('ready') == 'yes'
        was_ready = [power for power in by_power if meta['ready'].get(power)]
        errors = []
        for power, power_chosen in by_power.items():
            errors += gameplay.submit_orders(game, meta, power, power_chosen, ready, now)
        # Powers handled before a failing one were already updated in memory: save what was accepted.
        store.save(game, meta)
        if errors:
            return fail(errors)
        if autosave:
            processed = gameplay.process_if_due(game, meta, g.users, store, now)   # only a passed deadline can
            if processed:
                announce_processed(game, meta, processed)
                return jsonify(ok=True, reload=True)
            state = my_orders_state(game, meta, powers)
            unready = [power for power in was_ready if not meta['ready'].get(power)]
            LOGGER.info('Autosave by %r in %s: ready=%s no longer ready=%s', g.user.email, phase,
                        {power: meta['ready'].get(power, False) for power in by_power}, unready)
            return jsonify(ok=True, ready=state['my_ready'], unready=bool(unready), svg=str(state['svg']),
                           summary=render_template('_orders_summary.html', **state),
                           status=render_template('_status_table.html', **state))
        flash('Orders saved for %s%s.' % (phase, ' and marked ready' if ready else
                                          ' (not marked ready: the phase waits for you until the deadline)'), 'ok')
        announce_processed(game, meta, gameplay.process_if_due(game, meta, g.users, store, now))
    return redirect(url_for('game.index'))


@bp.route('/history')
@bp.route('/history/<phase>')
@login_required
def history(phase=None):
    """ Map and orders of a past phase. """
    with open_game() as (game, _, _):
        if not game:
            return redirect(url_for('game.index'))
        phases = game.get_phase_history()
        if not phases:
            return render_template('history.html', phases=[], phase=None)
        by_name = {phase_data.name: phase_data for phase_data in phases}
        phase = phase or phases[-1].name
        if phase not in by_name:
            abort(404)
        context = {
            'phases': [phase_data.name for phase_data in phases],
            'phase': phase,
            'phase_title': phase_title(phase),
            'svg': Markup(gameplay.render_phase(game, by_name[phase])),
            'orders': gameplay.phase_orders(game, by_name[phase]),
        }
    return render_template('history.html', **context)


# ----------------------------------------------------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------------------------------------------------
@bp.route('/help')
def help_page():
    """ Cheat sheet: rules in brief, worked examples, how to use this site, our province abbreviations.
        Public: it shows nothing about the game in progress. """
    return render_template('help.html', examples=tutorial.examples(), provinces=tutorial.provinces(),
                           phase_hours=gameplay.DEFAULT_PHASE_HOURS)


@bp.route('/help/diagram/<example_id>.svg')
def help_diagram(example_id):
    """ Picture of a worked example. Served separately so browsers cache it (each is ~100 KB). """
    for example in tutorial.examples():
        if example['id'] == example_id:
            return Response(example['svg'], mimetype='image/svg+xml',
                            headers={'Cache-Control': 'public, max-age=86400'})
    abort(404)


@bp.route('/rules.pdf')
@login_required
def rules_pdf():
    """ The official rulebook (4th edition, 2000), shown in the browser. Players only: it is copyrighted. """
    response = send_from_directory(current_app.root_path, 'rules.pdf', mimetype='application/pdf', max_age=86400)
    response.cache_control.public = False
    response.cache_control.private = True       # behind the login: browsers may cache it, shared proxies not
    return response


@bp.route('/cron/tick')
def cron_tick():
    """ Called every few minutes by an external scheduler (cron-job.org; PythonAnywhere's free tier has no
        background processes): processes the phase if its deadline passed and sends deadline reminders, even when
        nobody is visiting the site. Protected by DIPLOMACY_CRON_TOKEN (?token=...); 404 when unset or wrong. """
    expected = current_app.config['CRON_TOKEN']
    given = request.args.get('token', '')
    if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
        LOGGER.warning('Rejected /cron/tick from %s (token %s)', g.client_ip, 'not configured' if not expected
                       else 'wrong')
        abort(404)
    now = time.time()
    with open_game() as (game, meta, _):
        if not game:
            return jsonify(game=None)
        return jsonify(phase=game.get_current_phase(), done=game.is_game_done,
                       deadline_in_s=round(meta['deadline'] - now) if meta['deadline'] else None,
                       queued_notifications=len(g.get('pending_push') or []))


# ----------------------------------------------------------------------------------------------------------------
# Notifications (Web Push) and installing the site as an app
# ----------------------------------------------------------------------------------------------------------------
@bp.route('/sw.js')
def service_worker():
    """ The service worker that shows notifications. Served from the root so its scope is the whole site. """
    response = send_from_directory(os.path.join(current_app.root_path, 'static'), 'sw.js',
                                   mimetype='text/javascript', max_age=0)
    response.headers['Cache-Control'] = 'no-cache'     # browsers must pick up a new version on the next visit
    return response


@bp.route('/manifest.webmanifest')
def manifest():
    """ Lets players add the site to their home screen (on iPhone that is required for notifications). """
    icons = [{'src': url_for('static', filename='icon-%d.png' % size), 'sizes': '%dx%d' % (size, size),
              'type': 'image/png', 'purpose': 'any maskable'} for size in (192, 512)]
    data = {'name': 'Diplomacy', 'short_name': 'Diplomacy', 'start_url': url_for('game.index'), 'scope': '/',
            'display': 'standalone', 'background_color': '#f6f8fa', 'theme_color': '#0b5cad', 'icons': icons}
    return Response(json.dumps(data), mimetype='application/manifest+json')


def notifier_or_404():
    """ The app's Notifier; 404 if push notifications could not be set up (the reason is in the startup log).
        The views below import webapp.notify / webapp.webpush only after this check: they need `cryptography`,
        and without it the app must still run (without notifications) instead of failing to start. """
    notifier = current_app.config['NOTIFIER']
    if not notifier:
        LOGGER.warning('%s requested but push notifications are disabled (see startup log)', request.path)
        abort(404)
    return notifier


def push_site_url():
    """ The site's https URL, the VAPID subject when DIPLOMACY_PUSH_CONTACT is unset. Built from the Host
        header because PythonAnywhere terminates HTTPS in front of the app (request.url_root says http). """
    return 'https://%s/' % request.host


def absolute_url(endpoint, **values):
    """ The https URL of a page, for links sent outside the site (e.g. set-password links). """
    return push_site_url()[:-1] + url_for(endpoint, **values)


def device_label(agent):
    """ 'Mozilla/5.0 (Linux; Android 14; ...) Chrome/129...' -> 'Chrome on Android'. Rough, for humans only. """
    system = next((name for pattern, name in [('iPhone|iPad|iPod', 'iPhone/iPad'), ('Android', 'Android'),
                                              ('Windows', 'Windows'), ('Mac OS X|Macintosh', 'Mac'),
                                              ('Linux|X11', 'Linux')] if re.search(pattern, agent)), '')
    browser = next((name for pattern, name in [('Edg/', 'Edge'), ('Firefox/|FxiOS/', 'Firefox'),
                                               ('Chrome/|CriOS/', 'Chrome'), ('Safari/', 'Safari')]
                    if re.search(pattern, agent)), 'Browser')
    return '%s on %s' % (browser, system) if system else browser


@bp.route('/notifications')
@login_required
def notifications():
    """ Enable notifications on this device, send a test, see and remove the user's devices. """
    notifier = current_app.config['NOTIFIER']
    devices = []
    for entry in notifier.store.for_users([g.user.email]) if notifier else []:
        from webapp.notify import describe_device   # pylint: disable=import-outside-toplevel (see notifier_or_404)
        device = describe_device(entry)
        error = device['last_error']
        devices.append(dict(device, label=device_label(device['agent']),
                            created=format_time(device['created_at']) if device['created_at'] else '',
                            last_ok=format_time(device['last_ok']) if device['last_ok'] else 'never',
                            error='%s (%s)' % (format_time(error['at']), error['status'] or 'unreachable')
                                  if error else ''))
    return render_template('notifications.html', enabled=bool(notifier),
                           public_key=notifier.public_key if notifier else '', devices=devices)


@bp.route('/notifications/subscribe', methods=['POST'])
@login_required
def notifications_subscribe():
    """ Stores this browser's push subscription (sent by the notifications page's script, and re-sent by every
        page once per browser session so that a renewed subscription is picked up). JSON reply. """
    notifier = notifier_or_404()
    from webapp import webpush                      # pylint: disable=import-outside-toplevel (see notifier_or_404)
    from webapp.notify import device_id             # pylint: disable=import-outside-toplevel
    try:
        subscription = json.loads(request.form.get('subscription', ''))
    except ValueError:
        subscription = None
    error = webpush.check_subscription(subscription)
    if error:
        LOGGER.warning('Rejected push subscription from %r: %s', g.user.email, error)
        return jsonify(ok=False, error='This browser sent an unusable subscription: %s.' % error), 400
    agent = request.headers.get('User-Agent', '')
    is_new = notifier.store.add(g.user.email, subscription, agent, time.time())
    LOGGER.log(logging.INFO if is_new else logging.DEBUG, 'Push subscription %s %s for %r (%s)',
               webpush.describe_endpoint(subscription['endpoint']), 'added' if is_new else 'refreshed', g.user.email,
               device_label(agent))
    return jsonify(ok=True, new=is_new, device=device_id(subscription['endpoint']))


@bp.route('/notifications/remove', methods=['POST'])
@login_required
def notifications_remove():
    """ Forgets one of the user's devices: by id (the devices table) or by endpoint (the page's script, when
        notifications are disabled on this device; JSON reply). """
    notifier = notifier_or_404()
    from webapp.notify import device_id             # pylint: disable=import-outside-toplevel (see notifier_or_404)
    endpoint = request.form.get('endpoint', '')
    device = device_id(endpoint) if endpoint else request.form.get('device', '')
    removed = notifier.store.remove(g.user.email, device)
    LOGGER.info('Push device %s of %r removed by the user: %s', device, g.user.email, removed)
    if endpoint:
        return jsonify(ok=True, removed=removed)
    flash('Device removed: it will not get notifications any more.' if removed else 'Device not found.',
          'ok' if removed else 'error')
    return redirect(url_for('game.notifications'))


@bp.route('/notifications/test', methods=['POST'])
@login_required
def notifications_test():
    """ Sends a test notification to all the user's devices right away and reports the outcome. """
    notifier = notifier_or_404()
    results = notifier.send([g.user.email], {'title': 'Diplomacy', 'body': 'Test: notifications work on this device.',
                                            'url': url_for('game.notifications'), 'tag': 'test'},
                            push_site_url(), ttl=600)[g.user.email]
    if not results:
        flash('You have not enabled notifications on any device yet.', 'error')
    elif all(result.ok for result in results):
        flash('Test notification sent to %d device(s). It should appear within a few seconds.' % len(results), 'ok')
    else:
        failed = [result for result in results if not result.ok]
        flash('Test notification: %d of %d device(s) failed (%s). Devices that no longer exist were removed; '
              'if the others keep failing, tell the admin.' % (
                  len(failed), len(results), ', '.join(str(result.status or 'unreachable') for result in failed)),
              'error')
    return redirect(url_for('game.notifications'))


# ----------------------------------------------------------------------------------------------------------------
# Admin
# ----------------------------------------------------------------------------------------------------------------
@bp.route('/admin')
@admin_required
def admin():
    """ Admin page. """
    now = time.time()
    new_link = session.pop('new_link', None)       # shown once, right after it was issued
    if new_link:
        new_link['expires_text'] = format_time(new_link['expires'])
        new_link['mailto'] = 'mailto:%s?%s' % (new_link['email'], urllib.parse.urlencode({
            'subject': 'Diplomacy: set your password',
            'body': 'Open this link to set your password for our Diplomacy game (it works once, until %s):\n\n%s\n'
                    % (new_link['expires_text'], new_link['url'])}, quote_via=urllib.parse.quote))
    users = [dict(user._asdict(), link_state=link_state(user, now),
                  link_expires=format_time(user.link['expires']) if user.link else '') for user in g.users.values()]
    with open_game() as (game, meta, _):
        context = {'has_game': bool(game), 'users': users, 'new_link': new_link, 'link_days': LINK_DAYS,
                   'variants': {count: {'groups': groups, 'neutral': gameplay.neutral_powers(count),
                                        'warnings': gameplay.check_assignment(count, g.users)}
                                for count, groups in sorted(gameplay.VARIANTS.items(), reverse=True)},
                   'default_players': gameplay.MAX_PLAYERS}
        if game:
            context.update(phase=game.get_current_phase(), done=game.is_game_done, deadline=deadline_text(meta, now),
                           phase_hours=meta['phase_hours'], phase_names=gameplay.PHASE_TYPE_NAMES,
                           neutral=meta.get('neutral', []), players=meta.get('players'))
    return render_template('admin.html', **context)


@bp.route('/admin/new-game', methods=['POST'])
@admin_required
def admin_new_game():
    """ Starts a new game, archiving the current one. """
    if request.form.get('confirm') != 'yes':
        flash('Tick the confirmation box to start a new game.', 'error')
        return redirect(url_for('game.admin'))
    try:
        players = int(request.form.get('players') or gameplay.MAX_PLAYERS)
        if players not in gameplay.VARIANTS:
            raise ValueError(players)
    except ValueError:
        flash('The number of players must be between %d and %d.' % (gameplay.MIN_PLAYERS, gameplay.MAX_PLAYERS),
              'error')
        return redirect(url_for('game.admin'))
    now = time.time()
    store = current_app.config['GAME_STORE']
    with store.locked():
        archived = store.archive()
        game, meta = gameplay.new_game(g.user.email, now, players)
        store.save(game, meta)
    warnings = gameplay.check_assignment(players, g.users)
    LOGGER.info('Admin %r started a new %d player game (previous archived to %s). users=%s warnings=%s',
                g.user.email, players, archived, {user.email: list(user.powers) for user in g.users.values()}, warnings)
    flash('New game started for %d players.' % players, 'ok')
    for warning in warnings:
        flash('Check users file: %s' % warning, 'error')
    return redirect(url_for('game.index'))


@bp.route('/admin/assign', methods=['POST'])
@admin_required
def admin_assign():
    """ Rewrites the powers in the users file: picks N of the ticked users (randomly or in file order) and gives
        them the groups of powers of the N player game (shuffled or in order). Everybody else gets no power. """
    names = [email for email in g.users if email in request.form.getlist('candidates')]
    try:
        players = int(request.form.get('players', ''))
        assignment = gameplay.plan_assignment(names, players,
                                              random_select=request.form.get('random_select') == 'yes',
                                              random_powers=request.form.get('random_powers') == 'yes')
    except ValueError as exc:
        flash('Cannot assign powers: %s' % exc, 'error')
        return redirect(url_for('game.admin'))
    with open_game() as (game, meta, _):
        if game and not game.is_game_done and request.form.get('confirm') != 'yes':
            flash('A game is in progress: tick the confirmation box to change who plays what.', 'error')
            return redirect(url_for('game.admin'))
    changed = current_app.config['USER_STORE'].assign_powers(assignment)
    LOGGER.info('Admin %r rewrote powers in the users file for a %d player game: %s (candidates=%s, '
                'random_select=%s, random_powers=%s, %d users changed)', g.user.email, players,
                assignment, names, request.form.get('random_select'), request.form.get('random_powers'), changed)
    flash('Powers assigned: %s.' % '; '.join('%s: %s' % (g.users[email].name, ', '.join(power.title()
                                                                                        for power in powers))
                                             for email, powers in assignment.items()), 'ok')
    return redirect(url_for('game.admin'))


def issue_link(email):
    """ Makes a new set-password link for `email` and keeps it in the admin's session, so that the admin page
        shows it once. The token itself is never logged. """
    token, expires = current_app.config['USER_STORE'].issue_link(email, time.time())
    session['new_link'] = {'email': email, 'url': absolute_url('game.set_password', token=token),
                           'expires': expires}
    LOGGER.info('Admin %r issued a set-password link for %r, valid until %s', g.user.email, email,
                format_time(expires))


@bp.route('/admin/users/add', methods=['POST'])
@admin_required
def admin_add_user():
    """ Creates a user (without password) and a link for them to set it. """
    email, name = normalize_email(request.form.get('email', '')), request.form.get('name', '').strip()
    is_admin = request.form.get('admin') == 'yes'
    try:
        current_app.config['USER_STORE'].create(email, name, is_admin=is_admin, now=time.time())
    except ValueError as exc:
        LOGGER.info('Admin %r could not add user %r (name %r): %s', g.user.email, email, name, exc)
        flash('Cannot add the user: %s' % exc, 'error')
        return redirect(url_for('game.admin'))
    LOGGER.info('Admin %r added user %r (name %r, admin=%s)', g.user.email, email, name, is_admin)
    issue_link(email)
    flash('User %s added. Send them the link below.' % name, 'ok')
    return redirect(url_for('game.admin'))


@bp.route('/admin/users/link', methods=['POST'])
@admin_required
def admin_user_link():
    """ Issues a new set-password link (first login, forgotten password); the previous link stops working. """
    email = normalize_email(request.form.get('email', ''))
    try:
        issue_link(email)
    except ValueError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('game.admin'))
    flash('New link for %s. Send it to them; the previous link no longer works.' % g.users[email].name, 'ok')
    return redirect(url_for('game.admin'))


@bp.route('/admin/users/admin', methods=['POST'])
@admin_required
def admin_user_admin():
    """ Grants or revokes admin rights. Admins cannot revoke their own (so there is always one left). """
    email, is_admin = normalize_email(request.form.get('email', '')), request.form.get('admin') == 'yes'
    if email == g.user.email:
        LOGGER.warning('Admin %r tried to change their own admin rights', g.user.email)
        flash('You cannot change your own admin rights.', 'error')
        return redirect(url_for('game.admin'))
    try:
        user = current_app.config['USER_STORE'].set_admin(email, is_admin)
    except ValueError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('game.admin'))
    LOGGER.info('Admin %r set admin=%s for %r', g.user.email, is_admin, email)
    flash('%s is %s an admin.' % (user.name, 'now' if is_admin else 'no longer'), 'ok')
    return redirect(url_for('game.admin'))


@bp.route('/admin/users/delete', methods=['POST'])
@admin_required
def admin_delete_user():
    """ Deletes a user (their powers are left without a player). Admins cannot delete themselves. """
    email = normalize_email(request.form.get('email', ''))
    if email == g.user.email:
        LOGGER.warning('Admin %r tried to delete themselves', g.user.email)
        flash('You cannot delete yourself.', 'error')
        return redirect(url_for('game.admin'))
    if request.form.get('confirm') != 'yes':
        flash('Tick the confirmation box to delete a user.', 'error')
        return redirect(url_for('game.admin'))
    try:
        user = current_app.config['USER_STORE'].delete(email)
    except ValueError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('game.admin'))
    LOGGER.info('Admin %r deleted user %r (name %r, powers %s, admin=%s)', g.user.email, user.email, user.name,
                list(user.powers), user.is_admin)
    flash('User %s deleted.' % user.name, 'ok')
    return redirect(url_for('game.admin'))


@bp.route('/admin/process', methods=['POST'])
@admin_required
def admin_process():
    """ Processes the current phase now, with whatever orders were submitted. """
    now = time.time()
    with open_game() as (game, meta, store):
        if not game or game.is_game_done:
            flash('There is no game in progress.', 'error')
        else:
            phase = game.get_current_phase()
            gameplay.process_phase(game, meta, store, now, 'forced by admin %s' % g.user.email)
            announce_processed(game, meta, [phase] + gameplay.process_if_due(game, meta, g.users, store, now))
    return redirect(url_for('game.admin'))


@bp.route('/admin/deadline', methods=['POST'])
@admin_required
def admin_deadline():
    """ Sets the deadline of the current phase to N hours from now (empty = no deadline). """
    now = time.time()
    raw = request.form.get('hours', '').strip()
    try:
        hours = float(raw) if raw else None
        if hours is not None and not 0 < hours <= 24 * 60:
            raise ValueError('out of range')
    except ValueError:
        flash('Hours must be a number between 0 and 1440, or empty for no deadline.', 'error')
        return redirect(url_for('game.admin'))
    with open_game() as (game, meta, store):
        if not game or game.is_game_done:
            flash('There is no game in progress.', 'error')
        else:
            previous = meta['deadline']
            meta['deadline'] = now + hours * 3600 if hours else None
            store.save(game, meta)
            LOGGER.info('Admin %r changed deadline of %s: %s -> %s', g.user.email, game.get_current_phase(),
                        previous, meta['deadline'])
            flash('Deadline updated.', 'ok')
    return redirect(url_for('game.admin'))


@bp.route('/admin/settings', methods=['POST'])
@admin_required
def admin_settings():
    """ Sets the default phase lengths (hours per phase type; 0 = no deadline). Applies from the next phase. """
    try:
        hours = {kind: float(request.form.get('hours_%s' % kind, '0') or 0) for kind in gameplay.PHASE_TYPE_NAMES}
        if any(not 0 <= value <= 24 * 60 for value in hours.values()):
            raise ValueError('out of range')
    except ValueError:
        flash('Phase lengths must be numbers between 0 and 1440 hours.', 'error')
        return redirect(url_for('game.admin'))
    with open_game() as (game, meta, store):
        if not game:
            flash('There is no game.', 'error')
        else:
            LOGGER.info('Admin %r changed phase lengths: %s -> %s', g.user.email, meta['phase_hours'], hours)
            meta['phase_hours'] = hours
            store.save(game, meta)
            flash('Phase lengths updated. They apply from the next phase.', 'ok')
    return redirect(url_for('game.admin'))


@bp.route('/admin/draw', methods=['POST'])
@admin_required
def admin_draw():
    """ Ends the game as a draw between the surviving powers. """
    if request.form.get('confirm') != 'yes':
        flash('Tick the confirmation box to end the game.', 'error')
        return redirect(url_for('game.admin'))
    with open_game() as (game, meta, store):
        if not game or game.is_game_done:
            flash('There is no game in progress.', 'error')
        else:
            store.save(game, meta)
            store.backup('before_draw_%s' % game.get_current_phase())
            game.draw()
            meta['deadline'] = None
            store.save(game, meta)
            LOGGER.info('Admin %r ended the game as a draw: outcome=%s', g.user.email, game.outcome)
            notify_new_phase(game, meta, ['draw by admin'])
            flash('Game ended as a draw.', 'ok')
    return redirect(url_for('game.index'))
