# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Simplified fork of [diplomacy/diplomacy](https://github.com/diplomacy/diplomacy) (branch `simple`): its DATC-compliant rules engine (`diplomacy/`) plus a small Flask app (`webapp/`) hosting a single game among friends on the PythonAnywhere free tier: WSGI only (no websockets, no background processes), little CPU, 512 MB disk, internet limited to an allowlist. Upstream's Tornado server/client, network protocol, DAIDE adapter, React UI and Sphinx docs have been removed; they are still in git history (e.g. `git show a5854a2:diplomacy/server/server_game.py`) if something from them is needed. Game state lives in files under `DIPLOMACY_DATA_DIR`; deadlines are checked lazily on each request. Deployment steps: `deploy/PYTHONANYWHERE.md`.

The engine must stay dependency-free (stdlib only): every compiled or extra package is a liability on PythonAnywhere.

## Remote debugging rule (important)

There is **no shell access** to the production server; the only way to diagnose problems there is what the app itself logs and exposes. So **log a lot, and log useful things**:

- Log every state change and decision with the values involved (who, what, which phase, before/after), not just "error occurred". Use `logging.getLogger(__name__)`; never `print`.
- Log full tracebacks for unexpected exceptions (`LOGGER.exception` / the app's error handler does this) and keep the request id: every log line carries `[request_id]` and error pages show it, so a user report can be matched to log lines.
- Log startup context (versions, paths, config) and warn loudly on misconfiguration instead of failing silently.
- Never log secrets (passwords, the debug token): redact them.
- When adding a feature, ask: "if this breaks on the server, will `/debug/logs` and `/debug/info` show why?" If not, add logging or extend `webapp/diagnostics.py`.

## Commands

uv project (`pyproject.toml` / `uv.lock`, both packages installed editable). Keep `requires-python` compatible with 3.13 (PythonAnywhere) and commit `uv.lock` after changing dependencies. PythonAnywhere's preinstalled uv is 0.4.18 (too old for `[dependency-groups]`); the server uses a pip-installed uv from `~/.local/bin`, see `deploy/PYTHONANYWHERE.md`.

```bash
uv sync                                        # .venv with Flask, pytest, diplomacy + webapp
uv run pytest                                  # all tests (~10 s)
uv run pytest diplomacy/tests/test_datc.py::TestDATC::test_6_a_1    # one test
uv run flask --app webapp run --debug          # http://127.0.0.1:5000; logs to instance/logs/app.log
DIPLOMACY_DEBUG_TOKEN=x uv run flask --app webapp run   # enables /debug/info, /debug/logs, /debug/error (?token=x)
```

Convoy paths are precomputed in `diplomacy/maps/convoy_paths_cache.pkl`. A map missing from it gets its paths generated on first load (minutes of CPU on all cores, written to `~/.cache/diplomacy/`), which would exhaust PythonAnywhere's CPU quota; `test_internal_cache` enforces that every `.map` is cached. If tests are unexpectedly slow locally, a stale `~/.cache/diplomacy/` may be hiding such a map.

## Architecture

- **`webapp/`**: Flask app factory `create_app()` (config from `DIPLOMACY_*` env vars, set in the PythonAnywhere WSGI file whose template is `deploy/pythonanywhere_wsgi.py`). Logs go to a rotating file in the data dir and to stderr (the PythonAnywhere error log). Every request is logged with a request id; `/debug/*` endpoints are token-protected and return 404 when the token is unset. `diagnostics.py` collects environment info for startup logs and `/debug/info`.

Engine package (`diplomacy/`, from upstream):

- **`engine/`** — core, network-free game logic. `game.py` (`Game`, ~4.5k lines) holds state, order validation/expansion (`set_orders`), possible-order generation, and adjudication (`process` → `_process` → `_resolve_moves`/`_resolve`). `map.py` parses the text `.map` files in `diplomacy/maps/` (see `README_MAPS.txt`, `README_RULES.txt` for map/rule formats). `renderer.py` produces SVG from `maps/svg/`.
- **`utils/jsonable.py`** — `Jsonable` base class used by `Game`, `Power`, `Message`, `GamePhaseData`. Each subclass declares a `model` dict of typed fields (types from `utils/parsing.py`); `__init__` must set model attributes to `None` before calling `super().__init__(**kwargs)`. Serialization, validation, and defaults all come from `model`.
- **Save/load**: `utils/export.py` `to_saved_game_format()` / `from_saved_game_format()` convert a game (with full phase history) to/from a JSON-able dict.
- `Game` still carries fields for upstream's server features (roles, controllers, registration password, deadlines as seconds); they are inert here.
- Logging: the `diplomacy` logger has no handlers and propagates to the root logger, so engine logs land in the web app's log.

## Tests

- `tests/test_datc.py` holds the DATC adjudication cases; `test_datc_no_check.py` and `test_datc_no_expand.py` subclass it to re-run the suite with order checking/expansion disabled — adjudication changes must pass all three.
- `tests/test_readme.py` plays a full random game and checks the save/load round trip.
- Other unit tests live next to their modules (`utils/tests`, `maps/tests`).
