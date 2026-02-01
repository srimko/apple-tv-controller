#!/usr/bin/env python3
"""
Script de contrôle complet pour Apple TV via pyatv.

Ce script permet de :
- Scanner le réseau pour trouver les Apple TV
- Allumer/éteindre une Apple TV
- Contrôler la lecture (play, pause, etc.)
- Utiliser la télécommande virtuelle
- Gérer le volume

Prérequis :
    pip install pyatv

Utilisation :
    # Gestion des appareils
    python apple_tv_power.py scan                    # Scanner les appareils
    python apple_tv_power.py pair                    # Appairer avec l'Apple TV
    python apple_tv_power.py status                  # Voir l'état actuel

    # Alimentation
    python apple_tv_power.py on                      # Allumer l'Apple TV
    python apple_tv_power.py off                     # Éteindre l'Apple TV

    # Lecture
    python apple_tv_power.py play                    # Lancer la lecture
    python apple_tv_power.py pause                   # Mettre en pause
    python apple_tv_power.py play_pause              # Toggle lecture/pause
    python apple_tv_power.py stop                    # Arrêter la lecture
    python apple_tv_power.py next                    # Piste suivante
    python apple_tv_power.py previous                # Piste précédente

    # Télécommande
    python apple_tv_power.py up                      # Flèche haut
    python apple_tv_power.py down                    # Flèche bas
    python apple_tv_power.py left                    # Flèche gauche
    python apple_tv_power.py right                   # Flèche droite
    python apple_tv_power.py select                  # Bouton OK/Sélection
    python apple_tv_power.py menu                    # Bouton Menu (retour)
    python apple_tv_power.py home                    # Bouton Home

    # Volume
    python apple_tv_power.py volume_up               # Augmenter le volume
    python apple_tv_power.py volume_down             # Baisser le volume
    python apple_tv_power.py volume 50               # Régler le volume à 50%
    python apple_tv_power.py volume                  # Afficher le volume actuel

    # Applications
    python apple_tv_power.py apps                    # Lister les apps installées
    python apple_tv_power.py apps_config             # Afficher la config apps.json
    python apple_tv_power.py apps_sync               # Synchroniser apps.json
    python apple_tv_power.py launch netflix          # Lancer une app par alias

    # Scénarios
    python apple_tv_power.py scenarios               # Lister les scénarios
    python apple_tv_power.py scenario netflix_profil1 --device "Salon"  # Exécuter

    # Options
    python apple_tv_power.py on --device "Salon"     # Spécifier l'appareil par nom
    python apple_tv_power.py on --device 1           # Spécifier l'appareil par index
"""

import asyncio
import json
import os
import sys
import pyatv
from pyatv.const import Protocol, FeatureName, FeatureState

# Fichier de stockage des credentials (dans le même dossier que le script)
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")

# Fichier de configuration des applications
APPS_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps.json")

# Configuration par défaut des applications
DEFAULT_APPS_CONFIG = {
    "netflix": "com.netflix.Netflix",
    "youtube": "com.google.ios.youtube",
    "disney": "com.disney.disneyplus",
    "prime": "com.amazon.aiv.AIVApp",
    "apple_tv": "com.apple.TVWatchList",
    "spotify": "com.spotify.client",
    "twitch": "tv.twitch"
}

# Fichier de configuration des applications
APPS_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps.json")

# Fichier de configuration des scénarios
SCENARIOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenarios.json")

# Configuration par défaut des applications
DEFAULT_APPS_CONFIG = {
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
    "mycanal": "com.canal.canalplus"
}

# Configuration par défaut des scénarios
DEFAULT_SCENARIOS = {
    "netflix_profil1": {
        "description": "Lancer Netflix et sélectionner le premier profil",
        "steps": [
            {"action": "launch", "app": "netflix"},
            {"action": "wait", "seconds": 3},
            {"action": "select"}
        ]
    },
    "canal_direct": {
        "description": "Lancer Canal+ et aller sur le direct",
        "steps": [
            {"action": "launch", "app": "canal"},
            {"action": "wait", "seconds": 2},
            {"action": "down", "repeat": 2},
            {"action": "select"}
        ]
    }
}

# Timeout pour les opérations réseau (en secondes)
SCAN_TIMEOUT = 5
OPERATION_TIMEOUT = 10


