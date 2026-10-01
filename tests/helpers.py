import math

from tests.reference import is_free


def run_to_end(algo, start, end, grid):
    # Drain the search generator and return the last (visited, path) it yielded.
    visited = set()
    path = None
    for visited, path in algo.search(start, end, grid):
        pass
    return visited, path


def path_cost_4dir(path, grid):
    # Every move costs the value of the cell being entered, so the start cell is not counted.
    total = 0
    for row, col in path[1:]:
        total += grid.get_cost(row, col)
    return total


def path_cost_8dir(path):
    # Cost between consecutive points: diagonal steps cost sqrt(2), straight steps cost 1.
    # For a single step this is just 1 or sqrt(2). It also gives the right cost for a
    # straight or diagonal run, so a path of JPS jump points can still be costed.
    total = 0
    for i in range(len(path) - 1):
        dr = abs(path[i + 1][0] - path[i][0])
        dc = abs(path[i + 1][1] - path[i][1])
        diagonal_steps = min(dr, dc)
        straight_steps = max(dr, dc) - diagonal_steps
        total += diagonal_steps * math.sqrt(2) + straight_steps
    return total


def path_cost(path, grid):
    # For a path of single steps in 4 or 8 directions:
    # each step costs its length (1 or sqrt(2)) times the cost of the cell being entered.
    total = 0
    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        if r1 != r2 and c1 != c2:
            step_length = math.sqrt(2)
        else:
            step_length = 1
        total += step_length * grid.get_cost(r2, c2)
    return total


def assert_valid_path(path, grid, start, end, diagonal):
    assert path is not None, "expected a path but got None"
    assert path[0] == start, f"path starts at {path[0]}, expected {start}"
    assert path[-1] == end, f"path ends at {path[-1]}, expected {end}"

    for row, col in path:
        assert is_free(grid, row, col), f"path enters wall or leaves grid at {(row, col)}"

    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        dr = r2 - r1
        dc = c2 - c1

        if diagonal:
            is_single_step = abs(dr) <= 1 and abs(dc) <= 1 and (dr, dc) != (0, 0)
        else:
            is_single_step = abs(dr) + abs(dc) == 1
        assert is_single_step, f"illegal step {path[i]} -> {path[i + 1]}"

        if dr != 0 and dc != 0:
            assert is_free(grid, r1 + dr, c1) and is_free(grid, r1, c1 + dc), \
                f"diagonal step {path[i]} -> {path[i + 1]} cuts a corner"
