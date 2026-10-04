from algos.base import PathAlgo
from grid import get_neighbours
import heapq as hq


class Bidirect(PathAlgo):
    # Bidirectional Dijkstra: run two Dijkstra searches at once, one forward from the
    # start and one backward from the end, until they meet in the middle.

    # The first place the two searches touch isn't always on the cheapest path, so we
    # keep the cheapest meeting found so far ("best") and only stop once nothing
    # cheaper is possible.

    def __init__(self, movement=4):
        # 4 = up/down/left/right only, 8 = diagonals too (see grid.get_neighbours).
        super().__init__()
        self.movement = movement

    def search(self, start, end, grid):
        # Start this run's stats from zero.
        self.reset_stats()

        # Forward search, from the start. Same four things as Dijkstra.
        distance_f = {start: 0}
        came_from_f = {}
        visited_f = set()
        queue_f = [(0, start)]

        # Backward search, from the end.
        distance_b = {end: 0}
        came_from_b = {}
        visited_b = set()
        queue_b = [(0, end)]

        # Cells visited by either side, for the visualiser. Kept up to date as we go
        # rather than yielding visited_f | visited_b, which built a whole new set on
        # every step and made big maps very slow.
        visited = set()

        # best:         cheapest full start -> end cost found so far.
        # meeting_node: the cell where that cheapest route joins the two halves.
        best = float('inf')
        meeting_node = None

        # Keep going while both sides still have cells to explore.
        while queue_f and queue_b:
            # Pause here so the visualiser can draw.
            yield visited, None

            # Take one step on whichever side has the cheaper cell waiting,
            # so the two searches grow at about the same rate.
            if queue_f[0][0] <= queue_b[0][0]:
                current_cost, current_cell = hq.heappop(queue_f)
                # Skip out-of-date copies of a cell this side has already finished.
                if current_cell in visited_f:
                    continue
                visited_f.add(current_cell)
                visited.add(current_cell)
                # Point the shared names at the forward side's data, so the code below
                # works the same for either direction.
                distance, came_from, queue, distance_other = distance_f, came_from_f, queue_f, distance_b
                forward = True
            else:
                current_cost, current_cell = hq.heappop(queue_b)
                if current_cell in visited_b:
                    continue
                visited_b.add(current_cell)
                visited.add(current_cell)
                # Same again, for the backward side.
                distance, came_from, queue, distance_other = distance_b, came_from_b, queue_b, distance_f
                forward = False

            self.stats["nodes_expanded"] += 1
            self.stats["cells_scanned"] += 1

            # If the other side has already reached this cell, the two halves join here.
            # Full cost = cost from our side + cost from the other side.
            if current_cell in distance_other:
                combined = current_cost + distance_other[current_cell]
                if combined < best:
                    best = combined
                    meeting_node = current_cell

            # Look at each neighbour, as in Dijkstra.
            row, col = current_cell
            for prox, step_length in get_neighbours(row, col, grid, self.movement):
                if forward:
                    # Real move is current_cell -> prox, so we pay for entering prox.
                    step_cost = step_length * grid.get_cost(prox[0], prox[1])
                else:
                    # The backward search walks the path in reverse. The real move is
                    # prox -> current_cell, so we pay for entering current_cell.
                    step_cost = step_length * grid.get_cost(row, col)
                new_cost = current_cost + step_cost

                # Only keep it if it beats the best route this side already knows.
                if new_cost < distance.get(prox, float('inf')):
                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    hq.heappush(queue, (new_cost, prox))

                    # If the other side has reached this neighbour too, it's another
                    # possible meeting point. Keep it if it's the cheapest so far.
                    if prox in distance_other:
                        combined = new_cost + distance_other[prox]
                        if combined < best:
                            best = combined
                            meeting_node = prox

            # If either side has run out of cells, it has explored everything it can reach,
            # so no better meeting point exists. Checking this first also avoids
            # reading queue[0] from an empty list.
            if not queue_f or not queue_b:
                break

            # Stopping rule: any route we haven't found yet costs at least the cheapest
            # cell waiting on the forward side plus the cheapest waiting on the backward
            # side. If best is already no more than that, nothing can beat it, so stop.
            if best <= queue_f[0][0] + queue_b[0][0]:
                break

        # The two searches never met, so there is no path.
        if meeting_node is None:
            yield visited, None
        else:
            # First half: follow the forward came_from from the meeting cell back to the
            # start, then flip it so it runs start -> meeting cell.
            path_f = [meeting_node]
            while path_f[-1] != start:
                path_f.append(came_from_f[path_f[-1]])
            path_f.reverse()

            # Second half: follow the backward came_from from the meeting cell to the end.
            # This already runs the right way (meeting cell -> end), so no flip needed.
            path_b = [meeting_node]
            while path_b[-1] != end:
                path_b.append(came_from_b[path_b[-1]])

            # Join the halves. path_b[1:] skips the meeting cell so it isn't in there twice.
            full_path = path_f + path_b[1:]
            self.record_path(full_path, best)
            yield visited, full_path
