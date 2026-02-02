"""Commandes de controle."""

from __future__ import annotations

from typing import Optional

import typer

from ...apps import list_apps as _list_apps, sync_apps_config
from ...config import setup_logging
from ...connection import connect_atv
from ..console import console, create_spinner, print_error, print_panel, print_success
from ..operations import get_device_status, launch_app, sleep_device, wake_device
from ..utils import require_device, run_async

router = typer.Typer()


@router.command("wake")
def wake_cmd(
    device: Optional[str] = typer.Option(
        None, "-d", "--device",
        help="Nom de l'Apple TV",
        envvar="ATV_DEVICE",
    ),
):
    """
    🔆 Allumer l'Apple TV.
    """
    with require_device(device) as selected:
        try:
            run_async(wake_device(selected))
            print_success(f"{selected.name} allumee")
        except Exception as e:
            print_error(f"Erreur: {e}")
            raise typer.Exit(1)


@router.command("sleep")
def sleep_cmd(
    device: Optional[str] = typer.Option(
        None, "-d", "--device",
        help="Nom de l'Apple TV",
        envvar="ATV_DEVICE",
    ),
):
    """
    🌙 Eteindre l'Apple TV (veille).
    """
    with require_device(device) as selected:
        try:
            run_async(sleep_device(selected))
            print_success(f"{selected.name} en veille")
        except Exception as e:
            print_error(f"Erreur: {e}")
            raise typer.Exit(1)


@router.command("launch")
def launch_cmd(
    app_name: str = typer.Argument(..., help="Nom ou bundle ID de l'application"),
    device: Optional[str] = typer.Option(
        None, "-d", "--device",
        help="Nom de l'Apple TV",
        envvar="ATV_DEVICE",
    ),
):
    """
    🚀 Lancer une application.
    """
    with require_device(device) as selected:
        try:
            run_async(launch_app(selected, app_name))
            print_success(f"{app_name} lance sur {selected.name}")
        except Exception as e:
            print_error(f"Erreur: {e}")
            raise typer.Exit(1)


@router.command("status")
def status_cmd(
    device: Optional[str] = typer.Option(
        None, "-d", "--device",
        help="Nom de l'Apple TV",
        envvar="ATV_DEVICE",
    ),
):
    """
    📊 Afficher l'etat de l'Apple TV.
    """
    with require_device(device) as selected:
        try:
            with create_spinner() as progress:
                progress.add_task("Connexion...", total=None)
                info = run_async(get_device_status(selected))

            console.print()
            print_panel(selected.name, border_style="cyan")

            # Power
            power_icon = "🟢" if info["power"] else "🔴"
            power_text = "Allumee" if info["power"] else "En veille"
            console.print(f"  {power_icon} Etat: [bold]{power_text}[/bold]")

            # App
            if info["app"]:
                console.print(f"  📱 App: [cyan]{info['app']}[/cyan]")

            # Lecture
            if info["title"]:
                console.print(f"  🎬 Titre: {info['title']}")
            if info["artist"]:
                console.print(f"  🎤 Artiste: {info['artist']}")
            if info["state"]:
                state_clean = info["state"].replace("DeviceState.", "")
                console.print(f"  ▶️  Etat: {state_clean}")

            console.print()

        except Exception as e:
            print_error(f"Erreur: {e}")
            raise typer.Exit(1)


@router.command("apps")
def apps_cmd(
    device: Optional[str] = typer.Option(
        None, "-d", "--device",
        help="Nom de l'Apple TV",
        envvar="ATV_DEVICE",
    ),
    sync: bool = typer.Option(False, "--sync", help="Synchroniser apps.json"),
):
    """
    📱 Lister les applications installees.
    """
    setup_logging()

    with require_device(device) as selected:
        try:
            async def get_apps():
                async with connect_atv(selected) as atv:
                    if sync:
                        await sync_apps_config(atv)
                        print_success("apps.json synchronise")
                    else:
                        await _list_apps(atv)

            run_async(get_apps())

        except Exception as e:
            print_error(f"Erreur: {e}")
            raise typer.Exit(1)
