"""Commandes CLI."""

from .config import router as config_router
from .control import router as control_router
from .help import router as help_router
from .scenarios import router as scenarios_router
from .server import router as server_router

__all__ = [
    "config_router",
    "control_router",
    "help_router",
    "scenarios_router",
    "server_router",
]
