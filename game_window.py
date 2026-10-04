import glob
import math
import os
import random
import sys

import numpy as np
import pygame

import race
import renderer
from algos.base import step_search
from algos.dijkstra import Dijkstra
from algos.astar import Astar
from algos.bidirectional import Bidirect
from algos.jps import JPS
from grid import Grid
from maps_io import load_movingai_map, load_scenarios

# Fixed window settings

GRID_AREA_WIDTH = 850
PANEL_WIDTH = 300
WINDOW_WIDTH = GRID_AREA_WIDTH + PANEL_WIDTH
TOOLBAR_HEIGHT = 60
GRID_AREA_HEIGHT = 800
STATUS_BAR_HEIGHT = 60
WINDOW_HEIGHT = TOOLBAR_HEIGHT + GRID_AREA_HEIGHT + STATUS_BAR_HEIGHT
PANEL_X = GRID_AREA_WIDTH + 15
STATUS_TOP = TOOLBAR_HEIGHT + GRID_AREA_HEIGHT

BUTTON_WIDTH = 120
BUTTON_HEIGHT = 40
FPS = 60
MUD_COST = 3.0
MAPS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps")

# Search steps per frame for keys 1-5.
SPEEDS = [1, 5, 25, 100, 500]
SPEED_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4}


# The label on the algorithm button, and the class it runs.
ALGORITHMS = {
    "Dijkstra": Dijkstra,
    "A*": Astar,
    "JPS": JPS,
    "Bidirectional": Bidirect,
}


# Selects the algorithm to run
# Sets algo_class to whatever algorithm the button says
# If the button is JPS, just run JPS, else then run the algo with the movement
def make_algorithm(selected_algo, movement):
    algo_class = ALGORITHMS[selected_algo]
    if algo_class is JPS:
        # JPS only works with 8-directional movement.
        return JPS()
    return algo_class(movement)


def run_label(selected_algo, movement):
    # The name shown in the stats panel, e.g. "A* 8". JPS is always 8-directional.
    if ALGORITHMS[selected_algo] is JPS:
        return "JPS"
    return f"{selected_algo} {movement}"


# Finds the maps files from the folder
def find_map_files():
    return sorted(glob.glob(os.path.join(MAPS_FOLDER, "*.map")))


def read_map(map_path, grid_width, grid_height):
    # The first maps is the empty grid, so it runs regardless
    if map_path is None:
        return Grid(grid_width, grid_height, 1), [], "Editable grid"
    # Loads up the maps and their scen data
    grid = load_movingai_map(map_path)
    scenario_path = map_path + ".scen"
    if os.path.exists(scenario_path):
        scenarios = load_scenarios(scenario_path)
    else:
        scenarios = []
    return grid, scenarios, os.path.basename(map_path)


def default_markers(grid):
    # Picks where the start and end markers go
    # top-left and bottom-right corners; on a benchmark map they avoid walls.
    # Gets a list of every cell that is not a wall
    free_cells = np.argwhere(~np.isinf(grid.grid))
    first = free_cells[0]
    last = free_cells[-1]
    return (int(first[0]), int(first[1])), (int(last[0]), int(last[1]))



def button(x, y, width=BUTTON_WIDTH):
    return pygame.Rect(x, y, width, BUTTON_HEIGHT)


# ---------- The app ----------

