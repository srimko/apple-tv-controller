"""Commandes de scenarios."""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import questionary
import typer

from ...apps import launch_app as _launch_app, load_apps_config
from ...config import SCENARIOS_FILE, save_json
from ...connection import connect_atv
from ...scenarios import load_scenarios
from ..console import console, create_table, print_error, print_panel, print_success, print_warning
from ..constants import QUESTIONARY_STYLE, SWIPE_GESTURES
from ..operations import execute_remote_action, run_scenario
from ..utils import require_device, run_async

router = typer.Typer()


@router.command("run")
def run_cmd(
    scenario_name: Optional[str] = typer.Argument(None, help="Nom du scenario a executer"),
    device: Optional[str] = typer.Option(
        None, "-d", "--device",
        help="Nom de l'Apple TV",
        envvar="ATV_DEVICE",
    ),
):
    """
    ▶️  Executer un scenario.

    Sans argument, affiche une liste interactive des scenarios.
    """
    # Charger les scenarios
    try:
        scenarios = load_scenarios()
    except Exception as e:
        print_error(f"Erreur de chargement des scenarios: {e}")
        raise typer.Exit(1)

    if not scenarios:
        print_warning("Aucun scenario configure.")
        console.print(f"[dim]Editez {SCENARIOS_FILE} pour creer vos scenarios[/dim]")
        raise typer.Exit(1)

    # Selection interactive du scenario si non specifie
    if not scenario_name:
        console.print()
        _print_scenarios_table(scenarios)
        console.print()

        scenario_name = questionary.select(
            "Quel scenario executer ?",
            choices=list(scenarios.keys()),
            style=questionary.Style(QUESTIONARY_STYLE)
        ).ask()

        if not scenario_name:
            raise typer.Exit(0)

    if scenario_name not in scenarios:
        print_error(f"Scenario '{scenario_name}' non trouve")
        raise typer.Exit(1)

    with require_device(device) as selected:
        console.print()
        console.print(f"[bold]▶ Execution de [cyan]{scenario_name}[/cyan] sur [cyan]{selected.name}[/cyan][/bold]")
        console.print("[dim]Ctrl+C pour interrompre[/dim]")
        console.print()

        try:
            success = run_async(run_scenario(selected, scenario_name))

            if success:
                print_success("Scenario termine avec succes")
            else:
                print_error("Scenario echoue")
                raise typer.Exit(1)

        except (KeyboardInterrupt, asyncio.CancelledError):
            print_warning("Scenario interrompu")
            raise typer.Exit(130)

        except Exception as e:
            print_error(f"Erreur: {e}")
            raise typer.Exit(1)


@router.command("list")
def list_cmd():
    """
    📋 Lister les scenarios disponibles.
    """
    try:
        scenarios = load_scenarios()
    except Exception as e:
        print_error(f"Erreur: {e}")
        raise typer.Exit(1)

    if not scenarios:
        print_warning("Aucun scenario configure.")
        raise typer.Exit(0)

    console.print()
    _print_scenarios_table(scenarios)
    console.print(f"\n[dim]Fichier: {SCENARIOS_FILE}[/dim]")


@router.command("record")
def record_cmd(
    name: str = typer.Argument(..., help="Nom du scenario a creer"),
    device: Optional[str] = typer.Option(
        None, "-d", "--device",
        help="Nom de l'Apple TV",
        envvar="ATV_DEVICE",
    ),
):
    """
    🎬 Enregistrer un nouveau scenario interactivement.
    """
    with require_device(device) as selected:
        console.print()
        print_panel(f"🎬 Enregistrement: {name}", f"Device: {selected.name}")
        console.print()
        console.print("[dim]Selectionnez les actions une par une.[/dim]")
        console.print("[dim]Les actions sont envoyees en temps reel a l'Apple TV.[/dim]")
        console.print()

        steps = []
        apps_config = load_apps_config()

        try:
            result = run_async(_record_session(selected, steps, apps_config))
        except (KeyboardInterrupt, asyncio.CancelledError):
            print_warning("Enregistrement annule")
            raise typer.Exit(0)

        if not result:
            print_warning("Enregistrement annule")
            raise typer.Exit(0)

        if not steps:
            print_warning("Aucune etape enregistree")
            raise typer.Exit(0)

        # Demander une description
        console.print()
        description = questionary.text(
            "Description du scenario ?",
            default=f"Scenario {name}"
        ).ask()

        # Afficher le scenario
        console.print()
        console.print("[bold]Scenario enregistre:[/bold]")
        console.print(f"  Nom: [cyan]{name}[/cyan]")
        console.print(f"  Description: {description}")
        console.print(f"  Etapes: {len(steps)}")

        # Confirmer la sauvegarde
        if questionary.confirm("Sauvegarder dans scenarios.json ?", default=True).ask():
            scenarios = load_scenarios(validate=False)
            scenarios[name] = {
                "description": description,
                "steps": steps
            }

            if save_json(SCENARIOS_FILE, scenarios):
                print_success(f"Scenario '{name}' sauvegarde")
            else:
                print_error("Erreur de sauvegarde")
                raise typer.Exit(1)
        else:
            console.print()
            console.print("[bold]JSON du scenario:[/bold]")
            scenario_json = {name: {"description": description, "steps": steps}}
            console.print(json.dumps(scenario_json, indent=2, ensure_ascii=False))


