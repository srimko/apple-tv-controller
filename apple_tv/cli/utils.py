"""Utilitaires pour le CLI."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator, Optional

import questionary
import typer

from ..config import get_default_device
from ..connection import scan_devices, select_device
from .console import console

if TYPE_CHECKING:
    from pyatv.conf import AppleTV


def run_async(coro):
    """Execute une coroutine de maniere synchrone."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        return asyncio.run(coro)
    else:
        return loop.run_until_complete(coro)


def resolve_device_name(device: Optional[str], devices: list["AppleTV"]) -> Optional[str]:
    """Resout le nom du device a utiliser.

    Args:
        device: Nom specifie ou None
        devices: Liste des devices disponibles

    Returns:
        Nom du device resolu ou None si annule
    """
    # Si specifie, l'utiliser
    if device:
        return device

    # Sinon, essayer le device par defaut
    default = get_default_device()
    if default:
        device_names = [d.name for d in devices]
        if default in device_names:
            console.print(f"[dim]Device par defaut: {default}[/dim]")
            return default

    # Sinon, selection interactive
    if len(devices) == 1:
        return devices[0].name

    device_choices = [d.name for d in devices]
    choice = questionary.select(
        "Quelle Apple TV ?",
        choices=device_choices
    ).ask()
    return choice


@contextmanager
def require_device(
    device: Optional[str] = None,
) -> Generator["AppleTV", None, None]:
    """Context manager pour obtenir un device.

    Gere le scan, la resolution et la selection du device.
    Leve typer.Exit en cas d'erreur.

    Args:
        device: Nom du device (optionnel)

    Yields:
        Le device AppleTV selectionne

    Example:
        with require_device(device_name) as selected:
            # utiliser selected
    """
    devices = run_async(scan_devices())

    if not devices:
        console.print("[red]✗[/red] Aucune Apple TV trouvee")
        raise typer.Exit(1)

    resolved_name = resolve_device_name(device, devices)
    if not resolved_name:
        raise typer.Exit(0)

    yield select_device(devices, resolved_name)
