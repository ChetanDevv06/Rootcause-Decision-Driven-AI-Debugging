"""Tests for the missing_dependency fixture."""

from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).parent.parent / "examples" / "fixtures" / "missing_dependency"


def test_fixture_directory_exists():
    """Verify the fixture directory exists."""
    assert FIXTURE_DIR.is_dir(), f"Fixture directory not found: {FIXTURE_DIR}"


def test_fixture_has_requirements():
    """Verify the fixture has a requirements.txt with psycopg."""
    req_file = FIXTURE_DIR / "requirements.txt"
    assert req_file.is_file(), "requirements.txt not found"
    content = req_file.read_text(encoding="utf-8")
    assert "psycopg" in content, "requirements.txt should declare psycopg"


def test_fixture_has_app():
    """Verify the fixture has an app.py that imports psycopg."""
    app_file = FIXTURE_DIR / "app.py"
    assert app_file.is_file(), "app.py not found"
    content = app_file.read_text(encoding="utf-8")
    assert "import psycopg" in content, "app.py should import psycopg"


def test_fixture_has_test():
    """Verify the fixture has a reproduction test."""
    test_file = FIXTURE_DIR / "test_fixture.py"
    assert test_file.is_file(), "test_fixture.py not found"
    content = test_file.read_text(encoding="utf-8")
    assert "test_missing_psycopg_raises_import_error" in content
    assert "test_app_module_import_fails_without_psycopg" in content


def test_fixture_has_readme():
    """Verify the fixture has documentation."""
    readme_file = FIXTURE_DIR / "README.md"
    assert readme_file.is_file(), "README.md not found"
    content = readme_file.read_text(encoding="utf-8")
    assert "ModuleNotFoundError" in content
    assert "psycopg" in content
    assert "requirements.txt" in content


def test_fixture_reproduction_works():
    """Verify the fixture's test reproduces the expected failure."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "test_fixture.py"],
        cwd=FIXTURE_DIR,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Fixture test failed: {result.stderr}"
    assert "PASS: test_missing_psycopg_raises_import_error" in result.stdout
    assert "PASS: test_app_module_import_fails_without_psycopg" in result.stdout
    assert "PASS: test_error_message_contains_module_name" in result.stdout
    assert "ModuleNotFoundError: No module named 'psycopg'" in result.stdout


def test_fixture_is_discoverable_by_rootcause():
    """Verify Rootcause can target the fixture directory."""
    from src.config import TargetProjectConfig

    config = TargetProjectConfig(str(FIXTURE_DIR))
    assert config.root == FIXTURE_DIR.resolve()
    assert config.root.is_dir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])