def _print_scenarios_table(scenarios: dict) -> None:
    """Affiche le tableau des scenarios."""
    rows = [
        [name, data.get("description", "-"), str(len(data.get("steps", [])))]
        for name, data in scenarios.items()
    ]
    table = create_table(
        "Scenarios disponibles",
        [
            ("Nom", {"style": "cyan"}),
            ("Description", {}),
            ("Etapes", {"justify": "right"}),
        ],
        rows,
    )
    console.print(table)


async def _record_session(selected, steps: list, apps_config: dict) -> bool:
    """Session d'enregistrement interactive."""
    actions_menu = {
        "⬆️  Haut (up)": "up",
        "⬇️  Bas (down)": "down",
        "⬅️  Gauche (left)": "left",
        "➡️  Droite (right)": "right",
        "✅ Valider (select)": "select",
        "↩️  Menu/Retour (menu)": "menu",
        "🏠 Home": "home",
        "🏠🏠 Home Double (App Switcher)": "home_double",
        "👆 Swipe Haut": "swipe_up",
        "👇 Swipe Bas": "swipe_down",
        "👈 Swipe Gauche": "swipe_left",
        "👉 Swipe Droite": "swipe_right",
        "📱 Lancer une app": "launch",
        "⏸️  Pause": "wait",
        "💾 Terminer et sauvegarder": "save",
        "❌ Annuler": "cancel",
    }

    async with connect_atv(selected) as atv:
        while True:
            choice = await questionary.select(
                f"Action #{len(steps) + 1}",
                choices=list(actions_menu.keys()),
                style=questionary.Style(QUESTIONARY_STYLE)
            ).ask_async()

            if not choice:
                return False

            action = actions_menu[choice]

            if action == "cancel":
                return False

            if action == "save":
                return True

            if action == "launch":
                app_name = await _select_app(apps_config)
                if not app_name:
                    continue

                console.print(f"  [cyan]→[/cyan] Lancement {app_name}...")
                await _launch_app(atv, app_name)
                steps.append({"action": "launch", "app": app_name})

                wait_secs = await questionary.text(
                    "Temps d'attente apres lancement (secondes) ?",
                    default="3"
                ).ask_async()

                if wait_secs:
                    try:
                        secs = float(wait_secs)
                        if secs > 0:
                            steps.append({"action": "wait", "seconds": secs})
                            await asyncio.sleep(secs)
                    except ValueError:
                        pass

            elif action == "wait":
                wait_secs = await questionary.text(
                    "Duree (secondes) ?",
                    default="2"
                ).ask_async()

                if wait_secs:
                    try:
                        secs = float(wait_secs)
                        if secs > 0:
                            console.print(f"  [cyan]→[/cyan] Pause {secs}s (enregistree)")
                            steps.append({"action": "wait", "seconds": secs})
                    except ValueError:
                        console.print("[red]Valeur invalide[/red]")

            else:
                console.print(f"  [cyan]→[/cyan] {action}")
                await execute_remote_action(atv, action)
                steps.append({"action": action})

            console.print(f"  [dim]{len(steps)} etape(s) enregistree(s)[/dim]")


async def _select_app(apps_config: dict) -> Optional[str]:
    """Selection interactive d'une application."""
    app_choices = list(apps_config.keys()) + ["[Autre - entrer manuellement]"]
    app_choice = await questionary.select(
        "Quelle application ?",
        choices=app_choices
    ).ask_async()

    if not app_choice:
        return None

    if app_choice == "[Autre - entrer manuellement]":
        return await questionary.text("Bundle ID ou nom:").ask_async()

    return app_choice
