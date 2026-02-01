"""Exceptions personnalisees."""


class AppleTVError(Exception):
    """Exception de base pour les erreurs Apple TV."""


class DeviceNotFoundError(AppleTVError):
    """Appareil non trouve."""


class FeatureNotAvailableError(AppleTVError):
    """Fonctionnalite non disponible."""
