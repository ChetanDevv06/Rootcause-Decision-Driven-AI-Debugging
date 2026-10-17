"""Test that reproduces the missing psycopg dependency failure."""

import importlib.util
import sys


def test_missing_psycopg_raises_import_error():
    """Verify that importing psycopg fails when not installed."""
    spec = importlib.util.find_spec("psycopg")
    assert spec is None, "psycopg should not be installed in the test environment"

    try:
        import psycopg  # noqa: F401
        raise AssertionError("Expected ImportError but import succeeded")
    except ImportError as exc:
        assert "No module named 'psycopg'" in str(exc)
        assert exc.name == "psycopg"


def test_app_module_import_fails_without_psycopg():
    """Verify the application module cannot be imported without psycopg."""
    # The app module imports psycopg at module level
    try:
        import app  # noqa: F401
        raise AssertionError("Expected ImportError but import succeeded")
    except ImportError as exc:
        assert "No module named 'psycopg'" in str(exc)


def test_error_message_contains_module_name():
    """Verify the error message identifies the missing module."""
    try:
        import psycopg  # noqa: F401
    except ImportError as exc:
        assert "psycopg" in str(exc).lower()


if __name__ == "__main__":
    # Run tests manually without pytest
    print("Running fixture reproduction tests...")
    
    try:
        test_missing_psycopg_raises_import_error()
        print("PASS: test_missing_psycopg_raises_import_error")
    except AssertionError as e:
        print(f"FAIL: test_missing_psycopg_raises_import_error - {e}")
        sys.exit(1)
    
    try:
        test_app_module_import_fails_without_psycopg()
        print("PASS: test_app_module_import_fails_without_psycopg")
    except AssertionError as e:
        print(f"FAIL: test_app_module_import_fails_without_psycopg - {e}")
        sys.exit(1)
    
    try:
        test_error_message_contains_module_name()
        print("PASS: test_error_message_contains_module_name")
    except AssertionError as e:
        print(f"FAIL: test_error_message_contains_module_name - {e}")
        sys.exit(1)
    
    print("\nAll reproduction tests passed!")
    print("Expected failure: ModuleNotFoundError: No module named 'psycopg'")