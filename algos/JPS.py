from algos.algo_rule import PathAlgo
from grid import Grid, get_prox, in_bounds
import numpy as np
import heapq as hq
import time
class JPS(PathAlgo):
    def search(self, start, end, grid):
        def heuristic(cell, end):
            return abs(cell[0] - end[0]) + abs(cell[1] - end[1])

        distance = {start: 0}
        came_from = {}
        visited = set()
        queue = [(heuristic(start, end), 0, start)]

        while queue:
            priority, current_cost, current_cell = hq.heappop(queue)
            if current_cell in visited:
                continue
            visited.add(current_cell)

            yield visited, None

            if current_cell == end:
                break

            parent = came_from.get(current_cell, None)
            if parent is None:
                jump_points = []
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        jp = jump(current_cell, (dr, dc), start, end, grid)
                        if jp is not None:
                            jump_points.append(jp)
            else:
                jump_points = identify_successors(current_cell, parent, start, end, grid)

            for jp in jump_points:
                steps = max(abs(jp[0] - current_cell[0]), abs(jp[1] - current_cell[1]))
                is_diagonal = jp[0] != current_cell[0] and jp[1] != current_cell[1]
                step_cost = (2 ** 0.5) if is_diagonal else 1
                new_cost = current_cost + steps * step_cost
                if new_cost < distance.get(jp, float('inf')):
                    distance[jp] = new_cost
                    came_from[jp] = current_cell
                    hq.heappush(queue, (new_cost + heuristic(jp, end), new_cost, jp))

        if end in came_from or end == start:
            path = [end]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            yield visited, path
        else:
            yield visited, None





def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0

def identify_successors(current, parent, start, goal, grid):
    valid = prune(parent, current, grid)
    successors = []
    for candidate in valid:
        r, c = candidate
        dr = r - current[0]
        dc = c - current[1]
        jump_point = jump(current, (dr, dc), start, goal, grid)
        if jump_point is not None:
            successors.append(jump_point)
    return successors

def prune(parent, current, grid):
    row, col = current
    raw_dr = current[0] - parent[0]
    raw_dc = current[1] - parent[1]
    dr = sign(raw_dr)
    dc = sign(raw_dc)

    if dr != 0 and dc != 0:
        candidates = [(row + dr, col), (row, col + dc), (row + dr, col + dc)]
    else:
        candidates = [(row + dr, col + dc)]

    fn = forced_neighbor(current, grid, (dr, dc))
    if fn is not None:
        candidates.append(fn)

    valid = []
    for candidate in candidates:
        r, c = candidate
        if 0 <= r < grid.height and 0 <= c < grid.width and not grid.is_wall(r, c):
            valid.append(candidate)

    return valid

def forced_neighbor(current_cell, grid, direction):
    row, col = current_cell
    dr, dc = direction
    if dr != 0 and dc != 0:
        diag_wall_row = in_bounds(grid, row - dr, col) and grid.is_wall(row - dr, col)
        diag_wall_col = in_bounds(grid, row , col - dc) and grid.is_wall(row, col - dc)
        if diag_wall_row and in_bounds(grid, row - dr , col + dc ) and not grid.is_wall(row - dr , col + dc):
            return (row - dr, col + dc)
        if diag_wall_col and in_bounds(grid, row + dr , col - dc ) and not grid.is_wall(row + dr , col - dc):
            return (row + dr , col - dc )

    elif dc != 0:
        wall_above = in_bounds(grid, row - 1, col) and grid.is_wall(row - 1, col)
        wall_below = in_bounds(grid, row + 1, col) and grid.is_wall(row + 1, col)
        if wall_above and in_bounds(grid, row - 1, col + dc) and not grid.is_wall(row - 1, col + dc):
            return (row - 1, col + dc)
        if wall_below and in_bounds(grid, row + 1, col + dc) and not grid.is_wall(row + 1, col + dc):
            return (row + 1, col + dc)

    elif dr != 0:
        wall_left = in_bounds(grid, row, col - 1) and grid.is_wall(row, col - 1)
        wall_right = in_bounds(grid, row, col + 1) and grid.is_wall(row, col + 1)
        if wall_left and in_bounds(grid, row + dr, col - 1) and not grid.is_wall(row + dr, col - 1):
            return (row + dr, col - 1)
        if wall_right and in_bounds(grid, row + dr, col + 1) and not grid.is_wall(row + dr, col + 1):
            return (row + dr, col + 1)
    return None



def jump(current_cell, direction, start, goal, grid):
    dr, dc = direction
    row, col = current_cell
    n = (row + dr,col + dc)
    r,c = n
    if not(0 <= r < grid.height and 0 <= c < grid.width and not grid.is_wall(r, c)):
        return None
    if n == goal:
        return n
    if forced_neighbor(n, grid, direction):
        return n
    if dr != 0 and dc != 0:
        for subdirection in [(dr, 0), (0, dc)]:
            if jump(n, subdirection, start, goal, grid) is not None:
                return n
        return jump(n, direction, start, goal, grid)
    else:
        return jump(n, direction, start, goal, grid)


