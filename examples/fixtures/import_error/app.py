"""Application with an incorrect Python import.

The module `nonexistent_local_module` does not exist anywhere on the import
path, so importing it raises a ModuleNotFoundError.
"""

import nonexistent_local_module  # noqa: F401


def main() -> None:
    """Main entry point - never reached because the import fails."""
    print("imported nonexistent_local_module")


if __name__ == "__main__":
    main()
