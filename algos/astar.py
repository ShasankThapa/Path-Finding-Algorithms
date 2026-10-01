from algos.base import PathAlgo
from grid import get_neighbours
from algos.heuristics import manhattan, octile
import heapq as hq

class Astar(PathAlgo):
    def __init__(self, movement=4):
        # 4 = up/down/left/right only, 8 = diagonals too (see grid.get_neighbours).
        super().__init__()
        self.movement = movement

    def search(self, start, end, grid):
        self.reset_stats()
        def heuristic(cell, end):
            if self.movement == 4:
                return manhattan(cell, end)
            return octile(cell, end)

        distance = {start: 0}
        came_from = {}
        visited = set()
        queue = [(heuristic(start, end), 0, start)]

        while queue:
            priority, current_cost, current_cell = hq.heappop(queue)
            if current_cell in visited:
                continue
            visited.add(current_cell)
            self.stats["nodes_expanded"] += 1
            self.stats["cells_scanned"] += 1

            yield visited, None

            if current_cell == end:
                break
            row, col = current_cell
            for prox, step_length in get_neighbours(row, col, grid, self.movement):
                new_cost = current_cost + step_length * grid.get_cost(prox[0], prox[1])
                if new_cost < distance.get(prox, float('inf')):
                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    hq.heappush(queue, (new_cost + heuristic(prox, end), new_cost, prox))

        if end in came_from or end == start:
            path = [end]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            self.record_path(path, distance[end])
            yield visited, path
        else:
            yield visited, None