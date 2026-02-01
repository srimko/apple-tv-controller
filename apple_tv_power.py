#!/usr/bin/env python3
"""
Controle Apple TV via pyatv.

Permet de scanner, appairer, controler l'alimentation, la lecture,
la telecommande, le volume, les applications et les scenarios.

Prerequis:
    pip install pyatv

Utilisation:
    python apple_tv_power.py <commande> [options]
    python apple_tv_power.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union

import pyatv
from pyatv.const import FeatureName, FeatureState, Protocol
from pyatv.interface import AppleTV

# =============================================================================
# CONFIGURATION
# =============================================================================

# Repertoire du script
SCRIPT_DIR = Path(__file__).parent.absolute()

# Fichiers de configuration
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
APPS_CONFIG_FILE = SCRIPT_DIR / "apps.json"
SCENARIOS_FILE = SCRIPT_DIR / "scenarios.json"
SCHEDULE_FILE = SCRIPT_DIR / "schedule.json"

# Timeouts (secondes)
SCAN_TIMEOUT = 5
OPERATION_TIMEOUT = 10

# Configuration par defaut des applications
DEFAULT_APPS_CONFIG: dict[str, str] = {
    "netflix": "com.netflix.Netflix",
    "youtube": "com.google.ios.youtube",
    "disney": "com.disney.disneyplus",
    "prime": "com.amazon.aiv.AIVApp",
    "apple_tv": "com.apple.TVWatchList",
    "spotify": "com.spotify.client",
    "twitch": "tv.twitch",
    "plex": "com.plexapp.plex",
    "infuse": "com.firecore.infuse",
    "arte": "tv.arte.plus7",
    "molotov": "com.molotov.ios",
    "mycanal": "com.canal.canalplus",
}

# Configuration par defaut des scenarios
DEFAULT_SCENARIOS: dict[str, dict[str, Any]] = {
    "netflix_profil1": {
        "description": "Lancer Netflix et selectionner le premier profil",
        "steps": [
            {"action": "launch", "app": "netflix"},
            {"action": "wait", "seconds": 3},
            {"action": "select"},
        ],
    },
    "canal_direct": {
        "description": "Lancer Canal+ et aller sur le direct",
        "steps": [
            {"action": "launch", "app": "canal"},
            {"action": "wait", "seconds": 2},
            {"action": "down", "repeat": 2},
            {"action": "select"},
        ],
    },
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class AppleTVError(Exception):
    """Exception de base pour les erreurs Apple TV."""

    pass


class DeviceNotFoundError(AppleTVError):
    """Appareil non trouve."""

    pass


class FeatureNotAvailableError(AppleTVError):
    """Fonctionnalite non disponible."""

    pass


class PairingRequiredError(AppleTVError):
    """Appairage requis."""

    pass


# =============================================================================
# UTILITAIRES JSON
# =============================================================================


def load_json(filepath: Path, default: Any = None) -> Any:
    """Charge un fichier JSON."""
    if not filepath.exists():
        return default if default is not None else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Impossible de lire {filepath}: {e}")
        return default if default is not None else {}


def save_json(filepath: Path, data: Any) -> bool:
    """Sauvegarde des donnees en JSON."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        logger.error(f"Erreur de sauvegarde {filepath}: {e}")
        return False


# =============================================================================
# GESTION DES CREDENTIALS
# =============================================================================


def load_credentials() -> dict[str, dict[str, str]]:
    """Charge les credentials depuis credentials.json."""
    return load_json(CREDENTIALS_FILE, {})


def save_credentials(identifier: str, protocol: str, credentials: str) -> None:
    """Sauvegarde les credentials."""
    all_creds = load_credentials()
    if identifier not in all_creds:
        all_creds[identifier] = {}
    all_creds[identifier][protocol] = credentials
    if save_json(CREDENTIALS_FILE, all_creds):
        logger.info(f"Credentials sauvegardes dans {CREDENTIALS_FILE}")


