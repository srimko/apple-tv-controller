"""Tests pour apple_tv.config."""

import json
import os
import pytest
from pathlib import Path

from apple_tv.config import load_json, save_json


class TestLoadJson:
    """Tests pour load_json."""

    def test_load_existing_file(self, temp_dir):
        """Charge un fichier JSON existant."""
        filepath = temp_dir / "test.json"
        data = {"key": "value", "number": 42}
        filepath.write_text(json.dumps(data))

        result = load_json(filepath)

        assert result == data

    def test_load_missing_file_returns_default(self, temp_dir):
        """Retourne la valeur par defaut si le fichier n'existe pas."""
        filepath = temp_dir / "missing.json"

        result = load_json(filepath, default={"default": True})

        assert result == {"default": True}

    def test_load_missing_file_returns_empty_dict(self, temp_dir):
        """Retourne un dict vide si pas de default."""
        filepath = temp_dir / "missing.json"

        result = load_json(filepath)

        assert result == {}

    def test_load_invalid_json_returns_default(self, temp_dir):
        """Retourne la valeur par defaut si JSON invalide."""
        filepath = temp_dir / "invalid.json"
        filepath.write_text("not valid json {{{")

        result = load_json(filepath, default={"fallback": True})

        assert result == {"fallback": True}

    def test_load_empty_file_returns_default(self, temp_dir):
        """Retourne la valeur par defaut si fichier vide."""
        filepath = temp_dir / "empty.json"
        filepath.write_text("")

        result = load_json(filepath, default=[])

        assert result == []


class TestSaveJson:
    """Tests pour save_json."""

    def test_save_creates_file(self, temp_dir):
        """Cree un nouveau fichier."""
        filepath = temp_dir / "new.json"
        data = {"test": "data"}

        result = save_json(filepath, data)

        assert result is True
        assert filepath.exists()
        assert json.loads(filepath.read_text()) == data

    def test_save_overwrites_file(self, temp_dir):
        """Ecrase un fichier existant."""
        filepath = temp_dir / "existing.json"
        filepath.write_text('{"old": "data"}')

        save_json(filepath, {"new": "data"})

        assert json.loads(filepath.read_text()) == {"new": "data"}

    def test_save_with_unicode(self, temp_dir):
        """Sauvegarde correctement les caracteres unicode."""
        filepath = temp_dir / "unicode.json"
        data = {"message": "Café résumé naïf"}

        save_json(filepath, data)

        content = filepath.read_text(encoding="utf-8")
        assert "Café" in content
        assert json.loads(content) == data

    def test_save_is_atomic(self, temp_dir):
        """Verifie que la sauvegarde est atomique (pas de fichier .tmp residuel)."""
        filepath = temp_dir / "atomic.json"

        save_json(filepath, {"data": "test"})

        # Pas de fichier temporaire residuel
        tmp_files = list(temp_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_save_secure_sets_permissions(self, temp_dir):
        """Verifie que secure=True applique les permissions 600."""
        filepath = temp_dir / "secure.json"

        save_json(filepath, {"secret": "data"}, secure=True)

        mode = oct(filepath.stat().st_mode)[-3:]
        assert mode == "600"

    def test_save_normal_file_is_readable(self, temp_dir):
        """Verifie que sans secure, le fichier est cree et lisible."""
        filepath = temp_dir / "normal.json"

        save_json(filepath, {"public": "data"})

        # Le fichier existe et peut etre lu
        assert filepath.exists()
        content = filepath.read_text()
        assert "public" in content

    def test_save_complex_data(self, temp_dir):
        """Sauvegarde des structures complexes."""
        filepath = temp_dir / "complex.json"
        data = {
            "list": [1, 2, 3],
            "nested": {"a": {"b": {"c": True}}},
            "null": None,
            "float": 3.14,
        }

        save_json(filepath, data)

        assert json.loads(filepath.read_text()) == data
