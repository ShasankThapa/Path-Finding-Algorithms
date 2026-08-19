from algos.algo_rule import PathAlgo
from grid import Grid, get_prox
import numpy as np
import heapq as hq
import time
class Astar(PathAlgo):
    def search(self, start, end, grid):

        def hueristic(cell, end):
            if cell == end:
                return 0
            row, col = cell
            end_row, end_col = end
            hueristic_val = abs(row - end_row) + abs(col - end_col)
            return hueristic_val

        start_time = time.time()
        distance = {start:0}
        came_from = {}
        visited = set()
        queue = [(hueristic(start,end),0,start)]


        while queue:
            priority, current_cost, current_cell = hq.heappop(queue)
            if current_cell in visited:
                continue
            visited.add(current_cell)
            if current_cell == end:
                print("early exit")
                break
            row, col = current_cell

            for prox in get_prox(row, col, grid):
                new_cost = current_cost + grid.get_cost(prox[0], prox[1])

                if new_cost < distance.get(prox, float('inf')):

                    distance[prox] = new_cost
                    came_from[prox] = current_cell
                    hq.heappush(queue, (new_cost + hueristic(prox,end), new_cost, prox))
        end_time = time.time()
        path_runtime = end_time - start_time
        path_taken = [end]
        while path_taken[-1] != start:
            path_taken.append(came_from[path_taken[-1]])
        path_taken.reverse()


        return path_taken, len(visited), path_runtime






