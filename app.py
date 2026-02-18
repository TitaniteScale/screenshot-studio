import os
import shutil
import sys
from typing import Any

import pygame

from config import Colors, build_colors, load_config
from constants import (
    AXIS_COOLDOWN,
    AXIS_DEAD,
    BAR_H,
    BTN_GAP,
    BTN_H,
    BTN_W,
    KB_ROWS,
    KB_W,
    KB_X,
    RENAME_INPUT_H,
    RENAME_INPUT_Y,
    RENAME_LABEL_Y,
    RENAME_PREVIEW_H,
    SCENE_BROWSE,
    SCENE_CONFIRM_DELETE,
    SCENE_RENAME,
    WINDOW_H,
    WINDOW_W,
)
from ui import draw_button, draw_keyboard, draw_slideshow_button
from utils import get_image_files, load_asset, load_image, scale_to_fit


class App:
    def __init__(self):
        config = load_config()
        settings = config.get("settings", {})
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # ── Directories ────────────────────────────────────────────────────
        screenshots_dir = settings.get("screenshots_dir", "screenshots")
        if not os.path.isabs(screenshots_dir):
            screenshots_dir = os.path.join(script_dir, screenshots_dir)
        self.screenshots_dir = screenshots_dir

        slideshow_dir = settings.get("slideshow_dir", "slideshow")
        if not os.path.isabs(slideshow_dir):
            slideshow_dir = os.path.join(script_dir, slideshow_dir)
        os.makedirs(slideshow_dir, exist_ok=True)
        self.slideshow_dir = slideshow_dir

        # ── Colors ─────────────────────────────────────────────────────────
        self.colors: Colors = build_colors(config)

        # ── Pygame init ────────────────────────────────────────────────────
        pygame.init()
        pygame.joystick.init()

        self.joysticks: list[Any] = []
        for i in range(pygame.joystick.get_count()):
            j = pygame.joystick.Joystick(i)
            j.init()
            self.joysticks.append(j)
            print(f"Gamepad detected: {j.get_name()}")

        fullscreen = settings.get("fullscreen", False)
        flags = (pygame.FULLSCREEN | pygame.SCALED) if fullscreen else 0
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), flags)
        pygame.display.set_caption("Screenshot Studio")
        self.clock = pygame.time.Clock()

        self.font_large = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)

        # ── Background ─────────────────────────────────────────────────────
        self.background: pygame.Surface | None = None
        bg_path = settings.get("background_image", None)
        if bg_path:
            if not os.path.isabs(bg_path):
                bg_path = os.path.join(script_dir, bg_path)
            try:
                bg_raw = pygame.image.load(bg_path).convert()
                self.background = pygame.transform.smoothscale(
                    bg_raw, (WINDOW_W, WINDOW_H)
                )
                print(f"Background loaded: {bg_path}")
            except Exception as e:
                print(f"Could not load background '{bg_path}': {e}")

        # ── Assets ─────────────────────────────────────────────────────────
        def _asset(key, scale=None):
            return load_asset(assets_cfg.get(key, ""), script_dir, scale=scale)

        assets_cfg = config.get("assets", {})
        self.toolbar_img = _asset("toolbar", scale=(WINDOW_W, BAR_H))
        self.button_imgs: dict[str, dict[str, pygame.Surface | None]] = {
            "Rename": {
                "normal": _asset("button_rename_normal", scale=(BTN_W, BTN_H)),
                "selected": _asset("button_rename_selected", scale=(BTN_W, BTN_H)),
            },
            "Exit": {
                "normal": _asset("button_exit_normal", scale=(BTN_W, BTN_H)),
                "selected": _asset("button_exit_selected", scale=(BTN_W, BTN_H)),
            },
            "Slideshow": {
                "normal": _asset("button_slideshow_off_normal", scale=(BTN_W, BTN_H)),
                "selected": _asset(
                    "button_slideshow_off_selected", scale=(BTN_W, BTN_H)
                ),
                "on_normal": _asset("button_slideshow_on_normal", scale=(BTN_W, BTN_H)),
                "on_selected": _asset(
                    "button_slideshow_on_selected", scale=(BTN_W, BTN_H)
                ),
            },
            "Delete": {
                "normal": _asset("button_delete_normal", scale=(BTN_W, BTN_H)),
                "selected": _asset("button_delete_selected", scale=(BTN_W, BTN_H)),
            },
        }

        # ── Image state ────────────────────────────────────────────────────
        self.image_files: list[str] = get_image_files(self.screenshots_dir)
        self.current_index: int = 0
        self.current_image: pygame.Surface | None = (
            load_image(self.image_files[0]) if self.image_files else None
        )

        # ── Scene state ────────────────────────────────────────────────────
        self.scene: str = SCENE_BROWSE
        self.axis_cooldown: int = 0

        # ── Browse state ───────────────────────────────────────────────────
        self.image_area_h: int = WINDOW_H - BAR_H
        self.browse_focus: str = "image"  # "image" | "buttons"
        self.button_index: int = 0
        self.buttons: list[str] = ["Rename", "Slideshow", "Delete", "Exit"]
        self.toast_text: str = ""
        self.toast_timer: int = 0
        self.in_slideshow: bool = False

        # ── Rename state ───────────────────────────────────────────────────
        self.rename_text: str = ""
        self.rename_ext: str = ""
        self.kb_row: int = 0
        self.kb_col: int = 0
        self.rename_error: str = ""
        self.rename_error_timer: int = 0

        # ── Confirm-delete state ───────────────────────────────────────────
        self.confirm_choice: int = 1  # 0 = Yes, 1 = No  (default No for safety)

        # Seed slideshow indicator for the first image
        self.check_in_slideshow()

    # ── Slideshow helpers ──────────────────────────────────────────────────

    def check_in_slideshow(self) -> None:
        if not self.image_files:
            self.in_slideshow = False
            return
        basename = os.path.basename(self.image_files[self.current_index])
        self.in_slideshow = os.path.exists(os.path.join(self.slideshow_dir, basename))

    def toggle_slideshow(self) -> None:
        if not self.image_files:
            return
        src = self.image_files[self.current_index]
        basename = os.path.basename(src)
        dest = os.path.join(self.slideshow_dir, basename)
        if self.in_slideshow:
            try:
                os.remove(dest)
                self.in_slideshow = False
                self.toast("Removed from slideshow")
            except OSError as e:
                self.toast(f"Error: {e}")
        else:
            try:
                shutil.copy2(src, dest)
                self.in_slideshow = True
                self.toast("Added to slideshow")
            except OSError as e:
                self.toast(f"Error: {e}")

    # ── Delete helpers ─────────────────────────────────────────────────────

    def enter_delete_confirm(self) -> None:
        if not self.image_files:
            return
        self.confirm_choice = 1  # reset to No each time for safety
        self.scene = SCENE_CONFIRM_DELETE

    def do_delete(self) -> None:
        if not self.image_files:
            self.scene = SCENE_BROWSE
            return
        path = self.image_files[self.current_index]
        basename = os.path.basename(path)
        # Also remove from slideshow dir if present
        slideshow_copy = os.path.join(self.slideshow_dir, basename)
        try:
            os.remove(path)
        except OSError as e:
            self.toast(f"Error: {e}")
            self.scene = SCENE_BROWSE
            return
        if os.path.exists(slideshow_copy):
            try:
                os.remove(slideshow_copy)
            except OSError:
                pass  # best-effort
        self.image_files.pop(self.current_index)
        if self.image_files:
            # Stay on the same index if possible, else step back one
            self.current_index = min(self.current_index, len(self.image_files) - 1)
            self.current_image = load_image(self.image_files[self.current_index])
        else:
            self.current_index = 0
            self.current_image = None
        self.check_in_slideshow()
        self.toast(f"Deleted  {basename}")
        self.scene = SCENE_BROWSE

    # ── Navigation ─────────────────────────────────────────────────────────

    def navigate_images(self, delta: int) -> None:
        if not self.image_files:
            return
        self.current_index = (self.current_index + delta) % len(self.image_files)
        self.current_image = load_image(self.image_files[self.current_index])
        self.check_in_slideshow()

    # ── Rename helpers ─────────────────────────────────────────────────────

    def enter_rename(self) -> None:
        if not self.image_files:
            return
        stem, ext = os.path.splitext(
            os.path.basename(self.image_files[self.current_index])
        )
        self.rename_text = stem
        self.rename_ext = ext
        self.kb_row = 0
        self.kb_col = 0
        self.rename_error = ""
        self.rename_error_timer = 0
        self.scene = SCENE_RENAME

    def do_rename(self) -> None:
        new_stem = self.rename_text.strip()
        if not new_stem:
            self.rename_error = "Name cannot be empty."
            self.rename_error_timer = 2500
            return
        old_path = self.image_files[self.current_index]
        directory = os.path.dirname(old_path)
        new_filename = new_stem + self.rename_ext
        new_path = os.path.join(directory, new_filename)
        if new_path == old_path:
            self.scene = SCENE_BROWSE
            return
        if os.path.exists(new_path):
            self.rename_error = f"'{new_filename}' already exists."
            self.rename_error_timer = 2500
            return
        try:
            os.rename(old_path, new_path)
            self.image_files[self.current_index] = new_path
            self.toast(f"Renamed to  {new_filename}")
            self.scene = SCENE_BROWSE
        except OSError as e:
            self.rename_error = str(e)
            self.rename_error_timer = 2500

    def press_kb_key(self) -> None:
        ch = KB_ROWS[self.kb_row][self.kb_col]
        if ch == "\b":
            self.rename_text = self.rename_text[:-1]
        elif ch == "\n":
            self.do_rename()
        elif ch == "\x1b":
            self.scene = SCENE_BROWSE
        else:
            self.rename_text += ch

    def move_kb(self, drow: int, dcol: int) -> None:
        if dcol != 0:
            self.kb_col = max(0, min(self.kb_col + dcol, len(KB_ROWS[self.kb_row]) - 1))
        elif drow != 0:
            new_row = max(0, min(self.kb_row + drow, len(KB_ROWS) - 1))
            if new_row != self.kb_row:
                ratio = self.kb_col / max(1, len(KB_ROWS[self.kb_row]) - 1)
                self.kb_col = round(ratio * max(1, len(KB_ROWS[new_row]) - 1))
                self.kb_row = new_row

    # ── Toast ──────────────────────────────────────────────────────────────

    def toast(self, message: str, duration: int = 2500) -> None:
        self.toast_text = message
        self.toast_timer = duration

    # ── Shutdown ───────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        pygame.quit()
        sys.exit()

    # ── Input handlers ─────────────────────────────────────────────────────

    def handle_confirm_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.scene = SCENE_BROWSE
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.confirm_choice = 1 - self.confirm_choice  # toggle between 0 and 1
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.confirm_choice == 0:
                self.do_delete()
            else:
                self.scene = SCENE_BROWSE

    def handle_browse_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.shutdown()
        elif self.browse_focus == "image":
            if event.key == pygame.K_LEFT:
                self.navigate_images(-1)
            elif event.key == pygame.K_RIGHT:
                self.navigate_images(1)
            elif event.key == pygame.K_DOWN:
                self.browse_focus = "buttons"
        elif self.browse_focus == "buttons":
            if event.key == pygame.K_LEFT:
                self.button_index = (self.button_index - 1) % len(self.buttons)
            elif event.key == pygame.K_RIGHT:
                self.button_index = (self.button_index + 1) % len(self.buttons)
            elif event.key == pygame.K_UP:
                self.browse_focus = "image"
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_button()

    def handle_rename_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.scene = SCENE_BROWSE
        elif event.key == pygame.K_RETURN:
            self.do_rename()
        elif event.key == pygame.K_BACKSPACE:
            self.rename_text = self.rename_text[:-1]
        elif event.key == pygame.K_LEFT:
            self.move_kb(0, -1)
        elif event.key == pygame.K_RIGHT:
            self.move_kb(0, 1)
        elif event.key == pygame.K_UP:
            self.move_kb(-1, 0)
        elif event.key == pygame.K_DOWN:
            self.move_kb(1, 0)
        elif event.key == pygame.K_SPACE:
            self.press_kb_key()
        elif event.unicode and event.unicode.isprintable():
            if event.unicode not in r'\/:*?"<>|':
                self.rename_text += event.unicode

    def handle_joy_button(self, event: pygame.event.Event) -> None:
        if self.scene == SCENE_CONFIRM_DELETE:
            if event.button == 0:  # A — confirm choice
                if self.confirm_choice == 0:
                    self.do_delete()
                else:
                    self.scene = SCENE_BROWSE
            elif event.button == 1:  # B — cancel
                self.scene = SCENE_BROWSE
            return
        if self.scene == SCENE_BROWSE:
            if event.button == 0:  # A / Cross — confirm
                if self.browse_focus == "buttons":
                    self._activate_button()
            elif event.button == 1:  # B / Circle — back
                self.browse_focus = "image"
        elif self.scene == SCENE_RENAME:
            if event.button == 0:  # A — press key
                self.press_kb_key()
            elif event.button == 1:  # B — cancel rename
                self.scene = SCENE_BROWSE

    def handle_joy_hat(self, event: pygame.event.Event) -> None:
        hx, hy = event.value
        if self.scene == SCENE_CONFIRM_DELETE:
            if hx != 0:
                self.confirm_choice = 1 - self.confirm_choice
            return
        if self.scene == SCENE_BROWSE:
            if self.browse_focus == "image":
                if hx == -1:
                    self.navigate_images(-1)
                elif hx == 1:
                    self.navigate_images(1)
                elif hy == -1:
                    self.browse_focus = "buttons"
            elif self.browse_focus == "buttons":
                if hx == -1:
                    self.button_index = (self.button_index - 1) % len(self.buttons)
                elif hx == 1:
                    self.button_index = (self.button_index + 1) % len(self.buttons)
                elif hy == 1:
                    self.browse_focus = "image"
        elif self.scene == SCENE_RENAME:
            if hx == -1:
                self.move_kb(0, -1)
            elif hx == 1:
                self.move_kb(0, 1)
            elif hy == 1:
                self.move_kb(-1, 0)
            elif hy == -1:
                self.move_kb(1, 0)

    def handle_axis(self) -> None:
        if not self.joysticks:
            return
        j = self.joysticks[0]
        ax = j.get_axis(0)
        ay = j.get_axis(1)
        moved = False
        if self.scene == SCENE_CONFIRM_DELETE:
            if ax < -AXIS_DEAD or ax > AXIS_DEAD:
                self.confirm_choice = 1 - self.confirm_choice
                moved = True
        elif self.scene == SCENE_BROWSE:
            if self.browse_focus == "image":
                if ax < -AXIS_DEAD:
                    self.navigate_images(-1)
                    moved = True
                elif ax > AXIS_DEAD:
                    self.navigate_images(1)
                    moved = True
                elif ay > AXIS_DEAD:
                    self.browse_focus = "buttons"
                    moved = True
            elif self.browse_focus == "buttons":
                if ax < -AXIS_DEAD:
                    self.button_index = (self.button_index - 1) % len(self.buttons)
                    moved = True
                elif ax > AXIS_DEAD:
                    self.button_index = (self.button_index + 1) % len(self.buttons)
                    moved = True
                elif ay < -AXIS_DEAD:
                    self.browse_focus = "image"
                    moved = True
        elif self.scene == SCENE_RENAME:
            if ax < -AXIS_DEAD:
                self.move_kb(0, -1)
                moved = True
            elif ax > AXIS_DEAD:
                self.move_kb(0, 1)
                moved = True
            elif ay < -AXIS_DEAD:
                self.move_kb(-1, 0)
                moved = True
            elif ay > AXIS_DEAD:
                self.move_kb(1, 0)
                moved = True
        if moved:
            self.axis_cooldown = AXIS_COOLDOWN

    def _activate_button(self) -> None:
        """Dispatch the currently selected browse button."""
        label = self.buttons[self.button_index]
        if label == "Exit":
            self.shutdown()
        elif label == "Rename":
            self.enter_rename()
        elif label == "Slideshow":
            self.toggle_slideshow()
        elif label == "Delete":
            self.enter_delete_confirm()

    # ── Draw helpers ───────────────────────────────────────────────────────

    def draw_background(self) -> None:
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(self.colors.bg)

    def draw_browse(self) -> None:
        c = self.colors
        self.draw_background()

        # Image
        if self.current_image:
            scaled = scale_to_fit(self.current_image, WINDOW_W, self.image_area_h)
            iw, ih = scaled.get_size()
            self.screen.blit(
                scaled, ((WINDOW_W - iw) // 2, (self.image_area_h - ih) // 2)
            )
        else:
            msg = self.font_large.render(
                "No images found in: " + self.screenshots_dir, True, c.text
            )
            self.screen.blit(
                msg, (WINDOW_W // 2 - msg.get_width() // 2, self.image_area_h // 2)
            )

        # HUD strip
        if self.image_files:
            strip = pygame.Surface((WINDOW_W, 30), pygame.SRCALPHA)
            strip.fill((0, 0, 0, 120))
            self.screen.blit(strip, (0, 0))
            name_s = self.font_small.render(
                os.path.basename(self.image_files[self.current_index]), True, c.text
            )
            counter_s = self.font_small.render(
                f"{self.current_index + 1} / {len(self.image_files)}", True, c.text
            )
            self.screen.blit(name_s, (10, 7))
            self.screen.blit(counter_s, (WINDOW_W - counter_s.get_width() - 10, 7))

        # Navigation hint
        if self.browse_focus == "image" and self.image_files:
            hint = self.font_small.render(
                "<  >  navigate    v  buttons", True, (110, 110, 145)
            )
            self.screen.blit(
                hint, (WINDOW_W // 2 - hint.get_width() // 2, self.image_area_h - 26)
            )

        # Bottom bar
        bar_rect = pygame.Rect(0, self.image_area_h, WINDOW_W, BAR_H)
        if self.toolbar_img:
            self.screen.blit(self.toolbar_img, (0, self.image_area_h))
        else:
            pygame.draw.rect(self.screen, c.bar, bar_rect)
        if self.browse_focus == "buttons":
            pygame.draw.rect(self.screen, c.accent, bar_rect, 2)

        total_w = len(self.buttons) * BTN_W + (len(self.buttons) - 1) * BTN_GAP
        bx0 = (WINDOW_W - total_w) // 2
        by = self.image_area_h + (BAR_H - BTN_H) // 2
        for i, label in enumerate(self.buttons):
            selected = self.browse_focus == "buttons" and i == self.button_index
            rect = pygame.Rect(bx0 + i * (BTN_W + BTN_GAP), by, BTN_W, BTN_H)
            imgs = self.button_imgs.get(label, {})

            if label == "Slideshow":
                img_key = (
                    ("on_selected" if selected else "on_normal")
                    if self.in_slideshow
                    else ("selected" if selected else "normal")
                )
                img_surf = imgs.get(img_key)
                if img_surf is not None:
                    self.screen.blit(img_surf, rect.topleft)
                else:
                    draw_slideshow_button(
                        self.screen,
                        self.font_large,
                        rect,
                        selected,
                        self.in_slideshow,
                        c,
                    )
            elif label == "Delete":
                img_key = "selected" if selected else "normal"
                img_surf = imgs.get(img_key)
                if img_surf is not None:
                    self.screen.blit(img_surf, rect.topleft)
                else:
                    color = c.key_cancel_sel if selected else c.key_cancel
                    pygame.draw.rect(self.screen, color, rect, border_radius=8)
                    if selected:
                        pygame.draw.rect(
                            self.screen, c.accent, rect, 2, border_radius=8
                        )
                    surf = self.font_large.render("Delete", True, c.btn_text)
                    self.screen.blit(
                        surf,
                        (
                            rect.x + (rect.w - surf.get_width()) // 2,
                            rect.y + (rect.h - surf.get_height()) // 2,
                        ),
                    )
            else:
                img_key = "selected" if selected else "normal"
                img_surf = imgs.get(img_key)
                if img_surf is not None:
                    self.screen.blit(img_surf, rect.topleft)
                else:
                    draw_button(self.screen, self.font_large, label, rect, selected, c)

        # Toast
        if self.toast_text:
            ts = self.font_large.render(self.toast_text, True, (255, 220, 80))
            tx = WINDOW_W // 2 - ts.get_width() // 2
            ty = self.image_area_h - 58
            bg = pygame.Surface(
                (ts.get_width() + 24, ts.get_height() + 12), pygame.SRCALPHA
            )
            bg.fill((0, 0, 0, 160))
            self.screen.blit(bg, (tx - 12, ty - 6))
            self.screen.blit(ts, (tx, ty))

    def draw_rename(self) -> None:
        c = self.colors
        self.draw_background()

        # Thumbnail
        if self.current_image:
            scaled = scale_to_fit(self.current_image, WINDOW_W, RENAME_PREVIEW_H - 10)
            iw, ih = scaled.get_size()
            self.screen.blit(
                scaled, ((WINDOW_W - iw) // 2, (RENAME_PREVIEW_H - ih) // 2)
            )

        # "Renaming: original_name" label
        orig = (
            os.path.basename(self.image_files[self.current_index])
            if self.image_files
            else ""
        )
        label_s = self.font_small.render(f"Renaming:  {orig}", True, c.dim)
        self.screen.blit(
            label_s, (WINDOW_W // 2 - label_s.get_width() // 2, RENAME_LABEL_Y)
        )

        # Input field — aligned to the keyboard bounds
        input_rect = pygame.Rect(KB_X, RENAME_INPUT_Y, KB_W, RENAME_INPUT_H)
        pygame.draw.rect(self.screen, (35, 35, 55), input_rect, border_radius=8)
        pygame.draw.rect(self.screen, c.accent, input_rect, 2, border_radius=8)

        # Blinking cursor
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        stem_s = self.font_large.render(self.rename_text + cursor, True, c.btn_text)
        ext_s = self.font_small.render(self.rename_ext, True, c.dim)
        text_x = input_rect.x + 14
        text_y = input_rect.y + (RENAME_INPUT_H - stem_s.get_height()) // 2
        self.screen.blit(stem_s, (text_x, text_y))
        self.screen.blit(
            ext_s,
            (
                text_x + stem_s.get_width() + 2,
                text_y + stem_s.get_height() - ext_s.get_height(),
            ),
        )

        # Error message
        if self.rename_error:
            err_s = self.font_small.render(self.rename_error, True, (240, 80, 80))
            self.screen.blit(
                err_s,
                (
                    WINDOW_W // 2 - err_s.get_width() // 2,
                    RENAME_INPUT_Y + RENAME_INPUT_H + 4,
                ),
            )

        # Keyboard
        draw_keyboard(
            self.screen, self.font_small, self.kb_row, self.kb_col, self.colors
        )

    def draw_confirm_delete(self) -> None:
        # Draw the browse scene underneath so the user can see the image
        self.draw_browse()

        # Semi-transparent dark overlay
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))

        # Dialog box
        box_w, box_h = 560, 200
        box_x = (WINDOW_W - box_w) // 2
        box_y = (WINDOW_H - box_h) // 2 - 20
        c = self.colors
        pygame.draw.rect(
            self.screen, c.bar, (box_x, box_y, box_w, box_h), border_radius=12
        )
        pygame.draw.rect(
            self.screen,
            c.key_cancel_sel,
            (box_x, box_y, box_w, box_h),
            2,
            border_radius=12,
        )

        # Prompt text
        prompt = self.font_large.render("Delete this image?", True, c.text)
        self.screen.blit(prompt, (WINDOW_W // 2 - prompt.get_width() // 2, box_y + 24))

        # Filename
        if self.image_files:
            fname = os.path.basename(self.image_files[self.current_index])
            # Truncate long names
            max_chars = 48
            if len(fname) > max_chars:
                fname = fname[: max_chars - 1] + "…"
            name_s = self.font_small.render(fname, True, c.dim)
            self.screen.blit(
                name_s, (WINDOW_W // 2 - name_s.get_width() // 2, box_y + 62)
            )

        # Yes / No buttons
        btn_w, btn_h = 160, 50
        gap = 24
        total = btn_w * 2 + gap
        bx = (WINDOW_W - total) // 2
        by = box_y + box_h - btn_h - 24
        labels = ["Yes", "No"]
        for i, label in enumerate(labels):
            selected = self.confirm_choice == i
            rect = pygame.Rect(bx + i * (btn_w + gap), by, btn_w, btn_h)
            if i == 0:  # Yes — red tint
                color = c.key_cancel_sel if selected else c.key_cancel
            else:  # No — normal
                color = c.btn_selected if selected else c.btn_normal
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            if selected:
                pygame.draw.rect(self.screen, c.accent, rect, 2, border_radius=8)
            surf = self.font_large.render(label, True, c.btn_text)
            self.screen.blit(
                surf,
                (
                    rect.x + (rect.w - surf.get_width()) // 2,
                    rect.y + (rect.h - surf.get_height()) // 2,
                ),
            )

    # ── Main loop ──────────────────────────────────────────────────────────

    def run(self) -> None:
        while True:
            dt = self.clock.tick(60)
            self.axis_cooldown = max(0, self.axis_cooldown - dt)

            if self.toast_timer > 0:
                self.toast_timer = max(0, self.toast_timer - dt)
                if self.toast_timer == 0:
                    self.toast_text = ""

            if self.rename_error_timer > 0:
                self.rename_error_timer = max(0, self.rename_error_timer - dt)
                if self.rename_error_timer == 0:
                    self.rename_error = ""

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.shutdown()
                elif event.type == pygame.KEYDOWN:
                    if self.scene == SCENE_BROWSE:
                        self.handle_browse_key(event)
                    elif self.scene == SCENE_CONFIRM_DELETE:
                        self.handle_confirm_key(event)
                    else:
                        self.handle_rename_key(event)
                elif event.type == pygame.JOYBUTTONDOWN:
                    self.handle_joy_button(event)
                elif event.type == pygame.JOYHATMOTION:
                    self.handle_joy_hat(event)

            if self.axis_cooldown == 0:
                self.handle_axis()

            if self.scene == SCENE_BROWSE:
                self.draw_browse()
            elif self.scene == SCENE_CONFIRM_DELETE:
                self.draw_confirm_delete()
            else:
                self.draw_rename()

            pygame.display.flip()
