"""Race mode: four algorithms search the same map at the same time, side by side.

Every frame, each racer takes the same number of search steps (one step = one cell
expanded). The racer that reaches the end in the fewest steps wins.
"""
import pygame

import renderer
from algos.astar import Astar
from algos.base import step_search
from algos.bidirectional import Bidirect
from algos.dijkstra import Dijkstra
from algos.jps import JPS


# ---------- Settings ----------

# The four racers. They all move in 8 directions, so they're solving the same problem.
# The same objects are reused for every race: search() resets their stats each time.
# Each entry is (the name shown in its panel, the algorithm object that does the searching).
RACE_ALGORITHMS = [
    ("Dijkstra", Dijkstra(8)),
    ("A*", Astar(8)),
    ("Bidirectional", Bidirect(8)),
    ("JPS", JPS()),
]

# How many search steps every racer takes each frame. Fixed, so every race runs the same.
STEPS_PER_FRAME = 5

HEADER_HEIGHT = 46      # space at the top of each panel for the racer's name and score
BORDER = (90, 90, 90)   # the grey outline drawn around each panel
PLACES = ["1st", "2nd", "3rd", "4th"]   # turns "how many racers beat you" (0-3) into a place


# ---------- One racer ----------

class Racer:
    # One panel of the race: one algorithm, its own drawing of the map, and its progress.
    # It works like a mini version of the normal app, squeezed into a quarter of the screen.

    def __init__(self, label, algo, grid, panel):
        self.label = label
        self.algo = algo
        self.panel = panel
        # The map sits under the header line, and gets its own layers
        map_area = pygame.Rect(panel.x, panel.y + HEADER_HEIGHT, panel.width, panel.height - HEADER_HEIGHT)
        # Work out how big each cell is so the whole map fits in this smaller space.
        self.layout = renderer.GridLayout(grid, map_area)
        # Draw the floor, walls and mud once, at this panel's size.
        self.background = renderer.build_background(grid, self.layout)
        self.reset()

    def reset(self):
        # Back to "not started": no search, no steps, no path, and no blue cells on screen.
        self.algo.reset_stats()
        self.generator = None       # the paused search; None means nothing is running
        self.steps = 0              # this racer's score: how many steps it has taken
        self.finished = False
        self.path = None
        self.overlay = renderer.new_overlay(self.layout)   # a fresh, empty layer for the blue cells
        self.drawn_visited = set()  # which cells are already painted blue

    def start(self, grid, start, end):
        # Called when Run is pressed in race mode: clear the last race and load a new paused search.
        # Nothing is searched yet; advance() does the actual steps, frame by frame.
        self.reset()
        self.generator = self.algo.search(start, end, grid)

    def advance(self):
        # The same idea as the normal Run button: take a few steps, then draw the new cells.
        if self.generator is None:
            return                          # not started yet, or already finished
        visited = None
        for i in range(STEPS_PER_FRAME):
            # Let the search explore one more cell, then pause it again.
            result = step_search(self.algo, self.generator)
            if result is None:              # the search is over and found no path
                self.finished = True
                self.generator = None
                break
            visited, path = result
            self.steps += 1                 # one more step towards this racer's score
            if path is not None:            # the search reached the end
                self.path = path
                self.finished = True
                self.generator = None
                break

        # Paint only the cells that are new since last frame, not every visited cell again.
        if visited is not None:
            new_cells = visited - self.drawn_visited
            renderer.draw_visited_cells(self.overlay, self.layout, new_cells)
            self.drawn_visited.update(new_cells)

    def draw(self, screen, font, start, end, place):
        # The map, the path and the markers, using the same renderer as normal mode.
        renderer.draw_grid_layers(screen, self.layout, self.background, self.overlay)
        if self.path:
            renderer.draw_path(screen, self.layout, self.path)
        renderer.draw_marker(screen, self.layout, start, renderer.START)
        renderer.draw_marker(screen, self.layout, end, renderer.END)
        pygame.draw.rect(screen, BORDER, self.panel, 1)     # the 1 means a thin outline, not a filled box

        # The header: name and score on the first line, progress or result on the second.
        stats = self.algo.stats
        x = self.panel.x + 8        # a little in from the panel's left edge
        y = self.panel.y + 5        # a little down from the panel's top edge
        header = f"{self.label}   nodes expanded: {stats['nodes_expanded']}"
        if self.label == "JPS":
            # One JPS step can scan many cells, so show that too, to keep the race honest.
            header += f"   scanned: {stats['cells_scanned']}"
        renderer.draw_text(screen, font, header, (x, y))

        # Second line, 20 pixels lower: the result if it's done, the step count if it's running,
        # or "Press Run" if the race hasn't started.
        if self.finished:
            result = f"{place} in {self.steps} steps, cost {renderer.format_cost(stats['path_cost'])}"
            renderer.draw_text(screen, font, result, (x, y + 20), renderer.NOTE_TEXT)
        elif self.generator is not None:
            renderer.draw_text(screen, font, f"step {self.steps}", (x, y + 20), renderer.TEXT_LOCKED)
        else:
            renderer.draw_text(screen, font, "Press Run", (x, y + 20), renderer.TEXT_LOCKED)


