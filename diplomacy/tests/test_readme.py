""" Smoke test: a full game with random valid orders runs to completion and survives a save/load round trip. """
import json
import random

from diplomacy import Game
from diplomacy.utils.export import from_saved_game_format, to_saved_game_format


def test_random_game_completes():
    """ Plays random valid orders until the game ends (as in the README example). """
    random.seed(0)
    game = Game()
    while not game.is_game_done:
        possible_orders = game.get_all_possible_orders()
        for power_name in game.powers:
            power_orders = [random.choice(possible_orders[loc]) for loc in game.get_orderable_locations(power_name)
                            if possible_orders[loc]]
            game.set_orders(power_name, power_orders)
        game.process()

    saved = json.loads(json.dumps(to_saved_game_format(game)))
    loaded = from_saved_game_format(saved)
    assert loaded.is_game_done
    assert loaded.get_current_phase() == game.get_current_phase()
    assert [phase.name for phase in loaded.get_phase_history()] == [phase.name for phase in game.get_phase_history()]