def load_credentials():
    """
    Charge les credentials depuis le fichier JSON.

    Retourne un dictionnaire {identifier: {protocol: credentials}}
    Retourne un dict vide si le fichier n'existe pas ou est corrompu.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        return {}

    try:
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Attention : Impossible de lire {CREDENTIALS_FILE} ({e})")
        return {}


def load_apps_config():
    """
    Charge la configuration des applications depuis le fichier JSON.

    Si le fichier n'existe pas, le crée avec la configuration par défaut.
    Retourne un dictionnaire {alias: bundle_id}.
    """
    if not os.path.exists(APPS_CONFIG_FILE):
        save_apps_config(DEFAULT_APPS_CONFIG)
        print(f"Fichier de configuration créé : {APPS_CONFIG_FILE}")
        return DEFAULT_APPS_CONFIG.copy()

    try:
        with open(APPS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Attention : Impossible de lire {APPS_CONFIG_FILE} ({e})")
        print("Utilisation de la configuration par défaut.")
        return DEFAULT_APPS_CONFIG.copy()


def save_apps_config(config):
    """Sauvegarde la configuration des applications dans le fichier JSON."""
    try:
        with open(APPS_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Erreur lors de la sauvegarde de la config apps : {e}")


def save_credentials(identifier, protocol, credentials):
    """
    Sauvegarde les credentials dans le fichier JSON.

    Les credentials sont stockés par identifiant d'appareil et par protocole.
    """
    all_credentials = load_credentials()

    if identifier not in all_credentials:
        all_credentials[identifier] = {}

    all_credentials[identifier][protocol] = credentials

    try:
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(all_credentials, f, indent=2)
        print(f"Credentials sauvegardés dans {CREDENTIALS_FILE}")
    except IOError as e:
        print(f"Erreur lors de la sauvegarde : {e}")


# =============================================================================
# GESTION DES APPLICATIONS
# =============================================================================

def load_apps_config():
    """
    Charge la configuration des applications depuis apps.json.

    Crée le fichier avec la configuration par défaut s'il n'existe pas.
    Retourne un dictionnaire {alias: bundle_id}.
    """
    if not os.path.exists(APPS_CONFIG_FILE):
        save_apps_config(DEFAULT_APPS_CONFIG)
        return DEFAULT_APPS_CONFIG

    try:
        with open(APPS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Attention : Impossible de lire {APPS_CONFIG_FILE} ({e})")
        return DEFAULT_APPS_CONFIG


def save_apps_config(config):
    """
    Sauvegarde la configuration des applications dans apps.json.
    """
    try:
        with open(APPS_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Erreur lors de la sauvegarde : {e}")


def show_apps_config():
    """
    Affiche le contenu du fichier de configuration des applications.
    """
    config = load_apps_config()
    print("Configuration des applications (apps.json) :\n")
    print(f"{'Alias':<15} {'Bundle ID'}")
    print("-" * 50)
    for alias, bundle_id in sorted(config.items()):
        print(f"{alias:<15} {bundle_id}")
    print(f"\nFichier : {APPS_CONFIG_FILE}")


async def list_apps(atv):
    """
    Liste les applications installées sur l'Apple TV.
    """
    if not atv.features.in_state(FeatureState.Available, FeatureName.AppList):
        print("La fonctionnalité AppList n'est pas disponible.")
        print("Vous devez d'abord appairer l'appareil :")
        print("  python3 apple_tv_power.py pair")
        return

    print("Applications installees sur l'Apple TV :\n")
    apps = await atv.apps.app_list()

    print(f"{'Nom':<30} {'Bundle ID'}")
    print("-" * 70)
    for app in sorted(apps, key=lambda x: x.name.lower()):
        print(f"{app.name:<30} {app.identifier}")

    print(f"\nTotal : {len(apps)} applications")
    print("\nPour ajouter une app a la config, editez apps.json avec :")
    print('  "alias": "bundle.id"')


async def sync_apps_config(atv):
    """
    Synchronise apps.json avec les applications installées sur l'Apple TV.

    Ajoute les nouvelles apps trouvées avec un alias basé sur leur nom.
    Conserve les alias personnalisés existants.
    """
    if not atv.features.in_state(FeatureState.Available, FeatureName.AppList):
        print("Impossible de recuperer la liste des applications.")
        return False

    print("\nRecuperation des applications installees...")
    apps = await atv.apps.app_list()

    # Charger la config existante
    config = load_apps_config()

    # Creer un set des bundle IDs deja dans la config
    existing_bundle_ids = set(config.values())

    # Ajouter les nouvelles apps
    added = 0
    for app in apps:
        if app.identifier not in existing_bundle_ids:
            # Creer un alias a partir du nom de l'app (minuscule, underscore)
            alias = app.name.lower().replace(" ", "_").replace("-", "_")
            # Supprimer les caracteres speciaux
            alias = "".join(c for c in alias if c.isalnum() or c == "_")

            # Eviter les doublons d'alias
            base_alias = alias
            counter = 1
            while alias in config:
                alias = f"{base_alias}_{counter}"
                counter += 1

            config[alias] = app.identifier
            added += 1

    # Sauvegarder si des apps ont ete ajoutees
    if added > 0:
        save_apps_config(config)
        print(f"{added} nouvelle(s) application(s) ajoutee(s) a apps.json")
    else:
        print("apps.json est deja a jour.")

    return True


async def launch_app(atv, app_name):
    """
    Lance une application par son alias ou bundle ID.

    Cherche d'abord dans apps.json, sinon utilise le nom comme bundle ID.
    """
    if not atv.features.in_state(FeatureState.Available, FeatureName.LaunchApp):
        print("La fonctionnalite LaunchApp n'est pas disponible.")
        print("Vous devez d'abord appairer l'appareil :")
        print("  python3 apple_tv_power.py pair")
        return

    config = load_apps_config()

    # Chercher l'alias dans la config
    bundle_id = config.get(app_name.lower())

    if bundle_id:
        print(f"Lancement de {app_name} ({bundle_id})...")
    else:
        # Utiliser directement comme bundle ID
        bundle_id = app_name
        print(f"Lancement de {bundle_id}...")

    try:
        await atv.apps.launch_app(bundle_id)
        print("Application lancee !")
    except Exception as e:
        print(f"Erreur lors du lancement : {e}")
        print("\nVerifiez que le bundle ID est correct.")
        print("Utilisez 'apps' pour lister les applications installees.")


def apply_credentials(device_config):
    """
    Applique les credentials sauvegardés à la configuration de l'appareil.

    Cherche les credentials correspondant à l'identifiant de l'appareil
    et les ajoute aux services appropriés.
    """
    all_credentials = load_credentials()
    identifier = device_config.identifier

    if identifier not in all_credentials:
        return False

    device_creds = all_credentials[identifier]
    applied = False

    for service in device_config.services:
        protocol_name = service.protocol.name
        if protocol_name in device_creds:
            service.credentials = device_creds[protocol_name]
            applied = True
            print(f"  Credentials {protocol_name} appliqués")

    return applied


async def scan_devices():
    """
    Scanne le réseau local pour trouver toutes les Apple TV disponibles.

    Retourne une liste de configurations d'appareils trouvés.
    Chaque configuration contient : nom, adresse IP, identifiant, protocoles supportés.
    """
    print("Recherche des Apple TV sur le réseau...")

    # scan() parcourt le réseau et retourne tous les appareils Apple TV/AirPlay trouvés
    loop = asyncio.get_event_loop()
    devices = await pyatv.scan(loop, timeout=SCAN_TIMEOUT)

    if not devices:
        print("Aucune Apple TV trouvée sur le réseau.")
        return []

    print(f"\n{len(devices)} appareil(s) trouvé(s) :\n")

    for i, device in enumerate(devices):
        print(f"[{i}] {device.name}")
        print(f"    Adresse : {device.address}")
        print(f"    Identifiant : {device.identifier}")

        # Affiche les protocoles/services disponibles sur cet appareil
        services = [str(service.protocol.name) for service in device.services]
        print(f"    Protocoles : {', '.join(services)}")
        print()

    return devices


async def pair_device(device_config):
    """
    Lance le processus d'appairage avec une Apple TV.

    L'appairage est nécessaire pour obtenir les credentials qui permettent
    de se connecter et contrôler l'appareil. Un code PIN sera affiché
    sur l'écran de l'Apple TV qu'il faudra saisir.

    Apres un appairage reussi, synchronise automatiquement apps.json
    avec les applications installees sur l'Apple TV.
    """
    # Vérifier que le protocole Companion est disponible
    has_companion = any(
        service.protocol == Protocol.Companion
        for service in device_config.services
    )

    if not has_companion:
        print(f"Erreur : {device_config.name} ne supporte pas le protocole Companion.")
        print("Les fonctionnalités d'alimentation ne seront pas disponibles.")
        return None

    print(f"Appairage avec {device_config.name}...")
    print("Un code PIN va s'afficher sur votre Apple TV.\n")

    # On appaire le protocole Companion car c'est lui qui gère le mieux
    # les fonctions d'alimentation (turn_on/turn_off)
    loop = asyncio.get_event_loop()
    pairing = await pyatv.pair(device_config, Protocol.Companion, loop)
    credentials = None

    try:
        await pairing.begin()

        if pairing.device_provides_pin:
            # L'Apple TV affiche un code PIN à l'écran
            pin = input("Entrez le code PIN affiché sur l'Apple TV : ")
            pairing.pin(pin)

        await pairing.finish()

        if pairing.has_paired:
            print("\nAppairage réussi !")
            credentials = pairing.service.credentials

            # Sauvegarder les credentials automatiquement
            save_credentials(
                device_config.identifier,
                Protocol.Companion.name,
                credentials
            )
        else:
            print("\nÉchec de l'appairage.")

    finally:
        # Toujours fermer la session de pairing (évite "Unclosed client session")
        await pairing.close()

    # Si appairage reussi, synchroniser apps.json
    if credentials:
        try:
            atv = await connect_to_device(device_config)
            await sync_apps_config(atv)
            atv.close()
        except Exception as e:
            print(f"Note : impossible de synchroniser les apps ({e})")

    return credentials


async def connect_to_device(device_config):
    """
    Établit une connexion avec l'Apple TV.

    Charge les credentials sauvegardés et les applique avant la connexion.
    """
    print(f"Connexion à {device_config.name}...")

    # Appliquer les credentials sauvegardés
    if apply_credentials(device_config):
        print("Credentials chargés depuis le fichier.")
    else:
        print("Aucun credential trouvé. Utilisez 'pair' d'abord.")

    # connect() établit la connexion en utilisant tous les protocoles configurés
    loop = asyncio.get_event_loop()
    atv = await pyatv.connect(device_config, loop)

    print("Connecté !")
    return atv


def check_power_features(atv):
    """
    Vérifie si les fonctionnalités d'alimentation sont disponibles.

    Retourne True si au moins une fonctionnalité power est supportée.
    Affiche un message d'aide si aucune n'est disponible.
    """
    features = atv.features

    power_state_available = features.in_state(FeatureState.Available, FeatureName.PowerState)
    turn_on_available = features.in_state(FeatureState.Available, FeatureName.TurnOn)
    turn_off_available = features.in_state(FeatureState.Available, FeatureName.TurnOff)

    print("Fonctionnalités disponibles :")
    print(f"  - PowerState : {'Oui' if power_state_available else 'Non'}")
    print(f"  - TurnOn     : {'Oui' if turn_on_available else 'Non'}")
    print(f"  - TurnOff    : {'Oui' if turn_off_available else 'Non'}")
    print()

    if not any([power_state_available, turn_on_available, turn_off_available]):
        print("Aucune fonctionnalité d'alimentation disponible !")
        print("Vous devez d'abord appairer l'appareil :")
        print("  python3 apple_tv_power.py pair")
        return False

    return True


async def get_power_status(atv):
    """
    Récupère et affiche l'état d'alimentation actuel de l'Apple TV.

    Les états possibles sont :
    - On : L'appareil est allumé
    - Off : L'appareil est éteint/en veille
    - Unknown : État inconnu
    """
    if not check_power_features(atv):
        return None

    # power_state retourne un enum PowerState
    state = atv.power.power_state
    print(f"État d'alimentation : {state.name}")
    return state


async def turn_on(atv):
    """Allume l'Apple TV."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.TurnOn):
        print("La fonctionnalité TurnOn n'est pas disponible.")
        print("Vous devez d'abord appairer l'appareil :")
        print("  python3 apple_tv_power.py pair")
        return

    print("Allumage de l'Apple TV...")
    await asyncio.wait_for(
        atv.power.turn_on(await_new_state=True),
        timeout=OPERATION_TIMEOUT
    )
    print("Apple TV allumée !")


