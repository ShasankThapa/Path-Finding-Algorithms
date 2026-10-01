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

GRID_AREA_WIDTH = 850
PANEL_WIDTH = 300
WINDOW_WIDTH = GRID_AREA_WIDTH + PANEL_WIDTH
TOOLBAR_HEIGHT = 60
GRID_AREA_HEIGHT = 800
STATUS_BAR_HEIGHT = 60
WINDOW_HEIGHT = TOOLBAR_HEIGHT + GRID_AREA_HEIGHT + STATUS_BAR_HEIGHT

BUTTON_WIDTH = 120
BUTTON_HEIGHT = 40
FPS = 60
MUD_COST = 3.0
MAPS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps")

# Search steps per frame for keys 1-5. +/- moves up and down this list.
SPEEDS = [1, 5, 25, 100, 500]

# Maps the label shown on the algorithm button to the PathAlgo subclass it runs.
ALGORITHMS = {
    "Dijkstra": Dijkstra,
    "A*": Astar,
    "JPS": JPS,
    "Bidirectional": Bidirect,
}

SPEED_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4}
FASTER_KEYS = (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)
SLOWER_KEYS = (pygame.K_MINUS, pygame.K_KP_MINUS)


def make_algorithm(selected_algo, movement):
    algo_class = ALGORITHMS[selected_algo]
    if algo_class is JPS:
        # JPS only works with 8-directional movement.
        return JPS()
    return algo_class(movement)


def find_map_files():
    return sorted(glob.glob(os.path.join(MAPS_FOLDER, "*.map")))


def load_map(map_path, grid_width, grid_height):
    # map_path None means the blank editable grid. Returns (grid, scenarios, name).
    if map_path is None:
        return Grid(grid_width, grid_height, 1), [], "Editable grid"
    grid = load_movingai_map(map_path)
    scenario_path = map_path + ".scen"
    if os.path.exists(scenario_path):
        scenarios = load_scenarios(scenario_path)
    else:
        scenarios = []
    return grid, scenarios, os.path.basename(map_path)


def default_markers(grid):
    # The first and last free cells in reading order. On a blank grid these are the
    # top-left and bottom-right corners; on a benchmark map they avoid walls.
    free_cells = np.argwhere(~np.isinf(grid.grid))
    first = free_cells[0]
    last = free_cells[-1]
    return (int(first[0]), int(first[1])), (int(last[0]), int(last[1]))


def run_label(selected_algo, movement):
    # Name shown in the stats panel, e.g. "A* 8". JPS is always 8-directional.
    if ALGORITHMS[selected_algo] is JPS:
        return "JPS"
    return f"{selected_algo} {movement}"


def is_on_marker(layout, marker, position):
    # True if the mouse is within the marker's circle (markers can be bigger than a cell).
    centre_x, centre_y = layout.cell_centre(marker[0], marker[1])
    distance = math.hypot(position[0] - centre_x, position[1] - centre_y)
    return distance <= layout.marker_radius()


