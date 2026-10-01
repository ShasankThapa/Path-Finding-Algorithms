"""Loading Moving AI Lab benchmark maps and scenarios (movingai.com/benchmarks)."""
import numpy as np

from grid import Grid

# Map characters we can walk on. Everything else ('@', 'O', 'T', 'W', ...) is a wall.
PASSABLE = {".", "G", "S"}


def load_movingai_map(path):
    with open(path) as f:
        lines = f.read().splitlines()

    # Header: "type octile", "height H", "width W", "map", then H rows of W characters.
    if lines[0].strip() != "type octile":
        raise ValueError(f"{path}: expected 'type octile', got {lines[0]!r}")
    height = int(lines[1].split()[1])
    width = int(lines[2].split()[1])
    if lines[3].strip() != "map":
        raise ValueError(f"{path}: expected 'map', got {lines[3]!r}")

    rows = lines[4:4 + height]
    if len(rows) != height:
        raise ValueError(f"{path}: expected {height} rows, found {len(rows)}")

    grid = Grid(width, height, 1)
    for row, text in enumerate(rows):
        if len(text) != width:
            raise ValueError(f"{path}: row {row} has {len(text)} characters, expected {width}")
        for col, char in enumerate(text):
            if char not in PASSABLE:
                grid.set_cost(row, col, np.inf)
    return grid


class Scenario:
    """One start/goal pair from a .scen file, already in our (row, col) convention."""

    def __init__(self, bucket, map_name, start, goal, optimal_length):
        self.bucket = bucket
        self.map_name = map_name
        self.start = start
        self.goal = goal
        self.optimal_length = optimal_length


def load_scenarios(path):
    with open(path) as f:
        lines = f.read().splitlines()

    if not lines[0].startswith("version"):
        raise ValueError(f"{path}: expected a 'version' line first, got {lines[0]!r}")

    scenarios = []
    for line in lines[1:]:
        if not line.strip():
            continue
        # Columns: bucket, map, map width, map height, start x, start y, goal x, goal y, optimal length.
        # Columns are tab-separated; the map name never contains a tab.
        parts = line.split("\t")
        if len(parts) != 9:
            parts = line.split()
        bucket = int(parts[0])
        map_name = parts[1]
        start_x = int(parts[4])
        start_y = int(parts[5])
        goal_x = int(parts[6])
        goal_y = int(parts[7])
        optimal_length = float(parts[8])
        # x is the column and y is the row, so (row, col) = (y, x).
        start = (start_y, start_x)
        goal = (goal_y, goal_x)
        scenarios.append(Scenario(bucket, map_name, start, goal, optimal_length))
    return scenarios