async def turn_off(atv):
    """Éteint l'Apple TV (mise en veille)."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.TurnOff):
        print("La fonctionnalité TurnOff n'est pas disponible.")
        print("Vous devez d'abord appairer l'appareil :")
        print("  python3 apple_tv_power.py pair")
        return

    print("Extinction de l'Apple TV...")
    await asyncio.wait_for(
        atv.power.turn_off(await_new_state=True),
        timeout=OPERATION_TIMEOUT
    )
    print("Apple TV éteinte !")


# =============================================================================
# GESTION DES APPLICATIONS
# =============================================================================

async def list_apps(atv):
    """Liste les applications installées sur l'Apple TV."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.AppList):
        print("La fonctionnalité AppList n'est pas disponible.")
        print("Assurez-vous d'avoir appairé l'appareil.")
        return

    print("Applications installées sur l'Apple TV :\n")
    apps = await atv.apps.app_list()

    for app in sorted(apps, key=lambda a: a.name.lower()):
        print(f"  {app.name}")
        print(f"    Bundle ID : {app.identifier}")
        print()


async def launch_app(atv, app_name):
    """
    Lance une application par son alias ou son bundle ID.

    Cherche d'abord dans apps.json, sinon utilise directement comme bundle ID.
    """
    if not atv.features.in_state(FeatureState.Available, FeatureName.LaunchApp):
        print("La fonctionnalité LaunchApp n'est pas disponible.")
        print("Assurez-vous d'avoir appairé l'appareil.")
        return

    apps_config = load_apps_config()

    # Chercher l'alias dans la config (insensible à la casse)
    app_name_lower = app_name.lower()
    bundle_id = None

    for alias, bid in apps_config.items():
        if alias.lower() == app_name_lower:
            bundle_id = bid
            print(f"Application trouvée : {alias} -> {bundle_id}")
            break

    # Si pas trouvé dans la config, utiliser directement comme bundle ID
    if bundle_id is None:
        bundle_id = app_name
        print(f"Alias non trouvé, utilisation directe du bundle ID : {bundle_id}")

    print(f"Lancement de l'application...")
    try:
        await atv.apps.launch_app(bundle_id)
        print("Application lancée !")
    except Exception as e:
        print(f"Erreur lors du lancement : {e}")
        print("\nPour voir les applications disponibles :")
        print("  python3 apple_tv_power.py apps --device \"Salon\"")


