""" Environment introspection used for remote debugging.
    There is no shell access to the production server, so everything useful for diagnosing
    a broken deploy (interpreter, venv, paths, git revision, package versions) is collected here,
    logged at startup and exposed through the token-protected /debug/info endpoint.
"""
import importlib.metadata
import os
import platform
import subprocess
import sys
import time

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES = ['diplomacy-simple', 'flask', 'werkzeug', 'jinja2']


def git_info():
    """ Returns commit, branch and dirty flag of the checkout the app is running from. """
    def run(*args):
        try:
            out = subprocess.run(['git', *args], cwd=REPO_DIR, capture_output=True, text=True, timeout=5)
            return out.stdout.strip() if out.returncode == 0 else 'error: %s' % out.stderr.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            return 'unavailable: %r' % exc
    return {
        'commit': run('rev-parse', '--short', 'HEAD'),
        'branch': run('rev-parse', '--abbrev-ref', 'HEAD'),
        'commit_date': run('log', '-1', '--format=%cI'),
        'dirty_files': run('status', '--porcelain').splitlines()[:20],
    }


def package_versions():
    """ Returns installed versions of the packages that matter, or the lookup error. """
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'NOT INSTALLED'
    return versions


def dir_size_bytes(path):
    """ Total size of files under path (0 if missing). Keep to small dirs: walking costs CPU quota. """
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def environment_info(config):
    """ Snapshot of everything needed to debug the deployment. Never includes secret values. """
    return {
        'pid': os.getpid(),
        'python_version': sys.version,
        'python_executable': sys.executable,
        'sys_prefix': sys.prefix,
        'in_virtualenv': sys.prefix != sys.base_prefix,
        'platform': platform.platform(),
        'cwd': os.getcwd(),
        'repo_dir': REPO_DIR,
        'sys_path': sys.path,
        'user': os.environ.get('USER') or os.environ.get('LOGNAME'),
        'home': os.path.expanduser('~'),
        'timezone': time.tzname,
        'git': git_info(),
        'packages': package_versions(),
        'data_dir': config['DATA_DIR'],
        'data_dir_exists': os.path.isdir(config['DATA_DIR']),
        'data_dir_size_bytes': dir_size_bytes(config['DATA_DIR']),
        'log_file': config['LOG_FILE'],
        'debug_token_set': bool(config['DEBUG_TOKEN']),
        # Names only: values may be secrets.
        'diplomacy_env_vars': sorted(key for key in os.environ if key.startswith('DIPLOMACY_')),
    }
