"""Race mode: several algorithms on the same map, side by side, advanced in lockstep.

Every tick, each racer takes the same number of search steps. One step is one yield from
search(), which is one node expansion, so the race is fair in expansions, not wall-clock
time. A JPS expansion can scan many cells, so its panel also shows cells scanned.
"""
import numpy as np
import pygame

import renderer
from algos.astar import Astar
from algos.base import step_search
from algos.dijkstra import Dijkstra
from algos.jps import JPS

# The algorithms that race, as (label, class, movement). Edit this list to race others.
# JPS ignores movement: it is always 8-directional.
RACE_ALGORITHMS = [
    ("Dijkstra", Dijkstra, 4),
    ("A* 4-dir", Astar, 4),
    ("A* 8-dir", Astar, 8),
    ("JPS", JPS, 8),
]

PANEL_HEADER_HEIGHT = 46
PANEL_BORDER = (90, 90, 90)


def make_algorithm(algo_class, movement):
    if algo_class is JPS:
        return JPS()
    return algo_class(movement)


def split_into_panels(area, count):
    # Two columns; as many rows as needed (4 algorithms -> 2x2).
    columns = 2
    rows = (count + 1) // 2
    width = area.width // columns
    height = area.height // rows
    panels = []
    for i in range(count):
        row = i // columns
        col = i % columns
        panels.append(pygame.Rect(area.x + col * width, area.y + row * height, width, height))
    return panels


class Racer:
    """One algorithm's lane: its search, its panel and how far it has got."""

    def __init__(self, label, algo_class, movement, grid, panel_rect):
        self.label = label
        self.algo_class = algo_class
        self.movement = movement
        self.panel_rect = panel_rect
        grid_rect = pygame.Rect(panel_rect.x, panel_rect.y + PANEL_HEADER_HEIGHT,
                                panel_rect.width, panel_rect.height - PANEL_HEADER_HEIGHT)
        # Each panel has its own layout and surfaces at its own size.
        self.layout = renderer.GridLayout(grid, grid_rect)
        self.background = renderer.build_background(grid, self.layout)
        # JPS treats mud as floor, so its cost is only comparable on a map with no mud.
        self.map_has_mud = bool(np.any((grid.grid > 1) & ~np.isinf(grid.grid)))
        self.reset()

    def reset(self):
        self.algo = None
        self.generator = None
        self.steps = 0
        self.finished = False
        self.path = None
        self.overlay = renderer.new_overlay(self.layout)
        self.drawn_visited = set()

    def start(self, grid, start, end):
        self.reset()
        self.algo = make_algorithm(self.algo_class, self.movement)
        self.generator = self.algo.search(start, end, grid)

    def advance(self, steps):
        # Take up to `steps` search steps. Only real yields count as steps; running off
        # the end of the generator (StopIteration) just means the search is over.
        if self.generator is None:
            return
        latest_visited = None
        for i in range(steps):
            # step_search also adds the time spent inside the search to algo.stats.
            result = step_search(self.algo, self.generator)
            if result is None:
                self.finished = True
                self.generator = None
                break
            latest_visited, path = result
            self.steps += 1
            if path is not None:
                self.path = path
                self.finished = True
                self.generator = None
                break

        if latest_visited is not None:
            new_cells = latest_visited - self.drawn_visited
            renderer.draw_visited_cells(self.overlay, self.layout, new_cells)
            self.drawn_visited.update(new_cells)


def map_fits(grid, area):
    # Each panel needs at least 1 pixel per cell, so very large maps can't be raced.
    panel = split_into_panels(area, len(RACE_ALGORITHMS))[0]
    grid_height_px = panel.height - PANEL_HEADER_HEIGHT
    return grid.width <= panel.width and grid.height <= grid_height_px


def make_racers(grid, area):
    panels = split_into_panels(area, len(RACE_ALGORITHMS))
    racers = []
    for (label, algo_class, movement), panel in zip(RACE_ALGORITHMS, panels):
        racers.append(Racer(label, algo_class, movement, grid, panel))
    return racers