def apply_credentials(device_config: pyatv.interface.BaseConfig) -> bool:
    """Applique les credentials sauvegardes a la configuration."""
    all_creds = load_credentials()
    identifier = device_config.identifier

    if identifier not in all_creds:
        return False

    device_creds = all_creds[identifier]
    applied = False

    for service in device_config.services:
        protocol_name = service.protocol.name
        if protocol_name in device_creds:
            service.credentials = device_creds[protocol_name]
            applied = True
            logger.debug(f"  Credentials {protocol_name} appliques")

    return applied


# =============================================================================
# GESTION DES APPLICATIONS
# =============================================================================


def load_apps_config() -> dict[str, str]:
    """Charge la configuration des applications."""
    config = load_json(APPS_CONFIG_FILE)
    if not config:
        save_json(APPS_CONFIG_FILE, DEFAULT_APPS_CONFIG)
        return DEFAULT_APPS_CONFIG.copy()
    return config


def get_bundle_id(app_name: str) -> str:
    """Retourne le bundle ID pour un alias ou le nom lui-meme."""
    config = load_apps_config()
    return config.get(app_name.lower(), app_name)


# =============================================================================
# GESTION DES SCENARIOS
# =============================================================================


def load_scenarios() -> dict[str, dict[str, Any]]:
    """Charge les scenarios."""
    scenarios = load_json(SCENARIOS_FILE)
    if not scenarios:
        save_json(SCENARIOS_FILE, DEFAULT_SCENARIOS)
        return DEFAULT_SCENARIOS.copy()
    return scenarios


# =============================================================================
# CONNEXION APPLE TV
# =============================================================================


@asynccontextmanager
async def connect_atv(device_config: pyatv.interface.BaseConfig):
    """Context manager pour la connexion Apple TV."""
    logger.info(f"Connexion a {device_config.name}...")

    if apply_credentials(device_config):
        logger.info("Credentials charges.")
    else:
        logger.warning("Aucun credential trouve. Utilisez 'pair' d'abord.")

    atv = await pyatv.connect(device_config, asyncio.get_event_loop())
    logger.info("Connecte!")

    try:
        yield atv
    finally:
        atv.close()


def require_feature(feature: FeatureName):
    """Decorateur qui verifie qu'une fonctionnalite est disponible."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(atv: AppleTV, *args, **kwargs):
            if not atv.features.in_state(FeatureState.Available, feature):
                raise FeatureNotAvailableError(
                    f"Fonctionnalite {feature.name} non disponible. "
                    "Assurez-vous d'avoir appaire l'appareil."
                )
            return await func(atv, *args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# SCAN ET SELECTION D'APPAREIL
# =============================================================================


async def scan_devices(timeout: int = SCAN_TIMEOUT) -> list[pyatv.interface.BaseConfig]:
    """Scanne le reseau pour trouver les Apple TV."""
    logger.info("Recherche des Apple TV...")
    devices = await pyatv.scan(asyncio.get_event_loop(), timeout=timeout)
    return devices


def select_device(
    devices: list[pyatv.interface.BaseConfig],
    selector: Optional[Union[int, str]] = None,
) -> pyatv.interface.BaseConfig:
    """Selectionne un appareil par index, nom ou interactivement."""
    if not devices:
        raise DeviceNotFoundError("Aucune Apple TV trouvee sur le reseau.")

    # Un seul appareil et pas de selecteur -> selection automatique
    if len(devices) == 1 and selector is None:
        return devices[0]

    # Selection par index
    if isinstance(selector, int):
        if 0 <= selector < len(devices):
            return devices[selector]
        raise DeviceNotFoundError(f"Index {selector} invalide (0-{len(devices) - 1})")

    # Selection par nom
    if isinstance(selector, str):
        for device in devices:
            if selector.lower() in device.name.lower():
                return device
        raise DeviceNotFoundError(f"Appareil '{selector}' non trouve")

    # Selection interactive
    print(f"\n{len(devices)} appareil(s) trouve(s):\n")
    for i, device in enumerate(devices):
        print(f"  [{i}] {device.name} ({device.address})")
    print()

    while True:
        try:
            choice = int(input(f"Choisissez (0-{len(devices) - 1}): "))
            if 0 <= choice < len(devices):
                return devices[choice]
            print("Index invalide.")
        except ValueError:
            print("Entrez un nombre.")


# =============================================================================
# APPAIRAGE
# =============================================================================


async def pair_device(device_config: pyatv.interface.BaseConfig) -> Optional[str]:
    """Lance l'appairage avec une Apple TV."""
    has_companion = any(
        s.protocol == Protocol.Companion for s in device_config.services
    )

    if not has_companion:
        logger.error(f"{device_config.name} ne supporte pas le protocole Companion.")
        return None

    logger.info(f"Appairage avec {device_config.name}...")
    logger.info("Un code PIN va s'afficher sur votre Apple TV.\n")

    pairing = await pyatv.pair(
        device_config, Protocol.Companion, asyncio.get_event_loop()
    )

    try:
        await pairing.begin()

        if pairing.device_provides_pin:
            pin = input("Entrez le code PIN: ")
            pairing.pin(pin)

        await pairing.finish()

        if pairing.has_paired:
            logger.info("\nAppairage reussi!")
            credentials = pairing.service.credentials
            save_credentials(
                device_config.identifier, Protocol.Companion.name, credentials
            )
            return credentials
        else:
            logger.error("\nEchec de l'appairage.")
            return None
    finally:
        await pairing.close()


