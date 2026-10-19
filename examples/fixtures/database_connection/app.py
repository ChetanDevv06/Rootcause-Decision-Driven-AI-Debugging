import socket


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", 54321))
    except OSError as exc:
        sock.close()
        raise RuntimeError(
            "Database connection failure: could not connect to "
            "127.0.0.1:54321 (connection refused). Verify the database host, "
            "port, and that the database server is running."
        ) from exc
    finally:
        sock.close()

    print("Database connection established")


if __name__ == "__main__":
    main()
