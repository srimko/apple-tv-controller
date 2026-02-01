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


def load_scenarios() -> dict[str, dict[str, Any]]:
    """Charge les scenarios."""
    scenarios = load_json(SCENARIOS_FILE)
    if not scenarios:
        save_json(SCENARIOS_FILE, DEFAULT_SCENARIOS)
        return DEFAULT_SCENARIOS.copy()
    return scenarios


def show_scenarios() -> None:
    """Affiche les scenarios disponibles."""
    scenarios = load_scenarios()
    print("\nScenarios disponibles:\n")
    print(f"{'Nom':<25} Description")
    print("-" * 70)

    for name, data in sorted(scenarios.items()):
        desc = data.get("description", "-")
        steps = len(data.get("steps", []))
        print(f"{name:<25} {desc} ({steps} etapes)")

    print(f"\nTotal: {len(scenarios)} scenario(s)")
    print(f"Fichier: {SCENARIOS_FILE}")


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
            print(f"  [{num}] Lancement {app}...{info}")
            await launch_app(atv, app)

        elif action == "wait":
            secs = step.get("seconds", 1)
            print(f"  [{num}] Attente {secs}s...{info}")
            await asyncio.sleep(secs)

        elif action in nav_actions:
            print(f"  [{num}] {symbols.get(action, '')} {action.capitalize()}{info}")
            await nav_actions[action]()

        elif action in play_actions:
            print(f"  [{num}] {symbols.get(action, '')} {action.capitalize()}{info}")
            await play_actions[action]()

        else:
            logger.error(f"  [{num}] Action inconnue: {action}")
            return False

        if repeat > 1 and i < repeat - 1:
            await asyncio.sleep(REPEAT_DELAY)

    return True


async def run_scenario(atv: AppleTV, name: str) -> bool:
    """Execute un scenario."""
    scenarios = load_scenarios()

    if name not in scenarios:
        logger.error(f"Scenario '{name}' non trouve.")
        print("\nScenarios disponibles:")
        for n in sorted(scenarios):
            print(f"  - {n}")
        return False

    scenario = scenarios[name]
    desc = scenario.get("description", "-")
    steps = scenario.get("steps", [])

    print(f"\n> Execution: {name}")
    print(f"  {desc}")
    print(f"  {len(steps)} etape(s)\n")

    for i, step in enumerate(steps, 1):
        if not await execute_step(atv, step, i):
            print(f"\n[X] Echec a l'etape {i}")
            return False

    print(f"\n[OK] Scenario '{name}' termine!")
    return True
