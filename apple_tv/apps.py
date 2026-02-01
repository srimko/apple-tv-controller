"""Gestion des applications."""

from __future__ import annotations

from typing import Any

from pyatv.const import FeatureName
from pyatv.interface import AppleTV

from .config import (
    APPS_CONFIG_FILE,
    DEFAULT_APPS_CONFIG,
    load_json,
    logger,
    save_json,
)
from .connection import require_feature


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


@require_feature(FeatureName.AppList)
async def list_apps(atv: AppleTV) -> list[Any]:
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
