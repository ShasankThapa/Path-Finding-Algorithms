import random

import numpy as np
import pytest

from algos.astar import Astar
from algos.bidirectional import Bidirect
from algos.dijkstra import Dijkstra
from algos.jps import JPS, forced_neighbours
from grid import Grid
from tests.helpers import assert_valid_path, path_cost, path_cost_8dir, run_to_end
from tests.reference import reference_4dir, reference_8dir

MUD_COST = 3.0
SEEDS = range(50)

# (algorithm, movement) pairs. Dijkstra, A* and Bidirectional run in both modes and
# are tested with mud. JPS is always 8-directional and only tested on uniform grids.
MUD_ALGO_SETUPS = [
    pytest.param(Dijkstra, 4, id="Dijkstra-4dir"),
    pytest.param(Dijkstra, 8, id="Dijkstra-8dir"),
    pytest.param(Astar, 4, id="Astar-4dir"),
    pytest.param(Astar, 8, id="Astar-8dir"),
    pytest.param(Bidirect, 4, id="Bidirect-4dir"),
    pytest.param(Bidirect, 8, id="Bidirect-8dir"),
]
ALL_ALGO_SETUPS = MUD_ALGO_SETUPS + [pytest.param(JPS, 8, id="JPS")]


def make_algo(algo_class, movement):
    if algo_class is JPS:
        return JPS()
    return algo_class(movement)


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


def check_against_reference(algo_class, movement, grid, start, end):
    _, path = run_to_end(make_algo(algo_class, movement), start, end, grid)

    if movement == 8:
        expected = reference_8dir(grid, start, end)
    else:
        expected = reference_4dir(grid, start, end)

    if expected is None:
        assert path is None, f"reference says unreachable but got path {path}"
        return

    assert path is not None, f"reference cost is {expected} but got no path"
    assert_valid_path(path, grid, start, end, diagonal=(movement == 8))

    cost = path_cost(path, grid)
    assert abs(cost - expected) < 1e-9, f"path cost {cost}, optimal is {expected}"


# ---------- Random grids ----------

@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("algo_class, movement", MUD_ALGO_SETUPS)
def test_random_mud_grid(algo_class, movement, seed):
    grid, start, end = make_random_grid(seed, with_mud=True)
    check_against_reference(algo_class, movement, grid, start, end)


@pytest.mark.parametrize("seed", range(200))
@pytest.mark.parametrize("algo_class, movement", MUD_ALGO_SETUPS)
def test_small_grid_mixed_mud_costs(algo_class, movement, seed):
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
    check_against_reference(algo_class, movement, grid, start, end)


@pytest.mark.parametrize("algo_class, movement", MUD_ALGO_SETUPS)
def test_mud_on_start_and_end_regression(algo_class, movement):
    # 2x2 grid, start top-left, end bottom-left, both on heavy mud (cost 7):
    #   S=7  1
    #   E=7  1
    # Going straight down costs 7 (we pay for entering the end cell).
    # The detour right, down, left costs 1 + 1 + 7 = 9.
    # The old Bidirectional backward search charged the neighbour's cost instead of the
    # current cell's, so it scored the detour as 3 and returned it.
    # In 8-dir mode the diagonal shortcut (0,0) -> (1,1) -> (1,0) costs sqrt(2) + 7, still worse.
    grid = Grid(2, 2, 1)
    grid.set_cost(0, 0, 7.0)
    grid.set_cost(1, 0, 7.0)
    _, path = run_to_end(make_algo(algo_class, movement), (0, 0), (1, 0), grid)
    assert path == [(0, 0), (1, 0)]
    assert path_cost(path, grid) == 7


@pytest.mark.parametrize("algo_class", [Dijkstra, Astar, Bidirect], ids=lambda a: a.__name__)
def test_default_movement_is_4dir(algo_class):
    # Creating an algorithm with no arguments must keep the original 4-directional behaviour.
    grid = Grid(8, 8, 1)
    _, path = run_to_end(algo_class(), (0, 0), (7, 7), grid)
    assert_valid_path(path, grid, (0, 0), (7, 7), diagonal=False)
    assert path_cost(path, grid) == reference_4dir(grid, (0, 0), (7, 7))


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


def test_jps_long_corridor_does_not_hit_recursion_limit():
    # A 1 x 1500 corridor. The old recursive jump() made one call per cell and raised
    # RecursionError here (Python's default limit is 1000).
    grid = Grid(1500, 1, 1)
    _, path = run_to_end(JPS(), (0, 0), (0, 1499), grid)
    assert len(path) == 1500


def test_jps_keeps_forced_neighbours_on_both_sides():
    # Moving right into C. The cells behind-above and behind-below are walls, and the
    # cells above and below C are open, so both of them are forced neighbours:
    #   #  .  .
    #   >  C  .
    #   #  .  .
    grid = Grid(3, 3, 1)
    grid.set_cost(0, 0, np.inf)
    grid.set_cost(2, 0, np.inf)
    forced = forced_neighbours((1, 1), grid, (0, 1))
    assert (0, 1) in forced
    assert (2, 1) in forced


def test_jps_counts_nodes_expanded_and_cells_scanned():
    # 1 x 10 corridor. JPS expands only the start and the goal, but the jump to the
    # right steps through all 9 cells after the start to get there.
    grid = Grid(10, 1, 1)
    jps = JPS()
    visited, path = run_to_end(jps, (0, 0), (0, 9), grid)
    assert jps.nodes_expanded == 2
    assert jps.nodes_expanded == len(visited)
    assert jps.cells_scanned == 9


# ---------- Edge cases, run for every algorithm ----------

@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_start_equals_end(algo_class, movement):
    grid = Grid(10, 10, 1)
    _, path = run_to_end(make_algo(algo_class, movement), (4, 4), (4, 4), grid)
    assert path == [(4, 4)]


@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_start_walled_in(algo_class, movement):
    grid = Grid(10, 10, 1)
    wall_in(grid, (4, 4))
    _, path = run_to_end(make_algo(algo_class, movement), (4, 4), (8, 8), grid)
    assert path is None


@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_end_walled_in(algo_class, movement):
    grid = Grid(10, 10, 1)
    wall_in(grid, (6, 6))
    _, path = run_to_end(make_algo(algo_class, movement), (1, 1), (6, 6), grid)
    assert path is None


@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_one_by_one_grid(algo_class, movement):
    grid = Grid(1, 1, 1)
    _, path = run_to_end(make_algo(algo_class, movement), (0, 0), (0, 0), grid)
    assert path == [(0, 0)]


@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_empty_open_grid(algo_class, movement):
    grid = Grid(15, 12, 1)
    check_against_reference(algo_class, movement, grid, (0, 0), (11, 14))
