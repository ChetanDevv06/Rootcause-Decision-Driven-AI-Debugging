"""Test that reproduces the dependency version conflict failure."""

import importlib.metadata


def test_shared_lib_not_installed():
    """Verify shared-lib is not installed in the test environment."""
    try:
        importlib.metadata.version("shared-lib")
        raise AssertionError("Expected PackageNotFoundError but version resolved")
    except importlib.metadata.PackageNotFoundError:
        pass


def test_app_raises_dependency_conflict():
    """Verify running the application raises a dependency conflict error."""
    import app  # noqa: F401

    try:
        app.main()  # top-level import is safe; main() raises the conflict
        raise AssertionError("Expected RuntimeError but main() succeeded")
    except RuntimeError as exc:
        assert "Dependency conflict" in str(exc)
        assert "shared-lib" in str(exc)


def test_error_mentions_version_constraints():
    """Verify the error message identifies the conflicting constraints."""
    import app  # noqa: F401

    try:
        app.main()
    except RuntimeError as exc:
        message = str(exc)
        assert ">=2.0" in message
        assert "<1.0" in message


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_shared_lib_not_installed()
        print("PASS: test_shared_lib_not_installed")
    except AssertionError as e:
        print(f"FAIL: test_shared_lib_not_installed - {e}")
        raise SystemExit(1)

    try:
        test_app_raises_dependency_conflict()
        print("PASS: test_app_raises_dependency_conflict")
    except AssertionError as e:
        print(f"FAIL: test_app_raises_dependency_conflict - {e}")
        raise SystemExit(1)

    try:
        test_error_mentions_version_constraints()
        print("PASS: test_error_mentions_version_constraints")
    except AssertionError as e:
        print(f"FAIL: test_error_mentions_version_constraints - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
