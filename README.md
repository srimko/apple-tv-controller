# Apple TV Controller

Script Python pour contrôler une Apple TV via le réseau local en utilisant la bibliothèque [pyatv](https://pyatv.dev/).

## Installation

```bash
pip install pyatv
```

## Configuration initiale

### 1. Scanner les appareils disponibles

```bash
python3 apple_tv_power.py scan
```

Affiche tous les appareils Apple TV/AirPlay sur le réseau avec leur nom, adresse IP et protocoles supportés.

### 2. Appairer avec une Apple TV

```bash
python3 apple_tv_power.py pair --device "Salon"
```

Un code PIN s'affiche sur l'écran de l'Apple TV. Entrez-le dans le terminal pour valider l'appairage.

Les credentials sont sauvegardés dans `credentials.json` et réutilisés automatiquement.

**Synchronisation automatique des applications :** Après un appairage réussi, le script récupère automatiquement la liste des applications installées sur l'Apple TV et met à jour le fichier `apps.json` avec les nouvelles applications trouvées.

---

## Commandes disponibles

### Alimentation

| Commande | Description |
|----------|-------------|
| `on` | Allumer l'Apple TV |
| `off` | Éteindre l'Apple TV (mise en veille) |
| `status` | Afficher l'état d'alimentation et les fonctionnalités disponibles |

```bash
python3 apple_tv_power.py on --device "Salon"
python3 apple_tv_power.py off --device "Salon"
python3 apple_tv_power.py status --device "Salon"
```

### Lecture

| Commande | Description |
|----------|-------------|
| `play` | Lancer la lecture |
| `pause` | Mettre en pause |
| `play_pause` | Toggle lecture/pause |
| `stop` | Arrêter la lecture |
| `next` | Piste/chapitre suivant |
| `previous` | Piste/chapitre précédent |

```bash
python3 apple_tv_power.py play --device "Salon"
python3 apple_tv_power.py pause --device "Salon"
python3 apple_tv_power.py play_pause --device "Salon"
python3 apple_tv_power.py next --device "Salon"
python3 apple_tv_power.py previous --device "Salon"
```

### Télécommande

| Commande | Description |
|----------|-------------|
| `up` | Flèche haut |
| `down` | Flèche bas |
| `left` | Flèche gauche |
| `right` | Flèche droite |
| `select` | Bouton OK/Sélection |
| `menu` | Bouton Menu (retour) |
| `home` | Bouton Home (accueil) |

```bash
python3 apple_tv_power.py up --device "Salon"
python3 apple_tv_power.py down --device "Salon"
python3 apple_tv_power.py left --device "Salon"
python3 apple_tv_power.py right --device "Salon"
python3 apple_tv_power.py select --device "Salon"
python3 apple_tv_power.py menu --device "Salon"
python3 apple_tv_power.py home --device "Salon"
```

### Volume

| Commande | Description |
|----------|-------------|
| `volume_up` | Augmenter le volume |
| `volume_down` | Baisser le volume |
| `volume` | Afficher le volume actuel |
| `volume <0-100>` | Régler le volume à un niveau précis |

```bash
python3 apple_tv_power.py volume_up --device "Salon"
python3 apple_tv_power.py volume_down --device "Salon"
python3 apple_tv_power.py volume --device "Salon"
python3 apple_tv_power.py volume 50 --device "Salon"
```

### Applications

| Commande | Description |
|----------|-------------|
| `apps` | Lister les applications installées sur l'Apple TV |
| `apps_config` | Afficher la configuration des alias (apps.json) |
| `apps_sync` | Synchroniser apps.json avec les apps installées |
| `launch <app>` | Lancer une application par son alias ou bundle ID |

```bash
python3 apple_tv_power.py apps --device "Salon"
python3 apple_tv_power.py apps_config
python3 apple_tv_power.py apps_sync --device "Salon"
python3 apple_tv_power.py launch netflix --device "Salon"
```

#### Configuration des applications (apps.json)

Le fichier `apps.json` contient les alias pour les applications. Il est :
- **Créé automatiquement** avec des apps courantes lors de la première utilisation
- **Mis à jour automatiquement** après chaque appairage (`pair`) avec les apps installées sur l'Apple TV

Exemple de contenu :
```json
{
  "netflix": "com.netflix.Netflix",
  "youtube": "com.google.ios.youtube",
  "disney": "com.disney.disneyplus",
  "prime": "com.amazon.aiv.AIVApp",
  "apple_tv": "com.apple.TVWatchList",
  "spotify": "com.spotify.client",
  "twitch": "tv.twitch"
}
```

**Personnalisation :** Vous pouvez modifier les alias dans `apps.json` selon vos préférences. Les alias personnalisés sont conservés lors des synchronisations.

---

## Options

### Sélection de l'appareil

Si plusieurs appareils sont détectés, vous pouvez spécifier lequel utiliser :

**Par nom (recherche partielle) :**
```bash
python3 apple_tv_power.py on --device "Salon"
```

**Par index :**
```bash
python3 apple_tv_power.py on --device 1
```

Si `--device` n'est pas spécifié et plusieurs appareils sont trouvés, le script demande de choisir.

---

## Fichiers

| Fichier | Description |
|---------|-------------|
| `apple_tv_power.py` | Script principal |
| `credentials.json` | Credentials d'appairage (créé automatiquement) |
| `apps.json` | Configuration des alias d'applications (créé automatiquement) |

---

## Dépannage

### "Aucune fonctionnalité d'alimentation disponible"

Vous devez d'abord appairer l'appareil :
```bash
python3 apple_tv_power.py pair --device "Salon"
```

### "Aucune Apple TV trouvée"

- Vérifiez que l'Apple TV est allumée
- Vérifiez que vous êtes sur le même réseau Wi-Fi
- Attendez quelques secondes et réessayez

### "Erreur d'authentification"

Les credentials ont peut-être expiré. Refaites un appairage :
```bash
python3 apple_tv_power.py pair --device "Salon"
```

### "Timeout"

L'Apple TV n'a pas répondu dans les 10 secondes. Vérifiez qu'elle est accessible sur le réseau.

---

## Protocoles utilisés

| Protocole | Fonctionnalités |
|-----------|-----------------|
| **Companion** | Power on/off, télécommande, apps (le plus fiable) |
| **MRP** | Télécommande, métadonnées, power (moins fiable) |
| **AirPlay** | Streaming audio/vidéo |
| **RAOP** | Streaming audio uniquement |

Le script utilise principalement le protocole **Companion** pour les fonctionnalités d'alimentation car il est le plus fiable.

---

## Exemples d'utilisation

### Allumer la TV et naviguer
```bash
python3 apple_tv_power.py on --device "Salon"
sleep 5
python3 apple_tv_power.py right --device "Salon"
python3 apple_tv_power.py select --device "Salon"
```

### Script d'extinction automatique
```bash
#!/bin/bash
python3 apple_tv_power.py off --device "Salon"
echo "Apple TV éteinte"
```

### Contrôle du volume
```bash
# Baisser le volume de 5 crans
for i in {1..5}; do
    python3 apple_tv_power.py volume_down --device "Salon"
    sleep 0.5
done
```
