"""Test 2: checking my answers against the official ones.

The Moving AI Lab (movingai.com) publishes real game maps along with lists of
start and goal points, and the correct cheapest cost for each one. Because
those answers come from outside this project, they're a fair way to check
that my algorithms really work.
"""
from algos.astar import Astar
from algos.bidirectional import Bidirect
from algos.dijkstra import Dijkstra
from algos.jps import JPS
from maps_io import load_movingai_map, load_scenarios


def run(algo, start, end, grid):
    # Let the search run all the way to the end, then hand back the path it found.
    # If there's no way through, the path comes back as None.
    path = None
    for visited, path in algo.search(start, end, grid):
        pass
    return path


def test_matches_official_moving_ai_answers():
    # den312d is a small map from the game Dragon Age: Origins. It comes with
    # 290 start and goal pairs, each with the official cheapest cost.
    grid = load_movingai_map("maps/den312d.map")
    scenarios = load_scenarios("maps/den312d.map.scen")

    # The official answers allow diagonal moves, so only the algorithms
    # that can move diagonally are checked here.
    for algo in [Dijkstra(8), Astar(8), Bidirect(8), JPS()]:
        for scenario in scenarios:
            run(algo, scenario.start, scenario.goal, grid)

            # The official file rounds each answer to 8 decimal places,
            # so I allow for a tiny difference instead of demanding an exact match.
            assert abs(algo.stats["path_cost"] - scenario.optimal_length) < 1e-4
