"""Simple calculator with an intentional implementation defect.

The `add` function subtracts instead of adding, so any test asserting
`add(2, 3) == 5` will fail.
"""


def add(a: int, b: int) -> int:
    """Return the sum of a and b.

    Defect: currently returns `a - b` instead of `a + b`.
    """
    return a - b  # BUG: should be a + b


def main() -> None:
    """Main entry point."""
    result = add(2, 3)
    print(f"2 + 3 = {result}")


if __name__ == "__main__":
    main()
