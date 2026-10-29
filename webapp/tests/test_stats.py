""" Raw statistics (stats.json): turn records, game records, and that they never get in the game's way. """
import json
import logging
import os
import time

import pytest

from webapp.tests.test_app import (Browser, app_fixture, read_game_file, start_game,  # pylint: disable=unused-import
                                   write_users)


@pytest.fixture(name='clock')
def clock_fixture(monkeypatch):
    """ A controllable time.time(), starting now. """
    now = [time.time()]
    monkeypatch.setattr(time, 'time', lambda: now[0])
    return now


def stats_of(app):
    path = os.path.join(app.config['DATA_DIR'], 'stats.json')
    if not os.path.exists(path):
        return {'turns': [], 'games': []}
    with open(path, encoding='utf-8') as file:
        return json.load(file)


def write_game_file(app, data):
    with open(os.path.join(app.config['DATA_DIR'], 'game.json'), 'w', encoding='utf-8') as file:
        json.dump(data, file)


def test_turn_records_have_ready_times_and_no_record_for_powers_without_player(app, clock):
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    carla = Browser(app, 'carla')
    started = clock[0]
    assert read_game_file(app)['meta']['scored'] is True
    clock[0] += 100
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    clock[0] += 50
    bruno.post('/orders', phase='S1901M', order_MUN='A MUN - RUH')          # saved, not ready
    assert stats_of(app)['turns'] == []
    data = read_game_file(app)
    data['meta']['deadline'] = clock[0] - 1
    write_game_file(app, data)
    carla.text('/')                                                         # processes: deadline passed
    turns = stats_of(app)['turns']
    assert sorted(t['power'] for t in turns) == ['FRANCE', 'GERMANY']
    france = next(t for t in turns if t['power'] == 'FRANCE')
    germany = next(t for t in turns if t['power'] == 'GERMANY')
    assert france['ready_at'] == pytest.approx(started + 100) and france['user'] == 'anna@example.com'
    assert germany['ready_at'] is None and germany['user'] == 'bruno@example.com'
    for turn in turns:
        assert turn['phase'] == 'S1901M' and turn['reason'] == 'deadline passed'
        assert turn['started'] == pytest.approx(started) and turn['deadline'] == pytest.approx(clock[0] - 1)
        assert turn['game_id'] == data['game']['game_id']
        assert 'orders' not in turn
    assert read_game_file(app)['meta']['ready_at'] == {}                     # reset for the next phase


def test_last_press_counts_and_a_changed_autosave_clears_it(app, clock):
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    clock[0] += 10
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - PIC', autosave='yes')    # changes orders: not ready
    assert read_game_file(app)['meta']['ready'] == {'FRANCE': False}
    clock[0] += 10
    pressed = clock[0]
    bruno.post('/orders', phase='S1901M', order_MUN='A MUN - RUH', ready='yes')
    assert stats_of(app)['turns'] == []                                      # anna is not ready: waiting
    data = read_game_file(app)
    data['meta']['deadline'] = clock[0] - 1
    write_game_file(app, data)
    Browser(app, 'carla').text('/')
    turns = stats_of(app)['turns']
    assert next(t for t in turns if t['power'] == 'FRANCE')['ready_at'] is None
    assert next(t for t in turns if t['power'] == 'GERMANY')['ready_at'] == pytest.approx(pressed)

    # Fall: press, change, press again: the later time counts.
    anna.post('/orders', phase='F1901M', order_PIC='A PIC - BEL', ready='yes')
    clock[0] += 30
    anna.post('/orders', phase='F1901M', order_PIC='A PIC H', autosave='yes')
    clock[0] += 30
    again = clock[0]
    anna.post('/orders', phase='F1901M', order_PIC='A PIC H', ready='yes')
    clock[0] += 5
    bruno.post('/orders', phase='F1901M', ready='yes')
    fall = [t for t in stats_of(app)['turns'] if t['phase'] == 'F1901M' and t['power'] == 'FRANCE']
    assert len(fall) == 1 and fall[0]['ready_at'] == pytest.approx(again) and fall[0]['reason'] == 'all players ready'


def test_draw_writes_one_game_record(app, clock):
    anna = start_game(app)
    anna.post('/admin/draw', confirm='yes')
    games = stats_of(app)['games']
    assert len(games) == 1
    record = games[0]
    assert record['end'] == 'draw' and record['phase'] and record['outcome'][1:]
    assert sorted(record['powers']) == ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
    assert record['powers']['FRANCE'] == {'centers': 3, 'user': 'anna@example.com'}
    assert record['powers']['AUSTRIA'] == {'centers': 3, 'user': None}
    assert record['powers']['RUSSIA']['centers'] == 4 and record['powers']['GERMANY']['user'] == 'bruno@example.com'
    assert read_game_file(app)['meta']['scored'] == 'recorded'
    anna.post('/admin/draw', confirm='yes')                                  # game already over
    anna.post('/admin/new-game', confirm='yes')                              # finished and recorded: nothing more
    assert len(stats_of(app)['games']) == 1


