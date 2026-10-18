"""Application that reads a data file using an incorrect relative path.

The program attempts to open `nonexistent_data.txt`, which does not exist in
the project directory, raising a FileNotFoundError.
"""


def main() -> None:
    """Main entry point - fails when the data file path is incorrect."""
    with open("nonexistent_data.txt", "r", encoding="utf-8") as fh:
        data = fh.read()
    print(f"Loaded {len(data)} bytes of data")


if __name__ == "__main__":
    main()
