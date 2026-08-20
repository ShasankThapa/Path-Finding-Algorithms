from algos.algo_rule import PathAlgo
from grid import Grid, get_prox
import numpy as np
import heapq as hq
import time

class Astar(PathAlgo):
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
            row, col = current_cell
            for prox in get_prox(row, col, grid):
                new_cost = current_cost + grid.get_cost(prox[0], prox[1])
                if new_cost < distance.get(prox, float('inf')):
                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    hq.heappush(queue, (new_cost + heuristic(prox, end), new_cost, prox))

        if end in came_from or end == start:
            path = [end]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            yield visited, path
        else:
            yield visited, None