from algos.base import PathAlgo
from grid import get_neighbours
import heapq as hq

class Dijkstra(PathAlgo):
    # Dijkstra's algorithm: always explore the cheapest unexplored cell next.
    # Every move costs something (never negative), so the first time we pop the end
    # from the queue, we've found the cheapest path to it.

    def __init__(self, movement=4):
        # 4 = up/down/left/right only, 8 = diagonals too (see grid.get_neighbours).
        super().__init__()
        self.movement = movement

    def search(self, start, end, grid):
        # Start this run's stats from zero.
        self.reset_stats()

        # distance:  the cheapest cost found to reach a cell.
        # came_from: dictionary consisting of which cell was visited from where.
        # visited:   cells that are finished; their cost is final.
        # queue:     contains current nodes neighbours with the cheapest total cost.
        distance = {start: 0}
        came_from = {}
        visited = set()
        queue = [(0, start)]

        # Keep going while there are still cells waiting to be explored.
        # If the queue runs out before we reach the end, there is no path.
        while queue:
            # Take the cheapest cell out of the queue.
            current_cost, current_cell = hq.heappop(queue)

            # A cell can be in the queue more than once (we push it again when we find a
            # cheaper route). The cheapest copy comes out first, so skip any later copy.
            if current_cell in visited:
                continue
            visited.add(current_cell)
            self.stats["nodes_expanded"] += 1
            self.stats["cells_scanned"] += 1

            # Pause here so the visualiser can draw the newly visited cell.
            yield visited, None

            # The end was the cheapest cell left, so its cost is final. Stop searching.
            if current_cell == end:
                break

            # Prox is the neighbours (proximity) and step_length is the cost of the step itself e.g: 1, root2
            # For each neighbours and their respective step_length, calculate a new overall cost
            row, col = current_cell
            for prox, step_length in get_neighbours(row, col, grid, self.movement):
                new_cost = current_cost + step_length * grid.get_cost(prox[0], prox[1])

                # If the new cost is cheaper than the current cost to reach that node, then assign the new cost to the node
                # Inf is used, so that new nodes that are discovered are always less than inf, therefore passing the condition.
                if new_cost < distance.get(prox, float('inf')):
                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    hq.heappush(queue, (new_cost, prox))

        # Did we reach the end? (If start == end there are no moves, so it isn't in came_from.)
        if end in came_from or end == start:
            # Rebuild the path: follow came_from backwards from the end to the start,
            # then flip it so it runs start -> end.
            path = [end]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            self.record_path(path, distance[end])
            yield visited, path
        else:
            # The queue ran out without reaching the end, so there is no path.
            yield visited, None

