"""Planification des scenarios."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .config import (
    SCHEDULE_FILE,
    SCHEDULER_INTERVAL,
    WEEKDAY_NAMES,
    load_json,
    logger,
    save_json,
)
from .connection import connect_atv, scan_devices, select_device
from .exceptions import DeviceNotFoundError, FeatureNotAvailableError
from .scenarios import load_scenarios, run_scenario


@dataclass
class ScheduleEntry:
    """Entree de planification."""

    scenario: str
    device: str
    hour: int
    minute: int
    weekdays: Optional[list[int]] = None
    enabled: bool = True

    def __post_init__(self) -> None:
        """Valide les champs apres initialisation."""
        if not 0 <= self.hour <= 23:
            raise ValueError(f"hour doit etre entre 0-23, recu: {self.hour}")
        if not 0 <= self.minute <= 59:
            raise ValueError(f"minute doit etre entre 0-59, recu: {self.minute}")
        if self.weekdays is not None:
            invalid = [d for d in self.weekdays if not 0 <= d <= 6]
            if invalid:
                raise ValueError(f"weekdays doit etre entre 0-6, invalides: {invalid}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduleEntry:
        """Cree une entree depuis un dictionnaire."""
        time_obj = data.get("time", {})
        return cls(
            scenario=data.get("scenario", ""),
            device=data.get("device", ""),
            hour=time_obj.get("hour", 0),
            minute=time_obj.get("minute", 0),
            weekdays=data.get("weekdays"),
            enabled=data.get("enabled", True),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dictionnaire."""
        result: dict[str, Any] = {
            "scenario": self.scenario,
            "device": self.device,
            "time": {"hour": self.hour, "minute": self.minute},
            "enabled": self.enabled,
        }
        if self.weekdays is not None:
            result["weekdays"] = self.weekdays
        return result

    def should_run_now(self) -> bool:
        """Verifie si cette planification doit s'executer maintenant."""
        now = datetime.now()

        # Verifier le jour (Python: lundi=0, notre format: dimanche=0)
        if self.weekdays is not None:
            current_day = (now.weekday() + 1) % 7
            if current_day not in self.weekdays:
                return False

        return now.hour == self.hour and now.minute == self.minute

    @property
    def time_str(self) -> str:
        """Retourne l'heure formatee."""
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def weekdays_str(self) -> str:
        """Retourne les jours formates."""
        if self.weekdays is None:
            return "Tous les jours"
        return ", ".join(WEEKDAY_NAMES[d] for d in sorted(self.weekdays))


def load_schedules() -> list[ScheduleEntry]:
    """Charge les planifications depuis schedule.json."""
    data = load_json(SCHEDULE_FILE, {"schedules": []})
    return [ScheduleEntry.from_dict(entry) for entry in data.get("schedules", [])]


def save_schedules(schedules: list[ScheduleEntry]) -> None:
    """Sauvegarde les planifications."""
    data = {"schedules": [s.to_dict() for s in schedules]}
    save_json(SCHEDULE_FILE, data)


def show_schedules() -> None:
    """Affiche les planifications."""
    schedules = load_schedules()

    if not schedules:
        print("Aucune planification configuree.")
        print(f"\nFichier: {SCHEDULE_FILE}")
        print("\nPour ajouter: python -m apple_tv schedule-add")
        return

    print("Planifications configurees:\n")

    for i, entry in enumerate(schedules):
        status_icon = "+" if entry.enabled else "-"
        status_text = "ON" if entry.enabled else "OFF"

        print(f"[{i}] {status_icon} {entry.scenario}")
        print(f"    Appareil: {entry.device}")
        print(f"    Heure:    {entry.time_str}")
        print(f"    Jours:    {entry.weekdays_str}")
        print(f"    Statut:   {status_text}")
        print()

    print(f"Total: {len(schedules)} planification(s)")
    print(f"Fichier: {SCHEDULE_FILE}")


