from algos.algo_rule import PathAlgo
import numpy as np

class Grid():
    def __init__(self, width, height, fill_value):
        self.width = width
        self.height = height
        self.fill_value = fill_value
        self.grid = np.full((width, height), fill_value, dtype = float)

    def set_cost(self, row, col, update_cost):
        self.grid[row,col] = update_cost

    def get_cost(self,row,col):
        return self.grid[row,col]

    def is_wall(self,row,col):
        return self.grid[row,col] == np.inf


def in_bounds(grid, row, col):
    return 0 <= row < grid.height and 0 <= col < grid.width


def get_prox( row, col, grid):
    candidates = [
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    ]
    neighbours = []
    for (r, c) in candidates:
        if 0 <= r < grid.height and 0 <= c < grid.width and not grid.is_wall(r, c):
            neighbours.append((r, c))
    return neighbours