# =============================================================================
# CONTROLES ALIMENTATION
# =============================================================================


async def get_power_status(atv: AppleTV) -> str:
    """Retourne l'etat d'alimentation."""
    features = atv.features

    power_available = features.in_state(FeatureState.Available, FeatureName.PowerState)
    turn_on_available = features.in_state(FeatureState.Available, FeatureName.TurnOn)
    turn_off_available = features.in_state(FeatureState.Available, FeatureName.TurnOff)

    print("Fonctionnalites disponibles:")
    print(f"  - PowerState: {'Oui' if power_available else 'Non'}")
    print(f"  - TurnOn:     {'Oui' if turn_on_available else 'Non'}")
    print(f"  - TurnOff:    {'Oui' if turn_off_available else 'Non'}")
    print()

    if power_available:
        state = atv.power.power_state
        print(f"Etat: {state.name}")
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


@require_feature(FeatureName.Play)
async def cmd_play(atv: AppleTV) -> None:
    """Lance la lecture."""
    await atv.remote_control.play()
    logger.info("Lecture lancee!")


@require_feature(FeatureName.Pause)
async def cmd_pause(atv: AppleTV) -> None:
    """Met en pause."""
    await atv.remote_control.pause()
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


@require_feature(FeatureName.Next)
async def cmd_next(atv: AppleTV) -> None:
    """Piste suivante."""
    await atv.remote_control.next()
    logger.info("Suivant!")


@require_feature(FeatureName.Previous)
async def cmd_previous(atv: AppleTV) -> None:
    """Piste precedente."""
    await atv.remote_control.previous()
    logger.info("Precedent!")


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


# =============================================================================
# APPLICATIONS
# =============================================================================


@require_feature(FeatureName.AppList)
async def list_apps(atv: AppleTV) -> list:
    """Liste les applications installees."""
    apps = await atv.apps.app_list()
    print("\nApplications installees:\n")
    for app in sorted(apps, key=lambda a: a.name.lower()):
        print(f"  {app.name}")
        print(f"    {app.identifier}\n")
    print(f"Total: {len(apps)} applications")
    return apps


@require_feature(FeatureName.LaunchApp)
async def launch_app(atv: AppleTV, app_name: str) -> None:
    """Lance une application par alias ou bundle ID."""
    bundle_id = get_bundle_id(app_name)
    logger.info(f"Lancement de {app_name} ({bundle_id})...")
    await atv.apps.launch_app(bundle_id)
    logger.info("Application lancee!")


@require_feature(FeatureName.AppList)
async def sync_apps_config(atv: AppleTV) -> int:
    """Synchronise apps.json avec les apps installees."""
    apps = await atv.apps.app_list()
    config = load_apps_config()
    existing_ids = set(config.values())

    added = 0
    for app in apps:
        if app.identifier not in existing_ids:
            alias = app.name.lower().replace(" ", "_").replace("-", "_")
            alias = "".join(c for c in alias if c.isalnum() or c == "_")

            # Eviter doublons
            base = alias
            counter = 1
            while alias in config:
                alias = f"{base}_{counter}"
                counter += 1

            config[alias] = app.identifier
            added += 1

    if added > 0:
        save_json(APPS_CONFIG_FILE, config)
        logger.info(f"{added} application(s) ajoutee(s)")
    else:
        logger.info("apps.json deja a jour")

    return added


