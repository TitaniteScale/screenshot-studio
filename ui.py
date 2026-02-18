import pygame

from config import Colors
from constants import (
    KB_LABELS,
    KB_ROWS,
    KB_W,
    KB_X,
    KB_Y,
    KEY_GAP,
    KEY_H,
)


def get_key_rect(row: int, col: int) -> pygame.Rect:
    """Return the pygame.Rect for a key at (row, col)."""
    n = len(KB_ROWS[row])
    key_w = (KB_W - (n - 1) * KEY_GAP) / n
    x = KB_X + col * (key_w + KEY_GAP)
    y = KB_Y + row * (KEY_H + KEY_GAP)
    return pygame.Rect(int(x), int(y), int(key_w), KEY_H)


def key_colors(ch: str, colors: Colors) -> tuple[tuple, tuple]:
    """Return (normal_color, selected_color) for a key character."""
    if ch == "\n":
        return colors.key_confirm, colors.key_confirm_sel
    if ch == "\x1b":
        return colors.key_cancel, colors.key_cancel_sel
    if ch in (" ", "\b", "-", "_", "."):
        return colors.key_special, colors.key_special_sel
    return colors.btn_normal, colors.btn_selected


def draw_button(
    screen: pygame.Surface,
    font: pygame.font.Font,
    label: str,
    rect: pygame.Rect,
    selected: bool,
    colors: Colors,
) -> None:
    """Draw a standard labelled button with selection highlight."""
    color = colors.btn_selected if selected else colors.btn_normal
    pygame.draw.rect(screen, color, rect, border_radius=8)
    if selected:
        pygame.draw.rect(screen, colors.accent, rect, 2, border_radius=8)
    surf = font.render(label, True, colors.btn_text)
    screen.blit(
        surf,
        (
            rect.x + (rect.w - surf.get_width()) // 2,
            rect.y + (rect.h - surf.get_height()) // 2,
        ),
    )


def draw_slideshow_button(
    screen: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    selected: bool,
    in_slideshow: bool,
    colors: Colors,
) -> None:
    """Draw the slideshow toggle button with green tint when active."""
    if in_slideshow:
        color = colors.key_confirm_sel if selected else colors.key_confirm
        pygame.draw.rect(screen, color, rect, border_radius=8)
        if selected:
            pygame.draw.rect(screen, colors.accent, rect, 2, border_radius=8)
        surf = font.render("★ Slideshow", True, colors.btn_text)
    else:
        color = colors.btn_selected if selected else colors.btn_normal
        pygame.draw.rect(screen, color, rect, border_radius=8)
        if selected:
            pygame.draw.rect(screen, colors.accent, rect, 2, border_radius=8)
        surf = font.render("+ Slideshow", True, colors.btn_text)
    screen.blit(
        surf,
        (
            rect.x + (rect.w - surf.get_width()) // 2,
            rect.y + (rect.h - surf.get_height()) // 2,
        ),
    )


def draw_keyboard(
    screen: pygame.Surface,
    font: pygame.font.Font,
    kb_row: int,
    kb_col: int,
    colors: Colors,
) -> None:
    """Draw the on-screen keyboard with the current key highlighted."""
    for row_i, row in enumerate(KB_ROWS):
        for col_i, ch in enumerate(row):
            rect = get_key_rect(row_i, col_i)
            selected = row_i == kb_row and col_i == kb_col
            normal, hi = key_colors(ch, colors)
            color = hi if selected else normal
            pygame.draw.rect(screen, color, rect, border_radius=6)
            if selected:
                pygame.draw.rect(screen, colors.accent, rect, 2, border_radius=6)
            lbl = KB_LABELS.get(ch, ch.upper())
            ls = font.render(lbl, True, colors.btn_text)
            screen.blit(
                ls,
                (
                    rect.x + (rect.w - ls.get_width()) // 2,
                    rect.y + (rect.h - ls.get_height()) // 2,
                ),
            )
