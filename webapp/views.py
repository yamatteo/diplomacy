""" Pages: login, the game (map, status, orders form), history and admin actions.

    Every request that touches the game runs inside `open_game()`: it takes the file lock, loads the game and
    processes the phase if it is due (lazy deadlines), so any page view keeps the game moving.
"""
import contextlib
import functools
import hmac
import logging
import secrets
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request,
                   send_from_directory, session, url_for)
from markupsafe import Markup

from webapp import gameplay, tutorial
from webapp.users import check_login, load_users

LOGGER = logging.getLogger(__name__)
bp = Blueprint('game', __name__)


# ----------------------------------------------------------------------------------------------------------------
# Request plumbing: users, CSRF, game access
# ----------------------------------------------------------------------------------------------------------------
@bp.before_request
def load_user():
    """ Resolves the logged-in user from the users file (so removing a user logs them out) and checks CSRF. """
    g.users = load_users(current_app.config['USERS_FILE'])
    g.user = g.users.get(session.get('user', ''))
    if session.get('user') and not g.user:
        LOGGER.warning('Session for unknown user %r (removed from users file?): logging out', session.get('user'))
        session.pop('user', None)
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
            LOGGER.warning('Non-admin %r tried to access %s', g.user.name, request.path)
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
            announce_processed(gameplay.process_if_due(game, meta, g.users, store, time.time()))
        yield game, meta, store


def announce_processed(processed):
    """ Tells the user that phases were just processed. """
    if processed:
        flash('Processed: %s.' % ', '.join(processed), 'info')


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
        name = request.form.get('username', '').strip()
        user = check_login(g.users, name, request.form.get('password', ''))
        if user:
            session.clear()
            session['user'] = user.name
            session['csrf'] = secrets.token_urlsafe(16)
            session.permanent = True
            LOGGER.info('Login: user=%r power=%s admin=%s ip=%s', user.name, user.power, user.is_admin, g.client_ip)
            return redirect(url_for('game.index'))
        LOGGER.warning('Failed login: username=%r known_user=%s ip=%s', name, name in g.users, g.client_ip)
        flash('Wrong username or password.', 'error')
    return render_template('login.html')


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
    """ The game page: map, status of every power, and the orders form of the user's power. """
    now = time.time()
    with open_game() as (game, meta, _):
        if not game:
            return render_template('nogame.html')
        my_power = g.user.power if g.user.power and game.has_power(g.user.power) else None
        choices = None
        if my_power and not game.is_game_done and game.get_orderable_locations(my_power):
            choices = gameplay.order_choices(game, my_power)
        history = game.get_phase_history()
        context = {
            'phase': game.get_current_phase(),
            'phase_title': phase_title(game.get_current_phase()),
            'done': game.is_game_done,
            'outcome': game.outcome,
            'deadline': deadline_text(meta, now),
            'status': gameplay.power_status(game, meta, g.users),
            'svg': Markup(gameplay.render_current(game, orders_of=my_power)),
            'my_power': my_power,
            'choices': choices,
            'my_ready': bool(my_power and meta['ready'].get(my_power)),
            'my_submitted': bool(my_power and my_power in meta['submitted']),
            'last_phase': history[-1].name if history else None,
            'last_orders': gameplay.phase_orders(game, history[-1]) if history else None,
        }
    return render_template('game.html', **context)


@bp.route('/orders', methods=['POST'])
@login_required
def orders():
    """ Receives the orders form. """
    now = time.time()
    with open_game() as (game, meta, store):
        if not game or game.is_game_done:
            flash('There is no game in progress.', 'error')
            return redirect(url_for('game.index'))
        power = g.user.power
        if not power or not game.has_power(power):
            LOGGER.warning('User %r without a power tried to submit orders', g.user.name)
            abort(403)
        phase = game.get_current_phase()
        if request.form.get('phase') != phase:
            # The phase was processed between showing the form and submitting it.
            LOGGER.warning('Stale orders from %s: form phase=%r current phase=%s', power,
                           request.form.get('phase'), phase)
            flash('The game moved on to %s before your orders arrived: they were NOT recorded. '
                  'Please enter orders for the new phase.' % phase, 'error')
            return redirect(url_for('game.index'))
        chosen = {key[len('order_'):]: value.strip() for key, value in request.form.items()
                  if key.startswith('order_')}
        errors = gameplay.submit_orders(game, meta, power, chosen, request.form.get('ready') == 'yes', now)
        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('game.index'))
        store.save(game, meta)
        flash('Orders saved for %s%s.' % (phase, ' and marked ready' if meta['ready'].get(power) else
                                          ' (not marked ready: the phase waits for you until the deadline)'), 'ok')
        announce_processed(gameplay.process_if_due(game, meta, g.users, store, now))
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


# ----------------------------------------------------------------------------------------------------------------
# Admin
# ----------------------------------------------------------------------------------------------------------------
@bp.route('/admin')
@admin_required
def admin():
    """ Admin page. """
    now = time.time()
    with open_game() as (game, meta, _):
        context = {'has_game': bool(game), 'users': list(g.users.values()),
                   'users_file': current_app.config['USERS_FILE']}
        if game:
            context.update(phase=game.get_current_phase(), done=game.is_game_done, deadline=deadline_text(meta, now),
                           phase_hours=meta['phase_hours'], phase_names=gameplay.PHASE_TYPE_NAMES)
    return render_template('admin.html', **context)


@bp.route('/admin/new-game', methods=['POST'])
@admin_required
def admin_new_game():
    """ Starts a new game, archiving the current one. """
    if request.form.get('confirm') != 'yes':
        flash('Tick the confirmation box to start a new game.', 'error')
        return redirect(url_for('game.admin'))
    now = time.time()
    store = current_app.config['GAME_STORE']
    with store.locked():
        archived = store.archive()
        game, meta = gameplay.new_game(g.user.name, now)
        store.save(game, meta)
    LOGGER.info('Admin %r started a new game (previous archived to %s)', g.user.name, archived)
    flash('New game started.', 'ok')
    return redirect(url_for('game.index'))


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
            gameplay.process_phase(game, meta, store, now, 'forced by admin %s' % g.user.name)
            flash('Processed %s.' % phase, 'ok')
            announce_processed(gameplay.process_if_due(game, meta, g.users, store, now))
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
            LOGGER.info('Admin %r changed deadline of %s: %s -> %s', g.user.name, game.get_current_phase(),
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
            LOGGER.info('Admin %r changed phase lengths: %s -> %s', g.user.name, meta['phase_hours'], hours)
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
            LOGGER.info('Admin %r ended the game as a draw: outcome=%s', g.user.name, game.outcome)
            flash('Game ended as a draw.', 'ok')
    return redirect(url_for('game.index'))
