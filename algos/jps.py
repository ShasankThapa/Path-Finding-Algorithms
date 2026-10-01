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

    def search(self, start, end, grid):
        self.reset_stats()

        distance = {start: 0}
        came_from = {}
        visited = set()
        queue = [(octile(start, end), 0, start)]

        while queue:
            priority, current_cost, current_cell = hq.heappop(queue)
            if current_cell in visited:
                continue
            visited.add(current_cell)
            self.stats["nodes_expanded"] += 1

            yield visited, None

            if current_cell == end:
                break

            parent = came_from.get(current_cell, None)
            if parent is None:
                jump_points = []
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        jp = self.jump(current_cell, (dr, dc), end, grid)
                        if jp is not None:
                            jump_points.append(jp)
            else:
                jump_points = self.identify_successors(current_cell, parent, end, grid)

            for jp in jump_points:
                steps = max(abs(jp[0] - current_cell[0]), abs(jp[1] - current_cell[1]))
                is_diagonal = jp[0] != current_cell[0] and jp[1] != current_cell[1]
                step_cost = SQRT2 if is_diagonal else 1
                new_cost = current_cost + steps * step_cost
                if new_cost < distance.get(jp, float('inf')):
                    distance[jp] = new_cost
                    came_from[jp] = current_cell
                    hq.heappush(queue, (new_cost + octile(jp, end), new_cost, jp))

        if end in came_from or end == start:
            jump_path = [end]
            while jump_path[-1] != start:
                jump_path.append(came_from[jump_path[-1]])
            jump_path.reverse()
            path = fill_in_path(jump_path)
            self.record_path(path, distance[end])
            yield visited, path
        else:
            yield visited, None

    def identify_successors(self, current, parent, goal, grid):
        valid = prune(parent, current, grid)
        successors = []
        for candidate in valid:
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
            if not can_move(grid, row, col, dr, dc):
                return None
            row += dr
            col += dc
            self.stats["cells_scanned"] += 1

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
                if forced_neighbours((row, col), grid, direction):
                    return (row, col)


def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0


def is_free(grid, row, col):
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
        dr = sign(target[0] - path[-1][0])
        dc = sign(target[1] - path[-1][1])
        while path[-1] != target:
            path.append((path[-1][0] + dr, path[-1][1] + dc))
    return path


def prune(parent, current, grid):
    row, col = current
    dr = sign(current[0] - parent[0])
    dc = sign(current[1] - parent[1])

    if dr != 0 and dc != 0:
        # Natural neighbours of a diagonal move: keep going straight in each part, or diagonally.
        candidates = [(row + dr, col), (row, col + dc), (row + dr, col + dc)]
    else:
        candidates = [(row + dr, col + dc)]
        candidates += forced_neighbours(current, grid, (dr, dc))

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
