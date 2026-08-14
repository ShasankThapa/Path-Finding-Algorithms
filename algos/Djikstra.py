from algos.algo_rule import PathAlgo
from grid import Grid, get_prox
import numpy as np
import heapq as hq
import time
class Djikstra(PathAlgo):
    def search(self, start, end, grid):
        start_time = time.time()
        distance = {start:0}
        came_from = {}
        visited = set()
        queue = [(0,start)]

        while queue:
            current_cost, current_cell = hq.heappop(queue)
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
                    hq.heappush(queue, (new_cost, prox))
        end_time = time.time()
        path_runtime = end_time - start_time
        path_taken = [end]
        while path_taken[-1] != start:
            path_taken.append(came_from[path_taken[-1]])
        path_taken.reverse()


        return path_taken, len(visited), path_runtime





g = Grid(50, 50, 1.0)

# Wall 1: column 10, rows 0-35 (gap at rows 36-49)
g.grid[0:36, 10] = np.inf

# Wall 2: column 25, rows 14-49 (gap at rows 0-13)
g.grid[14:50, 25] = np.inf

# Wall 3: column 40, rows 0-40 (gap at rows 41-49)
g.grid[0:41, 40] = np.inf

# Mud patch 1: rows 36-45, columns 11-24
g.grid[36:46, 11:25] = 3.0

# Mud patch 2: rows 0-13, columns 26-39
g.grid[0:14, 26:40] = 3.0

d = Djikstra()
path, nodes_expanded, runtime = d.search((0,0), (49,49), g)

print(path)
print(len(path))
print(nodes_expanded)
print(runtime)

def hueristic(cell,end):
    if cell == end:
        return 0
    row, col = cell
    end_row, end_col = end
    h = abs(row-end_row) + abs(col-end_col)
    return h

