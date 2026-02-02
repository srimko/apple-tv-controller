# Apple TV Controller

Controlez votre Apple TV depuis le terminal ou via des raccourcis iOS. Basé sur [pyatv](https://pyatv.dev/).

## Table des matieres

- [Demarrage rapide (5 min)](#demarrage-rapide-5-min)
- [Tutoriel : Votre premier scenario](#tutoriel--votre-premier-scenario)
- [Scenarios prets a l'emploi](#scenarios-prets-a-lemploi)
- [Integration Raccourcis iOS](#integration-raccourcis-ios)
- [Reference des commandes](#reference-des-commandes)
- [Depannage](#depannage)

---

## Demarrage rapide (5 min)

### Prerequis

- Python 3.9+
- Apple TV sur le meme reseau Wi-Fi que votre Mac
- Nom de votre Apple TV (visible dans **Reglages > General > Informations > Nom**)

### Etape 1 : Installation

```bash
# Cloner le projet
git clone https://github.com/username/apple-tv-controller.git
cd apple-tv-controller

# Installer les dependances
pip install pyatv aiohttp
```

### Etape 2 : Decouvrir votre Apple TV

```bash
python3 apple_tv_power.py scan
```

Resultat attendu :
```
[0] Salon
    Adresse: 192.168.1.91
    Protocoles: AirPlay, Companion, RAOP
```

> **Pas de resultat ?** Voir [Depannage > Aucune Apple TV trouvee](#aucune-apple-tv-trouvee)

### Etape 3 : Appairer

```bash
python3 apple_tv_power.py pair -d "Salon"
```

1. Un code PIN a 4 chiffres s'affiche sur votre TV
2. Entrez-le dans le terminal
3. Les credentials sont sauvegardes automatiquement

> **Erreur ?** Voir [Depannage > Erreur d'appairage](#erreur-dappairage)

### Etape 4 : Tester

```bash
# Appuyer sur OK
python3 apple_tv_power.py select -d "Salon"

# Naviguer
python3 apple_tv_power.py up -d "Salon"
python3 apple_tv_power.py down -d "Salon"
```

**Vous etes pret !** Continuez avec le tutoriel ci-dessous.

---

## Tutoriel : Votre premier scenario

Un scenario est une sequence d'actions automatisees. Exemple : lancer Netflix et selectionner un profil.

### Etape 1 : Creer le fichier scenarios.json

```bash
# Voir les scenarios existants
python3 apple_tv_power.py scenarios
```

### Etape 2 : Ajouter votre scenario

Editez `scenarios.json` :

```json
{
  "netflix_profil1": {
    "description": "Lancer Netflix et selectionner le 1er profil",
    "steps": [
      {"action": "launch", "app": "netflix"},
      {"action": "wait", "seconds": 4},
      {"action": "select"}
    ]
  }
}
```

### Etape 3 : Executer

```bash
python3 apple_tv_power.py scenario netflix_profil1 -d "Salon"
```

### Etape 4 : Ajuster le timing

Si ca va trop vite, augmentez le `wait` ou ajoutez un `delay` :

```json
{
  "netflix_profil1": {
    "description": "Lancer Netflix (version lente)",
    "steps": [
      {"action": "launch", "app": "netflix"},
      {"action": "wait", "seconds": 5},
      {"action": "down", "delay": 1.0},
      {"action": "select"}
    ]
  }
}
```

### Comprendre les parametres

| Parametre | Description | Defaut |
|-----------|-------------|--------|
| `action` | L'action a executer (obligatoire) | - |
| `wait` + `seconds` | Pause fixe en secondes | - |
| `delay` | Pause apres l'action | 0.5s |
| `repeat` | Nombre de repetitions | 1 |

---

## Scenarios prets a l'emploi

Copiez ces scenarios dans votre `scenarios.json`.

### Netflix - Selectionner un profil

```json
{
  "netflix_profil1": {
    "description": "Netflix - Premier profil",
    "steps": [
      {"action": "launch", "app": "netflix"},
      {"action": "wait", "seconds": 4},
      {"action": "select"}
    ]
  },
  "netflix_profil2": {
    "description": "Netflix - Deuxieme profil",
    "steps": [
      {"action": "launch", "app": "netflix"},
      {"action": "wait", "seconds": 4},
      {"action": "right"},
      {"action": "select"}
    ]
  }
}
```

### YouTube - Accueil

```json
{
  "youtube_home": {
    "description": "Ouvrir YouTube sur l'accueil",
    "steps": [
      {"action": "launch", "app": "youtube"},
      {"action": "wait", "seconds": 3},
      {"action": "menu"},
      {"action": "menu"}
    ]
  }
}
```

### Fermer toutes les apps

```json
{
  "close_apps": {
    "description": "Fermer les apps en arriere-plan",
    "steps": [
      {"action": "home_double"},
      {"action": "wait", "seconds": 1},
      {"action": "swipe_up", "repeat": 5, "delay": 0.3}
    ]
  }
}
```

### Routine du soir

```json
{
  "bonne_nuit": {
    "description": "Fermer les apps et eteindre",
    "steps": [
      {"action": "scenario", "name": "close_apps"},
      {"action": "wait", "seconds": 1},
      {"action": "home"},
      {"action": "wait", "seconds": 0.5}
    ]
  }
}
```

> **Note :** L'action `scenario` permet d'inclure un scenario dans un autre.

### Disney+ - Continuer a regarder

```json
{
  "disney_continue": {
    "description": "Disney+ - Reprendre la lecture",
    "steps": [
      {"action": "launch", "app": "disney"},
      {"action": "wait", "seconds": 4},
      {"action": "down"},
      {"action": "select"}
    ]
  }
}
```

---

## Integration Raccourcis iOS

Declenchez vos scenarios depuis votre iPhone avec l'app Raccourcis.

### Etape 1 : Lancer le serveur HTTP

Sur votre Mac (laissez le terminal ouvert) :

```bash
python3 apple_tv_power.py server
```

Resultat :
```
Serveur HTTP demarre sur http://0.0.0.0:8888
```

### Etape 2 : Trouver l'IP de votre Mac

```bash
ipconfig getifaddr en0
```

Exemple : `192.168.1.50`

### Etape 3 : Tester avec curl

```bash
# Verifier que le serveur repond
curl http://192.168.1.50:8888/health

# Lister les scenarios
curl http://192.168.1.50:8888/scenarios

# Executer un scenario
curl -X POST "http://192.168.1.50:8888/scenario/netflix_profil1?device=Salon"
```

### Etape 4 : Creer le raccourci iOS

1. Ouvrir l'app **Raccourcis** sur iPhone
2. Appuyer sur **+** (nouveau raccourci)
3. **Ajouter une action** > chercher **"Obtenir le contenu de l'URL"**
4. Configurer :
   - **URL** : `http://192.168.1.50:8888/scenario/netflix_profil1?device=Salon`
   - Appuyer sur **Afficher plus**
   - **Methode** : `POST`
5. Renommer le raccourci (ex: "Netflix Salon")
6. Optionnel : **Ajouter a l'ecran d'accueil**

### Etape 5 : Utiliser

- Tap sur l'icone de l'ecran d'accueil
- Ou dire **"Dis Siri, Netflix Salon"**

### Endpoints disponibles

| Methode | URL | Description |
|---------|-----|-------------|
| GET | `/health` | Verifier que le serveur tourne |
| GET | `/scenarios` | Lister les scenarios |
| POST | `/scenario/{nom}?device=Salon` | Executer un scenario |
| POST | `/shutdown` | Arreter le serveur |

### Lancer le serveur au demarrage (macOS)

Creer `~/Library/LaunchAgents/com.appletv.server.plist` :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.appletv.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/chemin/complet/vers/apple_tv_power.py</string>
        <string>server</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.appletv.server.plist
```

---

## Reference des commandes

### Telecommande

| Commande | Description |
|----------|-------------|
| `up`, `down`, `left`, `right` | Navigation |
| `select` | Bouton OK |
| `menu` | Retour |
| `home` | Ecran d'accueil |
| `home_double` | App Switcher (double home) |

### Touch (Swipe)

| Commande | Description |
|----------|-------------|
| `swipe_up`, `swipe_down` | Glissement vertical |
| `swipe_left`, `swipe_right` | Glissement horizontal |

> **Note :** Les swipes sont disponibles uniquement dans les scenarios.

### Lecture

| Commande | Description |
|----------|-------------|
| `play`, `pause`, `play_pause` | Controle lecture |
| `stop` | Arreter |
| `next`, `previous` | Piste suivante/precedente |

### Alimentation

| Commande | Description |
|----------|-------------|
| `on` | Allumer |
| `off` | Eteindre (veille) |
| `status` | Afficher l'etat |

### Volume

| Commande | Description |
|----------|-------------|
| `volume` | Afficher le volume |
| `volume 50` | Regler a 50% |
| `volume_up`, `volume_down` | +/- volume |

### Applications

| Commande | Description |
|----------|-------------|
| `apps` | Lister les apps installees |
| `launch <app>` | Lancer une app |
| `apps_sync` | Synchroniser apps.json |

### Actions de scenario

| Action | Parametres | Description |
|--------|------------|-------------|
| `launch` | `app` | Lancer une application |
| `wait` | `seconds` | Pause fixe |
| `scenario` | `name` | Executer un sous-scenario |
| Navigation | `repeat`, `delay` | up/down/left/right/select/menu/home |
| Swipe | `repeat`, `delay` | swipe_up/down/left/right |
| Lecture | `delay` | play/pause/play_pause |

---

## Depannage

### Aucune Apple TV trouvee

**Symptome :** `python3 apple_tv_power.py scan` ne retourne rien.

**Solutions :**

1. **Verifiez que l'Apple TV est allumee**
   - L'ecran doit etre actif (pas en veille profonde)
   - Essayez d'appuyer sur la telecommande physique d'abord

2. **Verifiez le reseau**
   - Mac et Apple TV doivent etre sur le **meme reseau Wi-Fi**
   - Certains routeurs isolent les appareils (isolation client) - desactivez cette option

3. **Attendez quelques secondes et reessayez**
   - La decouverte peut prendre du temps
   - Essayez : `python3 apple_tv_power.py scan` plusieurs fois

4. **Verifiez le pare-feu Mac**
   - Preferences Systeme > Securite > Pare-feu
   - Ajoutez Python aux exceptions ou desactivez temporairement

### Erreur d'appairage

**Symptome :** Le PIN ne fonctionne pas ou l'appairage echoue.

**Solutions :**

1. **Assurez-vous d'entrer le code rapidement**
   - Le PIN expire apres ~30 secondes

2. **Supprimez les anciens credentials**
   ```bash
   rm credentials.json
   python3 apple_tv_power.py pair -d "Salon"
   ```

3. **Redemarrez l'Apple TV**
   - Reglages > Systeme > Redemarrer

### "Fonctionnalite non disponible"

**Symptome :** Certaines commandes ne fonctionnent pas.

**Solutions :**

1. **Verifiez l'appairage**
   ```bash
   python3 apple_tv_power.py pair -d "Salon"
   ```

2. **Certaines fonctionnalites necessitent que l'Apple TV soit active**
   - Volume : necessite une app ouverte
   - Swipe : necessite tvOS 15+

### Connexion impossible depuis iPhone (Raccourcis)

**Symptome :** "Connexion impossible" dans Raccourcis iOS.

**Solutions :**

1. **Verifiez que le serveur tourne**
   ```bash
   curl http://localhost:8888/health
   ```

2. **Verifiez l'IP**
   ```bash
   ipconfig getifaddr en0
   ```

3. **Testez depuis le Mac avec l'IP externe**
   ```bash
   curl http://192.168.x.x:8888/health
   ```

4. **Verifiez le pare-feu**
   ```bash
   # Desactiver temporairement
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off

   # Tester, puis reactiver
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
   ```

5. **Verifiez que iPhone et Mac sont sur le meme Wi-Fi**

### Erreur 405 Method Not Allowed (Raccourcis)

**Symptome :** Le raccourci retourne "405 Method Not Allowed".

**Solution :** Vous utilisez GET au lieu de POST.

1. Ouvrir le raccourci
2. Appuyer sur l'action "Obtenir le contenu de l'URL"
3. Appuyer sur "Afficher plus"
4. Changer **Methode** de "GET" a **"POST"**

### Timeout lors de l'execution

**Symptome :** "Timeout lors de l'execution du scenario".

**Solutions :**

1. **Reduisez les delais** dans votre scenario
   ```json
   {"action": "down", "delay": 0.3}
   ```

2. **Le timeout par defaut est de 2 minutes**
   - Si votre scenario est tres long, divisez-le en plusieurs

### Mode debug

Pour plus de details sur les erreurs :

```bash
python3 apple_tv_power.py scenario mon_scenario -d "Salon" -v
```

---

## Fichiers de configuration

| Fichier | Description |
|---------|-------------|
| `credentials.json` | Credentials d'appairage (ne pas partager) |
| `apps.json` | Alias des applications |
| `scenarios.json` | Vos scenarios |
| `schedule.json` | Planifications horaires |

### apps.json

Alias pour les bundle IDs des applications :

```json
{
  "netflix": "com.netflix.Netflix",
  "youtube": "com.google.ios.youtube",
  "disney": "com.disney.disneyplus",
  "prime": "com.amazon.aiv.AIVApp"
}
```

> Utilisez `python3 apple_tv_power.py apps -d "Salon"` pour voir les bundle IDs.

---

## Licence

MIT
