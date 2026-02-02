"""Fixtures pytest."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Cree un repertoire temporaire pour les tests."""
    dirpath = tempfile.mkdtemp()
    yield Path(dirpath)
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def sample_scenarios():
    """Scenarios valides pour les tests."""
    return {
        "test_scenario": {
            "description": "Scenario de test",
            "steps": [
                {"action": "launch", "app": "netflix"},
                {"action": "wait", "seconds": 2},
                {"action": "select"},
            ],
        },
        "simple_nav": {
            "description": "Navigation simple",
            "steps": [
                {"action": "up"},
                {"action": "down", "repeat": 3},
                {"action": "select"},
            ],
        },
    }


@pytest.fixture
def sample_schedules():
    """Planifications valides pour les tests."""
    return {
        "schedules": [
            {
                "scenario": "test_scenario",
                "device": "Salon",
                "time": {"hour": 20, "minute": 0},
                "weekdays": [1, 2, 3, 4, 5],
                "enabled": True,
            },
            {
                "scenario": "simple_nav",
                "device": "Chambre",
                "time": {"hour": 8, "minute": 30},
                "enabled": False,
            },
        ]
    }
