import random
from pathlib import Path

import numpy as np
import pytest

from algos.astar import Astar
from algos.base import run_to_completion
from algos.jps import JPS
from maps_io import load_movingai_map, load_scenarios
from tests.helpers import assert_valid_path

MAPS_DIR = Path(__file__).resolve().parent.parent / "maps"
SCENARIOS_PER_MAP = 50
NO_SCENARIOS_MESSAGE = (
    "No Moving AI scenario files found: add <name>.map.scen next to each <name>.map in maps/ "
    "(download from movingai.com/benchmarks)"
)


# ---------- Loader tests on small hand-written files (always run) ----------

def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_load_map_walls_and_passable_cells(tmp_path):
    path = write(tmp_path, "tiny.map", "type octile\nheight 3\nwidth 4\nmap\n.@G.\nS.T.\nOW..\n")
    grid = load_movingai_map(path)
    assert (grid.height, grid.width) == (3, 4)
    walls = {(r, c) for r in range(3) for c in range(4) if grid.is_wall(r, c)}
    # '@', 'T', 'O' and 'W' are walls; '.', 'G' and 'S' are passable.
    assert walls == {(0, 1), (1, 2), (2, 0), (2, 1)}


def test_load_map_rejects_wrong_row_count(tmp_path):
    path = write(tmp_path, "bad.map", "type octile\nheight 3\nwidth 2\nmap\n..\n..\n")
    with pytest.raises(ValueError):
        load_movingai_map(path)


def test_load_map_rejects_wrong_row_width(tmp_path):
    path = write(tmp_path, "bad.map", "type octile\nheight 2\nwidth 3\nmap\n...\n..\n")
    with pytest.raises(ValueError):
        load_movingai_map(path)


def test_scenarios_swap_x_and_y(tmp_path):
    # x is the column and y is the row, so (row, col) = (y, x).
    text = "version 1\n3\ttiny.map\t4\t3\t1\t2\t3\t0\t3.41421356\n"
    path = write(tmp_path, "tiny.map.scen", text)
    scenarios = load_scenarios(path)
    assert len(scenarios) == 1
    scenario = scenarios[0]
    assert scenario.bucket == 3
    assert scenario.map_name == "tiny.map"
    assert scenario.start == (2, 1)
    assert scenario.goal == (0, 3)
    assert scenario.optimal_length == pytest.approx(3.41421356)


# ---------- Checks on the real maps in maps/ ----------

def map_files():
    return sorted(MAPS_DIR.glob("*.map"))


def maps_with_scenarios():
    pairs = []
    for map_path in map_files():
        scenario_path = map_path.with_name(map_path.name + ".scen")
        if scenario_path.exists():
            pairs.append((map_path, scenario_path))
    return pairs


def map_params():
    if not map_files():
        return [pytest.param(None, marks=pytest.mark.skip(reason="maps/ folder has no .map files"))]
    return [pytest.param(path, id=path.name) for path in map_files()]


@pytest.mark.parametrize("map_path", map_params())
def test_real_map_loads_with_matching_size_and_walls(map_path):
    lines = map_path.read_text().splitlines()
    height = int(lines[1].split()[1])
    width = int(lines[2].split()[1])
    body = "".join(lines[4:4 + height])
    expected_free = sum(1 for char in body if char in ".GS")

    grid = load_movingai_map(map_path)
    assert (grid.height, grid.width) == (height, width)
    assert int(np.sum(~np.isinf(grid.grid))) == expected_free


def sample_scenarios(scenarios, count, seed):
    # Pick `count` scenarios spread evenly across the buckets (short paths in low buckets,
    # long paths in high ones), choosing a random unused scenario within each bucket.
    rng = random.Random(seed)
    by_bucket = {}
    for scenario in scenarios:
        by_bucket.setdefault(scenario.bucket, []).append(scenario)
    for bucket_scenarios in by_bucket.values():
        rng.shuffle(bucket_scenarios)
    buckets = sorted(by_bucket)

    sample = []
    for i in range(count):
        bucket = buckets[i * len(buckets) // count]
        if by_bucket[bucket]:
            sample.append(by_bucket[bucket].pop())
    return sample


def scenario_params():
    pairs = maps_with_scenarios()
    if not pairs:
        return [pytest.param(None, None, None, marks=pytest.mark.skip(reason=NO_SCENARIOS_MESSAGE))]
    params = []
    for map_path, scenario_path in pairs:
        for algo_class in (Astar, JPS):
            params.append(pytest.param(map_path, scenario_path, algo_class,
                                       id=f"{map_path.name}-{algo_class.__name__}"))
    return params


@pytest.mark.movingai
@pytest.mark.parametrize("map_path, scenario_path, algo_class", scenario_params())
def test_matches_official_optimal_lengths(map_path, scenario_path, algo_class):
    grid = load_movingai_map(map_path)
    scenarios = load_scenarios(scenario_path)
    sample = sample_scenarios(scenarios, SCENARIOS_PER_MAP, seed=0)

    failures = []
    for scenario in sample:
        if algo_class is JPS:
            algo = JPS()
        else:
            algo = algo_class(8)
        _, path = run_to_completion(algo, scenario.start, scenario.goal, grid)
        if path is None:
            failures.append(f"bucket {scenario.bucket} {scenario.start}->{scenario.goal}: no path, "
                            f"official {scenario.optimal_length}")
            continue
        assert_valid_path(path, grid, scenario.start, scenario.goal, diagonal=True)
        cost = algo.stats["path_cost"]
        if abs(cost - scenario.optimal_length) > 1e-4:
            failures.append(f"bucket {scenario.bucket} {scenario.start}->{scenario.goal}: "
                            f"cost {cost:.6f}, official {scenario.optimal_length:.6f}")

    assert not failures, f"{len(failures)}/{len(sample)} scenarios wrong:\n" + "\n".join(failures)
