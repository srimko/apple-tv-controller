"""Modeles de donnees avec validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

# Actions valides pour les scenarios
VALID_ACTIONS = frozenset({
    "launch", "wait",
    "up", "down", "left", "right",
    "select", "menu", "home",
    "play", "pause", "play_pause",
})


class ValidationError(Exception):
    """Erreur de validation des donnees."""


@dataclass
class ScenarioStep:
    """Etape d'un scenario avec validation."""

    action: str
    app: Optional[str] = None
    seconds: Optional[float] = None
    repeat: int = 1

    def __post_init__(self) -> None:
        """Valide les champs apres initialisation."""
        if self.action not in VALID_ACTIONS:
            raise ValidationError(
                f"Action '{self.action}' invalide. "
                f"Actions valides: {', '.join(sorted(VALID_ACTIONS))}"
            )

        if self.action == "launch" and not self.app:
            raise ValidationError("L'action 'launch' requiert le parametre 'app'")

        if self.action == "wait" and self.seconds is None:
            raise ValidationError("L'action 'wait' requiert le parametre 'seconds'")

        if self.seconds is not None and self.seconds < 0:
            raise ValidationError(f"'seconds' doit etre positif, recu: {self.seconds}")

        if self.repeat < 1:
            raise ValidationError(f"'repeat' doit etre >= 1, recu: {self.repeat}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioStep:
        """Cree une etape depuis un dictionnaire."""
        return cls(
            action=data.get("action", ""),
            app=data.get("app"),
            seconds=data.get("seconds"),
            repeat=data.get("repeat", 1),
        )


@dataclass
class Scenario:
    """Scenario avec validation."""

    name: str
    description: str = ""
    steps: list[ScenarioStep] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Valide les champs apres initialisation."""
        if not self.name:
            raise ValidationError("Le nom du scenario est requis")

        if not self.steps:
            raise ValidationError(f"Le scenario '{self.name}' n'a aucune etape")

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> Scenario:
        """Cree un scenario depuis un dictionnaire."""
        steps_data = data.get("steps", [])
        steps = []

        for i, step_data in enumerate(steps_data, 1):
            try:
                steps.append(ScenarioStep.from_dict(step_data))
            except ValidationError as e:
                raise ValidationError(
                    f"Scenario '{name}', etape {i}: {e}"
                ) from e

        return cls(
            name=name,
            description=data.get("description", ""),
            steps=steps,
        )


def validate_scenarios(data: dict[str, Any]) -> dict[str, Scenario]:
    """Valide et parse tous les scenarios.

    Args:
        data: Dictionnaire brut depuis le JSON.

    Returns:
        Dictionnaire de scenarios valides.

    Raises:
        ValidationError: Si un scenario est invalide.
    """
    scenarios = {}
    errors = []

    for name, scenario_data in data.items():
        try:
            scenarios[name] = Scenario.from_dict(name, scenario_data)
        except ValidationError as e:
            errors.append(str(e))

    if errors:
        raise ValidationError(
            f"{len(errors)} erreur(s) de validation:\n" +
            "\n".join(f"  - {e}" for e in errors)
        )

    return scenarios


def validate_schedule_entry(data: dict[str, Any], index: int) -> None:
    """Valide une entree de planification.

    Args:
        data: Dictionnaire de l'entree.
        index: Index de l'entree (pour les messages d'erreur).

    Raises:
        ValidationError: Si l'entree est invalide.
    """
    prefix = f"Planification [{index}]"

    # Champs requis
    if not data.get("scenario"):
        raise ValidationError(f"{prefix}: 'scenario' requis")

    if not data.get("device"):
        raise ValidationError(f"{prefix}: 'device' requis")

    # Validation time
    time_obj = data.get("time", {})
    if not isinstance(time_obj, dict):
        raise ValidationError(f"{prefix}: 'time' doit etre un objet")

    hour = time_obj.get("hour")
    minute = time_obj.get("minute", 0)

    if hour is None:
        raise ValidationError(f"{prefix}: 'time.hour' requis")

    if not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValidationError(f"{prefix}: 'hour' doit etre entre 0-23")

    if not isinstance(minute, int) or not 0 <= minute <= 59:
        raise ValidationError(f"{prefix}: 'minute' doit etre entre 0-59")

    # Validation weekdays (optionnel)
    weekdays = data.get("weekdays")
    if weekdays is not None:
        if not isinstance(weekdays, list):
            raise ValidationError(f"{prefix}: 'weekdays' doit etre une liste")

        for day in weekdays:
            if not isinstance(day, int) or not 0 <= day <= 6:
                raise ValidationError(
                    f"{prefix}: 'weekdays' doit contenir des entiers 0-6"
                )


def validate_schedules(data: dict[str, Any]) -> None:
    """Valide le fichier schedule.json complet.

    Args:
        data: Dictionnaire brut depuis le JSON.

    Raises:
        ValidationError: Si une planification est invalide.
    """
    schedules = data.get("schedules", [])

    if not isinstance(schedules, list):
        raise ValidationError("'schedules' doit etre une liste")

    errors = []
    for i, entry in enumerate(schedules):
        try:
            validate_schedule_entry(entry, i)
        except ValidationError as e:
            errors.append(str(e))

    if errors:
        raise ValidationError(
            f"{len(errors)} erreur(s) de validation:\n" +
            "\n".join(f"  - {e}" for e in errors)
        )