def show_apps_config():
    """Affiche la configuration actuelle des applications."""
    apps_config = load_apps_config()

    print("Configuration des applications (apps.json) :\n")
    print(f"Fichier : {APPS_CONFIG_FILE}\n")

    max_alias_len = max(len(alias) for alias in apps_config.keys()) if apps_config else 10

    for alias, bundle_id in sorted(apps_config.items()):
        print(f"  {alias:<{max_alias_len}}  ->  {bundle_id}")

    print(f"\n{len(apps_config)} application(s) configurée(s).")
    print("\nPour ajouter une app, modifiez le fichier apps.json.")
    print("Pour trouver le bundle ID d'une app, utilisez :")
    print("  python3 apple_tv_power.py apps --device \"Salon\"")


# =============================================================================
# GESTION DES SCÉNARIOS
# =============================================================================

def load_scenarios():
    """
    Charge les scénarios depuis scenarios.json.

    Crée le fichier avec la configuration par défaut s'il n'existe pas.
    Retourne un dictionnaire {nom_scenario: {description, steps}}.
    """
    if not os.path.exists(SCENARIOS_FILE):
        save_scenarios(DEFAULT_SCENARIOS)
        print(f"Fichier de scénarios créé : {SCENARIOS_FILE}")
        return DEFAULT_SCENARIOS.copy()

    try:
        with open(SCENARIOS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Attention : Impossible de lire {SCENARIOS_FILE} ({e})")
        print("Utilisation des scénarios par défaut.")
        return DEFAULT_SCENARIOS.copy()


def save_scenarios(scenarios):
    """Sauvegarde les scénarios dans scenarios.json."""
    try:
        with open(SCENARIOS_FILE, "w") as f:
            json.dump(scenarios, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Erreur lors de la sauvegarde des scénarios : {e}")


def list_scenarios():
    """Affiche la liste des scénarios disponibles."""
    scenarios = load_scenarios()

    print("Scénarios disponibles :\n")
    print(f"{'Nom':<25} {'Description'}")
    print("-" * 70)

    for name, data in sorted(scenarios.items()):
        description = data.get("description", "Pas de description")
        steps_count = len(data.get("steps", []))
        print(f"{name:<25} {description} ({steps_count} étapes)")

    print(f"\nTotal : {len(scenarios)} scénario(s)")
    print(f"Fichier : {SCENARIOS_FILE}")
    print("\nUtilisation :")
    print('  python3 apple_tv_power.py scenario <nom> --device "Salon"')


async def execute_step(atv, step, step_num):
    """
    Exécute une étape d'un scénario.

    Args:
        atv: Connexion à l'Apple TV
        step: Dictionnaire contenant l'action et ses paramètres
        step_num: Numéro de l'étape (pour l'affichage)
    """
    action = step.get("action")
    repeat = step.get("repeat", 1)

    if not action:
        print(f"  [{step_num}] Erreur : action manquante")
        return False

    # Actions de navigation
    navigation_actions = {
        "up": atv.remote_control.up,
        "down": atv.remote_control.down,
        "left": atv.remote_control.left,
        "right": atv.remote_control.right,
        "select": atv.remote_control.select,
        "menu": atv.remote_control.menu,
        "home": atv.remote_control.home,
    }

    # Actions de lecture
    playback_actions = {
        "play": atv.remote_control.play,
        "pause": atv.remote_control.pause,
        "play_pause": atv.remote_control.play_pause,
    }

    for i in range(repeat):
        repeat_info = f" ({i+1}/{repeat})" if repeat > 1 else ""

        if action == "launch":
            app_name = step.get("app")
            if not app_name:
                print(f"  [{step_num}] Erreur : paramètre 'app' manquant pour launch")
                return False
            print(f"  [{step_num}] Lancement de {app_name}...{repeat_info}")
            await launch_app(atv, app_name)

        elif action == "wait":
            seconds = step.get("seconds", 1)
            print(f"  [{step_num}] Attente de {seconds}s...{repeat_info}")
            await asyncio.sleep(seconds)

        elif action in navigation_actions:
            symbols = {"up": "↑", "down": "↓", "left": "←", "right": "→",
                      "select": "●", "menu": "◀", "home": "⌂"}
            print(f"  [{step_num}] {symbols.get(action, '')} {action.capitalize()}{repeat_info}")
            await navigation_actions[action]()

        elif action in playback_actions:
            symbols = {"play": "▶", "pause": "⏸", "play_pause": "⏯"}
            print(f"  [{step_num}] {symbols.get(action, '')} {action.capitalize()}{repeat_info}")
            await playback_actions[action]()

        else:
            print(f"  [{step_num}] Action inconnue : {action}")
            return False

        # Petit délai entre les répétitions
        if repeat > 1 and i < repeat - 1:
            await asyncio.sleep(0.3)

    return True


async def run_scenario(atv, scenario_name):
    """
    Exécute un scénario complet.

    Args:
        atv: Connexion à l'Apple TV
        scenario_name: Nom du scénario à exécuter
    """
    scenarios = load_scenarios()

    if scenario_name not in scenarios:
        print(f"Erreur : scénario '{scenario_name}' non trouvé.")
        print("\nScénarios disponibles :")
        for name in sorted(scenarios.keys()):
            print(f"  - {name}")
        return False

    scenario = scenarios[scenario_name]
    description = scenario.get("description", "Pas de description")
    steps = scenario.get("steps", [])

    print(f"\n▶ Exécution du scénario : {scenario_name}")
    print(f"  {description}")
    print(f"  {len(steps)} étape(s) à exécuter\n")

    for i, step in enumerate(steps, 1):
        success = await execute_step(atv, step, i)
        if not success:
            print(f"\n✗ Scénario interrompu à l'étape {i}")
            return False

    print(f"\n✓ Scénario '{scenario_name}' terminé avec succès !")
    return True


# =============================================================================
# CONTRÔLES DE LECTURE
# =============================================================================

async def play(atv):
    """Lance la lecture."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Play):
        print("La fonctionnalité Play n'est pas disponible.")
        return
    await atv.remote_control.play()
    print("Lecture lancée !")


async def pause(atv):
    """Met en pause la lecture."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Pause):
        print("La fonctionnalité Pause n'est pas disponible.")
        return
    await atv.remote_control.pause()
    print("Lecture en pause !")


async def play_pause(atv):
    """Toggle lecture/pause."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.PlayPause):
        print("La fonctionnalité PlayPause n'est pas disponible.")
        return
    await atv.remote_control.play_pause()
    print("Toggle lecture/pause effectué !")


async def stop(atv):
    """Arrête la lecture."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Stop):
        print("La fonctionnalité Stop n'est pas disponible.")
        return
    await atv.remote_control.stop()
    print("Lecture arrêtée !")


async def next_track(atv):
    """Passe à la piste suivante."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Next):
        print("La fonctionnalité Next n'est pas disponible.")
        return
    await atv.remote_control.next()
    print("Piste suivante !")


async def previous_track(atv):
    """Revient à la piste précédente."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Previous):
        print("La fonctionnalité Previous n'est pas disponible.")
        return
    await atv.remote_control.previous()
    print("Piste précédente !")


# =============================================================================
# CONTRÔLES TÉLÉCOMMANDE
# =============================================================================

async def remote_up(atv):
    """Flèche haut."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Up):
        print("La fonctionnalité Up n'est pas disponible.")
        return
    await atv.remote_control.up()
    print("↑ Haut")


async def remote_down(atv):
    """Flèche bas."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Down):
        print("La fonctionnalité Down n'est pas disponible.")
        return
    await atv.remote_control.down()
    print("↓ Bas")


async def remote_left(atv):
    """Flèche gauche."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Left):
        print("La fonctionnalité Left n'est pas disponible.")
        return
    await atv.remote_control.left()
    print("← Gauche")


async def remote_right(atv):
    """Flèche droite."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Right):
        print("La fonctionnalité Right n'est pas disponible.")
        return
    await atv.remote_control.right()
    print("→ Droite")


async def remote_select(atv):
    """Bouton OK/Sélection."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Select):
        print("La fonctionnalité Select n'est pas disponible.")
        return
    await atv.remote_control.select()
    print("● Sélection")


async def remote_menu(atv):
    """Bouton Menu (retour)."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Menu):
        print("La fonctionnalité Menu n'est pas disponible.")
        return
    await atv.remote_control.menu()
    print("◀ Menu")


async def remote_home(atv):
    """Bouton Home."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Home):
        print("La fonctionnalité Home n'est pas disponible.")
        return
    await atv.remote_control.home()
    print("⌂ Home")


# =============================================================================
# CONTRÔLES VOLUME
# =============================================================================

async def volume_up(atv):
    """Augmente le volume."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.VolumeUp):
        print("La fonctionnalité VolumeUp n'est pas disponible.")
        return
    await atv.audio.volume_up()
    print("🔊 Volume +")


async def volume_down(atv):
    """Baisse le volume."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.VolumeDown):
        print("La fonctionnalité VolumeDown n'est pas disponible.")
        return
    await atv.audio.volume_down()
    print("🔉 Volume -")


async def set_volume(atv, level):
    """Règle le volume à un niveau spécifique (0-100)."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.SetVolume):
        print("La fonctionnalité SetVolume n'est pas disponible.")
        return

    level = max(0, min(100, level))  # Clamp entre 0 et 100
    await atv.audio.set_volume(level)
    print(f"🔊 Volume réglé à {level}%")


async def get_volume(atv):
    """Affiche le volume actuel."""
    if not atv.features.in_state(FeatureState.Available, FeatureName.Volume):
        print("La fonctionnalité Volume n'est pas disponible.")
        return None

    volume = atv.audio.volume
    print(f"🔊 Volume actuel : {volume}%")
    return volume


# =============================================================================
# PARSING DES ARGUMENTS
# =============================================================================

def parse_args():
    """
    Parse les arguments de la ligne de commande.

    Retourne (command, device_selector, extra_arg) où:
    - command: la commande à exécuter
    - device_selector: nom ou index de l'appareil (ou None)
    - extra_arg: argument supplémentaire (ex: niveau de volume ou nom d'app)
    """
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    device_selector = None
    extra_arg = None

    # Chercher l'option --device
    device_idx = None
    if "--device" in sys.argv:
        try:
            device_idx = sys.argv.index("--device")
            device_value = sys.argv[device_idx + 1]

            # Essayer de convertir en int (index)
            try:
                device_selector = int(device_value)
            except ValueError:
                # C'est un nom
                device_selector = device_value
        except IndexError:
            print("Erreur : --device nécessite une valeur (nom ou index)")
            sys.exit(1)

    # Chercher un argument supplémentaire (pour volume ou nom d'app)
    for i, arg in enumerate(sys.argv[2:], start=2):
        # Ignorer --device et sa valeur
        if arg == "--device":
            continue
        if device_idx is not None and i == device_idx + 1:
            continue

        # Pour volume, essayer de convertir en int
        if command == "volume":
            try:
                extra_arg = int(arg)
                break
            except ValueError:
                pass
        # Pour launch, prendre le premier argument comme nom d'app
        elif command == "launch":
            extra_arg = arg
            break
        # Pour scenario, prendre le premier argument comme nom du scénario
        elif command == "scenario":
            extra_arg = arg
            break

    return command, device_selector, extra_arg


def select_device(devices, device_selector):
    """
    Sélectionne un appareil parmi la liste.

    - Si device_selector est un int, utilise comme index
    - Si device_selector est un str, cherche par nom
    - Si device_selector est None, demande à l'utilisateur
    """
    if len(devices) == 1 and device_selector is None:
        return devices[0]

    # Sélection par index
    if isinstance(device_selector, int):
        if 0 <= device_selector < len(devices):
            return devices[device_selector]
        else:
            print(f"Erreur : index {device_selector} invalide (0-{len(devices)-1})")
            sys.exit(1)

    # Sélection par nom
    if isinstance(device_selector, str):
        for device in devices:
            if device_selector.lower() in device.name.lower():
                return device
        print(f"Erreur : aucun appareil trouvé avec le nom '{device_selector}'")
        print("Appareils disponibles :")
        for device in devices:
            print(f"  - {device.name}")
        sys.exit(1)

    # Demander à l'utilisateur
    print(f"{len(devices)} appareils trouvés :\n")
    for i, device in enumerate(devices):
        print(f"  [{i}] {device.name} ({device.address})")
    print()

    while True:
        try:
            choice = input(f"Choisissez un appareil (0-{len(devices)-1}) : ")
            index = int(choice)
            if 0 <= index < len(devices):
                return devices[index]
            else:
                print("Numéro invalide, réessayez.")
        except ValueError:
            print("Entrez un numéro valide.")


# Dictionnaire des commandes disponibles
COMMANDS = {
    # Alimentation
    "on": turn_on,
    "off": turn_off,
    "status": get_power_status,

    # Lecture
    "play": play,
    "pause": pause,
    "play_pause": play_pause,
    "stop": stop,
    "next": next_track,
    "previous": previous_track,

    # Télécommande
    "up": remote_up,
    "down": remote_down,
    "left": remote_left,
    "right": remote_right,
    "select": remote_select,
    "menu": remote_menu,
    "home": remote_home,

    # Volume (sans argument)
    "volume_up": volume_up,
    "volume_down": volume_down,
}


async def main():
    """Point d'entrée principal du script."""
    command, device_selector, extra_arg = parse_args()

    if command == "scan":
        await scan_devices()
        return

    if command == "apps_config":
        show_apps_config()
        return

    if command == "scenarios":
        list_scenarios()
        return

    # Pour toutes les autres commandes, on doit d'abord scanner
    loop = asyncio.get_event_loop()
    devices = await pyatv.scan(loop, timeout=SCAN_TIMEOUT)

    if not devices:
        print("Aucune Apple TV trouvée. Assurez-vous qu'elle est sur le même réseau.")
        sys.exit(1)

    # Sélection de l'appareil
    device_config = select_device(devices, device_selector)
    print(f"\nAppareil sélectionné : {device_config.name}")

    if command == "pair":
        await pair_device(device_config)
        return

    # Pour les autres commandes, on doit se connecter d'abord
    atv = None
    try:
        atv = await connect_to_device(device_config)

        # Commandes avec argument (volume)
        if command == "volume":
            if extra_arg is not None:
                await set_volume(atv, extra_arg)
            else:
                await get_volume(atv)

        # Commande apps - lister les applications installées
        elif command == "apps":
            await list_apps(atv)

        # Commande apps_sync - synchroniser apps.json avec les apps installées
        elif command == "apps_sync":
            await sync_apps_config(atv)

        # Commande launch - lancer une application
        elif command == "launch":
            if extra_arg:
                await launch_app(atv, extra_arg)
            else:
                print("Erreur : specifiez le nom de l'application a lancer.")
                print("Utilisation : python3 apple_tv_power.py launch <app> --device \"Salon\"")
                print("\nPour voir les alias disponibles :")
                print("  python3 apple_tv_power.py apps_config")

        # Commande scenario - exécuter un scénario
        elif command == "scenario":
            if extra_arg:
                await run_scenario(atv, extra_arg)
            else:
                print("Erreur : specifiez le nom du scénario à exécuter.")
                print('Utilisation : python3 apple_tv_power.py scenario <nom> --device "Salon"')
                print("\nPour voir les scénarios disponibles :")
                print("  python3 apple_tv_power.py scenarios")

        # Commandes standard
        elif command in COMMANDS:
            await COMMANDS[command](atv)

        else:
            print(f"Commande inconnue : {command}")
            print("\nCommandes disponibles :")
            print("  Alimentation  : on, off, status")
            print("  Lecture       : play, pause, play_pause, stop, next, previous")
            print("  Telecommande  : up, down, left, right, select, menu, home")
            print("  Volume        : volume_up, volume_down, volume [0-100]")
            print("  Applications  : apps, apps_config, apps_sync, launch <app>")
            print("  Scenarios     : scenarios, scenario <nom>")

    except pyatv.exceptions.AuthenticationError:
        print("\nErreur d'authentification !")
        print("Vous devez d'abord appairer l'appareil avec : python3 apple_tv_power.py pair")

    except asyncio.TimeoutError:
        print("\nTimeout : l'Apple TV n'a pas répondu dans les temps.")
        print("Vérifiez qu'elle est allumée et sur le même réseau.")

    except Exception as e:
        print(f"\nErreur : {e}")

    finally:
        # Toujours fermer la connexion proprement
        if atv:
            atv.close()


if __name__ == "__main__":
    asyncio.run(main())
