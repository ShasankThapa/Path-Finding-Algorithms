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


def step_search(algo, generator):
    # Advances a search by one step and adds the time spent inside it to
    # algo.stats["search_time_ms"]. Only the time inside the search is counted, so the UI
    # can draw between steps without the drawing being timed.
    # Returns the yielded (visited, path), or None once the search has finished.
    # Each yield costs the same small amount whichever algorithm is running, so the
    # comparison between algorithms stays fair.
    step_start = time.perf_counter()
    try:
        result = next(generator)
    except StopIteration:
        result = None
    elapsed_ms = (time.perf_counter() - step_start) * 1000
    if algo.stats["search_time_ms"] is None:
        algo.stats["search_time_ms"] = 0
    algo.stats["search_time_ms"] += elapsed_ms
    return result


def run_to_completion(algo, start, end, grid):
    # Runs a search to the end with no drawing, timed the same way as the animation.
    generator = algo.search(start, end, grid)
    visited = set()
    path = None
    result = step_search(algo, generator)
    while result is not None:
        visited, path = result
        result = step_search(algo, generator)
    return visited, path
