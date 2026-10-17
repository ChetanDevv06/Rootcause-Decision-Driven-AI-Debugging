"""Sample application that requires psycopg for PostgreSQL connectivity."""

import psycopg


def connect_to_database(dsn: str) -> psycopg.Connection:
    """Establish a connection to PostgreSQL using the provided DSN."""
    return psycopg.connect(dsn)


def fetch_users(conn: psycopg.Connection) -> list[dict]:
    """Fetch all users from the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, email FROM users")
        return [{"id": row[0], "name": row[1], "email": row[2]} for row in cur.fetchall()]


def main() -> None:
    """Main entry point - attempts to connect to database."""
    dsn = "postgresql://user:pass@localhost:5432/mydb"
    conn = connect_to_database(dsn)
    try:
        users = fetch_users(conn)
        for user in users:
            print(f"User: {user['name']} ({user['email']})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()