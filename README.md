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
