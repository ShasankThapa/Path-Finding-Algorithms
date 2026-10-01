import math

import numpy as np
import pytest

from grid import Grid, get_neighbours


def test_4dir_neighbours_skip_walls_and_edges():
    grid = Grid(3, 3, 1)
    grid.set_cost(0, 1, np.inf)
    neighbours = get_neighbours(0, 0, grid, 4)
    # (0, 1) is a wall and (-1, 0), (0, -1) are off the grid, so only (1, 0) is left.
    assert neighbours == [((1, 0), 1)]


def test_8dir_open_cell_has_eight_neighbours():
    grid = Grid(3, 3, 1)
    neighbours = get_neighbours(1, 1, grid, 8)
    assert len(neighbours) == 8
    for (r, c), step_length in neighbours:
        if r != 1 and c != 1:
            assert step_length == math.sqrt(2)
        else:
            assert step_length == 1


def test_8dir_no_corner_cutting():
    # A wall above the centre blocks both diagonals that would squeeze past it:
    #   .  #  .
    #   .  C  .
    #   .  .  .
    grid = Grid(3, 3, 1)
    grid.set_cost(0, 1, np.inf)
    cells = [cell for cell, step_length in get_neighbours(1, 1, grid, 8)]
    assert (0, 0) not in cells
    assert (0, 2) not in cells
    assert (2, 0) in cells
    assert (2, 2) in cells


def test_invalid_movement_raises():
    with pytest.raises(ValueError):
        get_neighbours(0, 0, Grid(3, 3, 1), 6)
