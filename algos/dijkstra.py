from algos.base import PathAlgo
from grid import get_neighbours
import heapq as hq

class Dijkstra(PathAlgo):
    def __init__(self, movement=4):
        # 4 = up/down/left/right only, 8 = diagonals too (see grid.get_neighbours).
        self.movement = movement

    def search(self, start, end, grid):
        distance = {start: 0}
        came_from = {}
        visited = set()
        queue = [(0, start)]

        while queue:
            current_cost, current_cell = hq.heappop(queue)
            if current_cell in visited:
                continue
            visited.add(current_cell)

            yield visited, None

            if current_cell == end:
                break
            row, col = current_cell
            for prox, step_length in get_neighbours(row, col, grid, self.movement):
                new_cost = current_cost + step_length * grid.get_cost(prox[0], prox[1])
                if new_cost < distance.get(prox, float('inf')):
                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    hq.heappush(queue, (new_cost, prox))

        if end in came_from or end == start:
            path = [end]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            yield visited, path
        else:
            yield visited, None

