from algos.base import PathAlgo
from grid import get_prox
import heapq as hq


class Bidirect(PathAlgo):
    def search(self, start, end, grid):
        distance_f = {start: 0}
        came_from_f = {}
        visited_f = set()
        queue_f = [(0, start)]

        distance_b = {end: 0}
        came_from_b = {}
        visited_b = set()
        queue_b = [(0, end)]

        best = float('inf')
        meeting_node = None

        while queue_f and queue_b:
            yield visited_f | visited_b, None
            if queue_f[0][0] <= queue_b[0][0]:
                current_cost, current_cell = hq.heappop(queue_f)
                if current_cell in visited_f:
                    continue
                visited_f.add(current_cell)
                distance, came_from, queue, distance_other = distance_f, came_from_f, queue_f, distance_b
                forward = True
            else:
                current_cost, current_cell = hq.heappop(queue_b)
                if current_cell in visited_b:
                    continue
                visited_b.add(current_cell)
                distance, came_from, queue, distance_other = distance_b, came_from_b, queue_b, distance_f
                forward = False

            if current_cell in distance_other:
                combined = current_cost + distance_other[current_cell]
                if combined < best:
                    best = combined
                    meeting_node = current_cell

            row, col = current_cell
            for prox in get_prox(row, col, grid):
                if forward:
                    # Real move is current_cell -> prox, so we pay for entering prox.
                    step_cost = grid.get_cost(prox[0], prox[1])
                else:
                    # The backward search walks the path in reverse. The real move is
                    # prox -> current_cell, so we pay for entering current_cell.
                    step_cost = grid.get_cost(row, col)
                new_cost = current_cost + step_cost
                if new_cost < distance.get(prox, float('inf')):
                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    hq.heappush(queue, (new_cost, prox))

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
            if best <= queue_f[0][0] + queue_b[0][0]:
                break

        if meeting_node is None:
            yield visited_f | visited_b, None
        else:
            path_f = [meeting_node]
            while path_f[-1] != start:
                path_f.append(came_from_f[path_f[-1]])
            path_f.reverse()

            path_b = [meeting_node]
            while path_b[-1] != end:
                path_b.append(came_from_b[path_b[-1]])

            full_path = path_f + path_b[1:]
            yield visited_f | visited_b, full_path
