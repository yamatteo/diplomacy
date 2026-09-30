# Diplomacy (simple)

A trimmed-down fork of [diplomacy/diplomacy](https://github.com/diplomacy/diplomacy): its DATC-compliant Diplomacy rules engine, plus a small Flask web app for playing **one game at a time with friends**, sized to run on the [PythonAnywhere](https://www.pythonanywhere.com) free tier.

Upstream's network server/client, React web interface, DAIDE bot adapter and documentation site were removed. The engine has no third-party dependencies.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                  # create .venv and install everything
uv run pytest                            # run the tests
uv run flask --app webapp run --debug    # web app on http://127.0.0.1:5000
```

## How it plays

- Players are listed in a plain text file (`users.txt` in the data folder): `username:password:POWERS` (comma separated for several countries), with `:admin` for admins. The admin picks 2-7 players when starting a game. On first start the app creates it with a random-password `admin`.
- An admin starts the game and sets how long each kind of phase lasts.
- Each player picks orders for their units from menus of legal orders. Orders stay secret until the phase is processed.
- A phase is processed as soon as every player is marked ready, or when its deadline passes (checked whenever someone opens a page).
- Past phases, with everyone's orders and results, are under History.

## Using the engine directly

```python
import random
from diplomacy import Game
from diplomacy.utils.export import to_saved_game_format

game = Game()                      # or Game(map_name='pure')
while not game.is_game_done:
    possible_orders = game.get_all_possible_orders()
    for power_name in game.powers:
        orders = [random.choice(possible_orders[loc]) for loc in game.get_orderable_locations(power_name)
                  if possible_orders[loc]]
        game.set_orders(power_name, orders)
    game.process()

to_saved_game_format(game, output_path='game.json')
```

## Deployment

See [deploy/PYTHONANYWHERE.md](deploy/PYTHONANYWHERE.md).

## License

AGPLv3, see [LICENSE](LICENSE). Original engine by Philip Paquette, Steven Bocco and contributors (see [ACKNOWLEDGEMENTS](ACKNOWLEDGEMENTS)).
