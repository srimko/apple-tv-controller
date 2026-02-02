"""CLI interactive pour Apple TV Controller."""

from __future__ import annotations

# Supprimer le warning urllib3/LibreSSL sur macOS
import warnings as _warnings
_warnings.filterwarnings("ignore", message=".*urllib3.*OpenSSL.*")

import typer

from .commands.config import config_cmd, scan_cmd, setup_cmd, test_cmd
from .commands.control import apps_cmd, launch_cmd, sleep_cmd, status_cmd, wake_cmd
from .commands.help import reference_cmd
from .commands.scenarios import list_cmd, record_cmd, run_cmd
from .commands.server import server_cmd

# Application principale
app = typer.Typer(
    name="atv",
    help="🍎 Apple TV Controller - Controlez votre Apple TV depuis le terminal",
    add_completion=False,
    no_args_is_help=True,
)

# Enregistrement des commandes avec leurs panels
# Aide
app.command("reference", rich_help_panel="Aide")(reference_cmd)

# Configuration
app.command("config", rich_help_panel="Configuration")(config_cmd)
app.command("setup", rich_help_panel="Configuration")(setup_cmd)
app.command("scan", rich_help_panel="Configuration")(scan_cmd)
app.command("test", rich_help_panel="Configuration")(test_cmd)

# Scenarios
app.command("run", rich_help_panel="Scenarios")(run_cmd)
app.command("list", rich_help_panel="Scenarios")(list_cmd)
app.command("record", rich_help_panel="Scenarios")(record_cmd)

# Controle
app.command("wake", rich_help_panel="Controle")(wake_cmd)
app.command("sleep", rich_help_panel="Controle")(sleep_cmd)
app.command("launch", rich_help_panel="Controle")(launch_cmd)
app.command("status", rich_help_panel="Controle")(status_cmd)

# Applications
app.command("apps", rich_help_panel="Applications")(apps_cmd)

# Serveur
app.command("server", rich_help_panel="Serveur")(server_cmd)


def main():
    """Point d'entree principal."""
    app()


if __name__ == "__main__":
    main()
