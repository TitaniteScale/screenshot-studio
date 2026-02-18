import os

import pygame

from constants import SUPPORTED_EXTS


def get_image_files(directory: str) -> list[str]:
    """Return a sorted list of supported image paths in directory."""
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


def load_image(path: str) -> pygame.Surface | None:
    """Load an image from disk and convert it for blitting. Returns None on failure."""
    try:
        return pygame.image.load(path).convert()
    except Exception as e:
        print(f"Error loading '{path}': {e}")
        return None


def load_asset(
    path: str, script_dir: str, scale: tuple[int, int] | None = None
) -> pygame.Surface | None:
    """Load an image asset (with alpha), optionally scaling it. Returns None on failure."""
    if not path:
        return None
    if not os.path.isabs(path):
        path = os.path.join(script_dir, path)
    try:
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.smoothscale(img, scale)
        return img
    except Exception as e:
        print(f"Could not load asset '{path}': {e}")
        return None


def scale_to_fit(img: pygame.Surface, area_w: int, area_h: int) -> pygame.Surface:
    """Scale img down (or up) to fit within area_w x area_h, preserving aspect ratio."""
    iw, ih = img.get_size()
    scale = min(area_w / iw, area_h / ih)
    return pygame.transform.smoothscale(img, (int(iw * scale), int(ih * scale)))
