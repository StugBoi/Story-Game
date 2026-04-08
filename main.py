import pygame
import json
import sys
import os
import psycopg
from datetime import datetime

# --- Config ---
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
IMAGES_DIR = "scenes"
STORY_FILE = "story.json"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "novel",
    "user": "postgres",
    "password": "712Samsung",
}


# Colors
COLOR_BOX_BG      = (10, 8, 20, 210)
COLOR_BOX_BORDER  = (80, 180, 120, 180)
COLOR_TEXT        = (220, 230, 215)
COLOR_TEXT_DIM    = (130, 150, 130)
COLOR_CHOICE_BG   = (20, 40, 30, 180)
COLOR_CHOICE_HV   = (30, 100, 60, 220)
COLOR_CHOICE_BD   = (60, 160, 90, 160)
COLOR_STAT_BG     = (10, 8, 20, 160)
COLOR_LOCKED      = (80, 80, 80, 160)
COLOR_LOCKED_TEXT = (100, 100, 100)
COLOR_INPUT_BG    = (15, 25, 18, 240)
COLOR_INPUT_BD    = (80, 180, 120, 220)
COLOR_INPUT_ACTV  = (40, 160, 80, 255)
COLOR_BTN_BG      = (20, 60, 35, 220)
COLOR_BTN_HV      = (30, 110, 55, 255)
COLOR_BTN_RED     = (60, 20, 20, 220)
COLOR_BTN_RED_HV  = (110, 30, 30, 255)
COLOR_NOTIFY_BG   = (10, 40, 20, 230)
COLOR_NOTIFY_BD   = (60, 200, 100, 180)

FONT_MAIN  = None
FONT_SMALL = None
FONT_TITLE = None

TEXT_BOX_H  = 220
CHOICE_H    = 46
CHOICE_PAD  = 10
BOX_MARGIN  = 40
BOX_PADDING = 28
CORNER_R    = 14

def db_connect():
    return  psycopg.connect(**DB_CONFIG)

def db_init():
    """Create table if it doesn't exist."""
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saves (
                id          SERIAL PRIMARY KEY,
                session_name TEXT NOT NULL UNIQUE,
                scene       TEXT NOT NULL,
                state       JSONB NOT NULL,
                saved_at    TIMESTAMP    DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] init error: {e}")
        return False

# db save

#db load list

#db load(session name)


def load_fonts():
    global FONT_MAIN, FONT_SMALL, FONT_TITLE
    for name in ["Georgia", "Palatino Linotype", "serif", None]:
        try:
            FONT_MAIN  = pygame.font.SysFont(name, 22) if name else pygame.font.Font(None, 24)
            FONT_SMALL = pygame.font.SysFont(name, 17) if name else pygame.font.Font(None, 19)
            FONT_TITLE = pygame.font.SysFont(name, 28) if name else pygame.font.Font(None, 30)
            break
        except Exception:
            continue


def load_story(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_image(image_id):
    """Load image by id (e.g. '1' -> scenes/1.jpg)"""
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = os.path.join(IMAGES_DIR, image_id + ext)
        if os.path.exists(path):
            img = pygame.image.load(path).convert()
            return pygame.transform.scale(img, (SCREEN_W, SCREEN_H))
    return None


def draw_rounded_rect(surface, rect, color, radius=CORNER_R):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
    surface.blit(s, rect.topleft)


def draw_rounded_border(surface, rect, color, width=2, radius=CORNER_R):
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)


def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def check_condition(choice, state):
    for stat, required in choice.get("condition", {}).items():
        if state.get(stat, 0) < required:
            return False
    return True


def draw_stats(surface, state):
    if not state:
        return
    x = SCREEN_W - BOX_MARGIN
    y = BOX_MARGIN
    for key, val in state.items():
        label = f"{key}: {val}"
        surf = FONT_SMALL.render(label, True, COLOR_TEXT_DIM)
        w = surf.get_width() + 16
        bg_rect = pygame.Rect(x - w, y, w, 26)
        draw_rounded_rect(surface, bg_rect, COLOR_STAT_BG, radius=6)
        surface.blit(surf, (x - w + 8, y + 4))
        y += 32


