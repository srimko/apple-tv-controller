"""Constantes partagees pour Apple TV Controller."""

from __future__ import annotations

# Swipe gestures: (start_x, start_y, end_x, end_y, duration_ms)
# Coordonnees de 0 (haut/gauche) a 1000 (bas/droite)
SWIPE_GESTURES: dict[str, tuple[int, int, int, int, int]] = {
    "swipe_up": (500, 700, 500, 300, 300),
    "swipe_down": (500, 300, 500, 700, 300),
    "swipe_left": (700, 500, 300, 500, 300),
    "swipe_right": (300, 500, 700, 500, 300),
}

# Actions de navigation
NAV_ACTIONS = frozenset({"up", "down", "left", "right", "select", "menu", "home", "home_double"})

# Actions de lecture
PLAY_ACTIONS = frozenset({"play", "pause", "play_pause", "stop", "next", "previous"})

# Toutes les actions swipe
SWIPE_ACTIONS = frozenset(SWIPE_GESTURES.keys())