class App:
    """The whole visualiser: its state, what happens on each click or key, and drawing."""

    def __init__(self, grid_width, grid_height):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Pathfinding Visualizer")
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 22)
        self.clock = pygame.time.Clock()
        self.grid_area = pygame.Rect(0, TOOLBAR_HEIGHT, GRID_AREA_WIDTH, GRID_AREA_HEIGHT)

        # Toolbar buttons along the top, and the side panel's buttons on the right.
        self.run_button = button(20, 10)
        self.clear_button = button(160, 10)
        self.algo_button = button(300, 10)
        self.mud_button = button(440, 10)
        self.wall_button = button(580, 10)
        self.movement_button = button(720, 10)
        self.race_button = button(PANEL_X, 10)
        self.next_map_button = button(PANEL_X + 130, 10)
        self.scenario_button = button(PANEL_X, 60, 2 * BUTTON_WIDTH + 10)

        # Starting choices.
        self.algo_names = list(ALGORITHMS.keys())
        self.selected_algo = "Dijkstra"
        self.movement = 4
        self.mode = "wall"          # what painting does: "wall" or "mud"
        self.speed_index = 0

        # What the mouse is doing right now.
        self.painting = False
        self.dragging = None        # None, "start" or "end"

        # Race mode.
        self.race_mode = False
        self.racers = None

        # The maps to cycle through: the blank editable grid, then every map in maps/.
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.map_paths = [None] + find_map_files()
        self.map_index = 0
        self.load_map()

    # ---------- Map and search state ----------

    def load_map(self):
        # Load the current map and reset everything that belongs to the old one.
        path = self.map_paths[self.map_index]
        self.grid, self.scenarios, self.map_name = read_map(path, self.grid_width, self.grid_height)
        self.layout = renderer.GridLayout(self.grid, self.grid_area)
        self.background = renderer.build_background(self.grid, self.layout)
        self.start, self.end = default_markers(self.grid)
        self.current_scenario = None
        self.race_allowed = race.map_fits(self.grid, self.grid_area)
        self.last_results = {}      # latest finished result per algorithm, for this map
        self.overlay = renderer.new_overlay(self.layout)
        self.drawn_visited = set()
        self.clear_search()

    def clear_search(self):
        # Wipe the current search off the screen.
        self.search_generator = None
        self.animated_algo = None
        self.current_label = None
        self.current_path = None
        if self.drawn_visited:      # only make a new overlay if there's something to wipe
            self.overlay = renderer.new_overlay(self.layout)
            self.drawn_visited = set()

    def map_changed(self):
        # After an edit, the old search and results no longer match the map.
        self.clear_search()
        self.last_results = {}
        self.current_scenario = None

    # ---------- Button actions ----------

    def start_run(self):
        self.clear_search()
        self.current_label = run_label(self.selected_algo, self.movement)
        self.animated_algo = make_algorithm(self.selected_algo, self.movement)
        self.search_generator = self.animated_algo.search(self.start, self.end, self.grid)

    def next_algorithm(self):
        index = self.algo_names.index(self.selected_algo)
        self.selected_algo = self.algo_names[(index + 1) % len(self.algo_names)]

    def toggle_movement(self):
        # Locked while JPS is selected, since JPS is always 8-directional.
        if ALGORITHMS[self.selected_algo] is JPS:
            return
        if self.movement == 4:
            self.movement = 8
        else:
            self.movement = 4

    def toggle_race(self):
        # Checks if race mode is already on, if so turn it off
        if self.race_mode:
            self.race_mode = False
            self.racers = None
        # If race mode is allowed, and the map is small enough then let it run
        elif self.race_allowed:
            self.race_mode = True
            self.racers = race.make_racers(self.grid, self.grid_area)

    def pick_scenario(self):
        # Use an official start/goal pair from the map's .scen file.
        self.current_scenario = random.choice(self.scenarios)
        self.start = self.current_scenario.start
        self.end = self.current_scenario.goal
        self.clear_search()
        self.last_results = {}

    # ---------- Input ----------

    # Handles the speed of the game
    def handle_key(self, key):
        if key in SPEED_KEYS:
            self.speed_index = SPEED_KEYS[key]
        elif key == pygame.K_ESCAPE:
            self.race_mode = False
            self.racers = None

    #
    def handle_click(self, pos):
        if self.race_button.collidepoint(pos):
            self.toggle_race()
        elif self.race_mode:
            # If we are in race mode, and press run, then start all races on the same map
            if self.run_button.collidepoint(pos):
                for racer in self.racers:
                    racer.start(self.grid, self.start, self.end)
        elif self.run_button.collidepoint(pos):
            self.start_run()
        elif self.clear_button.collidepoint(pos):
            self.load_map()                     # reload the current map from scratch
        elif self.next_map_button.collidepoint(pos):
            self.map_index = (self.map_index + 1) % len(self.map_paths)
            self.load_map()
        elif self.scenario_button.collidepoint(pos) and self.scenarios:
            self.pick_scenario()
        elif self.algo_button.collidepoint(pos):
            self.next_algorithm()
        elif self.movement_button.collidepoint(pos):
            self.toggle_movement()
        elif self.wall_button.collidepoint(pos):
            self.mode = "wall"
        elif self.mud_button.collidepoint(pos):
            self.mode = "mud"
        elif self.layout.cell_at(pos[0], pos[1]) is not None:
            self.painting = True

    def handle_drag(self, pos):
        # Called while the mouse button is held: move a marker, or paint the cell under the mouse.
        cell = self.layout.cell_at(pos[0], pos[1])
        if cell is None:
            return
        row, col = cell

        if self.dragging is not None:
            # Markers can't go onto a wall or onto each other.
            if self.grid.is_wall(row, col) or cell == self.start or cell == self.end:
                return
            if self.dragging == "start":
                self.start = cell
            else:
                self.end = cell
            self.map_changed()

        elif self.painting:
            if self.mode == "wall":
                if cell == self.start or cell == self.end:
                    return              # never paint a wall over a marker
                self.grid.set_cost(row, col, np.inf)
            else:
                self.grid.set_cost(row, col, MUD_COST)
            renderer.draw_background_cell(self.background, self.grid, self.layout, row, col)
            self.map_changed()

    # ---------- Each frame ----------

    def advance_search(self):
        # If in race mode use race mode advance method
        if self.race_mode:
            race.advance_all(self.racers)
            return
        # If nothing is being run then return
        if self.search_generator is None:
            return
        # Set visited to none, and finished to false
        visited = None
        finished = False
        # A speed dial for how many cells to explore before showing the next frame.
        for step in range(SPEEDS[self.speed_index]):
            # Takes the paused search, lets it explore one more cell, and pauses it again.
            result = step_search(self.animated_algo, self.search_generator)
            if result is None:
                finished = True
                break
            # Returns the visited nodes, and the path (if it is finished)
            visited, path = result
            # If the path is not empty then search is finished.
            if path is not None:
                self.current_path = path
                finished = True
                break

        # Works out which cells are newly explored, everything in visited that isn't already painted.
        if visited is not None:
            new_cells = visited - self.drawn_visited
            renderer.draw_visited_cells(self.overlay, self.layout, new_cells)
            self.drawn_visited.update(new_cells)
        if finished:
            self.search_generator = None
            # Saves data copy
            self.last_results[self.current_label] = dict(self.animated_algo.stats)

    def draw(self):
        self.screen.fill(renderer.BACKGROUND)
        self.draw_grid()
        self.draw_toolbar()
        self.draw_panel()
        self.draw_status_bar()
        pygame.display.flip()

    def draw_grid(self):
        if self.race_mode:
            race.draw_race(self.screen, self.small_font, self.racers, self.start, self.end)
            return
        renderer.draw_grid_layers(self.screen, self.layout, self.background, self.overlay)
        if self.current_path:
            renderer.draw_path(self.screen, self.layout, self.current_path)
        renderer.draw_marker(self.screen, self.layout, self.start, renderer.START)
        renderer.draw_marker(self.screen, self.layout, self.end, renderer.END)

    def draw_toolbar(self):
        # Editing buttons are shown locked in race mode.
        locked = self.race_mode
        renderer.draw_button(self.screen, self.font, self.run_button, "Run")
        renderer.draw_button(self.screen, self.font, self.clear_button, "Clear", locked=locked)
        renderer.draw_button(self.screen, self.font, self.algo_button, self.selected_algo, locked=locked)
        renderer.draw_button(self.screen, self.font, self.mud_button, "Mud Edit", locked=locked)
        renderer.draw_button(self.screen, self.font, self.wall_button, "Wall Edit", locked=locked)
        if ALGORITHMS[self.selected_algo] is JPS:
            renderer.draw_button(self.screen, self.font, self.movement_button, "8-dir (JPS)", locked=True)
        else:
            renderer.draw_button(self.screen, self.font, self.movement_button, f"{self.movement}-dir", locked=locked)

    def draw_panel(self):
        # The side panel: race and map buttons, map info, then stats or the race summary.
        screen, font, small = self.screen, self.font, self.small_font
        renderer.draw_button(screen, font, self.next_map_button, "Next map", locked=self.race_mode)

        # Show Random scenario if this map has scenarios and not racing.
        if self.scenarios and not self.race_mode:
            renderer.draw_button(screen, font, self.scenario_button, "Random scenario")
        # Shows map details like size, name etc
        map_text = f"Map: {self.map_name} ({self.grid.width}x{self.grid.height})"
        renderer.draw_text(screen, small, map_text, (PANEL_X, 110))

        # Displays the algos path cost against offical answers
        if self.current_scenario is not None:
            scenario_text = (f"Bucket {self.current_scenario.bucket}, "
                             f"official optimal {self.current_scenario.optimal_length:.4f}")
            renderer.draw_text(screen, small, scenario_text, (PANEL_X, 132), renderer.NOTE_TEXT)
        elif not self.race_allowed:
            renderer.draw_text(screen, small, "Too large for race view", (PANEL_X, 132), renderer.TEXT_LOCKED)

        # Displays finishing order summary of the race mode
        if self.race_mode:
            renderer.draw_button(screen, font, self.race_button, "Back")
            race.draw_race_summary(screen, font, small, PANEL_X, 165, self.racers)
            return
        renderer.draw_button(screen, font, self.race_button, "Race", locked=not self.race_allowed)

        #Show the live stats of the algo whilst it is running
        if self.current_label is None:
            renderer.draw_current_stats(screen, font, small, PANEL_X, 165, None, None, False)
        else:
            searching = self.search_generator is not None
            renderer.draw_current_stats(screen, font, small, PANEL_X, 165, self.current_label,
                                        self.animated_algo.stats, searching)
        renderer.draw_results_table(screen, font, small, PANEL_X, 405, self.last_results)

    def draw_status_bar(self):
        # The legend and the speed line under the grid.
        renderer.draw_legend(self.screen, self.small_font, 20, STATUS_TOP + 8)
        # Displays the speed mode of each mode
        if self.race_mode:
            speed_text = f"Race speed: {race.STEPS_PER_FRAME} steps/frame (fixed)"
        else:
            speed_text = f"Speed: {SPEEDS[self.speed_index]} steps/frame (keys 1-5)"
        renderer.draw_text(self.screen, self.small_font, speed_text, (20, STATUS_TOP + 34))
        # Display that mud is to be treated as a normal floor as JPS doesnt account for weights
        if ALGORITHMS[self.selected_algo] is JPS and not self.race_mode:
            renderer.draw_text(self.screen, self.small_font, "Assumes uniform cost: mud is treated as floor",
                               (440, STATUS_TOP + 34), renderer.NOTE_TEXT)

    # ---------- The main loop ----------

    def run(self):
        # Keep the app going until the window is closed. Each time round this loop is one frame
        # (about 60 a second): deal with what the user did, move the search on, then draw.
        running = True
        while running:
            # Go through everything the user did since the last frame (clicks, keys, mouse moves).
            for event in pygame.event.get():
                # The window's close button was pressed, so stop the loop.
                if event.type == pygame.QUIT:
                    running = False
                # A key was pressed: change the speed, or Esc to leave race mode.
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
                # The left mouse button was pressed: work out what was clicked.
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                    # If that click started painting, paint the cell under the mouse straight away,
                    # so a single click paints one cell without having to move the mouse.
                    if self.painting or self.dragging:
                        self.handle_drag(event.pos)     # the first click paints too
                # The left mouse button was let go, so stop painting.
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.painting = False
                    self.dragging = None
                # The mouse moved while the button is held down, so paint the cell it's now over.
                elif event.type == pygame.MOUSEMOTION and (self.painting or self.dragging):
                    self.handle_drag(event.pos)

            # Let the search explore a few more cells (or move the racers on in race mode).
            self.advance_search()
            # Draw the whole window for this frame and show it.
            self.draw()
            # Wait a moment so the loop runs at 60 frames a second, not as fast as the computer can.
            self.clock.tick(FPS)

        # The loop has ended because the window was closed, so shut Pygame down cleanly.
        pygame.quit()


def main(grid_width=50, grid_height=50):
    # Create the app (opens the window and loads the first map), then start its main loop.
    App(grid_width, grid_height).run()


# Only start the app if this file is run directly (python game_window.py),
# not when another file such as a test imports it.
if __name__ == "__main__":
        main()
