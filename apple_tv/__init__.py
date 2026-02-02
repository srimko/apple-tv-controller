"""
Apple TV Controller - Controle Apple TV via pyatv.

Usage:
    python -m apple_tv <commande> [options]
    python -m apple_tv --help
"""

__version__ = "1.0.0"

from .apps import get_bundle_id, launch_app, list_apps, load_apps_config, sync_apps_config
from .config import (
    APPS_CONFIG_FILE,
    CREDENTIALS_FILE,
    SCENARIOS_FILE,
    SCHEDULE_FILE,
    logger,
    setup_logging,
)
from .connection import (
    connect_atv,
    pair_device,
    scan_devices,
    select_device,
)
from .controls import (
    RemoteButton,
    cmd_next,
    cmd_pause,
    cmd_play,
    cmd_play_pause,
    cmd_previous,
    cmd_stop,
    get_power_status,
    get_volume,
    press_button,
    set_volume,
    turn_off,
    turn_on,
    volume_down,
    volume_up,
)
from .exceptions import AppleTVError, DeviceNotFoundError, FeatureNotAvailableError
from .models import ValidationError, validate_scenarios, validate_schedules
from .scenarios import load_scenarios, run_scenario
from .scheduler import ScheduleEntry, load_schedules, run_scheduler, save_schedules
from .server import run_server

__all__ = [
    # Config
    "APPS_CONFIG_FILE",
    "CREDENTIALS_FILE",
    "SCENARIOS_FILE",
    "SCHEDULE_FILE",
    "logger",
    "setup_logging",
    # Exceptions
    "AppleTVError",
    "DeviceNotFoundError",
    "FeatureNotAvailableError",
    "ValidationError",
    # Validation
    "validate_scenarios",
    "validate_schedules",
    # Connection
    "connect_atv",
    "pair_device",
    "scan_devices",
    "select_device",
    # Controls
    "RemoteButton",
    "cmd_next",
    "cmd_pause",
    "cmd_play",
    "cmd_play_pause",
    "cmd_previous",
    "cmd_stop",
    "get_power_status",
    "get_volume",
    "press_button",
    "set_volume",
    "turn_off",
    "turn_on",
    "volume_down",
    "volume_up",
    # Apps
    "get_bundle_id",
    "launch_app",
    "list_apps",
    "load_apps_config",
    "sync_apps_config",
    # Scenarios
    "load_scenarios",
    "run_scenario",
    # Scheduler
    "ScheduleEntry",
    "load_schedules",
    "run_scheduler",
    "save_schedules",
    # Server
    "run_server",
]
