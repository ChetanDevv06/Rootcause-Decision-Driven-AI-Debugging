"""Test that reproduces the missing environment variable failure."""

import os


def test_database_url_not_set():
    """Verify DATABASE_URL is not set in the test environment."""
    assert "DATABASE_URL" not in os.environ, "DATABASE_URL should not be set"


def test_app_raises_missing_env():
    """Verify running the application raises RuntimeError when DATABASE_URL missing."""
    os.environ.pop("DATABASE_URL", None)
    import app  # noqa: F401

    try:
        app.main()
        raise AssertionError("Expected RuntimeError but main() succeeded")
    except RuntimeError as exc:
        assert "DATABASE_URL" in str(exc)
        assert "not set" in str(exc)


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_database_url_not_set()
        print("PASS: test_database_url_not_set")
    except AssertionError as e:
        print(f"FAIL: test_database_url_not_set - {e}")
        raise SystemExit(1)

    try:
        test_app_raises_missing_env()
        print("PASS: test_app_raises_missing_env")
    except AssertionError as e:
        print(f"FAIL: test_app_raises_missing_env - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
    print("Expected failure: RuntimeError: Missing environment variable: DATABASE_URL is not set.")
