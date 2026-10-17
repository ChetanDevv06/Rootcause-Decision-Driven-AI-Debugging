from pathlib import Path

from src.diagnostics import inspect_dependencies


def test_inspect_dependencies_reads_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text(
        "psycopg[binary]>=3.2\n",
        encoding="utf-8",
    )

    result = inspect_dependencies(str(tmp_path))

    assert result["action"] == "inspect_dependencies"
    assert "requirements.txt" in result["files_found"]
    assert "psycopg" in result["files_found"]["requirements.txt"]


def test_inspect_dependencies_handles_missing_directory():
    result = inspect_dependencies("Z:/rootcause_missing_test_directory")

    assert "error" in result