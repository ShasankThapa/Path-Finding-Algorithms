from algos.algo_rule import PathAlgo
from grid import Grid, get_prox
import numpy as np
import heapq as hq
import time


class Bidirect(PathAlgo):
    def search(self, start, end, grid):
        start_time = time.time()
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
            if queue_f[0][0] <= queue_b[0][0]:
                current_cost, current_cell = hq.heappop(queue_f)
                if current_cell in visited_f:
                    continue
                visited_f.add(current_cell)
                distance, came_from, queue, distance_other = distance_f, came_from_f, queue_f, distance_b
            else:
                current_cost, current_cell = hq.heappop(queue_b)
                if current_cell in visited_b:
                    continue
                visited_b.add(current_cell)
                distance, came_from, queue, distance_other = distance_b, came_from_b, queue_b, distance_f

            if current_cell in distance_other:
                combined = current_cost + distance_other[current_cell]
                if combined < best:
                    best = combined
                    meeting_node = current_cell

            row, col = current_cell
            for prox in get_prox(row, col, grid):
                new_cost = current_cost + grid.get_cost(prox[0], prox[1])
                if new_cost < distance.get(prox, float('inf')):
                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    hq.heappush(queue, (new_cost, prox))

                    if prox in distance_other:
                        combined = new_cost + distance_other[prox]
                        if combined < best:
                            best = combined
                            meeting_node = prox

            if best <= queue_f[0][0] + queue_b[0][0]:
                break

        end_time = time.time()
        path_runtime = end_time - start_time

        return best, meeting_node, path_runtime



