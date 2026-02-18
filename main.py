import os
import shutil
import sys

import pygame

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.toml")
DEFAULT_CONFIG = {"settings": {"screenshots_dir": "screenshots", "fullscreen": False}}

# ── Colours (defaults — all overridable via [colors] in config.toml) ───────
BG_COLOR = (20, 20, 30)
BAR_COLOR = (30, 30, 45)
BTN_NORMAL = (50, 50, 70)
BTN_SELECTED = (60, 100, 180)
BTN_TEXT = (220, 220, 220)
TEXT_COLOR = (180, 180, 200)
ACCENT = (100, 160, 255)
DIM_COLOR = (100, 100, 130)
KEY_CONFIRM = (35, 100, 55)
KEY_CONFIRM_SEL = (55, 160, 85)
KEY_CANCEL = (110, 35, 35)
KEY_CANCEL_SEL = (170, 55, 55)
KEY_SPECIAL = (70, 55, 40)
KEY_SPECIAL_SEL = (130, 100, 60)


def hex_to_rgb(hex_str):
    """Convert a '#rrggbb' string to an (r, g, b) tuple."""
    h = hex_str.strip().lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


# ── Window ─────────────────────────────────────────────────────────────────
WINDOW_W = 1280
WINDOW_H = 720

# ── Browse scene constants ─────────────────────────────────────────────────
BAR_H = 80
BTN_W = 180
BTN_H = 56
BTN_GAP = 20

# ── Rename scene / keyboard constants ─────────────────────────────────────
RENAME_PREVIEW_H = 240  # height of the thumbnail area
RENAME_LABEL_Y = 248  # y of "Renaming: …" label
RENAME_INPUT_Y = 278  # y of the text-input field
RENAME_INPUT_H = 54  # height of the text-input field
KB_Y = 344  # y of top of keyboard
KB_X = 90  # left edge of keyboard
KB_W = 1100  # total keyboard width
KEY_H = 56  # height of every key
KEY_GAP = 8  # gap between keys (both axes)

# Rows: plain chars = append to name; special tokens handled by press_kb_key()
KB_ROWS = [
    list("1234567890"),
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
    [" ", "\b", "-", "_", ".", "\n", "\x1b"],
]

KB_LABELS = {
    " ": "SPC",
    "\b": "DEL",
    "\n": "DONE",
    "\x1b": "BACK",
}

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

AXIS_DEAD = 0.5
AXIS_COOLDOWN = 200  # ms between axis-driven steps

# ── Scenes ─────────────────────────────────────────────────────────────────
SCENE_BROWSE = "browse"
SCENE_RENAME = "rename"


# ── Helpers ────────────────────────────────────────────────────────────────


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    return DEFAULT_CONFIG


def get_image_files(directory):
    try:
        entries = sorted(os.listdir(directory))
    except OSError as e:
        print(f"Cannot read directory '{directory}': {e}")
        return []
    return [
        os.path.join(directory, f)
        for f in entries
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
    ]


def load_image(path):
    try:
        return pygame.image.load(path).convert()
    except Exception as e:
        print(f"Error loading '{path}': {e}")
        return None


def scale_to_fit(img, area_w, area_h):
    iw, ih = img.get_size()
    scale = min(area_w / iw, area_h / ih)
    return pygame.transform.smoothscale(img, (int(iw * scale), int(ih * scale)))


def draw_button(screen, font, label, rect, selected):
    color = BTN_SELECTED if selected else BTN_NORMAL
    pygame.draw.rect(screen, color, rect, border_radius=8)
    if selected:
        pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=8)
    surf = font.render(label, True, BTN_TEXT)
    screen.blit(
        surf,
        (
            rect.x + (rect.w - surf.get_width()) // 2,
            rect.y + (rect.h - surf.get_height()) // 2,
        ),
    )


