# ── Window ─────────────────────────────────────────────────────────────────
WINDOW_W = 1280
WINDOW_H = 720

# ── Browse scene constants ──────────────────────────────────────────────────
BAR_H = 80
BTN_W = 180
BTN_H = 56
BTN_GAP = 20

# ── Rename scene / keyboard constants ──────────────────────────────────────
RENAME_PREVIEW_H = 240  # height of the thumbnail area
RENAME_LABEL_Y = 248  # y of "Renaming: …" label
RENAME_INPUT_Y = 278  # y of the text-input field
RENAME_INPUT_H = 54  # height of the text-input field
KB_Y = 344  # y of top of keyboard
KB_X = 90  # left edge of keyboard
KB_W = 1100  # total keyboard width
KEY_H = 56  # height of every key
KEY_GAP = 8  # gap between keys (both axes)

# Rows: plain chars = append to name; special tokens handled by App.press_kb_key()
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

# ── File support ────────────────────────────────────────────────────────────
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

# ── Gamepad ─────────────────────────────────────────────────────────────────
AXIS_DEAD = 0.5
AXIS_COOLDOWN = 200  # ms between axis-driven navigation steps

# ── Scenes ──────────────────────────────────────────────────────────────────
SCENE_BROWSE = "browse"
SCENE_RENAME = "rename"
SCENE_CONFIRM_DELETE = "confirm_delete"

# ── Default colour palette (Everforest Dark Medium) ─────────────────────────
# All of these are overridable via [colors] in config.toml.
DEFAULT_BG_COLOR = (20, 20, 30)
DEFAULT_BAR_COLOR = (30, 30, 45)
DEFAULT_BTN_NORMAL = (50, 50, 70)
DEFAULT_BTN_SELECTED = (60, 100, 180)
DEFAULT_BTN_TEXT = (220, 220, 220)
DEFAULT_TEXT_COLOR = (180, 180, 200)
DEFAULT_ACCENT = (100, 160, 255)
DEFAULT_DIM_COLOR = (100, 100, 130)
DEFAULT_KEY_CONFIRM = (35, 100, 55)
DEFAULT_KEY_CONFIRM_SEL = (55, 160, 85)
DEFAULT_KEY_CANCEL = (110, 35, 35)
DEFAULT_KEY_CANCEL_SEL = (170, 55, 55)
DEFAULT_KEY_SPECIAL = (70, 55, 40)
DEFAULT_KEY_SPECIAL_SEL = (130, 100, 60)
