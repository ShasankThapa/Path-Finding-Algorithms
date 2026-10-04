from algos.base import PathAlgo
from algos.heuristics import octile
from grid import in_bounds
import heapq as hq

SQRT2 = 2 ** 0.5


class JPS(PathAlgo):
    """Jump Point Search on an 8-directional grid.

    Assumes uniform cost: straight steps cost 1 and diagonal steps cost sqrt(2).
    It ignores mud (any cell cost other than a wall is treated as 1), because skipping
    over runs of cells is only safe when every cell in the run costs the same.
    No corner cutting: a diagonal step needs both cells beside it to be free.

    Two counters in self.stats are worth comparing:
    - nodes_expanded: cells popped from the priority queue and expanded.
    - cells_scanned: every cell the jump loop stepped through, including the straight
      scans made from each diagonal step. JPS expands few nodes but still scans many cells.
    """

    # The big idea: on an open grid there are lots of equally cheap paths, and A* wastes
    # time putting every cell of them in the queue. JPS instead "jumps" in a straight or
    # diagonal line, skipping cells, and only stops at cells where something interesting
    # happens (a wall opens up a new route, or we reach the end). Those stopping cells
    # are called jump points, and only they go in the queue.
    # Apart from that, the main loop is just A*.

    def search(self, start, end, grid):
        # Start this run's stats from zero.
        self.reset_stats()

        # Same four things as A*, but they only ever hold jump points, not every cell.
        distance = {start: 0}
        came_from = {}
        visited = set()
        queue = [(octile(start, end), 0, start)]

        while queue:
            # Take the most promising jump point (smallest f = g + h).
            priority, current_cost, current_cell = hq.heappop(queue)

            # Skip out-of-date copies of a cell we've already finished.
            if current_cell in visited:
                continue
            visited.add(current_cell)
            self.stats["nodes_expanded"] += 1

            # Pause here so the visualiser can draw.
            yield visited, None

            # Reached the end: its cost is final, so stop searching.
            if current_cell == end:
                break

            # Find the next jump points reachable from here.
            parent = came_from.get(current_cell, None)
            if parent is None:
                # This is the start: we haven't come from anywhere, so jump in all 8 directions.
                jump_points = []
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        jp = self.jump(current_cell, (dr, dc), end, grid)
                        if jp is not None:
                            jump_points.append(jp)
            else:
                # Otherwise only jump in the directions that make sense given where we came from.
                jump_points = self.identify_successors(current_cell, parent, end, grid)

            # Treat each jump point like a neighbour in A*.
            for jp in jump_points:
                # A jump is always a straight or diagonal line, so its cost is
                # (number of steps) * (1 for straight, sqrt(2) for diagonal).
                steps = max(abs(jp[0] - current_cell[0]), abs(jp[1] - current_cell[1]))
                is_diagonal = jp[0] != current_cell[0] and jp[1] != current_cell[1]
                step_cost = SQRT2 if is_diagonal else 1
                new_cost = current_cost + steps * step_cost

                # Only keep it if it beats the best route we already know.
                if new_cost < distance.get(jp, float('inf')):
                    distance[jp] = new_cost
                    came_from[jp] = current_cell
                    hq.heappush(queue, (new_cost + octile(jp, end), new_cost, jp))

        # Did we reach the end?
        if end in came_from or end == start:
            # Follow came_from back from the end. This gives only the jump points...
            jump_path = [end]
            while jump_path[-1] != start:
                jump_path.append(came_from[jump_path[-1]])
            jump_path.reverse()
            # ...so fill in every cell between them to get a normal cell-by-cell path.
            path = fill_in_path(jump_path)
            self.record_path(path, distance[end])
            yield visited, path
        else:
            # No path.
            yield visited, None

    def identify_successors(self, current, parent, goal, grid):
        # Work out which directions are worth jumping in from this cell (prune),
        # then jump in each one and collect the jump points we find.
        valid = prune(parent, current, grid)
        successors = []
        for candidate in valid:
            # Turn the neighbour cell into a direction, e.g. (1, 0) = down.
            r, c = candidate
            dr = r - current[0]
            dc = c - current[1]
            jump_point = self.jump(current, (dr, dc), goal, grid)
            if jump_point is not None:
                successors.append(jump_point)
        return successors

    def jump(self, current_cell, direction, goal, grid):
        # Step from current_cell in one direction until we find a jump point (return it)
        # or hit a wall / the edge / an illegal diagonal (return None).
        # A loop rather than recursion, so long straight runs can't hit Python's recursion
        # limit. The only nested call is the straight scan from each diagonal step, and a
        # straight scan never calls jump() again, so the call depth is at most 2.
        dr, dc = direction
        row, col = current_cell

        while True:
            # Blocked: nothing useful this way.
            if not can_move(grid, row, col, dr, dc):
                return None
            # Take one step.
            row += dr
            col += dc
            self.stats["cells_scanned"] += 1

            # Found the end: always stop here.
            if (row, col) == goal:
                return (row, col)

            if dr != 0 and dc != 0:
                # Diagonal: no forced-neighbour check is needed here (see forced_neighbours).
                # This cell is a jump point if a straight scan from it finds something.
                if self.jump((row, col), (dr, 0), goal, grid) is not None:
                    return (row, col)
                if self.jump((row, col), (0, dc), goal, grid) is not None:
                    return (row, col)
            else:
                # Straight: stop if a wall beside us opens up a route that only goes
                # through this cell (a forced neighbour).
                if forced_neighbours((row, col), grid, direction):
                    return (row, col)


