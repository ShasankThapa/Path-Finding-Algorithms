import math

# Heuristics estimate the cost from a cell to the end. A* and JPS use them to decide
# which cell to explore next. A heuristic must never overestimate the real cost,
# otherwise A* might return a path that isn't the cheapest.


def manhattan(cell, end):
    # Fewest steps between two cells when only straight moves (cost 1) are allowed.
    # Rows apart + columns apart.
    return abs(cell[0] - end[0]) + abs(cell[1] - end[1])


def octile(cell, end):
    # Shortest distance between two cells when diagonal moves (cost sqrt(2)) are also allowed:
    # take min(dr, dc) diagonal steps, then the rest straight. This is exact on an empty grid,
    # and walls or mud (cost >= 1) can only make the real path more expensive, so it never
    # overestimates.
    dr = abs(cell[0] - end[0])
    dc = abs(cell[1] - end[1])
    return max(dr, dc) + (math.sqrt(2) - 1) * min(dr, dc)