def advance_all(racers, steps):
    for racer in racers:
        racer.advance(steps)


def finishing_positions(racers):
    # Rank finished racers by how many steps they needed. Everyone moves in lockstep,
    # so fewer steps means finished first. Racers with equal steps share a position.
    positions = {}
    for racer in racers:
        if racer.finished:
            faster = 0
            for other in racers:
                if other.finished and other.steps < racer.steps:
                    faster += 1
            positions[racer.label] = faster + 1
    return positions


def ordinal(n):
    if n == 1:
        return "1st"
    if n == 2:
        return "2nd"
    if n == 3:
        return "3rd"
    return f"{n}th"


def draw_racer(screen, small_font, racer, start, end, position):
    renderer.draw_grid_layers(screen, racer.layout, racer.background, racer.overlay)
    if racer.path:
        renderer.draw_path(screen, racer.layout, racer.path)
    renderer.draw_marker(screen, racer.layout, start, renderer.START)
    renderer.draw_marker(screen, racer.layout, end, renderer.END)
    pygame.draw.rect(screen, PANEL_BORDER, racer.panel_rect, 1)

    x = racer.panel_rect.x + 8
    y = racer.panel_rect.y + 5
    if racer.algo is None:
        nodes = 0
        scanned = 0
    else:
        nodes = racer.algo.stats["nodes_expanded"]
        scanned = racer.algo.stats["cells_scanned"]

    first_line = f"{racer.label}   nodes expanded: {nodes}"
    if racer.algo_class is JPS:
        first_line += f"   scanned: {scanned}"
    renderer.draw_text(screen, small_font, first_line, (x, y))

    if racer.finished:
        stats = racer.algo.stats
        if stats["path_cost"] is None:
            result = "No path"
        else:
            cost_text = renderer.format_cost(stats["path_cost"])
            if racer.algo_class is JPS and racer.map_has_mud:
                cost_text += "*"
            result = f"cost {cost_text}, {stats['path_length_cells']} cells"
        second_line = f"{ordinal(position)} in {racer.steps} steps: {result}, {stats['search_time_ms']:.1f} ms"
        renderer.draw_text(screen, small_font, second_line, (x, y + 20), renderer.NOTE_TEXT)
    elif racer.generator is not None:
        renderer.draw_text(screen, small_font, f"step {racer.steps}", (x, y + 20), renderer.TEXT_LOCKED)
    else:
        renderer.draw_text(screen, small_font, "Press Run", (x, y + 20), renderer.TEXT_LOCKED)


def draw_race(screen, small_font, racers, start, end):
    positions = finishing_positions(racers)
    for racer in racers:
        draw_racer(screen, small_font, racer, start, end, positions.get(racer.label))


def draw_race_summary(screen, font, small_font, x, y, racers):
    renderer.draw_text(screen, font, "Race mode", (x, y))
    y += 30
    lines = [
        "Run: start the race on the current map.",
        "Esc or Back: return to editing.",
        "Every racer takes the same number of",
        "steps (node expansions) per frame.",
    ]
    for line in lines:
        renderer.draw_text(screen, small_font, line, (x, y), renderer.TEXT_LOCKED)
        y += 22

    y += 14
    renderer.draw_text(screen, font, "Finishing order", (x, y))
    y += 30
    positions = finishing_positions(racers)
    finished = [racer for racer in racers if racer.finished]
    finished.sort(key=lambda racer: racer.steps)
    if not finished:
        renderer.draw_text(screen, small_font, "Nobody has finished yet.", (x, y), renderer.TEXT_LOCKED)
    for racer in finished:
        text = f"{ordinal(positions[racer.label])}  {racer.label}  ({racer.steps} steps)"
        renderer.draw_text(screen, small_font, text, (x, y))
        y += 22

    for racer in racers:
        if racer.algo_class is JPS and racer.finished and racer.map_has_mud:
            renderer.draw_text(screen, small_font, "* JPS cost treats mud as floor", (x, y + 10), renderer.NOTE_TEXT)
            break
