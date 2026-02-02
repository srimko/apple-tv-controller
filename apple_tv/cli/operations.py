"""Operations async sur l'Apple TV."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Optional

from ..apps import launch_app as _launch_app
from ..connection import connect_atv
from ..constants import SWIPE_GESTURES
from ..scenarios import run_scenario as _run_scenario

if TYPE_CHECKING:
    from pyatv.conf import AppleTV


async def get_power_state(device: "AppleTV") -> bool:
    """Recupere l'etat d'alimentation."""
    async with connect_atv(device) as atv:
        return atv.power.power_state


async def wake_device(device: "AppleTV") -> None:
    """Allume l'Apple TV."""
    async with connect_atv(device) as atv:
        await atv.power.turn_on()


async def sleep_device(device: "AppleTV") -> None:
    """Met l'Apple TV en veille."""
    async with connect_atv(device) as atv:
        await atv.power.turn_off()


async def launch_app(device: "AppleTV", app_name: str) -> None:
    """Lance une application."""
    async with connect_atv(device) as atv:
        await _launch_app(atv, app_name)


async def run_scenario(device: "AppleTV", scenario_name: str) -> bool:
    """Execute un scenario."""
    async with connect_atv(device) as atv:
        return await _run_scenario(atv, scenario_name)


async def get_device_status(device: "AppleTV") -> dict[str, Any]:
    """Recupere l'etat complet de l'Apple TV."""
    async with connect_atv(device) as atv:
        power_state = atv.power.power_state
        playing = await atv.metadata.playing()

        return {
            "power": power_state,
            "app": getattr(playing, "app_identifier", None) if playing else None,
            "title": getattr(playing, "title", None) if playing else None,
            "artist": getattr(playing, "artist", None) if playing else None,
            "state": str(playing.device_state) if playing else None,
        }


async def execute_remote_action(atv, action: str) -> None:
    """Execute une action de telecommande."""
    if action == "home_double":
        await atv.remote_control.home()
        await asyncio.sleep(0.15)
        await atv.remote_control.home()
    elif action == "up":
        await atv.remote_control.up()
    elif action == "down":
        await atv.remote_control.down()
    elif action == "left":
        await atv.remote_control.left()
    elif action == "right":
        await atv.remote_control.right()
    elif action == "select":
        await atv.remote_control.select()
    elif action == "menu":
        await atv.remote_control.menu()
    elif action == "home":
        await atv.remote_control.home()
    elif action in SWIPE_GESTURES:
        start_x, start_y, end_x, end_y, duration = SWIPE_GESTURES[action]
        await atv.touch.swipe(start_x, start_y, end_x, end_y, duration)
