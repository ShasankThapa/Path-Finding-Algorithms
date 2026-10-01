import random

import numpy as np
import pytest

from algos.astar import Astar
from algos.bidirectional import Bidirect
from algos.dijkstra import Dijkstra
from algos.jps import JPS
from grid import Grid
from tests.helpers import assert_valid_path, path_cost_4dir, path_cost_8dir, run_to_end
from tests.reference import reference_4dir, reference_8dir

MUD_COST = 3.0
SEEDS = range(50)

FOUR_DIR_ALGOS = [Dijkstra, Astar, Bidirect]
ALL_ALGOS = [Dijkstra, Astar, Bidirect, JPS]


def is_diagonal_algo(algo_class):
    return algo_class is JPS


def make_random_grid(seed, with_mud):
    # Seeded so every failure can be reproduced from the seed in the test name.
    rng = random.Random(seed)
    width = rng.randint(10, 40)
    height = rng.randint(10, 40)
    wall_density = rng.uniform(0.0, 0.35)
    mud_density = rng.uniform(0.0, 0.4) if with_mud else 0.0

    grid = Grid(width, height, 1)
    free_cells = []
    for row in range(height):
        for col in range(width):
            roll = rng.random()
            if roll < wall_density:
                grid.set_cost(row, col, np.inf)
            else:
                free_cells.append((row, col))
                if roll < wall_density + mud_density:
                    grid.set_cost(row, col, MUD_COST)

    start, end = rng.sample(free_cells, 2)

    if with_mud:
        # Cycle through: no forced mud, mud on start, mud on end, mud on both.
        mud_case = seed % 4
        if mud_case in (1, 3):
            grid.set_cost(start[0], start[1], MUD_COST)
        if mud_case in (2, 3):
            grid.set_cost(end[0], end[1], MUD_COST)
        if mud_case == 0:
            grid.set_cost(start[0], start[1], 1)
            grid.set_cost(end[0], end[1], 1)

    return grid, start, end


def wall_in(grid, cell):
    # Surround a cell with walls on all 8 sides so it is unreachable in 4 or 8 directions.
    row, col = cell
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if (dr, dc) != (0, 0):
                grid.set_cost(row + dr, col + dc, np.inf)


def check_against_reference(algo_class, grid, start, end):
    _, path = run_to_end(algo_class(), start, end, grid)

    if is_diagonal_algo(algo_class):
        expected = reference_8dir(grid, start, end)
    else:
        expected = reference_4dir(grid, start, end)

    if expected is None:
        assert path is None, f"reference says unreachable but got path {path}"
        return

    assert path is not None, f"reference cost is {expected} but got no path"
    assert_valid_path(path, grid, start, end, diagonal=is_diagonal_algo(algo_class))

    if is_diagonal_algo(algo_class):
        cost = path_cost_8dir(path)
    else:
        cost = path_cost_4dir(path, grid)
    assert abs(cost - expected) < 1e-9, f"path cost {cost}, optimal is {expected}"


# ---------- Random grids ----------

@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("algo_class", FOUR_DIR_ALGOS, ids=lambda a: a.__name__)
def test_4dir_random_mud_grid(algo_class, seed):
    grid, start, end = make_random_grid(seed, with_mud=True)
    check_against_reference(algo_class, grid, start, end)


@pytest.mark.parametrize("seed", range(200))
@pytest.mark.parametrize("algo_class", FOUR_DIR_ALGOS, ids=lambda a: a.__name__)
def test_4dir_small_grid_mixed_mud_costs(algo_class, seed):
    # Small grids with two different mud costs. With only one mud cost (3), the old
    # Bidirectional backward-cost bug never showed up, so this mixes in cost 7 as well.
    rng = random.Random(seed)
    width = rng.randint(2, 5)
    height = rng.randint(2, 5)
    grid = Grid(width, height, 1)
    free_cells = []
    for row in range(height):
        for col in range(width):
            roll = rng.random()
            if roll < 0.2:
                grid.set_cost(row, col, np.inf)
            else:
                free_cells.append((row, col))
                if roll < 0.6:
                    grid.set_cost(row, col, rng.choice([3.0, 7.0]))

    if len(free_cells) < 2:
        pytest.skip("not enough free cells for a start and an end")
    start, end = rng.sample(free_cells, 2)
    check_against_reference(algo_class, grid, start, end)


@pytest.mark.parametrize("seed", SEEDS)
def test_jps_random_path_is_valid(seed):
    grid, start, end = make_random_grid(seed, with_mud=False)
    if reference_8dir(grid, start, end) is None:
        pytest.skip("unreachable grid, covered by the cost test")
    _, path = run_to_end(JPS(), start, end, grid)
    assert_valid_path(path, grid, start, end, diagonal=True)


@pytest.mark.parametrize("seed", SEEDS)
def test_jps_random_cost(seed):
    # Checked separately from validity so a path-format problem doesn't hide a cost problem.
    grid, start, end = make_random_grid(seed, with_mud=False)
    expected = reference_8dir(grid, start, end)
    _, path = run_to_end(JPS(), start, end, grid)

    if expected is None:
        assert path is None, f"reference says unreachable but got path {path}"
        return

    assert path is not None, f"reference cost is {expected} but got no path"
    cost = path_cost_8dir(path)
    assert abs(cost - expected) < 1e-9, f"path cost {cost}, optimal is {expected}"


# ---------- Edge cases, run for every algorithm ----------

@pytest.mark.parametrize("algo_class", ALL_ALGOS, ids=lambda a: a.__name__)
def test_start_equals_end(algo_class):
    grid = Grid(10, 10, 1)
    _, path = run_to_end(algo_class(), (4, 4), (4, 4), grid)
    assert path == [(4, 4)]


@pytest.mark.parametrize("algo_class", ALL_ALGOS, ids=lambda a: a.__name__)
def test_start_walled_in(algo_class):
    grid = Grid(10, 10, 1)
    wall_in(grid, (4, 4))
    _, path = run_to_end(algo_class(), (4, 4), (8, 8), grid)
    assert path is None


@pytest.mark.parametrize("algo_class", ALL_ALGOS, ids=lambda a: a.__name__)
def test_end_walled_in(algo_class):
    grid = Grid(10, 10, 1)
    wall_in(grid, (6, 6))
    _, path = run_to_end(algo_class(), (1, 1), (6, 6), grid)
    assert path is None


@pytest.mark.parametrize("algo_class", ALL_ALGOS, ids=lambda a: a.__name__)
def test_one_by_one_grid(algo_class):
    grid = Grid(1, 1, 1)
    _, path = run_to_end(algo_class(), (0, 0), (0, 0), grid)
    assert path == [(0, 0)]


@pytest.mark.parametrize("algo_class", ALL_ALGOS, ids=lambda a: a.__name__)
def test_empty_open_grid(algo_class):
    grid = Grid(15, 12, 1)
    check_against_reference(algo_class, grid, (0, 0), (11, 14))
