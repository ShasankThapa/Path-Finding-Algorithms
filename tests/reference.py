"""Deliberately simple reference solvers used to check the real algorithms.

Both return the optimal path cost from start to end, or None if end is unreachable.
They are written independently of the code in algos/ so a bug there is not copied here.
"""
import heapq
import math


def reference_4dir(grid, start, end):
    # Plain Dijkstra. Moving into a cell costs that cell's value (same model as algos/).
    best_cost = {start: 0}
    queue = [(0, start)]
    done = set()

    while queue:
        cost, cell = heapq.heappop(queue)
        if cell in done:
            continue
        done.add(cell)

        if cell == end:
            return cost

        row, col = cell
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            r = row + dr
            c = col + dc
            if r < 0 or r >= grid.height or c < 0 or c >= grid.width:
                continue
            if grid.is_wall(r, c):
                continue
            new_cost = cost + grid.get_cost(r, c)
            if new_cost < best_cost.get((r, c), math.inf):
                best_cost[(r, c)] = new_cost
                heapq.heappush(queue, (new_cost, (r, c)))

    return None


def reference_8dir(grid, start, end):
    # Plain Dijkstra, 8 directions: straight step length = 1, diagonal = sqrt(2).
    # Move cost = step length * cost of the cell entered (so mud works too).
    # No corner cutting: a diagonal move needs both orthogonal cells next to it to be free.
    best_cost = {start: 0}
    queue = [(0, start)]
    done = set()

    while queue:
        cost, cell = heapq.heappop(queue)
        if cell in done:
            continue
        done.add(cell)

        if cell == end:
            return cost

        row, col = cell
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                r = row + dr
                c = col + dc
                if not is_free(grid, r, c):
                    continue

                if dr != 0 and dc != 0:
                    if not is_free(grid, row + dr, col) or not is_free(grid, row, col + dc):
                        continue
                    step = math.sqrt(2)
                else:
                    step = 1

                new_cost = cost + step * grid.get_cost(r, c)
                if new_cost < best_cost.get((r, c), math.inf):
                    best_cost[(r, c)] = new_cost
                    heapq.heappush(queue, (new_cost, (r, c)))

    return None


def is_free(grid, row, col):
    if row < 0 or row >= grid.height or col < 0 or col >= grid.width:
        return False
    return not grid.is_wall(row, col)
