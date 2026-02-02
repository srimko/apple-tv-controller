"""Tests pour apple_tv.models (validation)."""

import pytest

from apple_tv.models import (
    DEFAULT_ACTION_DELAY,
    ScenarioStep,
    Scenario,
    ValidationError,
    validate_scenarios,
    validate_schedule_entry,
    validate_schedules,
    VALID_ACTIONS,
)


class TestScenarioStep:
    """Tests pour ScenarioStep."""

    def test_valid_launch_step(self):
        """Etape launch valide."""
        step = ScenarioStep(action="launch", app="netflix")

        assert step.action == "launch"
        assert step.app == "netflix"

    def test_valid_wait_step(self):
        """Etape wait valide."""
        step = ScenarioStep(action="wait", seconds=3.5)

        assert step.seconds == 3.5

    def test_valid_navigation_step(self):
        """Etape navigation valide."""
        step = ScenarioStep(action="up", repeat=3)

        assert step.action == "up"
        assert step.repeat == 3

    def test_invalid_action_raises(self):
        """Action invalide leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioStep(action="invalid_action")

        assert "invalide" in str(exc_info.value)

    def test_launch_without_app_raises(self):
        """launch sans app leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioStep(action="launch")

        assert "app" in str(exc_info.value)

    def test_wait_without_seconds_raises(self):
        """wait sans seconds leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioStep(action="wait")

        assert "seconds" in str(exc_info.value)

    def test_negative_seconds_raises(self):
        """seconds negatif leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioStep(action="wait", seconds=-1)

        assert "positif" in str(exc_info.value)

    def test_zero_repeat_raises(self):
        """repeat=0 leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioStep(action="select", repeat=0)

        assert "repeat" in str(exc_info.value)

    def test_default_delay(self):
        """Delay par defaut est 0.5 seconde."""
        step = ScenarioStep(action="select")

        assert step.delay == DEFAULT_ACTION_DELAY
        assert step.delay == 0.5

    def test_custom_delay(self):
        """Delay personnalise."""
        step = ScenarioStep(action="down", delay=1.0)

        assert step.delay == 1.0

    def test_negative_delay_raises(self):
        """delay negatif leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioStep(action="select", delay=-0.5)

        assert "delay" in str(exc_info.value)

    def test_zero_delay_is_valid(self):
        """delay=0 est valide (pas de pause)."""
        step = ScenarioStep(action="select", delay=0)

        assert step.delay == 0

    def test_from_dict(self):
        """Creation depuis un dictionnaire."""
        data = {"action": "down", "repeat": 2}

        step = ScenarioStep.from_dict(data)

        assert step.action == "down"
        assert step.repeat == 2
        assert step.delay == DEFAULT_ACTION_DELAY

    def test_from_dict_with_delay(self):
        """Creation depuis un dictionnaire avec delay."""
        data = {"action": "up", "delay": 1.5}

        step = ScenarioStep.from_dict(data)

        assert step.action == "up"
        assert step.delay == 1.5

    def test_all_valid_actions(self):
        """Toutes les actions valides sont acceptees."""
        for action in VALID_ACTIONS:
            if action == "launch":
                step = ScenarioStep(action=action, app="test")
            elif action == "wait":
                step = ScenarioStep(action=action, seconds=1)
            elif action == "scenario":
                step = ScenarioStep(action=action, name="test_scenario")
            else:
                step = ScenarioStep(action=action)

            assert step.action == action


class TestScenario:
    """Tests pour Scenario."""

    def test_valid_scenario(self, sample_scenarios):
        """Scenario valide."""
        data = sample_scenarios["test_scenario"]

        scenario = Scenario.from_dict("test_scenario", data)

        assert scenario.name == "test_scenario"
        assert len(scenario.steps) == 3

    def test_empty_name_raises(self):
        """Nom vide leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Scenario(name="", steps=[ScenarioStep(action="select")])

        assert "nom" in str(exc_info.value)

    def test_empty_steps_raises(self):
        """Scenario sans etapes leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Scenario(name="empty", steps=[])

        assert "etape" in str(exc_info.value)

    def test_invalid_step_reports_position(self, sample_scenarios):
        """Erreur dans une etape indique la position."""
        data = {
            "description": "Test",
            "steps": [
                {"action": "select"},
                {"action": "invalid"},  # Etape 2 invalide
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            Scenario.from_dict("test", data)

        assert "etape 2" in str(exc_info.value)


class TestValidateScenarios:
    """Tests pour validate_scenarios."""

    def test_valid_scenarios(self, sample_scenarios):
        """Scenarios valides passent la validation."""
        result = validate_scenarios(sample_scenarios)

        assert "test_scenario" in result
        assert "simple_nav" in result

    def test_empty_dict_is_valid(self):
        """Dictionnaire vide est valide."""
        result = validate_scenarios({})

        assert result == {}

    def test_multiple_errors_reported(self):
        """Plusieurs erreurs sont reportees ensemble."""
        data = {
            "bad1": {"description": "No steps", "steps": []},
            "bad2": {"description": "Invalid action", "steps": [{"action": "xxx"}]},
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_scenarios(data)

        error_msg = str(exc_info.value)
        assert "2 erreur(s)" in error_msg


class TestValidateScheduleEntry:
    """Tests pour validate_schedule_entry."""

    def test_valid_entry(self, sample_schedules):
        """Entree valide passe la validation."""
        entry = sample_schedules["schedules"][0]

        # Ne doit pas lever d'exception
        validate_schedule_entry(entry, 0)

    def test_missing_scenario_raises(self):
        """Scenario manquant leve ValidationError."""
        entry = {"device": "Salon", "time": {"hour": 10}}

        with pytest.raises(ValidationError) as exc_info:
            validate_schedule_entry(entry, 0)

        assert "scenario" in str(exc_info.value)

    def test_missing_device_raises(self):
        """Device manquant leve ValidationError."""
        entry = {"scenario": "test", "time": {"hour": 10}}

        with pytest.raises(ValidationError) as exc_info:
            validate_schedule_entry(entry, 0)

        assert "device" in str(exc_info.value)

    def test_invalid_hour_raises(self):
        """Heure invalide leve ValidationError."""
        entry = {
            "scenario": "test",
            "device": "Salon",
            "time": {"hour": 25, "minute": 0},
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_schedule_entry(entry, 0)

        assert "hour" in str(exc_info.value)

    def test_invalid_minute_raises(self):
        """Minute invalide leve ValidationError."""
        entry = {
            "scenario": "test",
            "device": "Salon",
            "time": {"hour": 10, "minute": 60},
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_schedule_entry(entry, 0)

        assert "minute" in str(exc_info.value)

    def test_invalid_weekday_raises(self):
        """Jour invalide leve ValidationError."""
        entry = {
            "scenario": "test",
            "device": "Salon",
            "time": {"hour": 10},
            "weekdays": [1, 2, 7],  # 7 est invalide
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_schedule_entry(entry, 0)

        assert "weekdays" in str(exc_info.value)


class TestValidateSchedules:
    """Tests pour validate_schedules."""

    def test_valid_schedules(self, sample_schedules):
        """Planifications valides passent."""
        # Ne doit pas lever d'exception
        validate_schedules(sample_schedules)

    def test_empty_schedules_is_valid(self):
        """Liste vide est valide."""
        validate_schedules({"schedules": []})

    def test_missing_schedules_key(self):
        """Cle 'schedules' manquante utilise liste vide."""
        validate_schedules({})  # Ne doit pas lever

    def test_schedules_not_list_raises(self):
        """schedules non-liste leve ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_schedules({"schedules": "not a list"})

        assert "liste" in str(exc_info.value)
