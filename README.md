# Apple TV Controller

Script Python pour controler une Apple TV via le reseau local en utilisant la bibliotheque [pyatv](https://pyatv.dev/).

## Quick Start

Controlez votre Apple TV en 4 commandes. Remplacez "Salon" par le nom de votre Apple TV (visible dans Reglages > General > Nom).

```bash
# Installer les dependances
pip install pyatv aiohttp

# Trouver les Apple TV sur votre reseau
python3 apple_tv_power.py scan
# ou: python3 -m apple_tv scan

# Appairer (un code PIN s'affiche sur la TV)
python3 apple_tv_power.py pair -d "Salon"

# Tester : appuie sur le bouton "OK"
python3 apple_tv_power.py select -d "Salon"
```

---

## Installation

```bash
pip install pyatv aiohttp
```

## Configuration initiale

### 1. Scanner les appareils disponibles

```bash
python3 apple_tv_power.py scan
```

Affiche tous les appareils Apple TV/AirPlay sur le reseau avec leur nom, adresse IP et protocoles supportes.

### 2. Appairer avec une Apple TV

```bash
python3 apple_tv_power.py pair -d "Salon"
```

Un code PIN s'affiche sur l'ecran de l'Apple TV. Entrez-le dans le terminal pour valider l'appairage.

Les credentials sont sauvegardes dans `credentials.json` et reutilises automatiquement.

---

## Commandes disponibles

### Aide

```bash
python3 apple_tv_power.py --help           # Aide generale
python3 apple_tv_power.py <commande> --help # Aide pour une commande
```

### Alimentation

| Commande | Description |
|----------|-------------|
| `on` | Allumer l'Apple TV |
| `off` | Eteindre l'Apple TV (mise en veille) |
| `status` | Afficher l'etat d'alimentation |

```bash
python3 apple_tv_power.py on -d "Salon"
python3 apple_tv_power.py off -d "Salon"
python3 apple_tv_power.py status -d "Salon"
```

### Lecture

| Commande | Description |
|----------|-------------|
| `play` | Lancer la lecture |
| `pause` | Mettre en pause |
| `play_pause` | Toggle lecture/pause |
| `stop` | Arreter la lecture |
| `next` | Piste/chapitre suivant |
| `previous` | Piste/chapitre precedent |

```bash
python3 apple_tv_power.py play -d "Salon"
python3 apple_tv_power.py pause -d "Salon"
```

### Telecommande

| Commande | Description |
|----------|-------------|
| `up` | Fleche haut |
| `down` | Fleche bas |
| `left` | Fleche gauche |
| `right` | Fleche droite |
| `select` | Bouton OK/Selection |
| `menu` | Bouton Menu (retour) |
| `home` | Bouton Home (accueil) |

```bash
python3 apple_tv_power.py up -d "Salon"
python3 apple_tv_power.py select -d "Salon"
```

### Volume

| Commande | Description |
|----------|-------------|
| `volume_up` | Augmenter le volume |
| `volume_down` | Baisser le volume |
| `volume` | Afficher le volume actuel |
| `volume <0-100>` | Regler le volume |

```bash
python3 apple_tv_power.py volume -d "Salon"
python3 apple_tv_power.py volume 50 -d "Salon"
```

### Applications

| Commande | Description |
|----------|-------------|
| `apps` | Lister les applications installees |
| `apps_config` | Afficher la configuration des alias |
| `apps_sync` | Synchroniser apps.json avec l'Apple TV |
| `launch <app>` | Lancer une application |

```bash
python3 apple_tv_power.py apps -d "Salon"
python3 apple_tv_power.py apps_config
python3 apple_tv_power.py launch netflix -d "Salon"
```

#### Configuration des applications (apps.json)

Le fichier `apps.json` contient les alias pour les applications :

```json
{
  "netflix": "com.netflix.Netflix",
  "youtube": "com.google.ios.youtube",
  "disney": "com.disney.disneyplus"
}
```

### Scenarios

Les scenarios permettent d'automatiser des sequences d'actions.

| Commande | Description |
|----------|-------------|
| `scenarios` | Lister les scenarios disponibles |
| `scenario <nom>` | Executer un scenario |

```bash
python3 apple_tv_power.py scenarios
python3 apple_tv_power.py scenario netflix_profil1 -d "Salon"
```

#### Configuration des scenarios (scenarios.json)

```json
{
  "netflix_profil1": {
    "description": "Lancer Netflix et selectionner le premier profil",
    "steps": [
      {"action": "launch", "app": "netflix"},
      {"action": "wait", "seconds": 3},
      {"action": "select"}
    ]
  }
}
```

**Actions disponibles :**

| Action | Parametres | Description |
|--------|------------|-------------|
| `launch` | `app` | Lancer une application |
| `wait` | `seconds` | Attendre N secondes |
| `up/down/left/right` | `repeat` (optionnel) | Navigation |
| `select/menu/home` | `repeat` (optionnel) | Boutons |
| `play/pause/play_pause` | - | Controle lecture |

### Planification

Executez automatiquement des scenarios a des heures definies.

| Commande | Description |
|----------|-------------|
| `schedules` | Lister les planifications |
| `schedule-add` | Ajouter une planification (interactif) |
| `schedule-remove <id>` | Supprimer une planification |
| `scheduler` | Lancer le daemon |
| `scheduler --daemon` | Lancer en arriere-plan |

### Serveur HTTP

Lancez un serveur HTTP pour declencher des scenarios depuis l'app Raccourcis iOS ou tout autre client HTTP.

| Commande | Description |
|----------|-------------|
| `server` | Lancer le serveur HTTP (port 8888) |
| `server --port 9000` | Lancer sur un port specifique |

```bash
# Lister les planifications
python3 apple_tv_power.py schedules

# Ajouter une planification (interactif)
python3 apple_tv_power.py schedule-add

# Supprimer la planification #0
python3 apple_tv_power.py schedule-remove 0

# Lancer le daemon (premier plan)
python3 apple_tv_power.py scheduler

# Lancer le daemon en arriere-plan
python3 apple_tv_power.py scheduler --daemon
```

#### Configuration des planifications (schedule.json)

```json
{
  "schedules": [
    {
      "scenario": "netflix_profil1",
      "device": "Salon",
      "time": {"hour": 20, "minute": 0},
      "weekdays": [1, 2, 3, 4, 5],
      "enabled": true
    }
  ]
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `scenario` | string | Nom du scenario (de scenarios.json) |
| `device` | string | Nom de l'Apple TV |
| `time` | object | `{"hour": 0-23, "minute": 0-59}` |
| `weekdays` | array | Jours (0=Dim, 1=Lun, ..., 6=Sam). Optionnel |
| `enabled` | bool | Activer/desactiver sans supprimer |

#### API HTTP

Lancer le serveur :
```bash
python3 apple_tv_power.py server
```

Endpoints disponibles :

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Verifier que le serveur tourne |
| GET | `/scenarios` | Lister les scenarios disponibles |
| POST | `/scenario/{name}?device=Salon` | Executer un scenario |
| POST | `/shutdown` | Arreter le serveur proprement |

Exemples avec curl :
```bash
# Health check
curl http://localhost:8888/health

# Lister les scenarios
curl http://localhost:8888/scenarios

# Executer un scenario
curl -X POST "http://localhost:8888/scenario/netflix_profil1?device=Salon"

# Arreter le serveur
curl -X POST http://localhost:8888/shutdown
```

#### Usage avec Raccourcis iOS

1. Ouvrir l'app Raccourcis
2. Creer un nouveau raccourci
3. Ajouter l'action "Obtenir le contenu de l'URL"
4. Configurer :
   - URL : `http://192.168.1.XX:8888/scenario/netflix_profil1?device=Salon`
   - Methode : POST
5. Optionnel : Ajouter "Afficher le resultat" pour voir la reponse

---

## Options globales

| Option | Description |
|--------|-------------|
| `-d, --device` | Nom ou index de l'appareil |
| `-v, --verbose` | Mode debug |
| `-h, --help` | Aide |

**Selection de l'appareil :**

```bash
# Par nom (recherche partielle)
python3 apple_tv_power.py on -d "Salon"

# Par index
python3 apple_tv_power.py on -d 0

# Interactif (si plusieurs appareils)
python3 apple_tv_power.py on
```

---

## Fichiers

| Fichier | Description |
|---------|-------------|
| `apple_tv_power.py` | Point d'entree (wrapper) |
| `apple_tv/` | Package Python |
| `apple_tv/cli.py` | Interface ligne de commande |
| `apple_tv/config.py` | Configuration et constantes |
| `apple_tv/connection.py` | Connexion et appairage |
| `apple_tv/controls.py` | Controles (power, lecture, volume) |
| `apple_tv/apps.py` | Gestion des applications |
| `apple_tv/scenarios.py` | Execution des scenarios |
| `apple_tv/scheduler.py` | Planification |
| `apple_tv/server.py` | Serveur HTTP |
| `credentials.json` | Credentials d'appairage |
| `apps.json` | Alias des applications |
| `scenarios.json` | Configuration des scenarios |
| `schedule.json` | Planifications horaires |

---

## Exemples

### Lancer Netflix a 20h en semaine

```bash
# Ajouter via l'interface interactive
python3 apple_tv_power.py schedule-add

# Ou editer schedule.json directement
```

### Script d'extinction automatique

```bash
#!/bin/bash
python3 apple_tv_power.py off -d "Salon"
```

### Demarrer le scheduler au boot (macOS)

Creer `~/Library/LaunchAgents/com.appletv.scheduler.plist` :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.appletv.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/chemin/vers/apple_tv_power.py</string>
        <string>scheduler</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.appletv.scheduler.plist
```

---

## Depannage

### "Aucune Apple TV trouvee"

- Verifiez que l'Apple TV est allumee
- Verifiez que vous etes sur le meme reseau Wi-Fi

### "Erreur d'authentification"

Refaites un appairage :
```bash
python3 apple_tv_power.py pair -d "Salon"
```

### "Fonctionnalite non disponible"

Vous devez d'abord appairer l'appareil :
```bash
python3 apple_tv_power.py pair -d "Salon"
```

### Mode debug

Utilisez `-v` pour plus de details :
```bash
python3 apple_tv_power.py on -d "Salon" -v
```
