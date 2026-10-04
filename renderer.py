"""Drawing code for the visualiser. No game logic lives here.

The grid is drawn in three layers:
1. background: floor, walls, mud and grid lines. Built once, and only changed when a cell
   is painted, so a big grid isn't redrawn cell by cell every frame.
2. overlay: visited cells. Cells are added as the search reaches them, never redrawn.
3. path and start/end markers: drawn straight onto the screen every frame, on top.
"""
import pygame

FLOOR = (211, 211, 211)
WALL = (0, 0, 0)
MUD = (139, 69, 19)
VISITED = (100, 180, 255)
PATH = (255, 200, 0)
START = (0, 170, 0)
END = (210, 0, 0)
GRID_LINE = (100, 100, 100)
MARKER_OUTLINE = (20, 20, 20)

BACKGROUND = (30, 30, 30)
BUTTON = (80, 80, 80)
BUTTON_LOCKED = (50, 50, 50)
TEXT = (255, 255, 255)
TEXT_LOCKED = (160, 160, 160)
NOTE_TEXT = (255, 210, 120)

# Below this cell size, grid lines would cover most of each cell, so we skip them.
MIN_CELL_SIZE_FOR_LINES = 6


def compute_cell_size(grid, area_width, area_height):
    # The largest whole-pixel square cell that lets the whole grid fit in the area.
    return max(1, min(area_width // grid.width, area_height // grid.height))


class GridLayout:
    # Where a grid is drawn on screen: its cell size and top-left corner.

    # Each grid panel gets its own layout, so several panels could sit side by side.


    def __init__(self, grid, area_rect):
        self.cell_size = compute_cell_size(grid, area_rect.width, area_rect.height)
        self.width_px = self.cell_size * grid.width
        self.height_px = self.cell_size * grid.height
        self.rows = grid.height
        self.cols = grid.width
        # Centre the grid inside its area.
        self.left = area_rect.x + (area_rect.width - self.width_px) // 2
        self.top = area_rect.y + (area_rect.height - self.height_px) // 2

    def local_rect(self, row, col):
        # Cell position on the grid-sized background/overlay surfaces.
        return pygame.Rect(col * self.cell_size, row * self.cell_size, self.cell_size, self.cell_size)

    def screen_rect(self, row, col):
        # Cell position on the screen.
        return self.local_rect(row, col).move(self.left, self.top)

    def cell_centre(self, row, col):
        return self.screen_rect(row, col).center

    def cell_at(self, x, y):
        # Screen pixel -> (row, col), or None if the pixel is outside the grid.
        col = (x - self.left) // self.cell_size
        row = (y - self.top) // self.cell_size
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return (row, col)
        return None

    def marker_radius(self):
        # Markers are at least 5px so they stay visible (and draggable) on big maps.
        return max(self.cell_size // 2, 5)


def cell_colour(grid, row, col):
    if grid.is_wall(row, col):
        return WALL
    if grid.get_cost(row, col) > 1:
        return MUD
    return FLOOR


def draw_background_cell(background, grid, layout, row, col):
    # Redraw one cell of the background, e.g. after the user paints it.
    rect = layout.local_rect(row, col)
    pygame.draw.rect(background, cell_colour(grid, row, col), rect)
    if layout.cell_size >= MIN_CELL_SIZE_FOR_LINES:
        pygame.draw.rect(background, GRID_LINE, rect, 1)


def build_background(grid, layout):
    # Draw every cell once. Only needed at start-up or when the whole grid is replaced.
    background = pygame.Surface((layout.width_px, layout.height_px))
    background.fill(FLOOR)
    for row in range(grid.height):
        for col in range(grid.width):
            draw_background_cell(background, grid, layout, row, col)
    return background


def new_overlay(layout):
    # A transparent surface the same size as the grid, for visited cells.
    overlay = pygame.Surface((layout.width_px, layout.height_px), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))
    return overlay


def draw_visited_cells(overlay, layout, cells):
    for row, col in cells:
        pygame.draw.rect(overlay, VISITED, layout.local_rect(row, col))


def draw_grid_layers(screen, layout, background, overlay):
    screen.blit(background, (layout.left, layout.top))
    screen.blit(overlay, (layout.left, layout.top))


def draw_path(screen, layout, path):
    for row, col in path:
        pygame.draw.rect(screen, PATH, layout.screen_rect(row, col))


def draw_marker(screen, layout, cell, colour):
    centre = layout.cell_centre(cell[0], cell[1])
    radius = layout.marker_radius()
    pygame.draw.circle(screen, colour, centre, radius)
    pygame.draw.circle(screen, MARKER_OUTLINE, centre, radius, 2)


def draw_button(screen, font, rect, label, locked=False):
    if locked:
        pygame.draw.rect(screen, BUTTON_LOCKED, rect)
        text_colour = TEXT_LOCKED
    else:
        pygame.draw.rect(screen, BUTTON, rect)
        text_colour = TEXT
    screen.blit(font.render(label, True, text_colour), (rect.x + 5, rect.y + 10))


def draw_text(screen, font, text, position, colour=TEXT):
    screen.blit(font.render(text, True, colour), position)


def draw_legend(screen, font, x, y):
    items = [
        ("Floor", FLOOR),
        ("Wall", WALL),
        ("Mud", MUD),
        ("Visited", VISITED),
        ("Path", PATH),
        ("Start", START),
        ("End", END),
    ]
    for label, colour in items:
        swatch = pygame.Rect(x, y + 2, 14, 14)
        pygame.draw.rect(screen, colour, swatch)
        pygame.draw.rect(screen, GRID_LINE, swatch, 1)
        label_surface = font.render(label, True, TEXT)
        screen.blit(label_surface, (x + 20, y))
        x += 20 + label_surface.get_width() + 18


def format_cost(cost):
    if cost is None:
        return "No path"
    return f"{cost:.2f}"


def draw_current_stats(screen, font, small_font, x, y, label, live_stats, searching):
    # The run in progress (or just finished). Everything comes from the animated search,
    # so counts tick up live. The time only counts time spent inside the search.
    draw_text(screen, font, "Stats", (x, y))
    y += 30
    if label is None:
        draw_text(screen, small_font, "Press Run to start a search.", (x, y), TEXT_LOCKED)
        return

    if searching:
        cost_text = "searching..."
        length_text = "searching..."
        time_text = "searching..."
    elif live_stats["path_cost"] is None:
        cost_text = "No path"
        length_text = "No path"
        time_text = f"{live_stats['search_time_ms']:.1f} ms"
    else:
        cost_text = format_cost(live_stats["path_cost"])
        length_text = f"{live_stats['path_length_cells']} cells"
        time_text = f"{live_stats['search_time_ms']:.1f} ms"

    lines = [
        f"Algorithm: {label}",
        f"Nodes expanded: {live_stats['nodes_expanded']}",
        f"Cells scanned: {live_stats['cells_scanned']}",
        f"Path cost: {cost_text}",
        f"Path length: {length_text}",
        f"Time: {time_text}",
    ]
    for line in lines:
        draw_text(screen, small_font, line, (x, y))
        y += 22
    draw_text(screen, small_font, "(time = search only, not drawing)", (x, y), TEXT_LOCKED)


def draw_results_table(screen, font, small_font, x, y, last_results):
    # The most recent finished result for each algorithm on the current map.
    draw_text(screen, font, "Last results (this map)", (x, y))
    y += 30
    columns = [("Algorithm", 0), ("Cost", 115), ("Nodes", 185), ("ms", 240)]
    for heading, offset in columns:
        draw_text(screen, small_font, heading, (x + offset, y), TEXT_LOCKED)
    y += 22
    if not last_results:
        draw_text(screen, small_font, "No finished runs yet.", (x, y), TEXT_LOCKED)
        return
    for label, stats in last_results.items():
        cost_text = format_cost(stats["path_cost"])
        if label == "JPS" and stats["path_cost"] is not None:
            # JPS treats mud as floor, so its cost isn't comparable on a map with mud.
            cost_text += "*"
        draw_text(screen, small_font, label, (x, y))
        draw_text(screen, small_font, cost_text, (x + 115, y))
        draw_text(screen, small_font, str(stats["nodes_expanded"]), (x + 185, y))
        draw_text(screen, small_font, f"{stats['search_time_ms']:.1f}", (x + 240, y))
        y += 22
    if "JPS" in last_results:
        draw_text(screen, small_font, "* JPS cost treats mud as floor", (x, y + 6), NOTE_TEXT)
