from types import SimpleNamespace

import pygame
import pytest

import race
from algos.jps import JPS
from tests.helpers import path_cost
from tests.reference import reference_4dir, reference_8dir
from tests.test_algorithms import make_random_grid

AREA = pygame.Rect(0, 0, 850, 800)


def fake_racer(label, finished, steps):
    return SimpleNamespace(label=label, finished=finished, steps=steps)


def test_positions_rank_by_steps():
    racers = [
        fake_racer("slow", True, 300),
        fake_racer("fast", True, 10),
        fake_racer("running", False, 50),
        fake_racer("middle", True, 120),
    ]
    assert race.finishing_positions(racers) == {"fast": 1, "middle": 2, "slow": 3}


def test_equal_steps_share_a_position():
    racers = [fake_racer("a", True, 40), fake_racer("b", True, 40), fake_racer("c", True, 90)]
    assert race.finishing_positions(racers) == {"a": 1, "b": 1, "c": 3}


def test_panels_are_a_2x2_split():
    panels = race.split_into_panels(AREA, 4)
    assert [(p.x, p.y, p.width, p.height) for p in panels] == [
        (0, 0, 425, 400), (425, 0, 425, 400), (0, 400, 425, 400), (425, 400, 425, 400),
    ]


def count_yields(algo, start, end, grid):
    count = 0
    for _ in algo.search(start, end, grid):
        count += 1
    return count


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("speed", [1, 7])
def test_race_runs_in_lockstep_and_finishes_correctly(seed, speed):
    # JPS ignores mud, so odd seeds use a mud-free map where A* 8-dir and JPS
    # solve the same problem; even seeds have mud.
    grid, start, end = make_random_grid(seed, with_mud=(seed % 2 == 0))
    racers = race.make_racers(grid, AREA)
    for racer in racers:
        racer.start(grid, start, end)

    ticks = 0
    while not all(racer.finished for racer in racers):
        race.advance_all(racers, speed)
        ticks += 1
        for racer in racers:
            if not racer.finished:
                # Everyone still racing has taken exactly the same number of steps.
                assert racer.steps == ticks * speed

    for racer in racers:
        # A racer's step count is exactly the number of yields its search makes.
        fresh = race.make_algorithm(racer.algo_class, racer.movement)
        assert racer.steps == count_yields(fresh, start, end, grid)

        if racer.algo_class is JPS:
            if seed % 2 == 0:
                continue   # JPS cost on a mud map isn't comparable to anything
            expected = reference_8dir(grid, start, end)
        elif racer.movement == 8:
            expected = reference_8dir(grid, start, end)
        else:
            expected = reference_4dir(grid, start, end)

        if expected is None:
            assert racer.path is None
        else:
            assert abs(path_cost(racer.path, grid) - expected) < 1e-9
