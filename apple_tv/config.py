"""Configuration et utilitaires."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import Any

# Repertoire du package
PACKAGE_DIR = Path(__file__).parent.absolute()
# Repertoire racine (parent du package)
ROOT_DIR = PACKAGE_DIR.parent

# Fichiers de configuration
CREDENTIALS_FILE = ROOT_DIR / "credentials.json"
APPS_CONFIG_FILE = ROOT_DIR / "apps.json"
SCENARIOS_FILE = ROOT_DIR / "scenarios.json"
SCHEDULE_FILE = ROOT_DIR / "schedule.json"

# Fichiers sensibles (permissions 600)
SENSITIVE_FILES = {CREDENTIALS_FILE}

# Timeouts (secondes)
SCAN_TIMEOUT = 5
OPERATION_TIMEOUT = 10
REPEAT_DELAY = 0.3  # Delai entre repetitions d'actions
SCHEDULER_INTERVAL = 60  # Intervalle de verification du scheduler

# Port serveur HTTP
SERVER_PORT = 8888
HTTP_REQUEST_TIMEOUT = 60  # Timeout pour les requetes HTTP

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

# Noms des jours de la semaine
WEEKDAY_NAMES = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]

# Logging - NullHandler par defaut, l'appelant configure le logging
logger = logging.getLogger("apple_tv")
logger.addHandler(logging.NullHandler())


def setup_logging(level: int = logging.INFO) -> None:
    """Configure le logging pour l'application CLI."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)


def load_json(filepath: Path, default: Any = None) -> Any:
    """Charge un fichier JSON.

    Args:
        filepath: Chemin du fichier JSON.
        default: Valeur par defaut si le fichier n'existe pas ou est invalide.

    Returns:
        Contenu du fichier JSON ou la valeur par defaut.
    """
    if not filepath.exists():
        return default if default is not None else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Impossible de lire {filepath}: {e}")
        return default if default is not None else {}


def save_json(filepath: Path, data: Any, *, secure: bool = False) -> bool:
    """Sauvegarde des donnees en JSON avec ecriture atomique.

    Utilise un fichier temporaire puis rename pour eviter la corruption
    en cas de crash pendant l'ecriture.

    Args:
        filepath: Chemin du fichier JSON.
        data: Donnees a sauvegarder.
        secure: Si True, applique les permissions 600 (fichiers sensibles).

    Returns:
        True si la sauvegarde a reussi, False sinon.
    """
    temp_fd = None
    temp_path = None
    try:
        # Creer un fichier temporaire dans le meme repertoire (pour atomic rename)
        temp_fd, temp_path_str = tempfile.mkstemp(
            dir=filepath.parent,
            prefix=f".{filepath.name}.",
            suffix=".tmp"
        )
        temp_path = Path(temp_path_str)

        # Ecrire dans le fichier temporaire
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            temp_fd = None  # fdopen prend possession du fd
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Appliquer les permissions avant le rename si fichier sensible
        if secure or filepath in SENSITIVE_FILES:
            temp_path.chmod(0o600)

        # Atomic rename (POSIX garantit l'atomicite)
        shutil.move(temp_path, filepath)
        temp_path = None

        return True

    except (IOError, OSError) as e:
        logger.error(f"Erreur de sauvegarde {filepath}: {e}")
        return False

    finally:
        # Nettoyage en cas d'erreur
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
