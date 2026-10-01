# PathFinder

A Pygame pathfinding visualiser (Dijkstra, A*, Bidirectional Dijkstra, Jump Point Search).
The owner is presenting it at a graduate interview, so correctness and being able to
explain every line matter more than clever code.

## How it fits together

- `grid.py` – `Grid` stores per-cell costs in a NumPy array. `np.inf` means wall,
  values > 1 are "mud". Also has `in_bounds()` and `get_neighbours(row, col, grid, movement)`,
  which returns `((row, col), step_length)` pairs for movement 4 or 8 (diagonal = sqrt(2),
  no corner cutting).
- `algos/base.py` – `PathAlgo`, the abstract base class. Every algorithm subclasses it
  and implements `search(start, end, grid)`.
- `search()` is a generator: it yields `(visited_set, None)` after each expansion step and
  finally `(visited_set, path)` (or `(visited_set, None)` if no path exists).
- Each algorithm fills `self.stats` (nodes_expanded, cells_scanned, path_cost,
  path_length_cells, search_time_ms) as it runs. `run_to_completion()` in `algos/base.py`
  drains a search with no UI and sets search_time_ms. The UI times one such run when Run is
  pressed and animates a second copy; a side panel shows live stats and the last result per
  algorithm on the current map (cleared when the map changes).
- `game_window.py` – the Pygame loop. It calls `next()` on the generator once per frame to
  animate the search, and lets the user draw walls/mud and pick an algorithm.
- Dijkstra (`algos/dijkstra.py`), A* (`algos/astar.py`) and Bidirectional (`algos/bidirectional.py`)
  take `movement=4` (default) or `movement=8` and respect mud costs.
  Move cost = step length * cost of the cell entered. A* uses Manhattan (4) or octile (8).
  The UI has a 4-dir / 8-dir toggle, locked to 8-dir while JPS is selected.
- `algos/heuristics.py` – `manhattan()` and `octile()`, shared by A* and JPS.
- JPS (`algos/jps.py`) is 8-directional with no corner cutting, and assumes uniform cost
  (it ignores mud). It returns the full cell-by-cell path, not just the jump points.
  `jump()` is iterative. After a search, `nodes_expanded` and `cells_scanned` hold the counts.
- `renderer.py` – all drawing. Background surface (walls/mud/floor) built once and patched per
  painted cell; visited cells drawn incrementally onto an overlay; path and markers on top.
  `GridLayout` maps cells to screen pixels so a grid can be drawn in any panel.
- Run the app: `.venv/bin/python game_window.py` (optional size: `game_window.py 200 200`).
  Keys 1-5 or +/- set search steps per frame. Drag the start/end markers to move them.

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
