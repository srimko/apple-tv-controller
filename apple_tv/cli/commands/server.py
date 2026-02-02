"""Commande serveur HTTP."""

from __future__ import annotations

import asyncio

import typer

from ..console import console, print_panel, print_warning
from ..utils import run_async

router = typer.Typer()


@router.command("server")
def server_cmd(
    port: int = typer.Option(8888, "--port", "-p", help="Port du serveur"),
):
    """
    🌐 Lancer le serveur HTTP pour les Raccourcis iOS.
    """
    from ...server import run_server as start_server

    console.print()
    print_panel("🌐 Serveur HTTP", f"Port: {port}")
    console.print()
    console.print("Endpoints:")
    console.print("  [cyan]GET[/cyan]  /health")
    console.print("  [cyan]GET[/cyan]  /scenarios")
    console.print("  [cyan]POST[/cyan] /scenario/{name}?device=Salon")
    console.print("  [cyan]POST[/cyan] /shutdown")
    console.print()
    console.print("[dim]Ctrl+C pour arreter[/dim]")
    console.print()

    try:
        run_async(start_server(port))
    except (KeyboardInterrupt, asyncio.CancelledError):
        print_warning("Serveur arrete")
        raise typer.Exit(0)
