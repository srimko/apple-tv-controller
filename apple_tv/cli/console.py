"""Console et helpers d'affichage."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Console Rich globale
console = Console()


def print_error(message: str) -> None:
    """Affiche un message d'erreur."""
    console.print(f"[red]✗[/red] {message}")


def print_success(message: str) -> None:
    """Affiche un message de succes."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Affiche un avertissement."""
    console.print(f"[yellow]![/yellow] {message}")


def print_panel(title: str, subtitle: str = "", border_style: str = "blue") -> None:
    """Affiche un panel."""
    content = f"[bold {border_style}]{title}[/bold {border_style}]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel.fit(content, border_style=border_style))


def create_spinner(description: str = "Chargement..."):
    """Cree un spinner de progression."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )


def create_table(
    title: str,
    columns: list[tuple[str, dict[str, Any]]],
    rows: list[list[str]],
) -> Table:
    """Cree une table Rich.

    Args:
        title: Titre de la table
        columns: Liste de (nom, kwargs) pour chaque colonne
        rows: Liste de lignes (liste de valeurs)

    Returns:
        Table Rich configuree
    """
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col_name, col_kwargs in columns:
        table.add_column(col_name, **col_kwargs)
    for row in rows:
        table.add_row(*row)
    return table
