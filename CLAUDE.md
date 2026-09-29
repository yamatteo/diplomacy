# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

DATC-compliant Diplomacy game engine (Python package `diplomacy`) plus a Tornado websocket client/server for network play, a React web UI (`diplomacy/web`), and a DAIDE adapter for DAIDE bots. Originally targeted Python 3.5–3.7. Full docs: https://diplomacy.readthedocs.io.

**Direction (branch `simple`):** turning this into a small Flask app (`webapp/`) that hosts a single game among friends on the PythonAnywhere free tier: WSGI only (no websockets, no background processes), little CPU, 512 MB disk, internet limited to an allowlist. The plan is to reuse `diplomacy/engine/` and drop the Tornado server/client, communication protocol, DAIDE and React UI. Game state lives in files under `DIPLOMACY_DATA_DIR`; deadlines are checked lazily on each request. Deployment steps: `deploy/PYTHONANYWHERE.md`.

## Remote debugging rule (important)

There is **no shell access** to the production server; the only way to diagnose problems there is what the app itself logs and exposes. So **log a lot, and log useful things**:

- Log every state change and decision with the values involved (who, what, which phase, before/after), not just "error occurred". Use `logging.getLogger(__name__)`; never `print`.
- Log full tracebacks for unexpected exceptions (`LOGGER.exception` / the app's error handler does this) and keep the request id: every log line carries `[request_id]` and error pages show it, so a user report can be matched to log lines.
- Log startup context (versions, paths, config) and warn loudly on misconfiguration instead of failing silently.
- Never log secrets (passwords, the debug token): redact them.
- When adding a feature, ask: "if this breaks on the server, will `/debug/logs` and `/debug/info` show why?" If not, add logging or extend `webapp/diagnostics.py`.

## Commands

```bash
# New web app (uv project, pyproject.toml / uv.lock; keep requires-python compatible with 3.13 for PythonAnywhere)
uv sync                                        # create .venv with Flask + webapp (editable)
uv run flask --app webapp run --debug          # http://127.0.0.1:5000; logs to instance/logs/app.log
DIPLOMACY_DEBUG_TOKEN=x uv run flask --app webapp run   # enables /debug/info, /debug/logs, /debug/error (?token=x)

# Legacy package
pip install -r requirements_dev.txt        # installs package in editable mode + pytest/pylint/sphinx

./run_tests.sh             # pytest (parallel, --forked) + pylint + sphinx build + eslint/npm build (if node_modules present)
./run_tests.sh 4           # same, pytest on 4 cores
./run_tests.sh 0           # skip pytest; lint/docs only

pytest diplomacy/tests/test_datc.py                          # one file
pytest diplomacy/tests/test_datc.py::TestDATC::test_6_a_1    # one test
pylint diplomacy/engine/game.py                              # lint (config: .pylintrc; files named _*.py / zzz_*.py are excluded)

python -m diplomacy.server.run [--port 8432]   # game server; stores data in ./data of the cwd
cd diplomacy/web && npm install && npm start   # React UI on http://localhost:3000 (login admin/password)
```

Convoy paths are precomputed and cached (`diplomacy/maps/convoy_paths_cache.pkl`, or `~/.cache/diplomacy/`); if missing for a map, they are computed on first use, which is slow.

## Architecture

- **`webapp/`**: Flask app factory `create_app()` (config from `DIPLOMACY_*` env vars, set in the PythonAnywhere WSGI file whose template is `deploy/pythonanywhere_wsgi.py`). Logs go to a rotating file in the data dir and to stderr (the PythonAnywhere error log). Every request is logged with a request id; `/debug/*` endpoints are token-protected and return 404 when the token is unset. `diagnostics.py` collects environment info for startup logs and `/debug/info`.

Legacy package (`diplomacy/`):

- **`engine/`** — core, network-free game logic. `game.py` (`Game`, ~4.5k lines) holds state, order validation/expansion (`set_orders`), possible-order generation, and adjudication (`process` → `_process` → `_resolve_moves`/`_resolve`). `map.py` parses the text `.map` files in `diplomacy/maps/` (see `README_MAPS.txt`, `README_RULES.txt` for map/rule formats). `renderer.py` produces SVG from `maps/svg/`.
- **`utils/jsonable.py`** — `Jsonable` base class used by `Game`, `Power`, `Message`, and every request/response/notification. Each subclass declares a `model` dict of typed fields (types from `utils/parsing.py`); `__init__` must set model attributes to `None` before calling `super().__init__(**kwargs)`. Serialization, validation, and defaults all come from `model`.
- **Game subclasses**: `server/server_game.py:ServerGame` and `client/network_game.py:NetworkGame` both extend `engine.Game`. Network games mirror state locally and forward actions (e.g. `set_orders`) to the server as requests.
- **Protocol**: `communication/requests.py`, `responses.py`, `notifications.py` define all message types. Server dispatch is `server/request_managers.py` (`MAPPING` of request class → handler); server push is `server/notifier.py`. Client side: `client/connection.py` → `channel.py` (authenticated) → `NetworkGame`, with `response_managers.py` / `notification_managers.py` applying results to local game instances.
- **`daide/`** — separate TCP server translating DAIDE tokens/messages to the internal request API; tests replay CSV game logs in `daide/tests/`.
- **`web/`** — create-react-app. `web/src/diplomacy/` is a hand-maintained JS port of the Python client/communication/engine layers (keep them in sync when changing the protocol); `web/src/diplomacy/maps` is a symlink to `diplomacy/maps`. `web/src/gui/maps/*` React map components are generated from SVGs by `web/convert_svg_maps_to_react.sh` (`svg_to_react.py`).
- **`integration/`** — API client for webdiplomacy.net.

## Tests

- `tests/test_datc.py` holds the DATC adjudication cases; `test_datc_no_check.py` and `test_datc_no_expand.py` subclass it to re-run the suite with order checking/expansion disabled — adjudication changes must pass all three.
- `tests/network/test_real_game.py` spins up a real server and replays recorded games (`1.json`…`3.json`).
- Other unit tests live next to their modules (`utils/tests`, `maps/tests`, `daide/tests`).