def draw_scene(surface, bg, scene, available, locked, state, hover_idx):
    if bg:
        surface.blit(bg, (0, 0))
    else:
        surface.fill((10, 10, 18))

    # Vignette
    vignette = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for i in range(80):
        alpha = int(i * 2.2)
        pygame.draw.rect(vignette, (0, 0, 0, alpha),
                         (i, i, SCREEN_W - i*2, SCREEN_H - i*2), width=1)
    surface.blit(vignette, (0, 0))

    draw_stats(surface, state)

    # Text box size
    box_x = BOX_MARGIN
    box_w = SCREEN_W - BOX_MARGIN * 2
    total_choices = len(available) + len(locked)
    choices_h = total_choices * (CHOICE_H + CHOICE_PAD) + CHOICE_PAD
    box_h = TEXT_BOX_H + choices_h
    box_y = SCREEN_H - box_h - BOX_MARGIN

    text_rect = pygame.Rect(box_x, box_y, box_w, box_h)
    draw_rounded_rect(surface, text_rect, COLOR_BOX_BG)
    draw_rounded_border(surface, text_rect, COLOR_BOX_BORDER, width=1)

    # Scene text
    text_area_w = box_w - BOX_PADDING * 2
    lines = wrap_text(scene["text"], FONT_MAIN, text_area_w)
    ty = box_y + BOX_PADDING
    for line in lines[:6]:
        surf = FONT_MAIN.render(line, True, COLOR_TEXT)
        surface.blit(surf, (box_x + BOX_PADDING, ty))
        ty += FONT_MAIN.get_linesize() + 2

    # Divider
    div_y = box_y + TEXT_BOX_H - 12
    pygame.draw.line(surface,
                     (*COLOR_BOX_BORDER[:3], 80),
                     (box_x + BOX_PADDING, div_y),
                     (box_x + box_w - BOX_PADDING, div_y), 1)

    # Choices
    choice_rects = []
    cy = box_y + TEXT_BOX_H + CHOICE_PAD
    choice_w = box_w - BOX_PADDING * 2

    for i, choice in enumerate(available):
        crect = pygame.Rect(box_x + BOX_PADDING, cy, choice_w, CHOICE_H)
        color = COLOR_CHOICE_HV if i == hover_idx else COLOR_CHOICE_BG
        draw_rounded_rect(surface, crect, color, radius=8)
        draw_rounded_border(surface, crect, COLOR_CHOICE_BD, width=1, radius=8)

        badge = FONT_SMALL.render(str(i + 1), True, COLOR_BOX_BORDER[:3])
        surface.blit(badge, (crect.x + 14, crect.y + CHOICE_H//2 - badge.get_height()//2))

        label = FONT_MAIN.render(choice["text"], True, COLOR_TEXT)
        surface.blit(label, (crect.x + 40, crect.y + CHOICE_H//2 - label.get_height()//2))

        choice_rects.append(crect)
        cy += CHOICE_H + CHOICE_PAD

    for choice in locked:
        crect = pygame.Rect(box_x + BOX_PADDING, cy, choice_w, CHOICE_H)
        draw_rounded_rect(surface, crect, COLOR_LOCKED, radius=8)
        req_str = ", ".join(f"{k}>={v}" for k, v in choice["condition"].items())
        label = FONT_SMALL.render(f"[locked: {req_str}]  {choice['text']}", True, COLOR_LOCKED_TEXT)
        surface.blit(label, (crect.x + 14, crect.y + CHOICE_H//2 - label.get_height()//2))
        cy += CHOICE_H + CHOICE_PAD

    return choice_rects


def ending_screen(surface, scene, bg):
    if bg:
        surface.blit(bg, (0, 0))
    else:
        surface.fill((5, 5, 12))

    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surface.blit(overlay, (0, 0))

    box_w = SCREEN_W - 200
    box_x = 100
    lines = wrap_text(scene["text"], FONT_MAIN, box_w - 60)
    total_h = len(lines) * (FONT_MAIN.get_linesize() + 4) + 100
    box_y = SCREEN_H // 2 - total_h // 2

    box_rect = pygame.Rect(box_x, box_y - 20, box_w, total_h + 20)
    draw_rounded_rect(surface, box_rect, COLOR_BOX_BG)
    draw_rounded_border(surface, box_rect, COLOR_BOX_BORDER, width=1)

    end_label = FONT_TITLE.render("-- THE END --", True, COLOR_BOX_BORDER[:3])
    surface.blit(end_label, (SCREEN_W // 2 - end_label.get_width() // 2, box_y))

    ty = box_y + 50
    for line in lines:
        surf = FONT_MAIN.render(line, True, COLOR_TEXT)
        surface.blit(surf, (box_x + 30, ty))
        ty += FONT_MAIN.get_linesize() + 4

    hint = FONT_SMALL.render("Press any key to quit", True, COLOR_TEXT_DIM)
    surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, box_y + total_h - 10))


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Dark Forest")
    clock = pygame.time.Clock()

    load_fonts()

    story = load_story(STORY_FILE)
    state = {}
    current_scene = "start"
    image_cache = {}

    def get_bg(scene):
        image_id = scene.get("image")
        if not image_id:
            return None
        if image_id not in image_cache:
            image_cache[image_id] = load_image(image_id)
        return image_cache[image_id]

    hover_idx = -1

    while True:
        scene = story[current_scene]
        bg = get_bg(scene)
        choices = scene["choices"]

        available = [c for c in choices if check_condition(c, state)]
        locked    = [c for c in choices if not check_condition(c, state)]

        # Ending screen
        if not choices:
            ending_screen(screen, scene, bg)
            pygame.display.flip()
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                    if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                        pygame.quit(); sys.exit()

        mx, my = pygame.mouse.get_pos()

        # Hover detection
        hover_idx = -1
        choice_rects = draw_scene(screen, bg, scene, available, locked, state, hover_idx)
        for i, rect in enumerate(choice_rects):
            if rect.collidepoint(mx, my):
                hover_idx = i
                break

        choice_rects = draw_scene(screen, bg, scene, available, locked, state, hover_idx)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(available):
                        choice = available[idx]
                        for k, v in choice.get("effects", {}).items():
                            state[k] = state.get(k, 0) + v
                        current_scene = choice["next"]
                        hover_idx = -1

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(choice_rects):
                    if rect.collidepoint(event.pos):
                        choice = available[i]
                        for k, v in choice.get("effects", {}).items():
                            state[k] = state.get(k, 0) + v
                        current_scene = choice["next"]
                        hover_idx = -1
                        break

        clock.tick(FPS)


if __name__ == "__main__":
    main()