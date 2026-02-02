"""CLI interactive pour Apple TV Controller."""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

import questionary
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import (
    CREDENTIALS_FILE,
    SCENARIOS_FILE,
    logger,
    setup_logging,
    load_json,
)
from .connection import scan_devices, select_device, pair_device, connect_atv
from .scenarios import load_scenarios, run_scenario, show_scenarios
from .apps import list_apps, sync_apps_config

# Console Rich pour l'affichage
console = Console()

# Application Typer
app = typer.Typer(
    name="atv",
    help="🍎 Apple TV Controller - Controlez votre Apple TV depuis le terminal",
    add_completion=False,
    no_args_is_help=True,
)


def run_async(coro):
    """Execute une coroutine de maniere synchrone."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# COMMANDE: setup
# =============================================================================

@app.command()
def setup():
    """
    🔧 Assistant de configuration interactif.

    Recherche les Apple TV sur le reseau et guide l'appairage.
    """
    console.print()
    console.print(Panel.fit(
        "[bold blue]🍎 Apple TV Controller[/bold blue]\n"
        "[dim]Assistant de configuration[/dim]",
        border_style="blue"
    ))
    console.print()

    # Scan des appareils
    devices = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Recherche des Apple TV sur le reseau...", total=None)
        devices = run_async(scan_devices())

    if not devices:
        console.print("[red]✗[/red] Aucune Apple TV trouvee sur le reseau.")
        console.print()
        console.print("[dim]Verifiez que :[/dim]")
        console.print("  • L'Apple TV est allumee")
        console.print("  • Vous etes sur le meme reseau Wi-Fi")
        console.print("  • Le pare-feu ne bloque pas la connexion")
        raise typer.Exit(1)

    # Afficher les appareils trouves
    console.print(f"[green]✓[/green] {len(devices)} Apple TV trouvee(s)\n")

    # Selection de l'appareil
    device_choices = []
    for i, device in enumerate(devices):
        name = device.name or f"Apple TV {i}"
        address = device.address
        device_choices.append(questionary.Choice(
            title=f"{name} ({address})",
            value=device
        ))

    selected = questionary.select(
        "Quelle Apple TV voulez-vous configurer ?",
        choices=device_choices,
        style=questionary.Style([
            ("selected", "fg:green bold"),
            ("pointer", "fg:green bold"),
        ])
    ).ask()

    if not selected:
        raise typer.Exit(0)

    # Verifier si deja appaire
    credentials = load_json(CREDENTIALS_FILE)
    device_id = str(selected.identifier)

    if device_id in credentials:
        console.print(f"\n[yellow]![/yellow] {selected.name} est deja appaire.")
        if not questionary.confirm("Voulez-vous re-appairer ?", default=False).ask():
            console.print("[green]✓[/green] Configuration terminee.")
            raise typer.Exit(0)

    # Appairage
    console.print(f"\n[bold]Appairage avec {selected.name}...[/bold]")
    console.print("[dim]Un code PIN va s'afficher sur votre TV[/dim]\n")

    try:
        run_async(pair_device(selected))
        console.print(f"\n[green]✓[/green] Appairage reussi avec [bold]{selected.name}[/bold]")
    except Exception as e:
        console.print(f"\n[red]✗[/red] Erreur d'appairage: {e}")
        raise typer.Exit(1)

    # Test de connexion
    console.print()
    if questionary.confirm("Tester la connexion maintenant ?", default=True).ask():
        test_connection(selected.name)


# =============================================================================
# COMMANDE: run
# =============================================================================

@app.command()
def run(
    scenario_name: Optional[str] = typer.Argument(None, help="Nom du scenario a executer"),
    device: Optional[str] = typer.Option(None, "-d", "--device", help="Nom de l'Apple TV"),
):
    """
    ▶️  Executer un scenario.

    Sans argument, affiche une liste interactive des scenarios.
    """
    setup_logging()

    # Charger les scenarios
    try:
        scenarios = load_scenarios()
    except Exception as e:
        console.print(f"[red]✗[/red] Erreur de chargement des scenarios: {e}")
        raise typer.Exit(1)

    if not scenarios:
        console.print("[yellow]![/yellow] Aucun scenario configure.")
        console.print(f"[dim]Editez {SCENARIOS_FILE} pour creer vos scenarios[/dim]")
        raise typer.Exit(1)

    # Selection interactive du scenario si non specifie
    if not scenario_name:
        console.print()

        # Tableau des scenarios
        table = Table(title="Scenarios disponibles", show_header=True, header_style="bold cyan")
        table.add_column("Nom", style="cyan")
        table.add_column("Description")
        table.add_column("Etapes", justify="right")

        for name, data in scenarios.items():
            desc = data.get("description", "-")
            steps = len(data.get("steps", []))
            table.add_row(name, desc, str(steps))

        console.print(table)
        console.print()

        # Selection
        scenario_name = questionary.select(
            "Quel scenario executer ?",
            choices=list(scenarios.keys()),
            style=questionary.Style([
                ("selected", "fg:green bold"),
                ("pointer", "fg:green bold"),
            ])
        ).ask()

        if not scenario_name:
            raise typer.Exit(0)

    # Verifier que le scenario existe
    if scenario_name not in scenarios:
        console.print(f"[red]✗[/red] Scenario '{scenario_name}' non trouve")
        raise typer.Exit(1)

    # Selection du device si non specifie
    if not device:
        devices = run_async(scan_devices())

        if not devices:
            console.print("[red]✗[/red] Aucune Apple TV trouvee")
            raise typer.Exit(1)

        if len(devices) == 1:
            device = devices[0].name
        else:
            device_choices = [d.name for d in devices]
            device = questionary.select(
                "Sur quelle Apple TV ?",
                choices=device_choices
            ).ask()

            if not device:
                raise typer.Exit(0)

    # Execution
    console.print()
    console.print(f"[bold]▶ Execution de [cyan]{scenario_name}[/cyan] sur [cyan]{device}[/cyan][/bold]")
    console.print()

    try:
        devices = run_async(scan_devices())
        selected_device = select_device(devices, device)

        async def execute():
            async with connect_atv(selected_device) as atv:
                return await run_scenario(atv, scenario_name)

        success = run_async(execute())

        if success:
            console.print(f"\n[green]✓[/green] Scenario termine avec succes")
        else:
            console.print(f"\n[red]✗[/red] Scenario echoue")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[red]✗[/red] Erreur: {e}")
        raise typer.Exit(1)


# =============================================================================
# COMMANDE: list
# =============================================================================

@app.command("list")
def list_scenarios():
    """
    📋 Lister les scenarios disponibles.
    """
    try:
        scenarios = load_scenarios()
    except Exception as e:
        console.print(f"[red]✗[/red] Erreur: {e}")
        raise typer.Exit(1)

    if not scenarios:
        console.print("[yellow]![/yellow] Aucun scenario configure.")
        raise typer.Exit(0)

    console.print()
    table = Table(title="Scenarios disponibles", show_header=True, header_style="bold cyan")
    table.add_column("Nom", style="cyan")
    table.add_column("Description")
    table.add_column("Etapes", justify="right")

    for name, data in scenarios.items():
        desc = data.get("description", "-")
        steps = len(data.get("steps", []))
        table.add_row(name, desc, str(steps))

    console.print(table)
    console.print(f"\n[dim]Fichier: {SCENARIOS_FILE}[/dim]")


# =============================================================================
# COMMANDE: scan
# =============================================================================

@app.command()
def scan():
    """
    🔍 Rechercher les Apple TV sur le reseau.
    """
    console.print()

    devices = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Recherche des Apple TV...", total=None)
        devices = run_async(scan_devices())

    if not devices:
        console.print("[yellow]![/yellow] Aucune Apple TV trouvee")
        raise typer.Exit(0)

    table = Table(title=f"{len(devices)} Apple TV trouvee(s)", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Nom", style="cyan")
    table.add_column("Adresse IP")
    table.add_column("Protocoles")

    for i, device in enumerate(devices):
        protocols = ", ".join(str(s.protocol.name) for s in device.services)
        table.add_row(str(i), device.name or "-", str(device.address), protocols)

    console.print(table)


# =============================================================================
# COMMANDE: test
# =============================================================================

@app.command()
def test(
    device: Optional[str] = typer.Argument(None, help="Nom de l'Apple TV"),
):
    """
    🧪 Tester la connexion a une Apple TV.
    """
    test_connection(device)


def test_connection(device_name: Optional[str] = None):
    """Teste la connexion a une Apple TV."""
    console.print()

    # Scanner
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Recherche...", total=None)
        devices = run_async(scan_devices())

    if not devices:
        console.print("[red]✗[/red] Aucune Apple TV trouvee")
        raise typer.Exit(1)

    # Selection
    if device_name:
        device = select_device(devices, device_name)
    elif len(devices) == 1:
        device = devices[0]
    else:
        choice = questionary.select(
            "Quelle Apple TV tester ?",
            choices=[d.name for d in devices]
        ).ask()
        device = select_device(devices, choice)

    console.print(f"Test de connexion a [cyan]{device.name}[/cyan]...")

    # Test
    try:
        async def do_test():
            async with connect_atv(device) as atv:
                # Test simple: recuperer le power state
                power = atv.power
                is_on = power.power_state
                return is_on

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Connexion...", total=None)
            power_state = run_async(do_test())

        console.print(f"[green]✓[/green] Connexion reussie")
        console.print(f"  Etat: {'Allumee' if power_state else 'En veille'}")

    except Exception as e:
        console.print(f"[red]✗[/red] Echec de connexion: {e}")
        raise typer.Exit(1)


# =============================================================================
# COMMANDE: apps
# =============================================================================

@app.command()
def apps(
    device: Optional[str] = typer.Option(None, "-d", "--device", help="Nom de l'Apple TV"),
    sync: bool = typer.Option(False, "--sync", help="Synchroniser apps.json"),
):
    """
    📱 Lister les applications installees.
    """
    setup_logging()

    # Scanner
    devices = run_async(scan_devices())
    if not devices:
        console.print("[red]✗[/red] Aucune Apple TV trouvee")
        raise typer.Exit(1)

    # Selection
    if device:
        selected = select_device(devices, device)
    elif len(devices) == 1:
        selected = devices[0]
    else:
        choice = questionary.select(
            "Quelle Apple TV ?",
            choices=[d.name for d in devices]
        ).ask()
        selected = select_device(devices, choice)

    try:
        async def get_apps():
            async with connect_atv(selected) as atv:
                if sync:
                    await sync_apps_config(atv)
                    console.print("[green]✓[/green] apps.json synchronise")
                else:
                    await list_apps(atv)

        run_async(get_apps())

    except Exception as e:
        console.print(f"[red]✗[/red] Erreur: {e}")
        raise typer.Exit(1)


# =============================================================================
# COMMANDE: server
# =============================================================================

@app.command()
def server(
    port: int = typer.Option(8888, "--port", "-p", help="Port du serveur"),
):
    """
    🌐 Lancer le serveur HTTP pour les Raccourcis iOS.
    """
    from .server import run_server as start_server

    console.print()
    console.print(Panel.fit(
        f"[bold blue]🌐 Serveur HTTP[/bold blue]\n"
        f"[dim]Port: {port}[/dim]",
        border_style="blue"
    ))
    console.print()
    console.print("Endpoints:")
    console.print(f"  [cyan]GET[/cyan]  /health")
    console.print(f"  [cyan]GET[/cyan]  /scenarios")
    console.print(f"  [cyan]POST[/cyan] /scenario/{{name}}?device=Salon")
    console.print(f"  [cyan]POST[/cyan] /shutdown")
    console.print()
    console.print("[dim]Ctrl+C pour arreter[/dim]")
    console.print()

    run_async(start_server(port))


# =============================================================================
# POINT D'ENTREE
# =============================================================================

def main():
    """Point d'entree principal."""
    app()


if __name__ == "__main__":
    main()
