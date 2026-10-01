import time
from abc import ABC, abstractmethod


class PathAlgo(ABC):
    def __init__(self):
        self.reset_stats()

    def reset_stats(self):
        # Filled in by search() as it runs, so a UI can show them live.
        # cells_scanned only differs from nodes_expanded for JPS, which scans along
        # rows/columns/diagonals between the nodes it expands.
        self.stats = {
            "nodes_expanded": 0,
            "cells_scanned": 0,
            "path_cost": None,
            "path_length_cells": None,
            "search_time_ms": None,
        }

    def record_path(self, path, cost):
        # Called once at the end of a search that found a path.
        self.stats["path_cost"] = cost
        self.stats["path_length_cells"] = len(path)

    @abstractmethod
    def search(self, start, end, grid):
        pass


def run_to_completion(algo, start, end, grid):
    # Runs a search with no drawing and times it, so search_time_ms is pure search time.
    # The generator still yields after every expansion step. Each yield costs the same
    # small amount whichever algorithm is running, so the comparison stays fair.
    start_time = time.perf_counter()
    visited = set()
    path = None
    for visited, path in algo.search(start, end, grid):
        pass
    algo.stats["search_time_ms"] = (time.perf_counter() - start_time) * 1000
    return visited, path
