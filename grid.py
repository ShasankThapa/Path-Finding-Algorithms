import math

import numpy as np

class Grid():
    def __init__(self, width, height, fill_value):
        self.width = width
        self.height = height
        self.fill_value = fill_value
        # NumPy arrays are indexed [row, col], so the shape is (rows, cols) = (height, width).
        self.grid = np.full((height, width), fill_value, dtype = float)

    def set_cost(self, row, col, update_cost):
        self.grid[row,col] = update_cost

    def get_cost(self,row,col):
        return self.grid[row,col]

    def is_wall(self,row,col):
        return self.grid[row,col] == np.inf


def in_bounds(grid, row, col):
    return 0 <= row < grid.height and 0 <= col < grid.width


def get_neighbours(row, col, grid, movement):
    # Returns a list of ((row, col), step_length) pairs.
    # movement = 4: up, down, left, right, each with step length 1.
    # movement = 8: also the four diagonals, with step length sqrt(2). No corner cutting:
    # a diagonal is only allowed if both cells beside it are free.
    if movement != 4 and movement != 8:
        raise ValueError("movement must be 4 or 8")

    neighbours = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        r = row + dr
        c = col + dc
        if in_bounds(grid, r, c) and not grid.is_wall(r, c):
            neighbours.append(((r, c), 1))

    if movement == 8:
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            r = row + dr
            c = col + dc
            if not in_bounds(grid, r, c) or grid.is_wall(r, c):
                continue
            if grid.is_wall(row + dr, col) or grid.is_wall(row, col + dc):
                continue
            neighbours.append(((r, c), math.sqrt(2)))

    return neighbours
