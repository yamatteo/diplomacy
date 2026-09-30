""" Persistence of the single game as a JSON file in the data dir.

    ``game.json`` holds ``{"saved_at", "meta", "game"}`` where ``game`` is ``Game.to_dict()`` and ``meta`` is
    the web app's own state (deadline, who is ready, settings). Every request that may change the game runs
    inside ``store.locked()`` (an exclusive file lock), and writes are atomic (temp file + rename), so a crash
    or two simultaneous requests cannot corrupt or lose the game.
"""
import contextlib
import fcntl
import json
import logging
import os
import shutil
import time

from diplomacy import Game

LOGGER = logging.getLogger(__name__)


class GameStore:
    """ Loads and saves the game file. """

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.path = os.path.join(data_dir, 'game.json')
        self.lock_path = os.path.join(data_dir, 'game.lock')
        self.backup_dir = os.path.join(data_dir, 'backups')
        self.archive_dir = os.path.join(data_dir, 'archive')
        os.makedirs(data_dir, exist_ok=True)

    @contextlib.contextmanager
    def locked(self):
        """ Holds an exclusive lock on the game for the duration of the block. """
        started = time.perf_counter()
        with open(self.lock_path, 'w', encoding='utf-8') as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            waited_ms = (time.perf_counter() - started) * 1000
            if waited_ms > 200:
                LOGGER.warning('Waited %.0f ms for the game lock', waited_ms)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def exists(self):
        """ True if a game file exists. """
        return os.path.exists(self.path)

    def load(self):
        """ Returns (game, meta), or (None, None) if there is no game. Raises if the file is unreadable. """
        if not self.exists():
            return None, None
        try:
            with open(self.path, encoding='utf-8') as file:
                data = json.load(file)
            game = Game.from_dict(data['game'])
            return game, data['meta']
        except Exception:
            LOGGER.exception('Cannot load game file %s (size %s bytes). Backups are in %s',
                             self.path, os.path.getsize(self.path), self.backup_dir)
            raise

    def save(self, game, meta):
        """ Atomically writes the game file. """
        data = {'saved_at': time.time(), 'meta': meta, 'game': game.to_dict()}
        temp_path = self.path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as file:
            json.dump(data, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, self.path)
        LOGGER.debug('Saved game: phase=%s size=%d bytes', game.get_current_phase(), os.path.getsize(self.path))

    def backup(self, label):
        """ Copies the current game file to backups/game_<label>.json (e.g. before processing a phase). """
        if not self.exists():
            return None
        os.makedirs(self.backup_dir, exist_ok=True)
        target = os.path.join(self.backup_dir, 'game_%s.json' % label)
        shutil.copy2(self.path, target)
        LOGGER.info('Backed up game to %s', target)
        return target

    def archive(self):
        """ Moves the current game file (if any) to archive/, e.g. when a new game replaces it. """
        if not self.exists():
            return None
        os.makedirs(self.archive_dir, exist_ok=True)
        target = os.path.join(self.archive_dir, 'game_%s.json' % time.strftime('%Y%m%d_%H%M%S', time.gmtime()))
        os.replace(self.path, target)
        LOGGER.info('Archived previous game to %s', target)
        return target
