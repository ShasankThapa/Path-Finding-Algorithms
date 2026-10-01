# PathFinder

A Pygame pathfinding visualiser (Dijkstra, A*, Bidirectional Dijkstra, Jump Point Search).
The owner is presenting it at a graduate interview, so correctness and being able to
explain every line matter more than clever code.

## How it fits together

- `grid.py` – `Grid` stores per-cell costs in a NumPy array. `np.inf` means wall,
  values > 1 are "mud". Also has `in_bounds()` and `get_prox()` (4-directional neighbours).
- `algos/base.py` – `PathAlgo`, the abstract base class. Every algorithm subclasses it
  and implements `search(start, end, grid)`.
- `search()` is a generator: it yields `(visited_set, None)` after each expansion step and
  finally `(visited_set, path)` (or `(visited_set, None)` if no path exists).
- `game_window.py` – the Pygame loop. It calls `next()` on the generator once per frame to
  animate the search, and lets the user draw walls/mud and pick an algorithm.
- Dijkstra (`algos/dijkstra.py`), A* (`algos/astar.py`) and Bidirectional (`algos/bidirectional.py`)
  are 4-directional and respect mud costs. Moving into a cell costs that cell's value.
- JPS (`algos/jps.py`) is 8-directional with no corner cutting, and assumes uniform cost
  (it ignores mud). It returns the full cell-by-cell path, not just the jump points.
- Run the app: `.venv/bin/python game_window.py`

## Rules for every task

1. Keep code simple and readable for a final-year CS student to explain. No clever
   one-liners, no unnecessary abstraction, no new dependencies unless the task says so
   (allowed: pygame, numpy, pytest, matplotlib).
2. Never weaken or delete a test to make it pass. If a test fails, find the real cause and
   report it.
3. Do not change algorithm behaviour unless the task asks for it.
4. Run pytest (once tests exist) after every change and report the result.
5. At the end of each task, give: a summary of what changed, files touched, anything you
   were unsure about, and one likely interview question about the change with a short answer.
6. Don't commit. The owner reviews and commits.
