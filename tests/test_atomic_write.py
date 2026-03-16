"""Tests for atomic JSON write utilities."""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.utils.atomic_io import atomic_write_json, backup_rotate


class TestAtomicWriteJson:

    def test_creates_file(self, tmp_path):
        path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        atomic_write_json(path, data)

        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded == data

    def test_no_temp_left(self, tmp_path):
        path = tmp_path / "test.json"
        atomic_write_json(path, {"a": 1})

        tmp_file = path.with_suffix(".json.tmp")
        assert not tmp_file.exists()

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "test.json"
        path.write_text('{"old": true}')

        atomic_write_json(path, {"new": True})

        loaded = json.loads(path.read_text())
        assert loaded == {"new": True}

    def test_preserves_existing_on_error(self, tmp_path):
        path = tmp_path / "test.json"
        original = {"original": True}
        path.write_text(json.dumps(original))

        # Force an error by writing to an invalid path (directory as file)
        bad_path = tmp_path / "nonexistent_dir" / "deep" / "test.json"
        with pytest.raises((OSError, FileNotFoundError)):
            atomic_write_json(bad_path, {"bad": True})

        # Original file at valid path should be unchanged
        loaded = json.loads(path.read_text())
        assert loaded == original


class TestBackupRotate:

    def test_creates_backups(self, tmp_path):
        path = tmp_path / "registry.json"

        for i in range(6):
            path.write_text(json.dumps({"version": i}))
            backup_rotate(path, keep=5)

        # Should have bak.1 through bak.5
        for i in range(1, 6):
            bak = path.with_name(f"registry.bak.{i}.json")
            assert bak.exists(), f"Missing backup {i}"

        # bak.6 should NOT exist (keep=5)
        bak6 = path.with_name("registry.bak.6.json")
        assert not bak6.exists()

    def test_most_recent_is_bak_1(self, tmp_path):
        path = tmp_path / "registry.json"

        path.write_text('{"version": "first"}')
        backup_rotate(path, keep=5)

        path.write_text('{"version": "second"}')
        backup_rotate(path, keep=5)

        bak1 = json.loads(path.with_name("registry.bak.1.json").read_text())
        assert bak1["version"] == "second"

    def test_skips_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.json"

        # Should not crash
        backup_rotate(path, keep=5)