def test_solo_victory_writes_a_solo_record(app, clock):
    """ Cheapest solo: win=4 (meta['win'], applied to the engine before processing), Russia is left with 3 centers
        and France takes Spain, so it grows to 4 alone in the lead when Fall 1901 is processed. """
    anna = start_game(app)
    data = read_game_file(app)
    data['meta']['win'] = 4
    data['game']['powers']['RUSSIA']['centers'].remove('WAR')
    data['game']['powers']['RUSSIA']['units'].remove('A WAR')     # else it recaptures it
    write_game_file(app, data)
    bruno = Browser(app, 'bruno')
    for phase, orders in (('S1901M', {'order_MAR': 'A MAR - SPA'}), ('F1901M', {})):
        anna.post('/orders', phase=phase, ready='yes', **orders)
        bruno.post('/orders', phase=phase, ready='yes')
    assert read_game_file(app)['game']['phase'] == 'COMPLETED'
    games = stats_of(app)['games']
    assert len(games) == 1 and games[0]['end'] == 'solo' and games[0]['outcome'][1:] == ['FRANCE']
    assert games[0]['powers']['FRANCE'] == {'centers': 4, 'user': 'anna@example.com'}
    assert games[0]['powers']['RUSSIA']['centers'] == 3
    assert len(stats_of(app)['turns']) == 4
    anna.post('/admin/draw', confirm='yes')
    assert len(stats_of(app)['games']) == 1


def test_new_game_over_a_running_scored_game_records_it_as_abandoned(app, clock):
    anna = start_game(app)
    old_id = read_game_file(app)['game']['game_id']
    clock[0] += 3600                                                       # a distinct game id
    anna.post('/admin/new-game', confirm='yes')
    games = stats_of(app)['games']
    assert len(games) == 1 and games[0]['end'] == 'abandoned' and games[0]['game_id'] == old_id
    assert games[0]['powers']['FRANCE']['user'] == 'anna@example.com'
    assert read_game_file(app)['game']['game_id'] != old_id and read_game_file(app)['meta']['scored'] is True


@pytest.mark.parametrize('old_shape', [False, True])
def test_unscored_games_write_nothing_and_work(app, clock, old_shape):
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes', players='6')
    if old_shape:
        anna.post('/admin/new-game', confirm='yes')
        data = read_game_file(app)
        del data['meta']['scored']
        del data['meta']['ready_at']
        write_game_file(app, data)
    else:
        assert read_game_file(app)['meta']['scored'] is False
    bruno = Browser(app, 'bruno')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', autosave='yes')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    bruno.post('/orders', phase='S1901M', order_MUN='A MUN - RUH', ready='yes')
    assert read_game_file(app)['game']['phase'] == 'FALL 1901 MOVEMENT'
    clock[0] += 3600
    anna.post('/admin/new-game', confirm='yes', players='6')               # over a running unscored game
    clock[0] += 3600
    anna.post('/admin/draw', confirm='yes')
    assert stats_of(app) == {'turns': [], 'games': []}
    assert not os.path.exists(os.path.join(app.config['DATA_DIR'], 'stats.json'))


def test_unwritable_stats_do_not_break_processing(app, clock, caplog):
    os.mkdir(os.path.join(app.config['DATA_DIR'], 'stats.json'))
    anna = start_game(app)
    bruno = Browser(app, 'bruno')
    caplog.set_level(logging.INFO)
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    bruno.post('/orders', phase='S1901M', order_MUN='A MUN - RUH', ready='yes')
    assert read_game_file(app)['game']['phase'] == 'FALL 1901 MOVEMENT'
    assert any('Cannot record turn statistics' in r.getMessage() and r.exc_info for r in caplog.records)
    assert anna.post('/admin/draw', confirm='yes').status_code == 302
    assert read_game_file(app)['game']['phase'] == 'COMPLETED'
    assert any('Cannot record the draw' in r.getMessage() for r in caplog.records)
    assert read_game_file(app)['meta']['scored'] is True            # not marked recorded: nothing was written


def test_debug_info_shows_the_stats_summary(app):
    anna = start_game(app)
    anna.post('/admin/draw', confirm='yes')
    info = app.test_client().get('/debug/info?token=debug-secret').get_json()
    assert info['stats']['games'] == 1 and info['stats']['turns'] == 0 and info['stats']['size_bytes'] > 0
    assert info['stats']['last_game_id'].startswith('game_')
