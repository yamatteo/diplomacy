# ==============================================================================
# Copyright (C) 2019 - Philip Paquette
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU Affero General Public License as published by the Free
#  Software Foundation, either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
#  details.
#
#  You should have received a copy of the GNU Affero General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
""" Module diplomacy, represent strategy game Diplomacy (DATC-compliant rules engine).

    Logging: the 'diplomacy' logger has no handlers of its own; records propagate to the root
    logger, so the web app's handlers (log file + stderr) capture engine logs too.
"""
from .engine.map import Map
from .engine.power import Power
from .engine.game import Game
from .engine.message import Message
from .utils.game_phase_data import GamePhaseData
