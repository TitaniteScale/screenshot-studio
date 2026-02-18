import os
import sys

import pygame

try:
    import tomllib
except ImportError:
    import tomli as tomllib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.toml")

DEFAULT_CONFIG = {"settings": {"screenshots_dir": "screenshots"}}

# --- Colors ---
BG_COLOR = (20, 20, 30)
BAR_COLOR = (30, 30, 45)
BTN_NORMAL = (50, 50, 70)
BTN_SELECTED = (60, 100, 180)
BTN_TEXT = (220, 220, 220)
TEXT_COLOR = (180, 180, 200)
ACCENT = (100, 160, 255)

WINDOW_W = 1280
WINDOW_H = 720
BAR_H = 80
BTN_W = 180
BTN_H = 50
BTN_GAP = 20

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

AXIS_DEAD = 0.5
AXIS_COOLDOWN = 220  # ms between axis-driven navigation steps


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
    text_surf = font.render(label, True, BTN_TEXT)
    tx = rect.x + (rect.w - text_surf.get_width()) // 2
    ty = rect.y + (rect.h - text_surf.get_height()) // 2
    screen.blit(text_surf, (tx, ty))


def run():
    # --- Config ---
    config = load_config()
    screenshots_dir = config.get("settings", {}).get("screenshots_dir", "screenshots")
    if not os.path.isabs(screenshots_dir):
        screenshots_dir = os.path.join(SCRIPT_DIR, screenshots_dir)

    # --- Pygame init ---
    pygame.init()
    pygame.joystick.init()

    joysticks = []
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        joysticks.append(j)
        print(f"Gamepad detected: {j.get_name()}")

    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Screenshot Studio")
    clock = pygame.time.Clock()

    font_large = pygame.font.SysFont(None, 36)
    font_small = pygame.font.SysFont(None, 24)

    # --- State ---
    image_files = get_image_files(screenshots_dir)
    current_index = 0
    current_image = load_image(image_files[0]) if image_files else None

    # focus: "image" | "buttons"
    focus = "image"
    button_index = 0  # 0 = Rename, 1 = Exit
    buttons = ["Rename", "Exit"]

    # Toast / status message
    toast_text = ""
    toast_timer = 0  # ms remaining

    axis_cooldown = 0  # ms until next axis step is allowed

    IMAGE_AREA_H = WINDOW_H - BAR_H

    def navigate_images(delta):
        nonlocal current_index, current_image
        if not image_files:
            return
        current_index = (current_index + delta) % len(image_files)
        current_image = load_image(image_files[current_index])

    def activate_button():
        nonlocal toast_text, toast_timer
        label = buttons[button_index]
        if label == "Exit":
            shutdown()
        elif label == "Rename":
            toast_text = "Rename: not yet implemented"
            toast_timer = 2000

    def shutdown():
        pygame.quit()
        sys.exit()

    # --- Main loop ---
    while True:
        dt = clock.tick(60)
        axis_cooldown = max(0, axis_cooldown - dt)
        if toast_timer > 0:
            toast_timer = max(0, toast_timer - dt)
            if toast_timer == 0:
                toast_text = ""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    shutdown()

                elif focus == "image":
                    if event.key == pygame.K_LEFT:
                        navigate_images(-1)
                    elif event.key == pygame.K_RIGHT:
                        navigate_images(1)
                    elif event.key == pygame.K_DOWN:
                        focus = "buttons"

                elif focus == "buttons":
                    if event.key == pygame.K_LEFT:
                        button_index = (button_index - 1) % len(buttons)
                    elif event.key == pygame.K_RIGHT:
                        button_index = (button_index + 1) % len(buttons)
                    elif event.key == pygame.K_UP:
                        focus = "image"
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        activate_button()

            # --- Gamepad: face button press ---
            elif event.type == pygame.JOYBUTTONDOWN:
                # Button 0 = A (Xbox) / Cross (PlayStation) — confirm
                if event.button == 0:
                    if focus == "buttons":
                        activate_button()
                # Button 1 = B (Xbox) / Circle (PlayStation) — back to image focus
                elif event.button == 1:
                    focus = "image"

            # --- Gamepad: D-pad (hat) ---
            elif event.type == pygame.JOYHATMOTION:
                hx, hy = event.value
                if focus == "image":
                    if hx == -1:
                        navigate_images(-1)
                    elif hx == 1:
                        navigate_images(1)
                    elif hy == -1:  # hat down
                        focus = "buttons"
                elif focus == "buttons":
                    if hx == -1:
                        button_index = (button_index - 1) % len(buttons)
                    elif hx == 1:
                        button_index = (button_index + 1) % len(buttons)
                    elif hy == 1:  # hat up
                        focus = "image"

        # --- Gamepad: analog stick (polled with cooldown) ---
        if axis_cooldown == 0 and joysticks:
            j = joysticks[0]
            ax = j.get_axis(0)  # left stick X
            ay = j.get_axis(1)  # left stick Y

            if focus == "image":
                if ax < -AXIS_DEAD:
                    navigate_images(-1)
                    axis_cooldown = AXIS_COOLDOWN
                elif ax > AXIS_DEAD:
                    navigate_images(1)
                    axis_cooldown = AXIS_COOLDOWN
                elif ay > AXIS_DEAD:
                    focus = "buttons"
                    axis_cooldown = AXIS_COOLDOWN
            elif focus == "buttons":
                if ax < -AXIS_DEAD:
                    button_index = (button_index - 1) % len(buttons)
                    axis_cooldown = AXIS_COOLDOWN
                elif ax > AXIS_DEAD:
                    button_index = (button_index + 1) % len(buttons)
                    axis_cooldown = AXIS_COOLDOWN
                elif ay < -AXIS_DEAD:
                    focus = "image"
                    axis_cooldown = AXIS_COOLDOWN

        # =====================
        # --- Draw ---
        # =====================
        screen.fill(BG_COLOR)

        # --- Image area ---
        if current_image:
            scaled = scale_to_fit(current_image, WINDOW_W, IMAGE_AREA_H)
            iw, ih = scaled.get_size()
            screen.blit(scaled, ((WINDOW_W - iw) // 2, (IMAGE_AREA_H - ih) // 2))
        else:
            msg = font_large.render(
                "No images found in: " + screenshots_dir, True, TEXT_COLOR
            )
            screen.blit(msg, (WINDOW_W // 2 - msg.get_width() // 2, IMAGE_AREA_H // 2))

        # --- HUD: filename + counter ---
        if image_files:
            name = os.path.basename(image_files[current_index])
            counter = f"{current_index + 1} / {len(image_files)}"

            # Semi-transparent backing strip at top
            hud_surf = pygame.Surface((WINDOW_W, 30), pygame.SRCALPHA)
            hud_surf.fill((0, 0, 0, 120))
            screen.blit(hud_surf, (0, 0))

            name_surf = font_small.render(name, True, TEXT_COLOR)
            counter_surf = font_small.render(counter, True, TEXT_COLOR)
            screen.blit(name_surf, (10, 7))
            screen.blit(counter_surf, (WINDOW_W - counter_surf.get_width() - 10, 7))

        # --- Focus hint at bottom of image area ---
        if focus == "image" and image_files:
            hint = font_small.render(
                "<  >  navigate    v  buttons", True, (120, 120, 150)
            )
            screen.blit(
                hint, (WINDOW_W // 2 - hint.get_width() // 2, IMAGE_AREA_H - 26)
            )

        # --- Bottom bar ---
        bar_rect = pygame.Rect(0, IMAGE_AREA_H, WINDOW_W, BAR_H)
        pygame.draw.rect(screen, BAR_COLOR, bar_rect)
        if focus == "buttons":
            pygame.draw.rect(screen, ACCENT, bar_rect, 2)

        # --- Buttons ---
        total_btn_w = len(buttons) * BTN_W + (len(buttons) - 1) * BTN_GAP
        btn_x0 = (WINDOW_W - total_btn_w) // 2
        btn_y = IMAGE_AREA_H + (BAR_H - BTN_H) // 2

        for i, label in enumerate(buttons):
            bx = btn_x0 + i * (BTN_W + BTN_GAP)
            rect = pygame.Rect(bx, btn_y, BTN_W, BTN_H)
            draw_button(
                screen,
                font_large,
                label,
                rect,
                selected=(focus == "buttons" and i == button_index),
            )

        # --- Toast message ---
        if toast_text:
            toast_surf = font_large.render(toast_text, True, (255, 220, 80))
            tx = WINDOW_W // 2 - toast_surf.get_width() // 2
            ty = IMAGE_AREA_H - 60
            backing = pygame.Surface(
                (toast_surf.get_width() + 24, toast_surf.get_height() + 12),
                pygame.SRCALPHA,
            )
            backing.fill((0, 0, 0, 160))
            screen.blit(backing, (tx - 12, ty - 6))
            screen.blit(toast_surf, (tx, ty))

        pygame.display.flip()


if __name__ == "__main__":
    run()
