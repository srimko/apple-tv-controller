"""Controles Apple TV (alimentation, lecture, telecommande, volume)."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Optional

from pyatv.const import FeatureName, FeatureState
from pyatv.interface import AppleTV

from .config import OPERATION_TIMEOUT, logger
from .connection import require_feature
from .exceptions import FeatureNotAvailableError


# =============================================================================
# CONTROLES ALIMENTATION
# =============================================================================


async def get_power_status(atv: AppleTV) -> str:
    """Retourne l'etat d'alimentation."""
    features = atv.features

    power_available = features.in_state(FeatureState.Available, FeatureName.PowerState)
    turn_on_available = features.in_state(FeatureState.Available, FeatureName.TurnOn)
    turn_off_available = features.in_state(FeatureState.Available, FeatureName.TurnOff)

    logger.info("Fonctionnalites disponibles:")
    logger.info(f"  - PowerState: {'Oui' if power_available else 'Non'}")
    logger.info(f"  - TurnOn:     {'Oui' if turn_on_available else 'Non'}")
    logger.info(f"  - TurnOff:    {'Oui' if turn_off_available else 'Non'}")
    logger.info("")

    if power_available:
        state = atv.power.power_state
        logger.info(f"Etat: {state.name}")
        return state.name
    return "Unknown"


@require_feature(FeatureName.TurnOn)
async def turn_on(atv: AppleTV) -> None:
    """Allume l'Apple TV."""
    logger.info("Allumage...")
    await asyncio.wait_for(
        atv.power.turn_on(await_new_state=True), timeout=OPERATION_TIMEOUT
    )
    logger.info("Apple TV allumee!")


@require_feature(FeatureName.TurnOff)
async def turn_off(atv: AppleTV) -> None:
    """Eteint l'Apple TV."""
    logger.info("Extinction...")
    await asyncio.wait_for(
        atv.power.turn_off(await_new_state=True), timeout=OPERATION_TIMEOUT
    )
    logger.info("Apple TV eteinte!")


# =============================================================================
# CONTROLES LECTURE
# =============================================================================


async def cmd_play(atv: AppleTV) -> None:
    """Lance la lecture."""
    if atv.features.in_state(FeatureState.Available, FeatureName.Play):
        await atv.remote_control.play()
    elif atv.features.in_state(FeatureState.Available, FeatureName.PlayPause):
        await atv.remote_control.play_pause()
        logger.info("(via PlayPause)")
    else:
        raise FeatureNotAvailableError("Play non disponible")
    logger.info("Lecture lancee!")


async def cmd_pause(atv: AppleTV) -> None:
    """Met en pause."""
    if atv.features.in_state(FeatureState.Available, FeatureName.Pause):
        await atv.remote_control.pause()
    elif atv.features.in_state(FeatureState.Available, FeatureName.PlayPause):
        await atv.remote_control.play_pause()
        logger.info("(via PlayPause)")
    else:
        raise FeatureNotAvailableError("Pause non disponible")
    logger.info("Pause!")


@require_feature(FeatureName.PlayPause)
async def cmd_play_pause(atv: AppleTV) -> None:
    """Toggle lecture/pause."""
    await atv.remote_control.play_pause()
    logger.info("Toggle lecture/pause!")


@require_feature(FeatureName.Stop)
async def cmd_stop(atv: AppleTV) -> None:
    """Arrete la lecture."""
    await atv.remote_control.stop()
    logger.info("Arret!")


async def cmd_next(atv: AppleTV) -> None:
    """Piste suivante."""
    try:
        await atv.remote_control.next()
        logger.info("Suivant!")
    except Exception as e:
        raise FeatureNotAvailableError(f"Next non disponible: {e}")


async def cmd_previous(atv: AppleTV) -> None:
    """Piste precedente."""
    try:
        await atv.remote_control.previous()
        logger.info("Precedent!")
    except Exception as e:
        raise FeatureNotAvailableError(f"Previous non disponible: {e}")


# =============================================================================
# CONTROLES TELECOMMANDE
# =============================================================================


class RemoteButton(Enum):
    """Boutons de la telecommande."""

    UP = ("up", FeatureName.Up, "^")
    DOWN = ("down", FeatureName.Down, "v")
    LEFT = ("left", FeatureName.Left, "<")
    RIGHT = ("right", FeatureName.Right, ">")
    SELECT = ("select", FeatureName.Select, "o")
    MENU = ("menu", FeatureName.Menu, "M")
    HOME = ("home", FeatureName.Home, "H")

    def __init__(self, cmd: str, feature: FeatureName, symbol: str):
        self.cmd = cmd
        self.feature = feature
        self.symbol = symbol


async def press_button(atv: AppleTV, button: RemoteButton) -> None:
    """Appuie sur un bouton de la telecommande."""
    if not atv.features.in_state(FeatureState.Available, button.feature):
        raise FeatureNotAvailableError(f"Bouton {button.cmd} non disponible")

    method = getattr(atv.remote_control, button.cmd)
    await method()
    logger.info(f"{button.symbol} {button.cmd.capitalize()}")


# =============================================================================
# CONTROLES VOLUME
# =============================================================================


@require_feature(FeatureName.VolumeUp)
async def volume_up(atv: AppleTV) -> None:
    """Augmente le volume."""
    await atv.audio.volume_up()
    logger.info("Volume +")


@require_feature(FeatureName.VolumeDown)
async def volume_down(atv: AppleTV) -> None:
    """Baisse le volume."""
    await atv.audio.volume_down()
    logger.info("Volume -")


@require_feature(FeatureName.SetVolume)
async def set_volume(atv: AppleTV, level: int) -> None:
    """Regle le volume (0-100)."""
    level = max(0, min(100, level))
    await atv.audio.set_volume(level)
    logger.info(f"Volume: {level}%")


async def get_volume(atv: AppleTV) -> Optional[float]:
    """Retourne le volume actuel."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Volume):
        raise FeatureNotAvailableError("Volume non disponible")
    volume = atv.audio.volume
    logger.info(f"Volume: {volume}%")
    return volume