def show_apps_config() -> None:
    """Affiche la configuration des applications."""
    config = load_apps_config()
    print(f"\nConfiguration des applications ({APPS_CONFIG_FILE}):\n")

    if config:
        max_len = max(len(a) for a in config)
        for alias, bundle_id in sorted(config.items()):
            print(f"  {alias:<{max_len}}  ->  {bundle_id}")
        print(f"\n{len(config)} application(s)")


# =============================================================================
# SCENARIOS
# =============================================================================


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


async def execute_step(atv: AppleTV, step: dict, num: int) -> bool:
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
            await asyncio.sleep(0.3)

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


# =============================================================================
# PLANIFICATION (SCHEDULING)
# =============================================================================

# Noms des jours de la semaine
WEEKDAY_NAMES = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]


@dataclass
class ScheduleEntry:
    """Entree de planification."""

    scenario: str
    device: str
    hour: int
    minute: int
    weekdays: Optional[list[int]] = None
    enabled: bool = True

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
        print("\nPour ajouter: python apple_tv_power.py schedule-add")
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

        # Attendre la prochaine minute
        now = datetime.now()
        await asyncio.sleep(60 - now.second)


# =============================================================================
# CLI
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Cree le parser d'arguments."""
    parser = argparse.ArgumentParser(
        description="Controle Apple TV via pyatv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-d",
        "--device",
        help="Nom ou index de l'appareil",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Mode verbose",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")

    # Appareils
    subparsers.add_parser("scan", help="Scanner les appareils")
    subparsers.add_parser("pair", help="Appairer avec l'Apple TV")
    subparsers.add_parser("status", help="Etat d'alimentation")

    # Alimentation
    subparsers.add_parser("on", help="Allumer")
    subparsers.add_parser("off", help="Eteindre")

    # Lecture
    subparsers.add_parser("play", help="Lecture")
    subparsers.add_parser("pause", help="Pause")
    subparsers.add_parser("play_pause", help="Toggle lecture/pause")
    subparsers.add_parser("stop", help="Stop")
    subparsers.add_parser("next", help="Suivant")
    subparsers.add_parser("previous", help="Precedent")

    # Telecommande
    subparsers.add_parser("up", help="Haut")
    subparsers.add_parser("down", help="Bas")
    subparsers.add_parser("left", help="Gauche")
    subparsers.add_parser("right", help="Droite")
    subparsers.add_parser("select", help="Selection")
    subparsers.add_parser("menu", help="Menu")
    subparsers.add_parser("home", help="Home")

    # Volume
    subparsers.add_parser("volume_up", help="Volume +")
    subparsers.add_parser("volume_down", help="Volume -")
    vol_parser = subparsers.add_parser("volume", help="Volume (afficher ou regler)")
    vol_parser.add_argument("level", type=int, nargs="?", help="Niveau 0-100")

    # Applications
    subparsers.add_parser("apps", help="Lister les apps")
    subparsers.add_parser("apps_config", help="Afficher config apps")
    subparsers.add_parser("apps_sync", help="Synchroniser apps.json")
    launch_parser = subparsers.add_parser("launch", help="Lancer une app")
    launch_parser.add_argument("app", help="Nom ou bundle ID")

    # Scenarios
    subparsers.add_parser("scenarios", help="Lister les scenarios")
    scenario_parser = subparsers.add_parser("scenario", help="Executer un scenario")
    scenario_parser.add_argument("name", help="Nom du scenario")

    # Planification
    subparsers.add_parser("schedules", help="Lister les planifications")
    subparsers.add_parser("schedule-add", help="Ajouter une planification")
    schedule_rm = subparsers.add_parser("schedule-remove", help="Supprimer une planification")
    schedule_rm.add_argument("index", type=int, help="Index de la planification")

    # Scheduler daemon
    scheduler_parser = subparsers.add_parser("scheduler", help="Lancer le daemon")
    scheduler_parser.add_argument(
        "--daemon", action="store_true", help="Lancer en arriere-plan"
    )

    return parser


