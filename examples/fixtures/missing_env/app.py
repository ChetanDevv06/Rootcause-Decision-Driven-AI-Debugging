"""Application that requires a DATABASE_URL environment variable.

The application reads DATABASE_URL from the environment and raises a clear
RuntimeError when it is not set. No real database connection is attempted.
"""

import os


def main() -> None:
    """Main entry point - fails when DATABASE_URL is not configured."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Missing environment variable: DATABASE_URL is not set. "
            "Configure DATABASE_URL (e.g. postgresql://localhost:5432/mydb) "
            "before running the application."
        )
    print(f"Connected to {database_url}")


if __name__ == "__main__":
    main()
