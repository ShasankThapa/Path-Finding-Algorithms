import numpy as np
import pytest

from algos.base import run_to_completion
from algos.bidirectional import Bidirect
from algos.jps import JPS
from grid import Grid
from tests.helpers import path_cost, run_to_end
from tests.test_algorithms import ALL_ALGO_SETUPS, make_algo, make_random_grid, wall_in


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_stats_match_the_returned_path(algo_class, movement, seed):
    # JPS ignores mud, so it gets a uniform grid; everything else gets mud.
    grid, start, end = make_random_grid(seed, with_mud=(algo_class is not JPS))
    algo = make_algo(algo_class, movement)
    visited, path = run_to_end(algo, start, end, grid)
    stats = algo.stats

    if path is None:
        assert stats["path_cost"] is None
        assert stats["path_length_cells"] is None
    else:
        assert abs(stats["path_cost"] - path_cost(path, grid)) < 1e-9
        assert stats["path_length_cells"] == len(path)

    if algo_class is Bidirect:
        # A cell reached by both searches is expanded once by each side,
        # but appears only once in the combined visited set.
        assert stats["nodes_expanded"] >= len(visited)
    else:
        assert stats["nodes_expanded"] == len(visited)

    if algo_class is JPS:
        # Every expanded node except the start is a jump point that some scan stepped onto,
        # so it was counted as scanned. The start never is: if it is boxed in, JPS expands
        # 1 node and scans 0 cells (seed 19 is such a case).
        assert stats["cells_scanned"] >= stats["nodes_expanded"] - 1
    else:
        assert stats["cells_scanned"] == stats["nodes_expanded"]


@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_stats_when_no_path(algo_class, movement):
    grid = Grid(10, 10, 1)
    wall_in(grid, (6, 6))
    algo = make_algo(algo_class, movement)
    _, path = run_to_end(algo, (1, 1), (6, 6), grid)
    assert path is None
    assert algo.stats["path_cost"] is None
    assert algo.stats["path_length_cells"] is None
    assert algo.stats["nodes_expanded"] > 0


@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_start_equals_end_costs_nothing(algo_class, movement):
    algo = make_algo(algo_class, movement)
    _, path = run_to_end(algo, (3, 3), (3, 3), Grid(8, 8, 1))
    assert algo.stats["path_cost"] == 0
    assert algo.stats["path_length_cells"] == 1


@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_stats_reset_between_searches(algo_class, movement):
    # Reusing one algorithm object must not add the second search on top of the first.
    algo = make_algo(algo_class, movement)
    grid = Grid(12, 12, 1)
    run_to_end(algo, (0, 0), (11, 11), grid)
    first = dict(algo.stats)
    run_to_end(algo, (0, 0), (11, 11), grid)
    assert algo.stats == first


@pytest.mark.parametrize("algo_class, movement", ALL_ALGO_SETUPS)
def test_run_to_completion_times_search_and_matches_animation(algo_class, movement):
    grid, start, end = make_random_grid(3, with_mud=(algo_class is not JPS))
    timed = make_algo(algo_class, movement)
    animated = make_algo(algo_class, movement)

    _, timed_path = run_to_completion(timed, start, end, grid)
    _, animated_path = run_to_end(animated, start, end, grid)

    assert timed.stats["search_time_ms"] >= 0
    assert animated.stats["search_time_ms"] is None   # only run_to_completion times
    assert timed_path == animated_path
    for key in ["nodes_expanded", "cells_scanned", "path_cost", "path_length_cells"]:
        assert timed.stats[key] == animated.stats[key]


def test_bidirectional_yields_one_visited_set_that_grows():
    # The visited set Bidirectional yields is kept up to date as it goes,
    # instead of a new union being built on every step.
    grid = Grid(10, 10, 1)
    grid.set_cost(5, 5, np.inf)
    sizes = []
    yielded_sets = []
    for visited, path in Bidirect().search((0, 0), (9, 9), grid):
        sizes.append(len(visited))
        yielded_sets.append(visited)
    assert sizes == sorted(sizes)
    assert all(s is yielded_sets[0] for s in yielded_sets)
