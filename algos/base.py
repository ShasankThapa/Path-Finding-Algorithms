import time
from abc import ABC, abstractmethod


class PathAlgo(ABC):
    # The shared parent class for every algorithm. It holds the stats code they all use,
    # and says every algorithm must have a search() method (see @abstractmethod below).

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
        # Every algorithm must write its own search(). Python refuses to create an
        # algorithm object that doesn't have one.
        # search() is a generator: it yields (visited, None) after each step and
        # (visited, path) at the end, so the visualiser can animate it.
        pass


def step_search(algo, generator):
    # Advances a search by one step and adds the time spent inside it to
    # algo.stats["search_time_ms"]. Only the time inside the search is counted, so the UI
    # can draw between steps without the drawing being timed.
    # Returns the yielded (visited, path), or None once the search has finished.
    # Each yield costs the same small amount whichever algorithm is running, so the
    # comparison between algorithms stays fair.

    # Start the stopwatch.
    step_start = time.perf_counter()
    try:
        # Run the search until its next yield.
        result = next(generator)
    except StopIteration:
        # The search has nothing left to do.
        result = None
    # Stop the stopwatch and convert seconds to milliseconds.
    elapsed_ms = (time.perf_counter() - step_start) * 1000

    # Add this step's time to the running total (it starts as None, so set it to 0 first).
    if algo.stats["search_time_ms"] is None:
        algo.stats["search_time_ms"] = 0
    algo.stats["search_time_ms"] += elapsed_ms
    return result


def run_to_completion(algo, start, end, grid):
    # Runs a search to the end with no drawing, timed the same way as the animation.
    # Used by the benchmark and tests, which have no game loop to step the search for them.
    generator = algo.search(start, end, grid)

    # Safe defaults, in case the search never yields anything.
    visited = set()
    path = None

    # Keep stepping until step_search returns None (search finished).
    # Each result overwrites the last, so we end up with the final visited set and path.
    result = step_search(algo, generator)
    while result is not None:
        visited, path = result
        result = step_search(algo, generator)
    return visited, path