def get_key_rect(row, col):
    """Return the pygame.Rect for a key at (row, col)."""
    n = len(KB_ROWS[row])
    key_w = (KB_W - (n - 1) * KEY_GAP) / n
    x = KB_X + col * (key_w + KEY_GAP)
    y = KB_Y + row * (KEY_H + KEY_GAP)
    return pygame.Rect(int(x), int(y), int(key_w), KEY_H)


def key_colors(ch):
    """Return (normal_color, selected_color) for a key character."""
    if ch == "\n":
        return KEY_CONFIRM, KEY_CONFIRM_SEL
    if ch == "\x1b":
        return KEY_CANCEL, KEY_CANCEL_SEL
    if ch in (" ", "\b", "-", "_", "."):
        return KEY_SPECIAL, KEY_SPECIAL_SEL
    return BTN_NORMAL, BTN_SELECTED


# ── Main ───────────────────────────────────────────────────────────────────


def run():
    # Config
    config = load_config()
    settings = config.get("settings", {})
    screenshots_dir = settings.get("screenshots_dir", "screenshots")
    if not os.path.isabs(screenshots_dir):
        screenshots_dir = os.path.join(SCRIPT_DIR, screenshots_dir)

    slideshow_dir = settings.get("slideshow_dir", "slideshow")
    if not os.path.isabs(slideshow_dir):
        slideshow_dir = os.path.join(SCRIPT_DIR, slideshow_dir)
    os.makedirs(slideshow_dir, exist_ok=True)

    bg_image_path = settings.get("background_image", None)
    fullscreen = settings.get("fullscreen", False)

    # Apply [colors] overrides from config
    global BG_COLOR, BAR_COLOR, BTN_NORMAL, BTN_SELECTED, BTN_TEXT
    global TEXT_COLOR, ACCENT, DIM_COLOR
    global KEY_CONFIRM, KEY_CONFIRM_SEL, KEY_CANCEL, KEY_CANCEL_SEL
    global KEY_SPECIAL, KEY_SPECIAL_SEL

    colors_cfg = config.get("colors", {})
    _co = {
        "bg": ("BG_COLOR", BG_COLOR),
        "bar": ("BAR_COLOR", BAR_COLOR),
        "btn_normal": ("BTN_NORMAL", BTN_NORMAL),
        "btn_selected": ("BTN_SELECTED", BTN_SELECTED),
        "btn_text": ("BTN_TEXT", BTN_TEXT),
        "text": ("TEXT_COLOR", TEXT_COLOR),
        "accent": ("ACCENT", ACCENT),
        "dim": ("DIM_COLOR", DIM_COLOR),
        "key_confirm": ("KEY_CONFIRM", KEY_CONFIRM),
        "key_confirm_sel": ("KEY_CONFIRM_SEL", KEY_CONFIRM_SEL),
        "key_cancel": ("KEY_CANCEL", KEY_CANCEL),
        "key_cancel_sel": ("KEY_CANCEL_SEL", KEY_CANCEL_SEL),
        "key_special": ("KEY_SPECIAL", KEY_SPECIAL),
        "key_special_sel": ("KEY_SPECIAL_SEL", KEY_SPECIAL_SEL),
    }
    for cfg_key, (var_name, _default) in _co.items():
        if cfg_key in colors_cfg:
            try:
                globals()[var_name] = hex_to_rgb(colors_cfg[cfg_key])
            except Exception as e:
                print(f"Invalid color for '{cfg_key}': {e}")

    # Pygame
    pygame.init()
    pygame.joystick.init()

    joysticks = []
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        joysticks.append(j)
        print(f"Gamepad detected: {j.get_name()}")

    flags = (pygame.FULLSCREEN | pygame.SCALED) if fullscreen else 0
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), flags)
    pygame.display.set_caption("Screenshot Studio")
    clock = pygame.time.Clock()

    font_large = pygame.font.SysFont(None, 36)
    font_small = pygame.font.SysFont(None, 24)

    # Load and scale background image (if configured)
    background = None
    if bg_image_path:
        if not os.path.isabs(bg_image_path):
            bg_image_path = os.path.join(SCRIPT_DIR, bg_image_path)
        try:
            bg_raw = pygame.image.load(bg_image_path).convert()
            background = pygame.transform.smoothscale(bg_raw, (WINDOW_W, WINDOW_H))
            print(f"Background loaded: {bg_image_path}")
        except Exception as e:
            print(f"Could not load background '{bg_image_path}': {e}")

    # Load toolbar and button assets (if configured)
    def load_asset(path, scale=None):
        """Load an image asset, optionally scaling it. Returns None on failure."""
        if not path:
            return None
        if not os.path.isabs(path):
            path = os.path.join(SCRIPT_DIR, path)
        try:
            img = pygame.image.load(path).convert_alpha()
            if scale:
                img = pygame.transform.smoothscale(img, scale)
            return img
        except Exception as e:
            print(f"Could not load asset '{path}': {e}")
            return None

    assets_cfg = config.get("assets", {})
    toolbar_img = load_asset(assets_cfg.get("toolbar"), scale=(WINDOW_W, BAR_H))
    button_imgs = {
        "Rename": {
            "normal": load_asset(
                assets_cfg.get("button_rename_normal"), scale=(BTN_W, BTN_H)
            ),
            "selected": load_asset(
                assets_cfg.get("button_rename_selected"), scale=(BTN_W, BTN_H)
            ),
        },
        "Exit": {
            "normal": load_asset(
                assets_cfg.get("button_exit_normal"), scale=(BTN_W, BTN_H)
            ),
            "selected": load_asset(
                assets_cfg.get("button_exit_selected"), scale=(BTN_W, BTN_H)
            ),
        },
        "Slideshow": {
            "normal": load_asset(
                assets_cfg.get("button_slideshow_off_normal"), scale=(BTN_W, BTN_H)
            ),
            "selected": load_asset(
                assets_cfg.get("button_slideshow_off_selected"), scale=(BTN_W, BTN_H)
            ),
            "on_normal": load_asset(
                assets_cfg.get("button_slideshow_on_normal"), scale=(BTN_W, BTN_H)
            ),
            "on_selected": load_asset(
                assets_cfg.get("button_slideshow_on_selected"), scale=(BTN_W, BTN_H)
            ),
        },
    }

    # ── Shared state ───────────────────────────────────────────────────────
    image_files = get_image_files(screenshots_dir)
    current_index = 0
    current_image = load_image(image_files[0]) if image_files else None

    scene = SCENE_BROWSE
    axis_cooldown = 0

    # ── Browse state ───────────────────────────────────────────────────────
    IMAGE_AREA_H = WINDOW_H - BAR_H
    browse_focus = "image"  # "image" | "buttons"
    button_index = 0
    buttons = ["Rename", "Slideshow", "Exit"]
    toast_text = ""
    toast_timer = 0
    in_slideshow = False

    # ── Rename state ───────────────────────────────────────────────────────
    rename_text = ""
    rename_ext = ""
    kb_row = 0
    kb_col = 0
    rename_error = ""
    rename_error_timer = 0

    # ── Inner helpers ──────────────────────────────────────────────────────

    def shutdown():
        pygame.quit()
        sys.exit()

    def check_in_slideshow():
        nonlocal in_slideshow
        if not image_files:
            in_slideshow = False
            return
        basename = os.path.basename(image_files[current_index])
        in_slideshow = os.path.exists(os.path.join(slideshow_dir, basename))

    def navigate_images(delta):
        nonlocal current_index, current_image
        if not image_files:
            return
        current_index = (current_index + delta) % len(image_files)
        current_image = load_image(image_files[current_index])
        check_in_slideshow()

    def toggle_slideshow():
        nonlocal in_slideshow, toast_text, toast_timer
        if not image_files:
            return
        src = image_files[current_index]
        basename = os.path.basename(src)
        dest = os.path.join(slideshow_dir, basename)
        if in_slideshow:
            try:
                os.remove(dest)
                in_slideshow = False
                toast_text = "Removed from slideshow"
                toast_timer = 2500
            except OSError as e:
                toast_text = f"Error: {e}"
                toast_timer = 2500
        else:
            try:
                shutil.copy2(src, dest)
                in_slideshow = True
                toast_text = "Added to slideshow"
                toast_timer = 2500
            except OSError as e:
                toast_text = f"Error: {e}"
                toast_timer = 2500

    # Initialise in_slideshow for the first image
    check_in_slideshow()

    def enter_rename():
        nonlocal \
            scene, \
            rename_text, \
            rename_ext, \
            kb_row, \
            kb_col, \
            rename_error, \
            rename_error_timer
        if not image_files:
            return
        stem, ext = os.path.splitext(os.path.basename(image_files[current_index]))
        rename_text = stem
        rename_ext = ext
        kb_row = 0
        kb_col = 0
        rename_error = ""
        rename_error_timer = 0
        scene = SCENE_RENAME

    def do_rename():
        nonlocal scene, toast_text, toast_timer, rename_error, rename_error_timer
        new_stem = rename_text.strip()
        if not new_stem:
            rename_error = "Name cannot be empty."
            rename_error_timer = 2500
            return
        old_path = image_files[current_index]
        directory = os.path.dirname(old_path)
        new_filename = new_stem + rename_ext
        new_path = os.path.join(directory, new_filename)
        if new_path == old_path:
            scene = SCENE_BROWSE
            return
        if os.path.exists(new_path):
            rename_error = f"'{new_filename}' already exists."
            rename_error_timer = 2500
            return
        try:
            os.rename(old_path, new_path)
            image_files[current_index] = new_path
            toast_text = f"Renamed to  {new_filename}"
            toast_timer = 2500
            scene = SCENE_BROWSE
        except OSError as e:
            rename_error = str(e)
            rename_error_timer = 2500

    def press_kb_key():
        nonlocal rename_text, scene
        ch = KB_ROWS[kb_row][kb_col]
        if ch == "\b":
            rename_text = rename_text[:-1]
        elif ch == "\n":
            do_rename()
        elif ch == "\x1b":
            scene = SCENE_BROWSE
        else:
            rename_text += ch

    def move_kb(drow, dcol):
        nonlocal kb_row, kb_col
        if dcol != 0:
            kb_col = max(0, min(kb_col + dcol, len(KB_ROWS[kb_row]) - 1))
        elif drow != 0:
            new_row = max(0, min(kb_row + drow, len(KB_ROWS) - 1))
            if new_row != kb_row:
                ratio = kb_col / max(1, len(KB_ROWS[kb_row]) - 1)
                kb_col = round(ratio * max(1, len(KB_ROWS[new_row]) - 1))
                kb_row = new_row

    # ── Input handlers ─────────────────────────────────────────────────────

    def handle_browse_key(event):
        nonlocal browse_focus, button_index
        if event.key == pygame.K_ESCAPE:
            shutdown()
        elif browse_focus == "image":
            if event.key == pygame.K_LEFT:
                navigate_images(-1)
            elif event.key == pygame.K_RIGHT:
                navigate_images(1)
            elif event.key == pygame.K_DOWN:
                browse_focus = "buttons"
        elif browse_focus == "buttons":
            if event.key == pygame.K_LEFT:
                button_index = (button_index - 1) % len(buttons)
            elif event.key == pygame.K_RIGHT:
                button_index = (button_index + 1) % len(buttons)
            elif event.key == pygame.K_UP:
                browse_focus = "image"
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if buttons[button_index] == "Exit":
                    shutdown()
                elif buttons[button_index] == "Rename":
                    enter_rename()
                elif buttons[button_index] == "Slideshow":
                    toggle_slideshow()

    def handle_rename_key(event):
        nonlocal scene, rename_text
        if event.key == pygame.K_ESCAPE:
            scene = SCENE_BROWSE
        elif event.key == pygame.K_RETURN:
            do_rename()
        elif event.key == pygame.K_BACKSPACE:
            rename_text = rename_text[:-1]
        elif event.key == pygame.K_LEFT:
            move_kb(0, -1)
        elif event.key == pygame.K_RIGHT:
            move_kb(0, 1)
        elif event.key == pygame.K_UP:
            move_kb(-1, 0)
        elif event.key == pygame.K_DOWN:
            move_kb(1, 0)
        elif event.key == pygame.K_SPACE:
            press_kb_key()
        elif event.unicode and event.unicode.isprintable():
            # Direct physical-keyboard typing: allow valid filename chars
            if event.unicode not in r'\/:*?"<>|':
                rename_text += event.unicode

    def handle_joy_button(event):
        nonlocal browse_focus, button_index, scene
        if scene == SCENE_BROWSE:
            if event.button == 0:  # A / Cross — confirm
                if browse_focus == "buttons":
                    if buttons[button_index] == "Exit":
                        shutdown()
                    elif buttons[button_index] == "Rename":
                        enter_rename()
                    elif buttons[button_index] == "Slideshow":
                        toggle_slideshow()
            elif event.button == 1:  # B / Circle — back
                browse_focus = "image"
        elif scene == SCENE_RENAME:
            if event.button == 0:  # A — press key
                press_kb_key()
            elif event.button == 1:  # B — cancel rename
                scene = SCENE_BROWSE

    def handle_joy_hat(event):
        nonlocal browse_focus, button_index
        hx, hy = event.value
        if scene == SCENE_BROWSE:
            if browse_focus == "image":
                if hx == -1:
                    navigate_images(-1)
                elif hx == 1:
                    navigate_images(1)
                elif hy == -1:
                    browse_focus = "buttons"
            elif browse_focus == "buttons":
                if hx == -1:
                    button_index = (button_index - 1) % len(buttons)
                elif hx == 1:
                    button_index = (button_index + 1) % len(buttons)
                elif hy == 1:
                    browse_focus = "image"
        elif scene == SCENE_RENAME:
            if hx == -1:
                move_kb(0, -1)
            elif hx == 1:
                move_kb(0, 1)
            elif hy == 1:
                move_kb(-1, 0)
            elif hy == -1:
                move_kb(1, 0)

    def handle_axis():
        nonlocal axis_cooldown, browse_focus, button_index
        if not joysticks:
            return
        j = joysticks[0]
        ax = j.get_axis(0)
        ay = j.get_axis(1)
        moved = False
        if scene == SCENE_BROWSE:
            if browse_focus == "image":
                if ax < -AXIS_DEAD:
                    navigate_images(-1)
                    moved = True
                elif ax > AXIS_DEAD:
                    navigate_images(1)
                    moved = True
                elif ay > AXIS_DEAD:
                    browse_focus = "buttons"
                    moved = True
            elif browse_focus == "buttons":
                if ax < -AXIS_DEAD:
                    button_index = (button_index - 1) % len(buttons)
                    moved = True
                elif ax > AXIS_DEAD:
                    button_index = (button_index + 1) % len(buttons)
                    moved = True
                elif ay < -AXIS_DEAD:
                    browse_focus = "image"
                    moved = True
        elif scene == SCENE_RENAME:
            if ax < -AXIS_DEAD:
                move_kb(0, -1)
                moved = True
            elif ax > AXIS_DEAD:
                move_kb(0, 1)
                moved = True
            elif ay < -AXIS_DEAD:
                move_kb(-1, 0)
                moved = True
            elif ay > AXIS_DEAD:
                move_kb(1, 0)
                moved = True
        if moved:
            axis_cooldown = AXIS_COOLDOWN

    # ── Draw helpers ───────────────────────────────────────────────────────

    def draw_background():
        if background:
            screen.blit(background, (0, 0))
        else:
            screen.fill(BG_COLOR)

    def draw_browse():
        draw_background()

        # Image
        if current_image:
            scaled = scale_to_fit(current_image, WINDOW_W, IMAGE_AREA_H)
            iw, ih = scaled.get_size()
            screen.blit(scaled, ((WINDOW_W - iw) // 2, (IMAGE_AREA_H - ih) // 2))
        else:
            msg = font_large.render(
                "No images found in: " + screenshots_dir, True, TEXT_COLOR
            )
            screen.blit(msg, (WINDOW_W // 2 - msg.get_width() // 2, IMAGE_AREA_H // 2))

        # HUD strip
        if image_files:
            strip = pygame.Surface((WINDOW_W, 30), pygame.SRCALPHA)
            strip.fill((0, 0, 0, 120))
            screen.blit(strip, (0, 0))
            name_s = font_small.render(
                os.path.basename(image_files[current_index]), True, TEXT_COLOR
            )
            counter_s = font_small.render(
                f"{current_index + 1} / {len(image_files)}", True, TEXT_COLOR
            )
            screen.blit(name_s, (10, 7))
            screen.blit(counter_s, (WINDOW_W - counter_s.get_width() - 10, 7))

        # Navigation hint
        if browse_focus == "image" and image_files:
            hint = font_small.render(
                "<  >  navigate    v  buttons", True, (110, 110, 145)
            )
            screen.blit(
                hint, (WINDOW_W // 2 - hint.get_width() // 2, IMAGE_AREA_H - 26)
            )

        # Bottom bar
        bar_rect = pygame.Rect(0, IMAGE_AREA_H, WINDOW_W, BAR_H)
        if toolbar_img:
            screen.blit(toolbar_img, (0, IMAGE_AREA_H))
        else:
            pygame.draw.rect(screen, BAR_COLOR, bar_rect)
        if browse_focus == "buttons":
            pygame.draw.rect(screen, ACCENT, bar_rect, 2)

        total_w = len(buttons) * BTN_W + (len(buttons) - 1) * BTN_GAP
        bx0 = (WINDOW_W - total_w) // 2
        by = IMAGE_AREA_H + (BAR_H - BTN_H) // 2
        for i, label in enumerate(buttons):
            selected = browse_focus == "buttons" and i == button_index
            rect = pygame.Rect(bx0 + i * (BTN_W + BTN_GAP), by, BTN_W, BTN_H)
            imgs = button_imgs.get(label, {})

            if label == "Slideshow":
                img_key = (
                    ("on_selected" if selected else "on_normal")
                    if in_slideshow
                    else ("selected" if selected else "normal")
                )
                img_surf = imgs.get(img_key)
                if img_surf is not None:
                    screen.blit(img_surf, rect.topleft)
                else:
                    # Fallback drawn button — green tint when active
                    if in_slideshow:
                        color = KEY_CONFIRM_SEL if selected else KEY_CONFIRM
                        pygame.draw.rect(screen, color, rect, border_radius=8)
                        if selected:
                            pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=8)
                        surf = font_large.render("★ Slideshow", True, BTN_TEXT)
                        screen.blit(
                            surf,
                            (
                                rect.x + (rect.w - surf.get_width()) // 2,
                                rect.y + (rect.h - surf.get_height()) // 2,
                            ),
                        )
                    else:
                        draw_button(screen, font_large, "+ Slideshow", rect, selected)
            else:
                key = "selected" if selected else "normal"
                img_surf = imgs.get(key)
                if img_surf is not None:
                    screen.blit(img_surf, rect.topleft)
                else:
                    draw_button(screen, font_large, label, rect, selected)

        # Toast
        if toast_text:
            ts = font_large.render(toast_text, True, (255, 220, 80))
            tx = WINDOW_W // 2 - ts.get_width() // 2
            ty = IMAGE_AREA_H - 58
            bg = pygame.Surface(
                (ts.get_width() + 24, ts.get_height() + 12), pygame.SRCALPHA
            )
            bg.fill((0, 0, 0, 160))
            screen.blit(bg, (tx - 12, ty - 6))
            screen.blit(ts, (tx, ty))

    def draw_rename():
        draw_background()

        # Thumbnail
        if current_image:
            scaled = scale_to_fit(current_image, WINDOW_W, RENAME_PREVIEW_H - 10)
            iw, ih = scaled.get_size()
            screen.blit(scaled, ((WINDOW_W - iw) // 2, (RENAME_PREVIEW_H - ih) // 2))

        # "Renaming: original_name" label
        orig = os.path.basename(image_files[current_index]) if image_files else ""
        label_s = font_small.render(f"Renaming:  {orig}", True, DIM_COLOR)
        screen.blit(label_s, (WINDOW_W // 2 - label_s.get_width() // 2, RENAME_LABEL_Y))

        # Input field
        input_rect = pygame.Rect(KB_X, RENAME_INPUT_Y, KB_W, RENAME_INPUT_H)
        pygame.draw.rect(screen, (35, 35, 55), input_rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT, input_rect, 2, border_radius=8)

        # Blinking cursor
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        stem_s = font_large.render(rename_text + cursor, True, BTN_TEXT)
        ext_s = font_small.render(rename_ext, True, DIM_COLOR)
        text_x = input_rect.x + 14
        text_y = input_rect.y + (RENAME_INPUT_H - stem_s.get_height()) // 2
        screen.blit(stem_s, (text_x, text_y))
        screen.blit(
            ext_s,
            (
                text_x + stem_s.get_width() + 2,
                text_y + stem_s.get_height() - ext_s.get_height(),
            ),
        )

        # Error message
        if rename_error:
            err_s = font_small.render(rename_error, True, (240, 80, 80))
            screen.blit(
                err_s,
                (
                    WINDOW_W // 2 - err_s.get_width() // 2,
                    RENAME_INPUT_Y + RENAME_INPUT_H + 4,
                ),
            )

        # Keyboard
        for row_i, row in enumerate(KB_ROWS):
            for col_i, ch in enumerate(row):
                rect = get_key_rect(row_i, col_i)
                selected = row_i == kb_row and col_i == kb_col
                normal, hi = key_colors(ch)
                color = hi if selected else normal
                pygame.draw.rect(screen, color, rect, border_radius=6)
                if selected:
                    pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=6)
                lbl = KB_LABELS.get(ch, ch.upper())
                ls = font_small.render(lbl, True, BTN_TEXT)
                screen.blit(
                    ls,
                    (
                        rect.x + (rect.w - ls.get_width()) // 2,
                        rect.y + (rect.h - ls.get_height()) // 2,
                    ),
                )

    # ── Main loop ──────────────────────────────────────────────────────────
    while True:
        dt = clock.tick(60)
        axis_cooldown = max(0, axis_cooldown - dt)

        if toast_timer > 0:
            toast_timer = max(0, toast_timer - dt)
            if toast_timer == 0:
                toast_text = ""

        if rename_error_timer > 0:
            rename_error_timer = max(0, rename_error_timer - dt)
            if rename_error_timer == 0:
                rename_error = ""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown()
            elif event.type == pygame.KEYDOWN:
                if scene == SCENE_BROWSE:
                    handle_browse_key(event)
                else:
                    handle_rename_key(event)
            elif event.type == pygame.JOYBUTTONDOWN:
                handle_joy_button(event)
            elif event.type == pygame.JOYHATMOTION:
                handle_joy_hat(event)

        if axis_cooldown == 0:
            handle_axis()

        if scene == SCENE_BROWSE:
            draw_browse()
        else:
            draw_rename()

        pygame.display.flip()


if __name__ == "__main__":
    run()