def main(grid_width=50, grid_height=50):
    pygame.init()
    font = pygame.font.Font(None, 24)
    small_font = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Pathfinding Visualizer")

    grid_area = pygame.Rect(0, TOOLBAR_HEIGHT, GRID_AREA_WIDTH, GRID_AREA_HEIGHT)
    panel_x = GRID_AREA_WIDTH + 15
    status_top = TOOLBAR_HEIGHT + GRID_AREA_HEIGHT

    # The maps to cycle through: the blank editable grid, then every Moving AI map in maps/.
    map_paths = [None] + find_map_files()
    map_index = 0
    g, scenarios, map_name = load_map(map_paths[map_index], grid_width, grid_height)
    layout = renderer.GridLayout(g, grid_area)
    background = renderer.build_background(g, layout)
    start, end = default_markers(g)
    current_scenario = None
    race_allowed = race.map_fits(g, grid_area)

    # Search state. drawn_visited remembers which cells are already on the overlay,
    # so each frame only the newly visited cells get drawn.
    search_generator = None
    current_path = None
    overlay = renderer.new_overlay(layout)
    drawn_visited = set()

    # Stats panel state. animated_algo fills in its stats live as the animation runs.
    # last_results keeps the latest finished result per algorithm for this map.
    current_label = None
    animated_algo = None
    last_results = {}

    # Race mode shows several algorithms side by side on the current map (see race.py).
    race_mode = False
    racers = None

    algo_list = list(ALGORITHMS.keys())
    selected_algo = "Dijkstra"
    movement = 4
    mode = "wall"
    speed_index = 0

    painting = False
    dragging = None  # None, "start" or "end"

    run_button = pygame.Rect(20, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
    clear_button = pygame.Rect(160, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
    algo_button = pygame.Rect(300, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
    mud_button = pygame.Rect(440, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
    wall_button = pygame.Rect(580, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
    movement_button = pygame.Rect(720, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
    race_button = pygame.Rect(panel_x, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
    next_map_button = pygame.Rect(panel_x + 130, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
    scenario_button = pygame.Rect(panel_x, 60, 2 * BUTTON_WIDTH + 10, BUTTON_HEIGHT)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in SPEED_KEYS:
                    speed_index = SPEED_KEYS[event.key]
                elif event.key in FASTER_KEYS:
                    speed_index = min(speed_index + 1, len(SPEEDS) - 1)
                elif event.key in SLOWER_KEYS:
                    speed_index = max(speed_index - 1, 0)
                elif event.key == pygame.K_ESCAPE:
                    race_mode = False
                    racers = None

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos

                if race_button.collidepoint(mouse_x, mouse_y):
                    if race_mode:
                        race_mode = False
                        racers = None
                    elif race_allowed:
                        # Race on the map as it is now. Editing only happens in normal mode.
                        race_mode = True
                        racers = race.make_racers(g, grid_area)
                elif race_mode:
                    # In race mode the map can't be edited; only Run does anything.
                    if run_button.collidepoint(mouse_x, mouse_y):
                        for racer in racers:
                            racer.start(g, start, end)
                elif wall_button.collidepoint(mouse_x, mouse_y):
                    mode = "wall"
                elif mud_button.collidepoint(mouse_x, mouse_y):
                    mode = "mud"
                elif clear_button.collidepoint(mouse_x, mouse_y) or next_map_button.collidepoint(mouse_x, mouse_y):
                    # Clear reloads the current map; Next map moves on to the next one.
                    if next_map_button.collidepoint(mouse_x, mouse_y):
                        map_index = (map_index + 1) % len(map_paths)
                    g, scenarios, map_name = load_map(map_paths[map_index], grid_width, grid_height)
                    layout = renderer.GridLayout(g, grid_area)
                    background = renderer.build_background(g, layout)
                    start, end = default_markers(g)
                    current_scenario = None
                    race_allowed = race.map_fits(g, grid_area)
                    search_generator = None
                    current_path = None
                    overlay = renderer.new_overlay(layout)
                    drawn_visited = set()
                    current_label = None
                    last_results = {}
                elif scenario_button.collidepoint(mouse_x, mouse_y) and scenarios:
                    # Use an official start/goal pair from the map's .scen file.
                    current_scenario = random.choice(scenarios)
                    start = current_scenario.start
                    end = current_scenario.goal
                    search_generator = None
                    current_path = None
                    overlay = renderer.new_overlay(layout)
                    drawn_visited = set()
                    current_label = None
                    last_results = {}
                elif run_button.collidepoint(mouse_x, mouse_y):
                    current_label = run_label(selected_algo, movement)
                    animated_algo = make_algorithm(selected_algo, movement)
                    search_generator = animated_algo.search(start, end, g)
                    current_path = None
                    overlay = renderer.new_overlay(layout)
                    drawn_visited = set()
                elif algo_button.collidepoint(mouse_x, mouse_y):
                    current_index = algo_list.index(selected_algo)
                    next_index = (current_index + 1) % len(algo_list)
                    selected_algo = algo_list[next_index]
                elif movement_button.collidepoint(mouse_x, mouse_y):
                    # Locked while JPS is selected, since JPS is always 8-directional.
                    if ALGORITHMS[selected_algo] is not JPS:
                        if movement == 4:
                            movement = 8
                        else:
                            movement = 4
                elif is_on_marker(layout, start, event.pos):
                    dragging = "start"
                elif is_on_marker(layout, end, event.pos):
                    dragging = "end"
                elif layout.cell_at(mouse_x, mouse_y) is not None:
                    painting = True

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                painting = False
                dragging = None

            # Painting and dragging both act on the cell under the mouse. The click that
            # starts painting also paints the cell it landed on.
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION) and (painting or dragging):
                cell = layout.cell_at(event.pos[0], event.pos[1])
                changed = False

                if cell is not None and dragging is not None:
                    # Markers can't go onto a wall or onto each other.
                    if not g.is_wall(cell[0], cell[1]) and cell != start and cell != end:
                        if dragging == "start":
                            start = cell
                        else:
                            end = cell
                        changed = True

                elif cell is not None and painting:
                    if mode == "wall" and cell != start and cell != end:
                        g.set_cost(cell[0], cell[1], np.inf)
                        changed = True
                    elif mode == "mud":
                        g.set_cost(cell[0], cell[1], MUD_COST)
                        changed = True
                    if changed:
                        renderer.draw_background_cell(background, g, layout, cell[0], cell[1])

                if changed:
                    # The old search and results no longer match the map, so clear them.
                    search_generator = None
                    current_path = None
                    current_label = None
                    last_results = {}
                    current_scenario = None
                    if drawn_visited:
                        overlay = renderer.new_overlay(layout)
                        drawn_visited = set()

        # Advance the search by several steps per frame, then draw only the new cells.
        latest_visited = None
        finished = False
        if race_mode:
            # Every racer takes the same number of steps, so the race is fair in steps.
            race.advance_all(racers, SPEEDS[speed_index])
        elif search_generator is not None:
            for step in range(SPEEDS[speed_index]):
                # step_search also times the step, so drawing between steps isn't counted.
                result = step_search(animated_algo, search_generator)
                if result is None:
                    finished = True
                    break
                latest_visited, maybe_path = result
                if maybe_path is not None:
                    current_path = maybe_path
                    finished = True
                    break
        if finished:
            search_generator = None
            last_results[current_label] = dict(animated_algo.stats)
        if latest_visited is not None:
            new_cells = latest_visited - drawn_visited
            renderer.draw_visited_cells(overlay, layout, new_cells)
            drawn_visited.update(new_cells)

        screen.fill(renderer.BACKGROUND)
        if race_mode:
            race.draw_race(screen, small_font, racers, start, end)
        else:
            renderer.draw_grid_layers(screen, layout, background, overlay)
            if current_path:
                renderer.draw_path(screen, layout, current_path)
            renderer.draw_marker(screen, layout, start, renderer.START)
            renderer.draw_marker(screen, layout, end, renderer.END)

        # Editing buttons are shown locked in race mode.
        renderer.draw_button(screen, font, run_button, "Run")
        renderer.draw_button(screen, font, clear_button, "Clear", locked=race_mode)
        renderer.draw_button(screen, font, algo_button, selected_algo, locked=race_mode)
        renderer.draw_button(screen, font, mud_button, "Mud Edit", locked=race_mode)
        renderer.draw_button(screen, font, wall_button, "Wall Edit", locked=race_mode)
        if ALGORITHMS[selected_algo] is JPS:
            renderer.draw_button(screen, font, movement_button, "8-dir (JPS)", locked=True)
        else:
            renderer.draw_button(screen, font, movement_button, f"{movement}-dir", locked=race_mode)

        renderer.draw_button(screen, font, next_map_button, "Next map", locked=race_mode)
        if scenarios and not race_mode:
            renderer.draw_button(screen, font, scenario_button, "Random scenario")

        map_text = f"Map: {map_name} ({g.width}x{g.height})"
        renderer.draw_text(screen, small_font, map_text, (panel_x, 110))
        if current_scenario is not None:
            scenario_text = (f"Bucket {current_scenario.bucket}, "
                             f"official optimal {current_scenario.optimal_length:.4f}")
            renderer.draw_text(screen, small_font, scenario_text, (panel_x, 132), renderer.NOTE_TEXT)
        elif not race_allowed:
            renderer.draw_text(screen, small_font, "Too large for race view", (panel_x, 132), renderer.TEXT_LOCKED)

        if race_mode:
            renderer.draw_button(screen, font, race_button, "Back")
            race.draw_race_summary(screen, font, small_font, panel_x, 165, racers)
        else:
            renderer.draw_button(screen, font, race_button, "Race", locked=not race_allowed)
            searching = search_generator is not None
            if current_label is None:
                renderer.draw_current_stats(screen, font, small_font, panel_x, 165, None, None, False)
            else:
                renderer.draw_current_stats(screen, font, small_font, panel_x, 165, current_label,
                                            animated_algo.stats, searching)
            renderer.draw_results_table(screen, font, small_font, panel_x, 405, last_results)

        renderer.draw_legend(screen, small_font, 20, status_top + 8)
        speed_text = f"Speed: {SPEEDS[speed_index]} steps/frame (keys 1-5, +/-)"
        renderer.draw_text(screen, small_font, speed_text, (20, status_top + 34))
        if ALGORITHMS[selected_algo] is JPS and not race_mode:
            renderer.draw_text(screen, small_font, "Assumes uniform cost: mud is treated as floor",
                               (440, status_top + 34), renderer.NOTE_TEXT)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    # Optional grid size: python game_window.py 200 200
    if len(sys.argv) == 3:
        main(int(sys.argv[1]), int(sys.argv[2]))
    else:
        main()
