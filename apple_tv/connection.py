"""Gestion de la connexion Apple TV."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from typing import Callable, Optional, Union

import pyatv
from pyatv.const import FeatureName, FeatureState, Protocol
from pyatv.interface import AppleTV

from .config import (
    CREDENTIALS_FILE,
    SCAN_TIMEOUT,
    load_json,
    logger,
    save_json,
)
from .exceptions import DeviceNotFoundError, FeatureNotAvailableError


# =============================================================================
# GESTION DES CREDENTIALS
# =============================================================================


def load_credentials() -> dict[str, dict[str, str]]:
    """Charge les credentials depuis credentials.json."""
    return load_json(CREDENTIALS_FILE, {})


def save_credentials(identifier: str, protocol: str, credentials: str) -> None:
    """Sauvegarde les credentials (fichier protege en 600)."""
    all_creds = load_credentials()
    if identifier not in all_creds:
        all_creds[identifier] = {}
    all_creds[identifier][protocol] = credentials
    if save_json(CREDENTIALS_FILE, all_creds, secure=True):
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

    atv = await pyatv.connect(device_config, asyncio.get_running_loop())
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
    devices = await pyatv.scan(asyncio.get_running_loop(), timeout=timeout)
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


async def pair_protocol(
    device_config: pyatv.interface.BaseConfig, protocol: Protocol
) -> Optional[str]:
    """Appaire un protocole specifique."""
    logger.info(f"\n--- Appairage {protocol.name} ---")
    logger.info("Un code PIN va s'afficher sur votre Apple TV.\n")

    pairing = await pyatv.pair(
        device_config, protocol, asyncio.get_running_loop()
    )

    try:
        await pairing.begin()

        if pairing.device_provides_pin:
            pin = input(f"Entrez le code PIN pour {protocol.name}: ")
            pairing.pin(pin)

        await pairing.finish()

        if pairing.has_paired:
            logger.info(f"Appairage {protocol.name} reussi!")
            credentials = pairing.service.credentials
            save_credentials(
                device_config.identifier, protocol.name, credentials
            )
            return credentials
        else:
            logger.error(f"Echec de l'appairage {protocol.name}.")
            return None
    finally:
        await pairing.close()


async def pair_device(device_config: pyatv.interface.BaseConfig) -> bool:
    """Lance l'appairage avec une Apple TV (tous les protocoles)."""
    logger.info(f"Appairage avec {device_config.name}...")

    # Protocoles a appairer (ordre de priorite)
    protocols_to_pair = [Protocol.Companion, Protocol.AirPlay]

    available_protocols = {s.protocol for s in device_config.services}
    logger.info(f"Protocoles disponibles: {', '.join(p.name for p in available_protocols)}")

    success_count = 0

    for protocol in protocols_to_pair:
        if protocol not in available_protocols:
            logger.info(f"  {protocol.name}: non disponible")
            continue

        # Verifier si deja appaire
        creds = load_credentials()
        if device_config.identifier in creds and protocol.name in creds[device_config.identifier]:
            logger.info(f"  {protocol.name}: deja appaire")
            success_count += 1
            continue

        try:
            result = await pair_protocol(device_config, protocol)
            if result:
                success_count += 1
        except Exception as e:
            logger.error(f"  Erreur {protocol.name}: {e}")

    if success_count > 0:
        logger.info(f"\n[OK] {success_count} protocole(s) appaire(s)!")
        return True
    else:
        logger.error("\nAucun protocole n'a pu etre appaire.")
        return False
