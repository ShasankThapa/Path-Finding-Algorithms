"""Test 1: tiny maps where I already know the right answer.

Each map here is small enough to work out the answer on paper first.
Then I check that every algorithm comes up with that same answer.
I also try the awkward cases, like a start that's completely walled in,
because that's usually where bugs hide.
"""
import math

import numpy as np

from algos.astar import Astar
from algos.bidirectional import Bidirect
from algos.dijkstra import Dijkstra
from algos.jps import JPS
from grid import Grid

MUD = 3.0


def run(algo, start, end, grid):
    # Let the search run all the way to the end, then hand back the path it found.
    # If there's no way through, the path comes back as None.
    path = None
    for visited, path in algo.search(start, end, grid):
        pass
    return path


def test_small_grids_with_known_answers():

    # These three only move up, down, left and right, and they understand mud.
    for algo in [Dijkstra(4), Astar(4), Bidirect(4)]:

        # An empty 5x5 map. Going from one corner to the opposite corner
        # takes 4 steps right and 4 steps down, so it should cost 8.
        grid = Grid(5, 5, 1)
        run(algo, (0, 0), (4, 4), grid)
        assert algo.stats["path_cost"] == 8

        # A wall runs down the middle column, with a gap only at the bottom.
        # The only way across is down 4, across 4, then back up 4, so 12 in total.
        # I also check the path never walks through the wall.
        grid = Grid(5, 5, 1)
        for row in range(4):
            grid.set_cost(row, 2, np.inf)
        path = run(algo, (0, 0), (0, 4), grid)
        assert algo.stats["path_cost"] == 12
        for cell in path:
            assert not grid.is_wall(cell[0], cell[1])

        # Two mud cells sit right in the way:
        #   S  M  M  E      walking straight through the mud costs 3 + 3 + 1 = 7
        #   .  .  .  .      going round underneath costs 1 + 1 + 1 + 1 + 1 = 5
        # Going round is cheaper, so the path should avoid the mud completely.
        grid = Grid(4, 2, 1)
        grid.set_cost(0, 1, MUD)
        grid.set_cost(0, 2, MUD)
        path = run(algo, (0, 0), (0, 3), grid)
        assert algo.stats["path_cost"] == 5
        assert (0, 1) not in path and (0, 2) not in path

        # Very heavy mud (cost 7) on both the start and the end:
        #   S=7  1      stepping straight down costs 7 (you only pay to enter E)
        #   E=7  1      going round the right side costs 1 + 1 + 7 = 9
        # Straight down is cheaper. This little map found a real bug where
        # the bidirectional search was adding up the costs in the wrong place.
        grid = Grid(2, 2, 1)
        grid.set_cost(0, 0, 7.0)
        grid.set_cost(1, 0, 7.0)
        path = run(algo, (0, 0), (1, 0), grid)
        assert algo.stats["path_cost"] == 7
        assert path == [(0, 0), (1, 0)]

    # These four can also move diagonally.
    for algo in [Dijkstra(8), Astar(8), Bidirect(8), JPS()]:

        # An empty 5x5 map again. This time the quickest way is 4 diagonal steps,
        # and each diagonal step is sqrt(2) long, so the cost is 4 x sqrt(2).
        grid = Grid(5, 5, 1)
        run(algo, (0, 0), (4, 4), grid)
        assert abs(algo.stats["path_cost"] - 4 * math.sqrt(2)) < 1e-9

        # Two walls touch at their corners:
        #   S  #
        #   #  E
        # You're not allowed to squeeze diagonally through that gap
        # (that would be "cutting the corner"), so there should be no path at all.
        grid = Grid(2, 2, 1)
        grid.set_cost(0, 1, np.inf)
        grid.set_cost(1, 0, np.inf)
        assert run(algo, (0, 0), (1, 1), grid) is None

    # The awkward cases. Every algorithm has to handle these.
    for algo in [Dijkstra(4), Astar(4), Bidirect(4), Dijkstra(8), Astar(8), Bidirect(8), JPS()]:

        # The start is boxed in by walls, so there's no way out.
        # The algorithm should simply say "no path" rather than crash.
        # (The bidirectional search used to crash on exactly this.)
        grid = Grid(5, 5, 1)
        grid.set_cost(0, 1, np.inf)
        grid.set_cost(1, 0, np.inf)
        grid.set_cost(1, 1, np.inf)
        assert run(algo, (0, 0), (4, 4), grid) is None

        # The start and the end are the same cell. You're already there,
        # so the path is just that one cell and it costs nothing.
        grid = Grid(5, 5, 1)
        assert run(algo, (2, 2), (2, 2), grid) == [(2, 2)]
        assert algo.stats["path_cost"] == 0
