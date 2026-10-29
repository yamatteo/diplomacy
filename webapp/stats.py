""" Raw statistics for scored games (7 players, standard map): ``stats.json`` in the data dir.

    ``{"turns": [...], "games": [...]}``. A turn record is one player's response in one processed phase
    (``game_id, phase, power, user, started, ready_at, deadline, reason``); a game record is written once when a
    game ends (``game_id, created_at, ended_at, end, outcome, phase, powers: {POWER: {centers, user}}``).
    Raw facts only: aggregation is left to whatever displays them. No orders are stored.
    The file has its own lock, separate from the game's. A missing file means no statistics yet.
"""
import contextlib
import fcntl
import json
import logging
import os

LOGGER = logging.getLogger(__name__)


class StatsStore:
    """ Reads and writes stats.json. Every method takes the lock and re-reads the file. """

    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, 'stats.json')
        self.lock_path = os.path.join(data_dir, 'stats.lock')

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
            return {'turns': [], 'games': []}
        with open(self.path, encoding='utf-8') as file:     # a broken file raises: never overwrite it silently
            data = json.load(file)
        data.setdefault('turns', [])
        data.setdefault('games', [])
        return data

    def _write(self, data):
        temp = self.path + '.tmp'
        with open(temp, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=1)
        os.chmod(temp, 0o600)
        os.replace(temp, self.path)

    def all(self):
        """ {"turns": [...], "games": [...]} """
        with self._locked():
            return self._read()

    def add_turns(self, records):
        """ Appends turn records. """
        with self._locked():
            data = self._read()
            data['turns'].extend(records)
            self._write(data)

    def add_game(self, record):
        """ Appends a game record. """
        with self._locked():
            data = self._read()
            data['games'].append(record)
            self._write(data)

    def summary(self):
        """ Counts for /debug/info. Never raises. """
        try:
            exists = os.path.exists(self.path)
            data = self.all() if exists else {'turns': [], 'games': []}
            return {'path': self.path, 'exists': exists, 'size_bytes': os.path.getsize(self.path) if exists else 0,
                    'turns': len(data['turns']), 'games': len(data['games']),
                    'last_game_id': data['games'][-1].get('game_id') if data['games'] else None}
        except Exception as error:     # pylint: disable=broad-except
            LOGGER.exception('Cannot summarize %s', self.path)
            return {'path': self.path, 'error': repr(error)}
