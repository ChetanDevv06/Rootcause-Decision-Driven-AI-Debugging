"""Test that reproduces the incorrect Python import failure."""

import importlib.util


def test_module_not_installed():
    """Verify nonexistent_local_module is not importable."""
    spec = importlib.util.find_spec("nonexistent_local_module")
    assert spec is None, "nonexistent_local_module should not be importable"

    try:
        import nonexistent_local_module  # noqa: F401
        raise AssertionError("Expected ImportError but import succeeded")
    except ImportError as exc:
        assert "No module named 'nonexistent_local_module'" in str(exc)


def test_app_module_import_fails():
    """Verify the application module cannot be imported."""
    try:
        import app  # noqa: F401
        raise AssertionError("Expected ImportError but import succeeded")
    except ImportError as exc:
        assert "nonexistent_local_module" in str(exc)


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_module_not_installed()
        print("PASS: test_module_not_installed")
    except AssertionError as e:
        print(f"FAIL: test_module_not_installed - {e}")
        raise SystemExit(1)

    try:
        test_app_module_import_fails()
        print("PASS: test_app_module_import_fails")
    except AssertionError as e:
        print(f"FAIL: test_app_module_import_fails - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
    print("Expected failure: ModuleNotFoundError: No module named 'nonexistent_local_module'")
