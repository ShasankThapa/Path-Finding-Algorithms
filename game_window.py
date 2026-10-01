import math
import sys

import numpy as np
import pygame

import renderer
from algos.dijkstra import Dijkstra
from algos.astar import Astar
from algos.bidirectional import Bidirect
from algos.jps import JPS
from grid import Grid

WINDOW_WIDTH = 850
TOOLBAR_HEIGHT = 60
GRID_AREA_HEIGHT = 800
STATUS_BAR_HEIGHT = 60
WINDOW_HEIGHT = TOOLBAR_HEIGHT + GRID_AREA_HEIGHT + STATUS_BAR_HEIGHT

BUTTON_WIDTH = 120
BUTTON_HEIGHT = 40
FPS = 60
MUD_COST = 3.0

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

    grid_area = pygame.Rect(0, TOOLBAR_HEIGHT, WINDOW_WIDTH, GRID_AREA_HEIGHT)
    status_top = TOOLBAR_HEIGHT + GRID_AREA_HEIGHT

    g = Grid(grid_width, grid_height, 1)
    layout = renderer.GridLayout(g, grid_area)
    background = renderer.build_background(g, layout)
    start = (0, 0)
    end = (g.height - 1, g.width - 1)

    # Search state. drawn_visited remembers which cells are already on the overlay,
    # so each frame only the newly visited cells get drawn.
    search_generator = None
    current_path = None
    overlay = renderer.new_overlay(layout)
    drawn_visited = set()

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

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos

                if wall_button.collidepoint(mouse_x, mouse_y):
                    mode = "wall"
                elif mud_button.collidepoint(mouse_x, mouse_y):
                    mode = "mud"
                elif clear_button.collidepoint(mouse_x, mouse_y):
                    g = Grid(grid_width, grid_height, 1)
                    background = renderer.build_background(g, layout)
                    start = (0, 0)
                    end = (g.height - 1, g.width - 1)
                    search_generator = None
                    current_path = None
                    overlay = renderer.new_overlay(layout)
                    drawn_visited = set()
                elif run_button.collidepoint(mouse_x, mouse_y):
                    search_generator = make_algorithm(selected_algo, movement).search(start, end, g)
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
                    # The old search no longer matches the grid, so clear it.
                    search_generator = None
                    current_path = None
                    if drawn_visited:
                        overlay = renderer.new_overlay(layout)
                        drawn_visited = set()

        # Advance the search by several steps per frame, then draw only the new cells.
        latest_visited = None
        if search_generator is not None:
            for step in range(SPEEDS[speed_index]):
                try:
                    latest_visited, maybe_path = next(search_generator)
                except StopIteration:
                    search_generator = None
                    break
                if maybe_path is not None:
                    current_path = maybe_path
                    search_generator = None
                    break
        if latest_visited is not None:
            new_cells = latest_visited - drawn_visited
            renderer.draw_visited_cells(overlay, layout, new_cells)
            drawn_visited.update(new_cells)

        screen.fill(renderer.BACKGROUND)
        renderer.draw_grid_layers(screen, layout, background, overlay)
        if current_path:
            renderer.draw_path(screen, layout, current_path)
        renderer.draw_marker(screen, layout, start, renderer.START)
        renderer.draw_marker(screen, layout, end, renderer.END)

        renderer.draw_button(screen, font, run_button, "Run")
        renderer.draw_button(screen, font, clear_button, "Clear")
        renderer.draw_button(screen, font, algo_button, selected_algo)
        renderer.draw_button(screen, font, mud_button, "Mud Edit")
        renderer.draw_button(screen, font, wall_button, "Wall Edit")
        if ALGORITHMS[selected_algo] is JPS:
            renderer.draw_button(screen, font, movement_button, "8-dir (JPS)", locked=True)
        else:
            renderer.draw_button(screen, font, movement_button, f"{movement}-dir")

        renderer.draw_legend(screen, small_font, 20, status_top + 8)
        speed_text = f"Speed: {SPEEDS[speed_index]} steps/frame (keys 1-5, +/-)"
        renderer.draw_text(screen, small_font, speed_text, (20, status_top + 34))
        if ALGORITHMS[selected_algo] is JPS:
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
