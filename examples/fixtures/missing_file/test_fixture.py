"""Test that reproduces the incorrect file path failure."""

import os


def test_data_file_does_not_exist():
    """Verify nonexistent_data.txt does not exist in the fixture directory."""
    assert not os.path.exists("nonexistent_data.txt")


def test_app_raises_file_not_found():
    """Verify running the application raises FileNotFoundError for the bad path."""
    import app  # noqa: F401

    try:
        app.main()
        raise AssertionError("Expected FileNotFoundError but main() succeeded")
    except FileNotFoundError as exc:
        assert "nonexistent_data.txt" in str(exc)


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_data_file_does_not_exist()
        print("PASS: test_data_file_does_not_exist")
    except AssertionError as e:
        print(f"FAIL: test_data_file_does_not_exist - {e}")
        raise SystemExit(1)

    try:
        test_app_raises_file_not_found()
        print("PASS: test_app_raises_file_not_found")
    except AssertionError as e:
        print(f"FAIL: test_app_raises_file_not_found - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
    print("Expected failure: FileNotFoundError: No such file or directory: 'nonexistent_data.txt'")
