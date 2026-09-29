""" Template for the PythonAnywhere WSGI file.

    Copy this whole file into the WSGI configuration file linked from the Web tab
    (/var/www/<username>_pythonanywhere_com_wsgi.py, or <username>_eu_... on eu.pythonanywhere.com)
    and set DEBUG_TOKEN.
    Secrets live only there, never in the repository.
"""
import os
import pwd
import sys
import traceback

DEBUG_TOKEN = 'CHANGE-ME'   # generate with: python3 -c "import secrets; print(secrets.token_urlsafe(24))"

HOME = pwd.getpwuid(os.getuid()).pw_dir     # /home/<username>, detected automatically
PROJECT_DIR = os.path.join(HOME, 'diplomacy')

os.environ['DIPLOMACY_DATA_DIR'] = os.path.join(HOME, 'diplomacy-data')
os.environ['DIPLOMACY_DEBUG_TOKEN'] = DEBUG_TOKEN

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

try:
    if 'CHANGE-ME' in DEBUG_TOKEN:
        # The placeholder is public (it's in the repo): refuse to run with it.
        raise RuntimeError('Set DEBUG_TOKEN in the WSGI file (Web tab) to a long random string, then Reload.')
    from webapp import create_app
    application = create_app()
except Exception:  # pylint: disable=broad-except
    # If the app cannot even start (bad venv, missing package, syntax error), serve the traceback
    # so the problem can be diagnosed from a browser. It is also in the Web tab's error log.
    STARTUP_ERROR = ('App failed to start.\n\npython: %s\nsys.prefix: %s\n\n%s'
                     % (sys.executable, sys.prefix, traceback.format_exc()))
    print(STARTUP_ERROR, file=sys.stderr)

    def application(environ, start_response):  # pylint: disable=unused-argument
        """ Fallback WSGI app reporting the startup failure. """
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain; charset=utf-8')])
        return [STARTUP_ERROR.encode('utf-8')]
