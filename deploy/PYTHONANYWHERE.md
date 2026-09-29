# Deploying on PythonAnywhere (free tier)

Replace `USER` below with your PythonAnywhere username.

## First install

1. **Account → System image**: make sure it is `innit` (Python 3.13, uv available). Accounts created after March 2025 already have it.
2. **Consoles → Bash**, then:
   ```bash
   git clone -b simple https://github.com/yamatteo/diplomacy.git ~/diplomacy
   cd ~/diplomacy
   uv --version || pip install --user uv      # astral.sh is not allowlisted: install from PyPI, not with curl
   uv sync --locked --python /usr/bin/python3.13
   uv cache clean                             # the cache counts against the 512 MB disk quota
   python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # copy this: it is your debug token
   ```
   If `uv sync` complains about the lockfile format, the preinstalled uv is too old: `pip install --user --upgrade uv`.
3. **Web → Add a new web app** → *Manual configuration* (not the Flask quickstart) → **Python 3.13**.
4. On the Web tab set:
   - **Source code** and **Working directory**: `/home/USER/diplomacy`
   - **Virtualenv**: `/home/USER/diplomacy/.venv`
   - **Force HTTPS**: enabled (the debug token travels in the URL).
5. Click the **WSGI configuration file** link, replace its entire content with `deploy/pythonanywhere_wsgi.py` from this repo, and set `USERNAME` and `DIPLOMACY_DEBUG_TOKEN`.
6. Click **Reload**, then open:
   - `https://USER.pythonanywhere.com/`: should say "Diplomacy server is running"
   - `https://USER.pythonanywhere.com/healthz`
   - `https://USER.pythonanywhere.com/debug/info?token=TOKEN`: check `in_virtualenv: true`, the Python version and the git commit.

## Updating

```bash
cd ~/diplomacy && git pull && uv sync --locked --python /usr/bin/python3.13 && uv cache clean
touch /var/www/USER_pythonanywhere_com_wsgi.py     # reloads the web app (same as the Reload button)
```

## When something breaks

Send Claude the output of these; together they replace shell access to the server.

| What | Where |
|---|---|
| App can't start (import error, bad venv) | The site itself shows the traceback, python path and sys.prefix. Also in the **Error log** (Web tab). |
| Environment (Python, venv, git commit, package versions, data dir) | `/debug/info?token=TOKEN` |
| Application log (every request, startup, tracebacks tagged with request id) | `/debug/logs?token=TOKEN&lines=500`, or file `~/diplomacy-data/logs/app.log` |
| A user sees "Internal error … request id abc123" | Search the app log for `[abc123]` |
| Check that error logging works end to end | `/debug/error?token=TOKEN` (fails on purpose) |
| Web server / worker problems | **Server log** and **Error log** links on the Web tab |