# ---------- Setting up a race ----------

def make_panels(area):
    # Split the map area into a 2x2 grid of panels, one per racer.
    # // divides and drops the decimal, because pixels have to be whole numbers.
    w = area.width // 2
    h = area.height // 2
    return [
        pygame.Rect(area.x, area.y, w, h),            # top left
        pygame.Rect(area.x + w, area.y, w, h),        # top right
        pygame.Rect(area.x, area.y + h, w, h),        # bottom left
        pygame.Rect(area.x + w, area.y + h, w, h),    # bottom right
    ]


def map_fits(grid, area):
    # Each panel needs at least 1 pixel per cell, so very big maps can't be raced.
    # All four panels are the same size, so checking the first one is enough.
    panel = make_panels(area)[0]
    return grid.width <= panel.width and grid.height <= panel.height - HEADER_HEIGHT


def make_racers(grid, area):
    # Give each algorithm its own panel and build a Racer for it.
    # zip pairs the two lists up in order: the first algorithm gets the top-left panel, and so on.
    racers = []
    for (label, algo), panel in zip(RACE_ALGORITHMS, make_panels(area)):
        racers.append(Racer(label, algo, grid, panel))
    return racers


# ---------- Running the race ----------

def advance_all(racers):
    # Everyone takes the same number of steps each frame. That's what makes it a fair race.
    # Called once per frame by game_window.py while race mode is on.
    for racer in racers:
        racer.advance()


# ---------- Places and drawing ----------

def place_of(racer, racers):
    # Your place = 1 + how many finished racers needed fewer steps than you.
    # Racers with the same number of steps share a place.
    faster = 0
    for other in racers:
        if other.finished and other.steps < racer.steps:
            faster += 1
    return PLACES[faster]       # 0 faster racers = "1st", 1 = "2nd", and so on


def draw_race(screen, font, racers, start, end):
    # Draw all four panels, each one told what place it's in.
    for racer in racers:
        racer.draw(screen, font, start, end, place_of(racer, racers))


def draw_race_summary(screen, font, small_font, x, y, racers):
    # The side panel: how race mode works, then the finishing order.
    # After drawing each line, y is moved down so the next line goes underneath it.
    renderer.draw_text(screen, font, "Race mode", (x, y))
    y += 30
    lines = [
        "Run: start the race on the current map.",
        "Esc or Back: return to editing.",
        f"Every racer takes {STEPS_PER_FRAME} steps per frame.",
        "JPS ignores mud, so race without mud",
        "for a fair comparison.",
    ]
    for line in lines:
        renderer.draw_text(screen, small_font, line, (x, y), renderer.TEXT_LOCKED)
        y += 22

    y += 14
    renderer.draw_text(screen, font, "Finishing order", (x, y))
    y += 30
    # Keep only the racers that have crossed the line.
    finished = []
    for racer in racers:
        if racer.finished:
            finished.append(racer)
    # Sort them by their step count. lambda is a tiny function: give it a racer, get back its steps.
    finished.sort(key=lambda racer: racer.steps)    # fewest steps first

    if not finished:
        renderer.draw_text(screen, small_font, "Nobody has finished yet.", (x, y), renderer.TEXT_LOCKED)
    # One line per finished racer, e.g. "1st  JPS  (6 steps)".
    for racer in finished:
        text = f"{place_of(racer, racers)}  {racer.label}  ({racer.steps} steps)"
        renderer.draw_text(screen, small_font, text, (x, y))
        y += 22
