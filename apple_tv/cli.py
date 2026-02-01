"""Interface en ligne de commande."""

from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

import pyatv

from .apps import list_apps, launch_app, show_apps_config, sync_apps_config
from .config import ROOT_DIR, logger, setup_logging
from .connection import connect_atv, pair_device, scan_devices, select_device
from .controls import (
    RemoteButton,
    cmd_next,
    cmd_pause,
    cmd_play,
    cmd_play_pause,
    cmd_previous,
    cmd_stop,
    get_power_status,
    get_volume,
    press_button,
    set_volume,
    turn_off,
    turn_on,
    volume_down,
    volume_up,
)
from .exceptions import DeviceNotFoundError, FeatureNotAvailableError
from .scenarios import run_scenario, show_scenarios
from .scheduler import (
    add_schedule_interactive,
    remove_schedule,
    run_scheduler,
    show_schedules,
)
from .server import run_server


def create_parser() -> argparse.ArgumentParser:
    """Cree le parser d'arguments."""
    # Parser parent avec les arguments communs
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "-d",
        "--device",
        help="Nom ou index de l'appareil",
    )
    parent_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Mode verbose",
    )

    parser = argparse.ArgumentParser(
        description="Controle Apple TV via pyatv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parent_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")

    # Appareils
    subparsers.add_parser("scan", help="Scanner les appareils", parents=[parent_parser])
    subparsers.add_parser("pair", help="Appairer avec l'Apple TV", parents=[parent_parser])
    subparsers.add_parser("status", help="Etat d'alimentation", parents=[parent_parser])

    # Alimentation
    subparsers.add_parser("on", help="Allumer", parents=[parent_parser])
    subparsers.add_parser("off", help="Eteindre", parents=[parent_parser])

    # Lecture
    subparsers.add_parser("play", help="Lecture", parents=[parent_parser])
    subparsers.add_parser("pause", help="Pause", parents=[parent_parser])
    subparsers.add_parser("play_pause", help="Toggle lecture/pause", parents=[parent_parser])
    subparsers.add_parser("stop", help="Stop", parents=[parent_parser])
    subparsers.add_parser("next", help="Suivant", parents=[parent_parser])
    subparsers.add_parser("previous", help="Precedent", parents=[parent_parser])

    # Telecommande
    subparsers.add_parser("up", help="Haut", parents=[parent_parser])
    subparsers.add_parser("down", help="Bas", parents=[parent_parser])
    subparsers.add_parser("left", help="Gauche", parents=[parent_parser])
    subparsers.add_parser("right", help="Droite", parents=[parent_parser])
    subparsers.add_parser("select", help="Selection", parents=[parent_parser])
    subparsers.add_parser("menu", help="Menu", parents=[parent_parser])
    subparsers.add_parser("home", help="Home", parents=[parent_parser])

    # Volume
    subparsers.add_parser("volume_up", help="Volume +", parents=[parent_parser])
    subparsers.add_parser("volume_down", help="Volume -", parents=[parent_parser])
    vol_parser = subparsers.add_parser("volume", help="Volume (afficher ou regler)", parents=[parent_parser])
    vol_parser.add_argument("level", type=int, nargs="?", help="Niveau 0-100")

    # Applications
    subparsers.add_parser("apps", help="Lister les apps", parents=[parent_parser])
    subparsers.add_parser("apps_config", help="Afficher config apps", parents=[parent_parser])
    subparsers.add_parser("apps_sync", help="Synchroniser apps.json", parents=[parent_parser])
    launch_parser = subparsers.add_parser("launch", help="Lancer une app", parents=[parent_parser])
    launch_parser.add_argument("app", help="Nom ou bundle ID")

    # Scenarios
    subparsers.add_parser("scenarios", help="Lister les scenarios", parents=[parent_parser])
    scenario_parser = subparsers.add_parser("scenario", help="Executer un scenario", parents=[parent_parser])
    scenario_parser.add_argument("name", help="Nom du scenario")

    # Planification
    subparsers.add_parser("schedules", help="Lister les planifications", parents=[parent_parser])
    subparsers.add_parser("schedule-add", help="Ajouter une planification", parents=[parent_parser])
    schedule_rm = subparsers.add_parser("schedule-remove", help="Supprimer une planification", parents=[parent_parser])
    schedule_rm.add_argument("index", type=int, help="Index de la planification")

    # Scheduler daemon
    scheduler_parser = subparsers.add_parser("scheduler", help="Lancer le daemon", parents=[parent_parser])
    scheduler_parser.add_argument(
        "--daemon", action="store_true", help="Lancer en arriere-plan"
    )

    # Serveur HTTP
    server_parser = subparsers.add_parser("server", help="Lancer le serveur HTTP", parents=[parent_parser])
    server_parser.add_argument("--port", type=int, default=8888, help="Port (defaut: 8888)")

    return parser


async def main() -> int:
    """Point d'entree principal."""
    parser = create_parser()
    args = parser.parse_args()

    # Configurer le logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)

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
            script_path = Path(__file__).parent.parent / "apple_tv_power.py"
            log_file = ROOT_DIR / "scheduler.log"
            logger.info("Lancement du scheduler en arriere-plan...")
            logger.info(f"Logs: {log_file}")
            # Note: Le file handle reste ouvert intentionnellement pour le subprocess
            log_handle = open(log_file, "a")
            subprocess.Popen(
                ["nohup", sys.executable, str(script_path), "scheduler"],
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            logger.info("Scheduler demarre!")
            return 0
        else:
            await run_scheduler()
            return 0

    if args.command == "server":
        await run_server(args.port)
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
        logger.info("Essayez: python -m apple_tv pair")
        return 1

    except pyatv.exceptions.AuthenticationError:
        logger.error("Erreur d'authentification!")
        logger.info("Essayez: python -m apple_tv pair")
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


def run() -> None:
    """Point d'entree pour le script."""
    sys.exit(asyncio.run(main()))
