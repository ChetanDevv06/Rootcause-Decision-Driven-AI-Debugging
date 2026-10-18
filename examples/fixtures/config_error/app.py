"""Application that loads a JSON configuration file.

The config file (`config.json`) is intentionally malformed (truncated, missing
closing braces), so `json.load` raises a `json.JSONDecodeError`.
"""

import json


def main() -> None:
    """Main entry point - fails when config.json cannot be parsed."""
    with open("config.json", "r", encoding="utf-8") as fh:
        config = json.load(fh)
    print(f"Loaded config: {config}")


if __name__ == "__main__":
    main()
