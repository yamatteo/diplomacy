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

Upgrading from the old `users.txt`: it is no longer read (the log says so at startup; delete it). Recreate the accounts as below, assign the powers again (tick the confirmation box if a game is in progress), and delete `~/diplomacy-data/subscriptions.json`: its devices belong to the old usernames, so everybody enables notifications again.

1. Create your own admin account: open `https://USER.pythonanywhere.com/debug/admin-link?token=TOKEN&email=YOUR_EMAIL&name=YOUR_NAME` (the debug token from the WSGI file; `name` is what the other players see and defaults to the part of the email before `@`). It answers with a link: open it and choose your password. The same URL is the way back in if you ever lose the admin password (it issues a new link and makes that email an admin).
2. Add your friends in **Admin** → **Players** → **Add a user** (email and display name). Each new user gets a set-password link, shown once on the admin page: send it to them by email (the "Send it by email" link opens your mail program) or by chat. A link works once, for 7 days. For a forgotten password, click **New link** next to the user and send that. Then give out the countries with **Assign powers**. Accounts are stored in `~/diplomacy-data/users.json` (passwords hashed, never readable); manage them from the admin page, not by editing the file.
3. Open **Admin** and start a new game. Phase lengths and deadlines are set there.
4. Deadlines are shown in the `Europe/Rome` time zone; to change it add `os.environ['DIPLOMACY_TIMEZONE'] = 'Europe/London'` to the WSGI file.

There is no background process: a phase is processed when someone opens a page after the deadline has passed, or as soon as all players have marked themselves ready. To process deadlines on time and send reminders even when nobody visits, set up the external scheduler below.

## Notifications and the external scheduler

Players enable push notifications on the **Notifications** page (on iPhone, after adding the site to the home screen). They get one when a new phase needs their orders, and reminders 12 and 2 hours before the deadline if they are not done (change with `os.environ['DIPLOMACY_REMINDER_HOURS'] = '24,3'` in the WSGI file; empty for none). Nothing to install on the server: the push services of all browsers are on the free-tier allowlist. The server's key is `~/diplomacy-data/vapid_private.pem`; never delete it, or every player has to enable notifications again.

New-phase notifications go out whenever a phase is processed. Reminders, and processing when a deadline passes, need a request to the site, so let a free external scheduler call it every 5 minutes:

1. Generate a token: `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`, put it in `CRON_TOKEN` in the WSGI file (a different value from `DEBUG_TOKEN`: this one is stored on a third-party site) and **Reload**.
2. Check `https://USER.pythonanywhere.com/cron/tick?token=CRON_TOKEN` in a browser: it answers with the current phase as JSON (404 means the token is wrong or not set).
3. On [cron-job.org](https://cron-job.org) (free account): *Create cronjob*, URL as above, every 5 minutes. Turn on its failure notifications so you hear if the site goes down.

Each tick is one small request (in the access log, and in the app log with its result); `/debug/info` shows `cron_token_set`, the reminder hours and every user's devices with the last delivery and error. A device whose last error is `403`/unreachable means PythonAnywhere's proxy refused the push service (check the allowlist); `404`/`410` devices are removed automatically.

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
| Notifications not arriving | `/debug/info` → `push.devices` (last delivery and last error per device), and `Push to` / `Notification` lines in the app log. The *Send me a test notification* button on the Notifications page reports failures directly. |
| Web server / worker problems | **Server log** and **Error log** links on the Web tab |
