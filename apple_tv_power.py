#!/usr/bin/env python3
"""
Controle Apple TV via pyatv.

Permet de scanner, appairer, controler l'alimentation, la lecture,
la telecommande, le volume, les applications et les scenarios.

Prerequis:
    pip install pyatv aiohttp

Utilisation:
    python apple_tv_power.py <commande> [options]
    python apple_tv_power.py --help

    # Ou avec le package:
    python -m apple_tv <commande> [options]
"""

from apple_tv.cli import run

if __name__ == "__main__":
    run()
