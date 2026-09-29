""" Template for the PythonAnywhere WSGI file.

    Copy this whole file into the WSGI configuration file linked from the Web tab
    (/var/www/<username>_pythonanywhere_com_wsgi.py) and replace the CHANGE-ME values.
    Secrets live only there, never in the repository.
"""
import os
import sys
import traceback

USERNAME = 'CHANGE-ME'                       # your PythonAnywhere username
PROJECT_DIR = '/home/%s/diplomacy' % USERNAME

os.environ['DIPLOMACY_DATA_DIR'] = '/home/%s/diplomacy-data' % USERNAME
os.environ['DIPLOMACY_DEBUG_TOKEN'] = 'CHANGE-ME-to-a-long-random-string'

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

try:
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
