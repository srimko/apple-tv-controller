"""Gestion des scenarios."""

from __future__ import annotations

import asyncio
from typing import Any

from pyatv.interface import AppleTV

from .apps import launch_app
from .config import (
    DEFAULT_SCENARIOS,
    REPEAT_DELAY,
    SCENARIOS_FILE,
    load_json,
    logger,
    save_json,
)
from .models import ValidationError, validate_scenarios


def load_scenarios(*, validate: bool = True) -> dict[str, dict[str, Any]]:
    """Charge les scenarios.

    Args:
        validate: Si True, valide les scenarios au chargement.

    Returns:
        Dictionnaire des scenarios.

    Raises:
        ValidationError: Si validate=True et un scenario est invalide.
    """
    scenarios = load_json(SCENARIOS_FILE)
    if not scenarios:
        save_json(SCENARIOS_FILE, DEFAULT_SCENARIOS)
        scenarios = DEFAULT_SCENARIOS.copy()

    if validate:
        validate_scenarios(scenarios)

    return scenarios


def show_scenarios() -> None:
    """Affiche les scenarios disponibles."""
    try:
        scenarios = load_scenarios()
    except ValidationError as e:
        logger.error(f"Erreur de validation:\n{e}")
        return

    logger.info("\nScenarios disponibles:\n")
    logger.info(f"{'Nom':<25} Description")
    logger.info("-" * 70)

    for name, data in sorted(scenarios.items()):
        desc = data.get("description", "-")
        steps = len(data.get("steps", []))
        logger.info(f"{name:<25} {desc} ({steps} etapes)")

    logger.info(f"\nTotal: {len(scenarios)} scenario(s)")
    logger.info(f"Fichier: {SCENARIOS_FILE}")


async def execute_step(atv: AppleTV, step: dict[str, Any], num: int) -> bool:
    """Execute une etape de scenario."""
    action = step.get("action")
    repeat = step.get("repeat", 1)

    if not action:
        logger.error(f"  [{num}] Action manquante")
        return False

    nav_actions = {
        "up": atv.remote_control.up,
        "down": atv.remote_control.down,
        "left": atv.remote_control.left,
        "right": atv.remote_control.right,
        "select": atv.remote_control.select,
        "menu": atv.remote_control.menu,
        "home": atv.remote_control.home,
    }

    play_actions = {
        "play": atv.remote_control.play,
        "pause": atv.remote_control.pause,
        "play_pause": atv.remote_control.play_pause,
    }

    symbols = {
        "up": "^",
        "down": "v",
        "left": "<",
        "right": ">",
        "select": "o",
        "menu": "M",
        "home": "H",
        "play": ">",
        "pause": "||",
        "play_pause": ">||",
    }

    for i in range(repeat):
        info = f" ({i + 1}/{repeat})" if repeat > 1 else ""

        if action == "launch":
            app = step.get("app")
            if not app:
                logger.error(f"  [{num}] Parametre 'app' manquant")
                return False
            logger.info(f"  [{num}] Lancement {app}...{info}")
            await launch_app(atv, app)

        elif action == "wait":
            secs = step.get("seconds", 1)
            logger.info(f"  [{num}] Attente {secs}s...{info}")
            await asyncio.sleep(secs)

        elif action in nav_actions:
            logger.info(f"  [{num}] {symbols.get(action, '')} {action.capitalize()}{info}")
            await nav_actions[action]()

        elif action in play_actions:
            logger.info(f"  [{num}] {symbols.get(action, '')} {action.capitalize()}{info}")
            await play_actions[action]()

        else:
            logger.error(f"  [{num}] Action inconnue: {action}")
            return False

        if repeat > 1 and i < repeat - 1:
            await asyncio.sleep(REPEAT_DELAY)

    return True


async def run_scenario(atv: AppleTV, name: str) -> bool:
    """Execute un scenario."""
    try:
        scenarios = load_scenarios()
    except ValidationError as e:
        logger.error(f"Erreur de validation: {e}")
        return False

    if name not in scenarios:
        logger.error(f"Scenario '{name}' non trouve.")
        logger.info("\nScenarios disponibles:")
        for n in sorted(scenarios):
            logger.info(f"  - {n}")
        return False

    scenario = scenarios[name]
    desc = scenario.get("description", "-")
    steps = scenario.get("steps", [])

    logger.info(f"\n> Execution: {name}")
    logger.info(f"  {desc}")
    logger.info(f"  {len(steps)} etape(s)\n")

    for i, step in enumerate(steps, 1):
        if not await execute_step(atv, step, i):
            logger.error(f"\n[X] Echec a l'etape {i}")
            return False

    logger.info(f"\n[OK] Scenario '{name}' termine!")
    return True
