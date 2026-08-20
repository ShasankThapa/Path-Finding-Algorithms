import pygame
from algos.algo_rule import PathAlgo
from algos.Djikstra import Djikstra
from algos.Astar import Astar
from algos.Bidirect import Bidirect
from algos.JPS import JPS
from grid import Grid, get_prox, in_bounds
import numpy as np
import heapq as hq
import time

pygame.init()
search_generator = None
visited_so_far = set()
frame_counter = 0
font = pygame.font.Font(None, 24)

BUTTON_BAR_HEIGHT = 60
BUTTON_WIDTH = 120
BUTTON_HEIGHT = 40
ANIMATION_SPEED = 1

selected_algo = "Djikstra"
algo_list = ["Djikstra", "Astar", "JPS", "Bidirectional"]

screen = pygame.display.set_mode((850, 850 + BUTTON_BAR_HEIGHT))
pygame.display.set_caption("Pathfinding Visualizer")

g = Grid(50, 50, 1)
start = (0, 0)
end = (g.height - 1, g.width - 1)
current_path = None
cell_size = max(1, 850 // g.width)

run_button = pygame.Rect(20, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
clear_button = pygame.Rect(160, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
algo_button = pygame.Rect(300, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
mud_button = pygame.Rect(440, 10, BUTTON_WIDTH, BUTTON_HEIGHT)
wall_button = pygame.Rect(580, 10, BUTTON_WIDTH, BUTTON_HEIGHT)

mode = "wall"
mouse_held = False

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_held = True
            mouse_x, mouse_y = pygame.mouse.get_pos()

            if wall_button.collidepoint(mouse_x, mouse_y):
                mode = "wall"
            elif mud_button.collidepoint(mouse_x, mouse_y):
                mode = "mud"
            elif clear_button.collidepoint(mouse_x, mouse_y):
                g = Grid(50, 50, 1)
                current_path = None
                visited_so_far = set()
                search_generator = None
            elif run_button.collidepoint(mouse_x, mouse_y):
                current_path = None
                visited_so_far = set()
                if selected_algo == "Djikstra":
                    search_generator = Djikstra().search(start, end, g)
                elif selected_algo == "Astar":
                    search_generator = Astar().search(start, end, g)
                elif selected_algo == "JPS":
                    search_generator = JPS().search(start, end, g)
                elif selected_algo == "Bidirectional":
                    search_generator = Bidirect().search(start, end, g)
            elif algo_button.collidepoint(mouse_x, mouse_y):
                current_index = algo_list.index(selected_algo)
                next_index = (current_index + 1) % len(algo_list)
                selected_algo = algo_list[next_index]
            else:
                if mouse_y > BUTTON_BAR_HEIGHT:
                    col = mouse_x // cell_size
                    row = (mouse_y - BUTTON_BAR_HEIGHT) // cell_size
                    if 0 <= row < g.height and 0 <= col < g.width:
                        if mode == "wall":
                            g.set_cost(row, col, np.inf)
                        elif mode == "mud":
                            g.set_cost(row, col, 3.0)

        if event.type == pygame.MOUSEBUTTONUP:
            mouse_held = False

        if event.type == pygame.MOUSEMOTION and mouse_held:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            if mouse_y > BUTTON_BAR_HEIGHT:
                col = mouse_x // cell_size
                row = (mouse_y - BUTTON_BAR_HEIGHT) // cell_size
                if 0 <= row < g.height and 0 <= col < g.width:
                    if mode == "wall":
                        g.set_cost(row, col, np.inf)
                    elif mode == "mud":
                        g.set_cost(row, col, 3.0)

    frame_counter += 1
    if search_generator is not None and frame_counter % ANIMATION_SPEED == 0:
        try:
            visited_so_far, maybe_path = next(search_generator)
            if maybe_path is not None:
                current_path = maybe_path
                search_generator = None
        except StopIteration:
            search_generator = None

    screen.fill((30, 30, 30))

    for row in range(g.height):
        for col in range(g.width):
            x = col * cell_size
            y = row * cell_size + BUTTON_BAR_HEIGHT

            if g.get_cost(row, col) == float("inf"):
                color = (0, 0, 0)
            elif g.get_cost(row, col) > 1:
                color = (139, 69, 19)
            else:
                color = (211, 211, 211)

            pygame.draw.rect(screen, color, (x, y, cell_size, cell_size))
            pygame.draw.rect(screen, (100, 100, 100), (x, y, cell_size, cell_size), 1)

    for (row, col) in visited_so_far:
        x = col * cell_size
        y = row * cell_size + BUTTON_BAR_HEIGHT
        pygame.draw.rect(screen, (100, 180, 255), (x, y, cell_size, cell_size))

    if current_path:
        for (row, col) in current_path:
            x = col * cell_size
            y = row * cell_size + BUTTON_BAR_HEIGHT
            pygame.draw.rect(screen, (0, 200, 0), (x, y, cell_size, cell_size))

    pygame.draw.rect(screen, (80, 80, 80), run_button)
    screen.blit(font.render("Run", True, (255, 255, 255)), (25, 20))

    pygame.draw.rect(screen, (80, 80, 80), clear_button)
    screen.blit(font.render("Clear", True, (255, 255, 255)), (165, 20))

    pygame.draw.rect(screen, (80, 80, 80), algo_button)
    screen.blit(font.render(selected_algo, True, (255, 255, 255)), (305, 20))

    pygame.draw.rect(screen, (80, 80, 80), mud_button)
    screen.blit(font.render("Mud Edit", True, (255, 255, 255)), (445, 20))

    pygame.draw.rect(screen, (80, 80, 80), wall_button)
    screen.blit(font.render("Wall Edit", True, (255, 255, 255)), (585, 20))

    pygame.display.flip()

pygame.quit()
