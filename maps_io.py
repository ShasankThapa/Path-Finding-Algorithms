"""Loading Moving AI Lab benchmark maps and scenarios (movingai.com/benchmarks)."""
# This file is basically the translator. Moving AI give you maps and test cases as
# plain text files. This turns them into stuff the rest of the project understands:
# a Grid for the map, and a list of Scenario objects for the start/goal tests.
import numpy as np

from grid import Grid

# Map characters we can walk on. Everything else ('@', 'O', 'T', 'W', ...) is a wall.
# '.' is normal floor, 'G' and 'S' are grass/swamp in the original games, but for
# the benchmark they all count as plain walkable ground costing 1.
PASSABLE = {".", "G", "S"}


# ---------------------------------------------------------------------------
# Loading a .map file -> Grid
# ---------------------------------------------------------------------------

def load_movingai_map(path):
    # Read the whole file and chop it into a list of lines (no '\n' on the ends).
    with open(path) as f:
        lines = f.read().splitlines()

    # A .map file always starts with 4 header lines, like this:
    #   type octile
    #   height 81
    #   width 65
    #   map
    # ...and then the actual map, one row of characters per line.

    # Line 0: make sure this is actually a Moving AI map, not some random file.
    if lines[0].strip() != "type octile":
        raise ValueError(f"{path}: expected 'type octile', got {lines[0]!r}")
    # Lines 1 and 2: "height 81".split() -> ["height", "81"], so [1] is the number.
    height = int(lines[1].split()[1])
    width = int(lines[2].split()[1])
    # Line 3: should just say "map". Everything after it is the grid itself.
    if lines[3].strip() != "map":
        raise ValueError(f"{path}: expected 'map', got {lines[3]!r}")

    # Skip the 4 header lines and grab exactly `height` rows of map.
    rows = lines[4:4 + height]
    # If the file got cut short, shout about it now rather than crash weirdly later.
    if len(rows) != height:
        raise ValueError(f"{path}: expected {height} rows, found {len(rows)}")

    # Start with a grid where every cell is floor (cost 1)...
    grid = Grid(width, height, 1)
    # ...then go through it cell by cell and turn anything not walkable into a wall.
    # enumerate gives us the row number, then the column number, with the character.
    for row, text in enumerate(rows):
        # Every row should be the same width, otherwise the file's broken.
        if len(text) != width:
            raise ValueError(f"{path}: row {row} has {len(text)} characters, expected {width}")
        for col, char in enumerate(text):
            # Not floor? Make it a wall (infinite cost = can never walk there).
            if char not in PASSABLE:
                grid.set_cost(row, col, np.inf)
    return grid


# ---------------------------------------------------------------------------
# Loading a .scen file -> list of Scenario
# ---------------------------------------------------------------------------

class Scenario:
    """One start/goal pair from a .scen file, already in our (row, col) convention."""

    # Just a little box holding one test journey: where to start, where to finish,
    # and what the correct shortest cost should be. No logic, it only stores stuff.
    def __init__(self, bucket, map_name, start, goal, optimal_length):
        self.bucket = bucket                  # length group: 0 = short trips, bigger = longer
        self.map_name = map_name              # which map this journey is on
        self.start = start                    # (row, col)
        self.goal = goal                      # (row, col)
        self.optimal_length = optimal_length  # the right answer, our algorithms must match it


def load_scenarios(path):
    # Same as before: read the file into a list of lines.
    with open(path) as f:
        lines = f.read().splitlines()

    # First line is always something like "version 1". Check it's there, then ignore it.
    if not lines[0].startswith("version"):
        raise ValueError(f"{path}: expected a 'version' line first, got {lines[0]!r}")

    scenarios = []
    # Every line after "version" is one journey.
    for line in lines[1:]:
        # Blank line (usually one at the end of the file)? Skip it.
        if not line.strip():
            continue
        # Columns: bucket, map, map width, map height, start x, start y, goal x, goal y, optimal length.
        # Columns are tab-separated; the map name never contains a tab.
        # Real example:  0  den312d.map  65  81  61  72  60  72  1.00000000
        parts = line.split("\t")
        # Some files use spaces instead of tabs, so if tabs didn't give 9 bits, try spaces.
        if len(parts) != 9:
            parts = line.split()
        # Pull each column out and turn the text into proper numbers.
        # (parts[2] and parts[3] are the map width/height, we don't need them here.)
        bucket = int(parts[0])
        map_name = parts[1]
        start_x = int(parts[4])
        start_y = int(parts[5])
        goal_x = int(parts[6])
        goal_y = int(parts[7])
        optimal_length = float(parts[8])
        # x is the column and y is the row, so (row, col) = (y, x).
        # Easy one to get wrong: x=61, y=72 becomes (72, 61) for us.
        start = (start_y, start_x)
        goal = (goal_y, goal_x)
        # Box it up and add it to the list.
        scenarios.append(Scenario(bucket, map_name, start, goal, optimal_length))
    # e.g. den312d.map.scen gives back 290 of these.
    return scenarios
