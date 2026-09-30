# Deploying on PythonAnywhere (free tier)

Replace `USER` below with your PythonAnywhere username. On the EU site (eu.pythonanywhere.com) the app is at `https://USER.eu.pythonanywhere.com` and the WSGI file is `/var/www/USER_eu_pythonanywhere_com_wsgi.py`.

## First install

1. **Account → System image**: make sure it is `innit` (Python 3.13). Accounts created after March 2025 already have it.
2. **Consoles → Bash**, then:
   ```bash
   # The preinstalled uv (/usr/local/bin/uv, 0.4.18 as of 2026-09) is too old for our pyproject.toml / uv.lock.
   # Install a current one from PyPI (astral.sh is not allowlisted, so not with curl) and put it first on PATH.
   python3.13 -m pip install --user --upgrade uv
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
   uv --version                               # must NOT be 0.4.x

   git clone -b simple https://github.com/yamatteo/diplomacy.git ~/diplomacy
   cd ~/diplomacy
   uv sync --locked --python /usr/bin/python3.13
   uv cache clean                             # the cache counts against the 512 MB disk quota
   python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # copy this: it is your debug token
   ```
   If `uv sync` says the lockfile "needs to be updated", check `which uv` / `uv --version`: the old preinstalled uv is being used. Never run `uv lock` on the server: it would modify the tracked `uv.lock` and break the next `git pull`.
3. **Web → Add a new web app** → *Manual configuration* (not the Flask quickstart) → **Python 3.13**.
4. On the Web tab set:
   - **Source code** and **Working directory**: `/home/USER/diplomacy`
   - **Virtualenv**: `/home/USER/diplomacy/.venv`
   - **Force HTTPS**: enabled (the debug token travels in the URL).
5. Click the **WSGI configuration file** link, replace its entire content with `deploy/pythonanywhere_wsgi.py` from this repo, and set `DEBUG_TOKEN` (the username and paths are detected automatically).
6. Click **Reload**, then open:
   - `https://USER.pythonanywhere.com/`: should show the login page
   - `https://USER.pythonanywhere.com/healthz`
   - `https://USER.pythonanywhere.com/debug/info?token=TOKEN`: check `in_virtualenv: true`, the Python version and the git commit.

## Players and first game

1. After the first start, the app creates `~/diplomacy-data/users.txt` with one user, `admin`, and a random password. Open it from the **Files** tab to read the password.
2. Edit that file to add your friends, one per line: `username:password:POWER`, plus `:admin` for admins. POWER is `AUSTRIA`, `ENGLAND`, `FRANCE`, `GERMANY`, `ITALY`, `RUSSIA`, `TURKEY`, or `-` for none. Example:
   ```
   matteo:some-password:FRANCE:admin
   anna:another-password:GERMANY
   ```
   Changes apply immediately, no reload needed. Passwords are stored as plain text and cannot contain `:`.
3. Log in as an admin, open **Admin** and start a new game. Phase lengths and deadlines are set there.
4. Deadlines are shown in the `Europe/Rome` time zone; to change it add `os.environ['DIPLOMACY_TIMEZONE'] = 'Europe/London'` to the WSGI file.

There is no background process: a phase is processed when someone opens a page after the deadline has passed, or as soon as all players have marked themselves ready.

## Updating

```bash
cd ~/diplomacy && git pull && uv sync --locked --python /usr/bin/python3.13 && uv cache clean
touch /var/www/USER_pythonanywhere_com_wsgi.py     # (USER_eu_... on EU) reloads the web app (same as the Reload button)
```

## When something breaks

Send Claude the output of these; together they replace shell access to the server.

| What | Where |
|---|---|
| App can't start (import error, bad venv) | The site itself shows the traceback, python path and sys.prefix. Also in the **Error log** (Web tab). |
| Environment (Python, venv, git commit, package versions, data dir), users (no passwords) and game state (phase, deadline, who is ready; no orders) | `/debug/info?token=TOKEN` |
| Application log (every request, startup, tracebacks tagged with request id) | `/debug/logs?token=TOKEN&lines=500`, or file `~/diplomacy-data/logs/app.log` |
| A user sees "Internal error … request id abc123" | Search the app log for `[abc123]` |
| Check that error logging works end to end | `/debug/error?token=TOKEN` (fails on purpose) |
| Web server / worker problems | **Server log** and **Error log** links on the Web tab |