def sign(x):
    # 1 for positive, -1 for negative, 0 for zero. Turns a distance into a direction.
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0


def is_free(grid, row, col):
    # True if the cell is on the grid and not a wall.
    return in_bounds(grid, row, col) and not grid.is_wall(row, col)


def can_move(grid, row, col, dr, dc):
    # One step from (row, col) in direction (dr, dc). The target must be free, and a
    # diagonal step must not cut a corner: both cells beside the diagonal must be free too.
    if not is_free(grid, row + dr, col + dc):
        return False
    if dr != 0 and dc != 0:
        return is_free(grid, row + dr, col) and is_free(grid, row, col + dc)
    return True


def fill_in_path(jump_path):
    # Consecutive jump points always lie on a straight or diagonal line,
    # so walk one cell at a time from each jump point to the next.
    path = [jump_path[0]]
    for target in jump_path[1:]:
        # Direction of this line, e.g. (1, 1) = down-right.
        dr = sign(target[0] - path[-1][0])
        dc = sign(target[1] - path[-1][1])
        # Add each cell along the line until we reach the next jump point.
        while path[-1] != target:
            path.append((path[-1][0] + dr, path[-1][1] + dc))
    return path


def prune(parent, current, grid):
    # Decide which neighbours are worth looking at, given the direction we arrived from.
    # Most neighbours can be reached just as cheaply without going through this cell,
    # so we drop them. That's what makes JPS fast.
    row, col = current
    # Direction we travelled to get here, e.g. (0, 1) = moving right.
    dr = sign(current[0] - parent[0])
    dc = sign(current[1] - parent[1])

    if dr != 0 and dc != 0:
        # Natural neighbours of a diagonal move: keep going straight in each part, or diagonally.
        candidates = [(row + dr, col), (row, col + dc), (row + dr, col + dc)]
    else:
        # Straight move: keep going the same way, plus any forced neighbours.
        candidates = [(row + dr, col + dc)]
        candidates += forced_neighbours(current, grid, (dr, dc))

    # Keep only the ones we can actually step to (not a wall, no corner cutting).
    valid = []
    for r, c in candidates:
        if can_move(grid, row, col, r - row, c - col):
            valid.append((r, c))
    return valid


def forced_neighbours(current_cell, grid, direction):
    # Only for straight moves. Without corner cutting, a diagonal move never creates forced
    # neighbours: both cells beside the diagonal were free, so the parent could already
    # reach everything behind us without going through this cell.
    row, col = current_cell
    dr, dc = direction
    forced = []

    # The two sides perpendicular to the direction of travel.
    if dr == 0:
        sides = [(-1, 0), (1, 0)]
    else:
        sides = [(0, -1), (0, 1)]

    # Check both sides, so a cell with openings on both sides keeps both forced neighbours.
    for sr, sc in sides:
        side_cell = (row + sr, col + sc)
        behind_side = (row + sr - dr, col + sc - dc)
        # If the cell beside us is open but the cell behind it is blocked, the parent can't
        # reach side_cell without going through us, so it (and the diagonal past it) is forced.
        if is_free(grid, side_cell[0], side_cell[1]) and not is_free(grid, behind_side[0], behind_side[1]):
            forced.append(side_cell)
            forced.append((row + sr + dr, col + sc + dc))
    return forced
