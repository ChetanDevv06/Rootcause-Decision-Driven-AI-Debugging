"""Test suite for the calculator.

test_add asserts that add(2, 3) == 5, which fails because the implementation
subtracts instead of adding.
"""

from calculator import add


def test_add():
    """add(2, 3) should equal 5."""
    assert add(2, 3) == 5, f"Expected 5, got {add(2, 3)}"


def test_add_negative():
    """add(-1, 1) should equal 0."""
    assert add(-1, 1) == 0
