"""Test that reproduces the failing unit test failure."""

import subprocess
import sys


def test_add_returns_wrong_value():
    """Verify add(2, 3) returns -1 instead of 5."""
    from calculator import add
    result = add(2, 3)
    assert result == -1, f"Expected -1 (defective), got {result}"


def test_pytest_reports_failure():
    """Verify pytest reports test_calculator.py as failed."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "test_calculator.py", "-v"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0, "Expected pytest to exit non-zero"
    assert "test_add" in result.stdout or "test_add" in result.stderr
    assert "FAILED" in result.stdout or "FAILED" in result.stderr


if __name__ == "__main__":
    print("Running fixture reproduction tests...")

    try:
        test_add_returns_wrong_value()
        print("PASS: test_add_returns_wrong_value")
    except AssertionError as e:
        print(f"FAIL: test_add_returns_wrong_value - {e}")
        raise SystemExit(1)

    try:
        test_pytest_reports_failure()
        print("PASS: test_pytest_reports_failure")
    except AssertionError as e:
        print(f"FAIL: test_pytest_reports_failure - {e}")
        raise SystemExit(1)

    print("\nAll reproduction tests passed!")
    print("Expected failure: AssertionError - Expected 5, got -1")
