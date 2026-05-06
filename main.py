import pygame
import json
import sys
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime

SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
IMAGES_DIR = "scenes"
STORY_FILE = "story.json"

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "novel",
    "user":     "postgres",
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
    return psycopg2.connect(**DB_CONFIG)


def db_init():
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saves (
                id          SERIAL PRIMARY KEY,
                session_name TEXT NOT NULL UNIQUE,
                scene       TEXT NOT NULL,
                state       JSONB NOT NULL,
                saved_at    TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] init error: {e}")
        return False


def db_save(session_name, scene, state, inventory):
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO saves (session_name, scene, state, saved_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (session_name)
            DO UPDATE SET scene = EXCLUDED.scene,
                          state = EXCLUDED.state,
                          saved_at = NOW()
        """, (session_name, scene, json.dumps({"state": state, "inventory": list(inventory)})))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] save error: {e}")
        return False


def db_load_list():
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT session_name, scene, saved_at
            FROM saves
            ORDER BY saved_at DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[DB] load list error: {e}")
        return []


def db_load(session_name):
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT scene, state FROM saves WHERE session_name = %s
        """, (session_name,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return row[0], row[1]
        return None
    except Exception as e:
        print(f"[DB] load error: {e}")
        return None

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
    lines, current = [], ""
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

def check_item(choice, inventory):
    required = choice.get("require_item")
    if required and required not in inventory:
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


def draw_inventory(surface, inventory):
    if not inventory:
        return
    x = BOX_MARGIN
    y = BOX_MARGIN + 50
    title = FONT_SMALL.render("ITEMS:", True, COLOR_TEXT_DIM)
    surface.blit(title, (x, y))
    y += 22
    for item in inventory:
        surf = FONT_SMALL.render(f"+ {item}", True, (120,200,140))
        w = surf.get_width() + 16
        bg_rect = pygame.Rect(x, y, w, 24)
        draw_rounded_rect(surface, bg_rect, COLOR_STAT_BG, radius=6)
        surface.blit(surf, (x + 8, y + 4))
        y += 28


def apply_load(result):
    if result is None:
        return None, None, None
    scene, data = result
    if isinstance(data, dict) and "state" in data:
        state     = data.get("state", {})
        inventory = set(data.get("inventory", []))
    else:
        state     = data if isinstance(data, dict) else {}
        inventory = set()
    return scene, state, inventory

def draw_save_button(surface, hover=False):
    color = COLOR_BTN_HV if hover else COLOR_BTN_BG
    rect = pygame.Rect(BOX_MARGIN, BOX_MARGIN, 110, 34)
    draw_rounded_rect(surface, rect, color, radius=8)
    draw_rounded_border(surface, rect, COLOR_INPUT_BD, width=1, radius=8)
    label = FONT_SMALL.render("[S]  Save", True, COLOR_TEXT)
    surface.blit(label, (rect.x + 12, rect.y + 8))
    return rect


def draw_load_button(surface, hover=False):
    color = COLOR_BTN_HV if hover else COLOR_BTN_BG
    rect = pygame.Rect(BOX_MARGIN + 120, BOX_MARGIN, 110, 34)
    draw_rounded_rect(surface, rect, color, radius=8)
    draw_rounded_border(surface, rect, COLOR_INPUT_BD, width=1, radius=8)
    label = FONT_SMALL.render("[L]  Load", True, COLOR_TEXT)
    surface.blit(label, (rect.x + 12, rect.y + 8))
    return rect


class Notification:
    def __init__(self, text, duration=2500):
        self.text = text
        self.duration = duration
        self.timer = 0
        self.active = True

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.duration:
            self.active = False

    def draw(self, surface):
        alpha = 255
        if self.timer > self.duration - 400:
            alpha = int(255 * (self.duration - self.timer) / 400)
        w = FONT_MAIN.size(self.text)[0] + 40
        rect = pygame.Rect(SCREEN_W // 2 - w // 2, 20, w, 44)
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg = (*COLOR_NOTIFY_BG[:3], min(COLOR_NOTIFY_BG[3], alpha))
        pygame.draw.rect(s, bg, s.get_rect(), border_radius=10)
        surface.blit(s, rect.topleft)
        bd = (*COLOR_NOTIFY_BD[:3], min(COLOR_NOTIFY_BD[3], alpha))
        pygame.draw.rect(surface, bd, rect, width=1, border_radius=10)
        txt = FONT_MAIN.render(self.text, True, (*COLOR_TEXT[:3], alpha))
        surface.blit(txt, (rect.x + 20, rect.y + 11))



def run_save_dialog(surface, screen, clock, bg):
    input_text = ""
    active = True
    result_msg = None

    dialog_w, dialog_h = 520, 200
    dialog_x = SCREEN_W // 2 - dialog_w // 2
    dialog_y = SCREEN_H // 2 - dialog_h // 2

    input_rect  = pygame.Rect(dialog_x + 30, dialog_y + 90, dialog_w - 60, 44)
    btn_save    = pygame.Rect(dialog_x + 30, dialog_y + 148, 200, 36)
    btn_cancel  = pygame.Rect(dialog_x + dialog_w - 230, dialog_y + 148, 200, 36)

    while active:
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill((10, 10, 18))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # Dialog box
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        draw_rounded_rect(screen, dialog_rect, COLOR_INPUT_BG, radius=14)
        draw_rounded_border(screen, dialog_rect, COLOR_INPUT_BD, width=1, radius=14)

        # Title
        title = FONT_TITLE.render("Save session", True, COLOR_TEXT)
        screen.blit(title, (dialog_x + 30, dialog_y + 22))

        hint = FONT_SMALL.render("Enter session name:", True, COLOR_TEXT_DIM)
        screen.blit(hint, (dialog_x + 30, dialog_y + 66))

        # Input field
        draw_rounded_rect(screen, input_rect, (20, 35, 25, 240), radius=8)
        draw_rounded_border(screen, input_rect, COLOR_INPUT_ACTV, width=1, radius=8)
        txt_surf = FONT_MAIN.render(input_text + "|", True, COLOR_TEXT)
        screen.blit(txt_surf, (input_rect.x + 12, input_rect.y + 11))

        # Buttons
        mx, my = pygame.mouse.get_pos()
        sv_color = COLOR_BTN_HV if btn_save.collidepoint(mx, my) else COLOR_BTN_BG
        cn_color = COLOR_BTN_RED_HV if btn_cancel.collidepoint(mx, my) else COLOR_BTN_RED

        draw_rounded_rect(screen, btn_save,   sv_color, radius=8)
        draw_rounded_rect(screen, btn_cancel, cn_color, radius=8)
        draw_rounded_border(screen, btn_save,   COLOR_INPUT_BD, width=1, radius=8)
        draw_rounded_border(screen, btn_cancel, (150, 60, 60, 180), width=1, radius=8)

        sv_lbl = FONT_MAIN.render("Save", True, COLOR_TEXT)
        cn_lbl = FONT_MAIN.render("Cancel", True, COLOR_TEXT)
        screen.blit(sv_lbl, (btn_save.x   + btn_save.w   // 2 - sv_lbl.get_width() // 2, btn_save.y   + 8))
        screen.blit(cn_lbl, (btn_cancel.x + btn_cancel.w // 2 - cn_lbl.get_width() // 2, btn_cancel.y + 8))

        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    active = False
                elif event.key == pygame.K_RETURN:
                    result_msg = input_text
                    active = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if len(input_text) < 40:
                        input_text += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_save.collidepoint(event.pos):
                    result_msg = input_text
                    active = False
                if btn_cancel.collidepoint(event.pos):
                    active = False

    return result_msg  # None = cancelled, str = session name

def run_load_dialog(surface, screen, clock, bg):
    saves = db_load_list()
    active = True

    dialog_w = 600
    row_h = 52
    dialog_h = min(60 + len(saves) * row_h + 60, 520)
    dialog_x = SCREEN_W // 2 - dialog_w // 2
    dialog_y = SCREEN_H // 2 - dialog_h // 2

    while active:
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill((10, 10, 18))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        draw_rounded_rect(screen, dialog_rect, COLOR_INPUT_BG, radius=14)
        draw_rounded_border(screen, dialog_rect, COLOR_INPUT_BD, width=1, radius=14)

        title = FONT_TITLE.render("Load session", True, COLOR_TEXT)
        screen.blit(title, (dialog_x + 30, dialog_y + 18))

        mx, my = pygame.mouse.get_pos()
        row_rects = []

        if not saves:
            msg = FONT_MAIN.render("No saves found.", True, COLOR_TEXT_DIM)
            screen.blit(msg, (dialog_x + 30, dialog_y + 70))
        else:
            for i, (name, scene, saved_at) in enumerate(saves):
                ry = dialog_y + 58 + i * row_h
                rrect = pygame.Rect(dialog_x + 20, ry, dialog_w - 40, row_h - 6)
                color = COLOR_CHOICE_HV if rrect.collidepoint(mx, my) else COLOR_CHOICE_BG
                draw_rounded_rect(screen, rrect, color, radius=8)
                draw_rounded_border(screen, rrect, COLOR_CHOICE_BD, width=1, radius=8)

                name_surf  = FONT_MAIN.render(name, True, COLOR_TEXT)
                scene_surf = FONT_SMALL.render(f"scene: {scene}", True, COLOR_TEXT_DIM)
                date_str   = saved_at.strftime("%d.%m.%Y %H:%M") if hasattr(saved_at, 'strftime') else str(saved_at)
                date_surf  = FONT_SMALL.render(date_str, True, COLOR_TEXT_DIM)

                screen.blit(name_surf,  (rrect.x + 14, rrect.y + 6))
                screen.blit(scene_surf, (rrect.x + 14, rrect.y + 28))
                screen.blit(date_surf,  (rrect.x + dialog_w - 180, rrect.y + 17))
                row_rects.append((rrect, name))

        # Cancel button
        btn_cancel = pygame.Rect(dialog_x + dialog_w - 150, dialog_y + dialog_h - 50, 130, 34)
        cn_color = COLOR_BTN_RED_HV if btn_cancel.collidepoint(mx, my) else COLOR_BTN_RED
        draw_rounded_rect(screen, btn_cancel, cn_color, radius=8)
        draw_rounded_border(screen, btn_cancel, (150, 60, 60, 180), width=1, radius=8)
        cn_lbl = FONT_MAIN.render("Cancel", True, COLOR_TEXT)
        screen.blit(cn_lbl, (btn_cancel.x + btn_cancel.w // 2 - cn_lbl.get_width() // 2, btn_cancel.y + 7))

        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    active = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_cancel.collidepoint(event.pos):
                    active = False
                for rrect, name in row_rects:
                    if rrect.collidepoint(event.pos):
                        result = db_load(name)
                        return result  # (scene, state) or None

    return None

def draw_scene(surface, bg, scene, available, locked, state, inventory, hover_idx,
               save_hover=False, load_hover=False):
    if bg:
        surface.blit(bg, (0, 0))
    else:
        surface.fill((10, 10, 18))

    vignette = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for i in range(80):
        alpha = int(i * 2.2)
        pygame.draw.rect(vignette, (0, 0, 0, alpha),
                         (i, i, SCREEN_W - i*2, SCREEN_H - i*2), width=1)
    surface.blit(vignette, (0, 0))

    draw_stats(surface, state)
    draw_inventory(surface, inventory)
    save_rect = draw_save_button(surface, hover=save_hover)
    load_rect = draw_load_button(surface, hover=load_hover)

    box_x = BOX_MARGIN
    box_w = SCREEN_W - BOX_MARGIN * 2
    total_choices = len(available) + len(locked)
    choices_h = total_choices * (CHOICE_H + CHOICE_PAD) + CHOICE_PAD
    box_h = TEXT_BOX_H + choices_h
    box_y = SCREEN_H - box_h - BOX_MARGIN

    text_rect = pygame.Rect(box_x, box_y, box_w, box_h)
    draw_rounded_rect(surface, text_rect, COLOR_BOX_BG)
    draw_rounded_border(surface, text_rect, COLOR_BOX_BORDER, width=1)

    text_area_w = box_w - BOX_PADDING * 2
    lines = wrap_text(scene["text"], FONT_MAIN, text_area_w)
    ty = box_y + BOX_PADDING
    for line in lines[:6]:
        surf = FONT_MAIN.render(line, True, COLOR_TEXT)
        surface.blit(surf, (box_x + BOX_PADDING, ty))
        ty += FONT_MAIN.get_linesize() + 2

    div_y = box_y + TEXT_BOX_H - 12
    pygame.draw.line(surface,
                     (*COLOR_BOX_BORDER[:3], 80),
                     (box_x + BOX_PADDING, div_y),
                     (box_x + box_w - BOX_PADDING, div_y), 1)

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
        reasons = []
        for k, v in choice.get("condition", {}).items():
            reasons.append(f"{k}>={v}")
        if choice.get("require_item"):
            reasons.append(f"item: {choice['require_item']}")
        req_str = ", ".join(reasons)

        label = FONT_SMALL.render(f"[locked: {req_str}]  {choice['text']}", True, COLOR_LOCKED_TEXT)
        surface.blit(label, (crect.x + 14, crect.y + CHOICE_H//2 - label.get_height()//2))
        cy += CHOICE_H + CHOICE_PAD

    return choice_rects, save_rect, load_rect


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

    db_ok = db_init()
    if not db_ok:
        print("[DB] Could not connect to PostgreSQL. Save/Load disabled.")

    story = load_story(STORY_FILE)
    state = {}
    current_scene = "start"
    inventory = set()
    image_cache = {}
    notification = None

    def get_bg(scene):
        image_id = scene.get("image")
        if not image_id:
            return None
        if image_id not in image_cache:
            image_cache[image_id] = load_image(image_id)
        return image_cache[image_id]

    hover_idx = -1

    while True:
        dt = clock.tick(FPS)
        scene = story[current_scene]
        bg = get_bg(scene)
        choices = scene["choices"]

        available = [c for c in choices if check_condition(c, state) and check_item(c, state)]
        locked    = [c for c in choices if not check_condition(c, state) or not check_item(c, inventory)]

        # Ending
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

        # Temporary rects for hover detection (first pass)
        save_rect_tmp = pygame.Rect(BOX_MARGIN, BOX_MARGIN, 110, 34)
        load_rect_tmp = pygame.Rect(BOX_MARGIN + 120, BOX_MARGIN, 110, 34)
        save_hover = save_rect_tmp.collidepoint(mx, my)
        load_hover = load_rect_tmp.collidepoint(mx, my)

        hover_idx = -1
        choice_rects, save_rect, load_rect = draw_scene(
            screen, bg, scene, available, locked, state, inventory, hover_idx,
            save_hover, load_hover
        )
        for i, rect in enumerate(choice_rects):
            if rect.collidepoint(mx, my):
                hover_idx = i
                break

        choice_rects, save_rect, load_rect = draw_scene(
            screen, bg, scene, available, locked, state, inventory, hover_idx,
            save_hover, load_hover
        )

        # Notification
        if notification:
            notification.update(dt)
            if notification.active:
                notification.draw(screen)
            else:
                notification = None

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

                # Save
                if event.key == pygame.K_s and db_ok:
                    session_name = run_save_dialog(screen, screen, clock, bg)
                    if session_name and session_name.strip():
                        ok = db_save(session_name.strip(), current_scene, state, inventory)
                        notification = Notification(
                            f"Saved as '{session_name.strip()}'" if ok else "Save failed."
                        )

                # Load
                if event.key == pygame.K_l and db_ok:
                    result = run_load_dialog(screen, screen, clock, bg)
                    if result:
                        current_scene, load_data = result
                        if isinstance(load_data, dict) and "state" in load_data:
                            state = load_data.get("state", {})
                            inventory = set(load_data.get("inventory", []))
                        else:
                            state = load_data if isinstance(load_data, dict) else {}
                            inventory = set()
                        notification = Notification(f"Loaded: {current_scene}")

                # Choice by number
                if pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(available):
                        choice = available[idx]
                        for k, v in choice.get("effects", {}).items():
                            state[k] = state.get(k, 0) + v
                        current_scene = choice["next"]
                        hover_idx = -1

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Save button click
                if save_rect.collidepoint(event.pos) and db_ok:
                    session_name = run_save_dialog(screen, screen, clock, bg)
                    if session_name and session_name.strip():
                        ok = db_save(session_name.strip(), current_scene, state, inventory)
                        notification = Notification(
                            f"Saved as '{session_name.strip()}'" if ok else "Save failed."
                        )

                # Load button click
                elif load_rect.collidepoint(event.pos) and db_ok:
                    result = run_load_dialog(screen, screen, clock, bg)
                    if result:
                        loaded_scene, loaded_state, loaded_inv = apply_load(result)
                        if loaded_scene:
                            current_scene, loaded_state = result
                            state = loaded_state if isinstance(loaded_state, dict) else {}
                            inventory = loaded_inv
                            notification = Notification(f"Loaded: {current_scene}")

                else:
                    for i, rect in enumerate(choice_rects):
                        if rect.collidepoint(event.pos):
                            choice = available[i]
                            for k, v in choice.get("effects", {}).items():
                                state[k] = state.get(k, 0) + v
                            if "give_item" in choice:
                                item = choice["give_item"]
                                if item not in inventory:
                                    inventory.add(item)
                                    notification = Notification(f"Item received:{item}")
                            current_scene = choice["next"]
                            hover_idx = -1
                            break


if __name__ == "__main__":
    main()