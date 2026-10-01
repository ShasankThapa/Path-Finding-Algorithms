# Baseline test results (before any algorithm fixes)

Recorded on 2026-10-01 with `.venv/bin/python -m pytest`. No algorithm code was changed.

**Total: 265 tests. 186 passed, 79 failed, 5 skipped.**

| Algorithm | Tests run | Failed | First failure message |
|---|---|---|---|
| Dijkstra | 55 | 0 | – |
| A* | 55 | 0 | – |
| Bidirectional | 55 | 5 | `test_4dir_random_mud_grid[Bidirect-8]`: `IndexError: list index out of range` at `algos/bidirectional.py:56` |
| JPS | 105 (5 skipped) | 74 | `test_jps_random_path_is_valid[0]`: `diagonal step (16, 34) -> (15, 33) cuts a corner` |

Skipped tests: `test_jps_random_path_is_valid` skips a seed when the reference says the
end is unreachable (that case is covered by `test_jps_random_cost`).

## Bidirectional: 5 failures, all the same bug

All five are `IndexError` on the stopping check `if best <= queue_f[0][0] + queue_b[0][0]`.
When one side's queue becomes empty, `queue_f[0]` or `queue_b[0]` doesn't exist.

- `test_start_walled_in`, `test_end_walled_in`: one search has nowhere to go.
- `test_one_by_one_grid`: start == end, but the cell has no neighbours, so the queue empties.
- `test_4dir_random_mud_grid` seeds 8 and 36: random grids where one side gets boxed in.

Every random mud grid where Bidirectional did finish gave the optimal cost.

## JPS: 74 failures, three separate problems

1. **Path contains only jump points, not every cell** (19 validity failures + `test_empty_open_grid`).
   Example: `illegal step (0, 0) -> (11, 11)` on an empty grid. The game window then draws
   isolated dots instead of a line.
2. **Corner cutting** (22 validity failures). JPS moves diagonally between two walls, e.g.
   `diagonal step (16, 34) -> (15, 33) cuts a corner`.
3. **Wrong cost** (32 of 50 cost tests failed):
   - 25 seeds return a path *cheaper* than the no-corner-cutting optimum (it cut corners).
   - 2 seeds return a path *more expensive* than optimal (the Manhattan heuristic overestimates
     once diagonals cost sqrt(2), so A*-style search is no longer guaranteed optimal).
   - 5 seeds (e.g. 8) find a path where the reference says there is none: the only route
     goes through a corner gap.

The validity test stops at the first problem in a path, so a path with both problems is
counted once. Jump-point paths are costed segment by segment (`path_cost_8dir`), so the cost
test doesn't fail just because of problem 1.

## After the JPS fixes

Recorded with the suite as it stands after the JPS task (3 JPS tests were added since the
baseline: long corridor, forced neighbours on both sides, node/scan counters).

| JPS version | JPS tests failed |
|---|---|
| Original (before any fix) | 77 of 103 run (the 74 above + the 3 new tests) |
| Fixed but still recursive (`1d5ebde`) | 2 (long corridor, counters) |
| Current | 0 |

Extra check, 500 unseen seeds per wall density (sizes 10x10 to 40x40), JPS against
`reference_8dir`: 500/500 passed at 10%, 20%, 30% and 40% walls.