async def main() -> int:
    """Point d'entree principal."""
    parser = create_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.command:
        parser.print_help()
        return 1

    # Commandes sans connexion
    if args.command == "scan":
        devices = await scan_devices()
        if not devices:
            print("Aucune Apple TV trouvee.")
            return 1
        print(f"\n{len(devices)} appareil(s) trouve(s):\n")
        for i, d in enumerate(devices):
            protocols = ", ".join(s.protocol.name for s in d.services)
            print(f"[{i}] {d.name}")
            print(f"    Adresse: {d.address}")
            print(f"    ID: {d.identifier}")
            print(f"    Protocoles: {protocols}\n")
        return 0

    if args.command == "apps_config":
        show_apps_config()
        return 0

    if args.command == "scenarios":
        show_scenarios()
        return 0

    if args.command == "schedules":
        show_schedules()
        return 0

    if args.command == "schedule-add":
        add_schedule_interactive()
        return 0

    if args.command == "schedule-remove":
        return 0 if remove_schedule(args.index) else 1

    if args.command == "scheduler":
        if args.daemon:
            # Lancer en arriere-plan avec nohup
            script_path = Path(__file__).absolute()
            log_file = SCRIPT_DIR / "scheduler.log"
            logger.info(f"Lancement du scheduler en arriere-plan...")
            logger.info(f"Logs: {log_file}")
            subprocess.Popen(
                ["nohup", sys.executable, str(script_path), "scheduler"],
                stdout=open(log_file, "a"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            logger.info("Scheduler demarre!")
            return 0
        else:
            await run_scheduler()
            return 0

    # Commandes necessitant un appareil
    try:
        devices = await scan_devices()
        device_selector = None
        if args.device:
            try:
                device_selector = int(args.device)
            except ValueError:
                device_selector = args.device

        device = select_device(devices, device_selector)
        print(f"\nAppareil: {device.name}")

        if args.command == "pair":
            await pair_device(device)
            return 0

        # Commandes necessitant une connexion
        async with connect_atv(device) as atv:
            if args.command == "status":
                await get_power_status(atv)

            elif args.command == "on":
                await turn_on(atv)

            elif args.command == "off":
                await turn_off(atv)

            elif args.command == "play":
                await cmd_play(atv)

            elif args.command == "pause":
                await cmd_pause(atv)

            elif args.command == "play_pause":
                await cmd_play_pause(atv)

            elif args.command == "stop":
                await cmd_stop(atv)

            elif args.command == "next":
                await cmd_next(atv)

            elif args.command == "previous":
                await cmd_previous(atv)

            elif args.command in ("up", "down", "left", "right", "select", "menu", "home"):
                button = RemoteButton[args.command.upper()]
                await press_button(atv, button)

            elif args.command == "volume_up":
                await volume_up(atv)

            elif args.command == "volume_down":
                await volume_down(atv)

            elif args.command == "volume":
                if args.level is not None:
                    await set_volume(atv, args.level)
                else:
                    await get_volume(atv)

            elif args.command == "apps":
                await list_apps(atv)

            elif args.command == "apps_sync":
                await sync_apps_config(atv)

            elif args.command == "launch":
                await launch_app(atv, args.app)

            elif args.command == "scenario":
                await run_scenario(atv, args.name)

        return 0

    except DeviceNotFoundError as e:
        logger.error(str(e))
        return 1

    except FeatureNotAvailableError as e:
        logger.error(str(e))
        logger.info("Essayez: python apple_tv_power.py pair")
        return 1

    except pyatv.exceptions.AuthenticationError:
        logger.error("Erreur d'authentification!")
        logger.info("Essayez: python apple_tv_power.py pair")
        return 1

    except asyncio.TimeoutError:
        logger.error("Timeout: l'Apple TV n'a pas repondu.")
        return 1

    except KeyboardInterrupt:
        logger.info("\nInterrompu.")
        return 130

    except Exception as e:
        logger.error(f"Erreur: {e}")
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
