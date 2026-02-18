import os
from dataclasses import dataclass
from typing import cast

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from constants import (
    DEFAULT_ACCENT,
    DEFAULT_BAR_COLOR,
    DEFAULT_BG_COLOR,
    DEFAULT_BTN_NORMAL,
    DEFAULT_BTN_SELECTED,
    DEFAULT_BTN_TEXT,
    DEFAULT_DIM_COLOR,
    DEFAULT_KEY_CANCEL,
    DEFAULT_KEY_CANCEL_SEL,
    DEFAULT_KEY_CONFIRM,
    DEFAULT_KEY_CONFIRM_SEL,
    DEFAULT_KEY_SPECIAL,
    DEFAULT_KEY_SPECIAL_SEL,
    DEFAULT_TEXT_COLOR,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.toml")

DEFAULT_CONFIG = {
    "settings": {
        "screenshots_dir": "screenshots",
        "slideshow_dir": "slideshow",
        "fullscreen": False,
    }
}


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert a '#rrggbb' string to an (r, g, b) tuple."""
    h = hex_str.strip().lstrip("#")
    return cast(tuple[int, int, int], tuple(int(h[i : i + 2], 16) for i in (0, 2, 4)))


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    return DEFAULT_CONFIG


@dataclass
class Colors:
    bg: tuple
    bar: tuple
    btn_normal: tuple
    btn_selected: tuple
    btn_text: tuple
    text: tuple
    accent: tuple
    dim: tuple
    key_confirm: tuple
    key_confirm_sel: tuple
    key_cancel: tuple
    key_cancel_sel: tuple
    key_special: tuple
    key_special_sel: tuple


def build_colors(config: dict) -> Colors:
    """Build a Colors instance from config, falling back to defaults for any missing keys."""
    cfg = config.get("colors", {})

    def get(key, default):
        if key in cfg:
            try:
                return hex_to_rgb(cfg[key])
            except Exception as e:
                print(f"Invalid color for '{key}': {e}")
        return default

    return Colors(
        bg=get("bg", DEFAULT_BG_COLOR),
        bar=get("bar", DEFAULT_BAR_COLOR),
        btn_normal=get("btn_normal", DEFAULT_BTN_NORMAL),
        btn_selected=get("btn_selected", DEFAULT_BTN_SELECTED),
        btn_text=get("btn_text", DEFAULT_BTN_TEXT),
        text=get("text", DEFAULT_TEXT_COLOR),
        accent=get("accent", DEFAULT_ACCENT),
        dim=get("dim", DEFAULT_DIM_COLOR),
        key_confirm=get("key_confirm", DEFAULT_KEY_CONFIRM),
        key_confirm_sel=get("key_confirm_sel", DEFAULT_KEY_CONFIRM_SEL),
        key_cancel=get("key_cancel", DEFAULT_KEY_CANCEL),
        key_cancel_sel=get("key_cancel_sel", DEFAULT_KEY_CANCEL_SEL),
        key_special=get("key_special", DEFAULT_KEY_SPECIAL),
        key_special_sel=get("key_special_sel", DEFAULT_KEY_SPECIAL_SEL),
    )
