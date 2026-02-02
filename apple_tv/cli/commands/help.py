"""Commandes d'aide."""

from __future__ import annotations

import typer
from rich.table import Table

from ..console import console

router = typer.Typer()


@router.command("reference")
def reference_cmd():
    """
    📖 Afficher la reference des actions pour les scenarios.
    """
    console.print()

    # Navigation
    _print_actions_table(
        "Navigation",
        [
            ("up, down, left, right", "Navigation directionnelle"),
            ("select", "Bouton OK"),
            ("menu", "Retour / Menu"),
            ("home", "Ecran d'accueil"),
            ("home_double", "App Switcher (double home)"),
        ],
    )

    # Swipe
    _print_actions_table(
        "Swipe (gestes)",
        [
            ("swipe_up", "Glissement vers le haut"),
            ("swipe_down", "Glissement vers le bas"),
            ("swipe_left", "Glissement vers la gauche"),
            ("swipe_right", "Glissement vers la droite"),
        ],
    )

    # Lecture
    _print_actions_table(
        "Lecture",
        [
            ("play", "Lecture"),
            ("pause", "Pause"),
            ("play_pause", "Basculer lecture/pause"),
            ("stop", "Arreter"),
            ("next", "Piste suivante"),
            ("previous", "Piste precedente"),
        ],
    )

    # Actions speciales
    _print_actions_table(
        "Actions speciales",
        [
            ("launch", "Lancer une app (necessite: app)"),
            ("wait", "Pause fixe (necessite: seconds)"),
            ("scenario", "Executer un sous-scenario (necessite: name)"),
        ],
    )

    # Parametres
    param_table = Table(title="Parametres", show_header=True, header_style="bold cyan", box=None)
    param_table.add_column("Parametre", style="yellow", width=25)
    param_table.add_column("Description")
    param_table.add_column("Defaut", style="dim")
    param_table.add_row("delay", "Pause apres l'action (secondes)", "0.5")
    param_table.add_row("repeat", "Nombre de repetitions", "1")
    param_table.add_row("app", "Nom ou bundle ID de l'app", "-")
    param_table.add_row("seconds", "Duree de pause pour wait", "-")
    param_table.add_row("name", "Nom du sous-scenario", "-")
    console.print(param_table)
    console.print()

    # Exemple
    console.print("[bold]Exemple de scenario:[/bold]")
    console.print('[dim]{"action": "launch", "app": "netflix"}[/dim]')
    console.print('[dim]{"action": "wait", "seconds": 3}[/dim]')
    console.print('[dim]{"action": "down", "repeat": 2, "delay": 0.3}[/dim]')
    console.print('[dim]{"action": "select"}[/dim]')
    console.print()


def _print_actions_table(title: str, actions: list[tuple[str, str]]) -> None:
    """Affiche un tableau d'actions."""
    table = Table(title=title, show_header=True, header_style="bold cyan", box=None)
    table.add_column("Action", style="cyan", width=25)
    table.add_column("Description")
    for action, desc in actions:
        table.add_row(action, desc)
    console.print(table)
    console.print()
