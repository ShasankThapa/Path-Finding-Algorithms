from algos.base import PathAlgo
from grid import get_neighbours
from algos.heuristics import manhattan, octile
import heapq as hq

class Astar(PathAlgo):
    # A*: the same as Dijkstra, but the queue is now ordered by
    #     f = g + h
    # g = the real cost so far, h = an estimate of the cost still to go.
    # A* will use manhattan or octile huersitic

    def __init__(self, movement=4):
        # 4 = up/down/left/right only, 8 = diagonals too (see grid.get_neighbours).
        super().__init__()
        self.movement = movement

    def search(self, start, end, grid):
        # Start this run's stats from zero.
        self.reset_stats()

        # The estimate of the remaining cost (h). It has to match the movement rules:
        # Manhattan for 4 directions, octile for 8 (diagonals cost sqrt(2)).
        def heuristic(cell, end):
            if self.movement == 4:
                return manhattan(cell, end)
            return octile(cell, end)

        # distance:  cheapest cost found so far to reach each cell (this is g).
        # came_from: for each cell, the cell we reached it from (used to rebuild the path).
        # visited:   cells that are finished; their cost is final.
        # queue:     a heap of (f, g, cell). The smallest f comes out first.
        distance = {start: 0}
        came_from = {}
        visited = set()
        queue = [(heuristic(start, end), 0, start)]

        # Keep going while there are still cells waiting to be explored.
        while queue:
            # Take the most promising cell (smallest f) out of the queue.
            # priority (f) is only for ordering; current_cost (g) is the real cost.
            priority, current_cost, current_cell = hq.heappop(queue)

            # Skip out-of-date copies of a cell we've already finished.
            if current_cell in visited:
                continue
            visited.add(current_cell)
            self.stats["nodes_expanded"] += 1
            self.stats["cells_scanned"] += 1

            # Pause here so the visualiser can draw the newly visited cell.
            yield visited, None

            # Reached the end: its cost is final, so stop searching.
            if current_cell == end:
                break

            # Look at each neighbour we can step to from here.
            row, col = current_cell
            for prox, step_length in get_neighbours(row, col, grid, self.movement):
                # Real cost to reach the neighbour through this cell (g), same as Dijkstra.
                new_cost = current_cost + step_length * grid.get_cost(prox[0], prox[1])

                # Only keep it if it beats the best route we already know.
                if new_cost < distance.get(prox, float('inf')):
                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    # Queue it by f = g + h, so cells nearer the end come out sooner.
                    hq.heappush(queue, (new_cost + heuristic(prox, end), new_cost, prox))

        # Did we reach the end? (If start == end there are no moves, so it isn't in came_from.)
        if end in came_from or end == start:
            # Follow came_from backwards from the end, then flip it to run start -> end.
            path = [end]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            self.record_path(path, distance[end])
            yield visited, path
        else:
            # The queue ran out without reaching the end, so there is no path.
            yield visited, None