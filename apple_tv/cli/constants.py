"""Constantes partagees pour le CLI."""

from __future__ import annotations

# Re-exporter les constantes du package principal
from ..constants import NAV_ACTIONS, PLAY_ACTIONS, SWIPE_ACTIONS, SWIPE_GESTURES

# Styles questionary
QUESTIONARY_STYLE = [
    ("selected", "fg:green bold"),
    ("pointer", "fg:green bold"),
]

__all__ = [
    "NAV_ACTIONS",
    "PLAY_ACTIONS",
    "QUESTIONARY_STYLE",
    "SWIPE_ACTIONS",
    "SWIPE_GESTURES",
]
