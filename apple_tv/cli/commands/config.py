"""Commandes de configuration."""

from __future__ import annotations

from typing import Optional

import questionary
import typer

from ...config import (
    CONFIG_FILE,
    CREDENTIALS_FILE,
    get_default_device,
    load_json,
    set_default_device,
)
from ...connection import pair_device, scan_devices
from ..console import console, create_spinner, create_table, print_error, print_panel, print_success
from ..constants import QUESTIONARY_STYLE
from ..utils import require_device, resolve_device_name, run_async

router = typer.Typer()


@router.command("config")
def config_cmd(
    default_device: Optional[str] = typer.Option(
        None, "--default", "-d",
        help="Definir le device par defaut",
        envvar="ATV_DEFAULT_DEVICE",
    ),
    show: bool = typer.Option(False, "--show", "-s", help="Afficher la configuration"),
):
    """
    ⚙️  Configurer les parametres par defaut.
    """
    if show or (not default_device):
        current_default = get_default_device()
        console.print()
        console.print("[bold]Configuration actuelle:[/bold]")
        console.print(f"  Device par defaut: [cyan]{current_default or '(non defini)'}[/cyan]")
        console.print(f"\n[dim]Fichier: {CONFIG_FILE}[/dim]")

        if not default_device:
            return

    if default_device:
        devices = run_async(scan_devices())
        device_names = [d.name for d in devices]

        if default_device not in device_names:
            print_error(f"Device '{default_device}' non trouve")
            console.print(f"[dim]Devices disponibles: {', '.join(device_names)}[/dim]")
            raise typer.Exit(1)

        set_default_device(default_device)
        print_success(f"Device par defaut: [cyan]{default_device}[/cyan]")


@router.command("setup")
def setup_cmd():
    """
    🔧 Assistant de configuration interactif.

    Recherche les Apple TV sur le reseau et guide l'appairage.
    """
    console.print()
    print_panel("🍎 Apple TV Controller", "Assistant de configuration")
    console.print()

    # Scan des appareils
    with create_spinner() as progress:
        progress.add_task("Recherche des Apple TV sur le reseau...", total=None)
        devices = run_async(scan_devices())

    if not devices:
        print_error("Aucune Apple TV trouvee sur le reseau.")
        console.print()
        console.print("[dim]Verifiez que :[/dim]")
        console.print("  • L'Apple TV est allumee")
        console.print("  • Vous etes sur le meme reseau Wi-Fi")
        console.print("  • Le pare-feu ne bloque pas la connexion")
        raise typer.Exit(1)

    print_success(f"{len(devices)} Apple TV trouvee(s)\n")

    # Selection de l'appareil
    device_choices = [
        questionary.Choice(
            title=f"{d.name or f'Apple TV {i}'} ({d.address})",
            value=d
        )
        for i, d in enumerate(devices)
    ]

    selected = questionary.select(
        "Quelle Apple TV voulez-vous configurer ?",
        choices=device_choices,
        style=questionary.Style(QUESTIONARY_STYLE)
    ).ask()

    if not selected:
        raise typer.Exit(0)

    # Verifier si deja appaire
    credentials = load_json(CREDENTIALS_FILE)
    device_id = str(selected.identifier)

    if device_id in credentials:
        console.print(f"\n[yellow]![/yellow] {selected.name} est deja appaire.")
        if not questionary.confirm("Voulez-vous re-appairer ?", default=False).ask():
            print_success("Configuration terminee.")
            raise typer.Exit(0)

    # Appairage
    console.print(f"\n[bold]Appairage avec {selected.name}...[/bold]")
    console.print("[dim]Un code PIN va s'afficher sur votre TV[/dim]\n")

    try:
        run_async(pair_device(selected))
        print_success(f"Appairage reussi avec [bold]{selected.name}[/bold]")
    except Exception as e:
        print_error(f"Erreur d'appairage: {e}")
        raise typer.Exit(1)

    # Proposer de definir comme defaut
    console.print()
    if questionary.confirm("Definir comme device par defaut ?", default=True).ask():
        set_default_device(selected.name)
        print_success(f"Device par defaut: [cyan]{selected.name}[/cyan]")

    # Test de connexion
    console.print()
    if questionary.confirm("Tester la connexion maintenant ?", default=True).ask():
        test_connection_impl(selected.name)


@router.command("scan")
def scan_cmd():
    """
    🔍 Rechercher les Apple TV sur le reseau.
    """
    console.print()

    with create_spinner() as progress:
        progress.add_task("Recherche des Apple TV...", total=None)
        devices = run_async(scan_devices())

    if not devices:
        console.print("[yellow]![/yellow] Aucune Apple TV trouvee")
        raise typer.Exit(0)

    rows = [
        [
            str(i),
            d.name or "-",
            str(d.address),
            ", ".join(str(s.protocol.name) for s in d.services),
        ]
        for i, d in enumerate(devices)
    ]

    table = create_table(
        f"{len(devices)} Apple TV trouvee(s)",
        [
            ("#", {"style": "dim", "width": 3}),
            ("Nom", {"style": "cyan"}),
            ("Adresse IP", {}),
            ("Protocoles", {}),
        ],
        rows,
    )
    console.print(table)


@router.command("test")
def test_cmd(
    device: Optional[str] = typer.Argument(
        None,
        help="Nom de l'Apple TV",
        envvar="ATV_DEVICE",
    ),
):
    """
    🧪 Tester la connexion a une Apple TV.
    """
    test_connection_impl(device)


def test_connection_impl(device_name: Optional[str] = None):
    """Implementation du test de connexion."""
    from ..operations import get_power_state

    console.print()

    with create_spinner() as progress:
        progress.add_task("Recherche...", total=None)
        devices = run_async(scan_devices())

    if not devices:
        print_error("Aucune Apple TV trouvee")
        raise typer.Exit(1)

    resolved_name = resolve_device_name(device_name, devices)
    if not resolved_name:
        raise typer.Exit(0)

    from ...connection import select_device
    device = select_device(devices, resolved_name)

    console.print(f"Test de connexion a [cyan]{device.name}[/cyan]...")

    try:
        with create_spinner() as progress:
            progress.add_task("Connexion...", total=None)
            power_state = run_async(get_power_state(device))

        print_success("Connexion reussie")
        console.print(f"  Etat: {'Allumee' if power_state else 'En veille'}")

    except Exception as e:
        print_error(f"Echec de connexion: {e}")
        raise typer.Exit(1)
