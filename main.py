import pygame
import json
import sys
import os

from pygame import surface

SCREEN_W, SCREEN_H = 1280,720
FPS = 60
IMAGES_DIR = "scenes"
STORY_FILE = "story.json"

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

FONT_MAIN  = None
FONT_SMALL = None
FONT_TITLE = None

TEXT_BOX_H    = 220
CHOICE_H      = 46
CHOICE_PAD    = 10
BOX_MARGIN    = 40
BOX_PADDING   = 28
CORNER_R      = 14

def load_images(scene_id):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = os.path.join(IMAGES_DIR, scene_id + ext)
        if os.path.exists(path):
            img = pygame.image.load(path).convert()
            return pygame.transform.scale(img, (SCREEN_W, SCREEN_H))
    return None

def load_fonts():
    global FONT_MAIN, FONT_SMALL , FONT_TITLE
    for name in ["Georgia", "Palatino Linotype", "serif", None]:
        try:
            FONT_MAIN = pygame.font.SysFont(name, 27) if name else pygame.font.SysFont(None, 27)
            FONT_SMALL = pygame.font.SysFont(name, 17) if name else pygame.font.SysFont(None, 17)
            FONT_TITLE = pygame.font.SysFont(name, 28) if name else pygame.font.SysFont(None, 28)
            break
        except Exception:
            continue

def load_story(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def draw_rect(surface, rect, color, radius=CORNER_R):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
    surface.blit(s, rect.topleft)

def draw_border(surface, rect, color, width=2, radius=CORNER_R):
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

def draw_stats(state):
    if not state:
        return
    items = list(state.items())
    x = SCREEN_W - BOX_MARGIN
    y = BOX_MARGIN
    for key, val in items:
        label = f"{key}: {val}"
        surf = FONT_SMALL.render(label, True, COLOR_TEXT_DIM)
        w = surf.get.widt() + 16
        bg_rect = pygame.Rect(x - w, y, w, 26)
        draw_rect(surface, bg_rect, COLOR_STAT_BG, radius=2)
        surface.blit(surf, (x - w + 8, y + 4))
        y +=32


#draw scene
#ending screen

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Dark Forest")
    clock = pygame.time.Clock()

    load_fonts()

    story = load_story(STORY_FILE)
    state = {}
    current_scene = "1"
    image_cache = {}

    def get_bg(scene_id):
        if scene_id not in image_cache:
            image_cache[scene_id] = load_images(scene_id)
        return image_cache[scene_id]

    hover_idx = -1

    #wile true