def add_schedule_interactive() -> None:
    """Ajoute une planification interactivement."""
    print("Ajout d'une nouvelle planification\n")

    # Charger les scenarios
    scenarios = load_scenarios()
    if not scenarios:
        logger.error("Aucun scenario disponible.")
        return

    # Afficher les scenarios
    print("Scenarios disponibles:")
    scenario_list = list(scenarios.keys())
    for i, name in enumerate(scenario_list):
        desc = scenarios[name].get("description", "")
        print(f"  [{i}] {name} - {desc}")
    print()

    # Selection du scenario
    while True:
        try:
            choice = int(input(f"Choisissez un scenario (0-{len(scenario_list) - 1}): "))
            if 0 <= choice < len(scenario_list):
                scenario_name = scenario_list[choice]
                break
            print("Index invalide.")
        except ValueError:
            print("Entrez un nombre.")

    # Appareil
    device = input("\nNom de l'appareil (ex: Salon): ").strip() or "Salon"

    # Heure
    while True:
        time_input = input("\nHeure (HH:MM): ").strip()
        try:
            parts = time_input.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                break
            print("Heure invalide (0-23, minutes 0-59)")
        except (ValueError, IndexError):
            print("Format invalide. Utilisez HH:MM")

    # Jours
    print("\nJours (0=Dim, 1=Lun, 2=Mar, 3=Mer, 4=Jeu, 5=Ven, 6=Sam)")
    print("Exemples: 1,2,3,4,5 (semaine), 0,6 (weekend), vide (tous)")
    days_input = input("Jours: ").strip()

    weekdays: Optional[list[int]] = None
    if days_input:
        try:
            weekdays = [int(d.strip()) for d in days_input.split(",")]
            weekdays = [d for d in weekdays if 0 <= d <= 6]
            if not weekdays:
                weekdays = None
        except ValueError:
            weekdays = None

    # Creer et sauvegarder
    entry = ScheduleEntry(
        scenario=scenario_name,
        device=device,
        hour=hour,
        minute=minute,
        weekdays=weekdays,
        enabled=True,
    )

    schedules = load_schedules()
    schedules.append(entry)
    save_schedules(schedules)

    print(f"\n[OK] Planification ajoutee!")
    print(f"  Scenario: {scenario_name}")
    print(f"  Appareil: {device}")
    print(f"  Heure:    {entry.time_str}")
    print(f"  Jours:    {entry.weekdays_str}")


def remove_schedule(index: int) -> bool:
    """Supprime une planification par son index."""
    schedules = load_schedules()

    if not schedules:
        logger.error("Aucune planification a supprimer.")
        return False

    if not 0 <= index < len(schedules):
        logger.error(f"Index {index} invalide (0-{len(schedules) - 1})")
        return False

    removed = schedules.pop(index)
    save_schedules(schedules)

    logger.info(f"Planification supprimee: {removed.scenario} a {removed.time_str}")
    return True


async def execute_scheduled_entry(entry: ScheduleEntry) -> bool:
    """Execute une planification."""
    try:
        devices = await scan_devices()
        device = select_device(devices, entry.device)

        async with connect_atv(device) as atv:
            return await run_scenario(atv, entry.scenario)

    except (DeviceNotFoundError, FeatureNotAvailableError) as e:
        logger.error(f"  Erreur: {e}")
        return False
    except Exception as e:
        logger.error(f"  Erreur inattendue: {e}")
        return False


async def run_scheduler() -> None:
    """Boucle principale du scheduler."""
    print("=" * 50)
    print("Scheduler Apple TV demarre")
    print("=" * 50)
    print(f"Fichier: {SCHEDULE_FILE}")
    print("Ctrl+C pour arreter\n")

    last_check: Optional[tuple[int, int]] = None

    while True:
        now = datetime.now()
        current_minute = (now.hour, now.minute)

        # Eviter les executions multiples dans la meme minute
        if current_minute != last_check:
            last_check = current_minute

            # Recharger les planifications (modifs a chaud)
            schedules = load_schedules()

            for entry in schedules:
                if not entry.enabled:
                    continue

                if entry.should_run_now():
                    logger.info(
                        f"[{now.strftime('%H:%M:%S')}] "
                        f"Execution: {entry.scenario} sur {entry.device}"
                    )
                    await execute_scheduled_entry(entry)

        # Attendre la prochaine minute (calcul atomique pour eviter race condition)
        sleep_seconds = SCHEDULER_INTERVAL - datetime.now().second
        await asyncio.sleep(max(1, sleep_seconds))
